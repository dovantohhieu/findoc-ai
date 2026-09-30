from __future__ import annotations
import os
from typing import Literal

from pydantic import BaseModel, Field

from findoc.agent.llm import chat_model
from findoc.query_parse import parse_filters

AGG_WORDS = ("tổng cộng", "tổng số", "cộng lại", "bao nhiêu hóa đơn", "bao nhiêu hoá đơn",
             "số lượng hóa đơn", "trung bình", "nhiều nhất", "lớn nhất", "cao nhất")
PLURAL = ("các hóa đơn", "các hoá đơn", "những hóa đơn", "tất cả hóa đơn", "tất cả các")


def rule_route(q: str, f: dict) -> str | None:
    ql = q.lower()
    if f.get("invoice_no"):
        return "lookup"          # hỏi về MỘT hóa đơn cụ thể, kể cả khi có chữ "tổng"
    if any(w in ql for w in AGG_WORDS):
        return "aggregate"
    if "tổng" in ql and any(p in ql for p in PLURAL):
        return "aggregate"
    return None                  # luật không chắc → để LLM quyết


class RouteOut(BaseModel):
    route: Literal["lookup", "out_of_scope"] = Field(
        description="lookup nếu hỏi về nội dung chứng từ tài chính; out_of_scope nếu không liên quan")


ROUTE_PROMPT = """Bạn phân loại câu hỏi gửi tới hệ thống tra cứu hóa đơn, hợp đồng, chứng từ tài chính.
- lookup: hỏi về nội dung chứng từ (số tiền, mặt hàng, bên mua, bên bán, MST, ngày, điều khoản).
- out_of_scope: chào hỏi, thời tiết, kiến thức chung, hoặc thứ không thể tra từ chứng từ.
Câu hỏi: {q}"""


def classify(state: dict) -> dict:
    q = state["question"]
    f = parse_filters(q)
    route = rule_route(q, f)
    if route:
        return {"route": route, "route_by": "rule", "filters": f}
    out = chat_model().with_structured_output(RouteOut).invoke(ROUTE_PROMPT.format(q=q))
    return {"route": out.route, "route_by": "llm", "filters": f}
from findoc.answer import SYSTEM, build_prompt, check_citations
from findoc.search import hybrid_search

RERANK_N = int(os.getenv("FINDOC_RERANK_N", "10"))
NO_ANSWER = "Không tìm thấy thông tin trong tài liệu."
EMPTY_CITES = {"used": [], "invalid": [], "coverage": 1.0, "n_sentences": 1}


def _plain(r: dict) -> dict:
    """State phải lưu được vào Postgres: đổi date → chuỗi."""
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in r.items()}


def retrieve(state: dict) -> dict:
    debug: dict = {}
    rows = hybrid_search(state["question"], top_k=5, filters=state.get("filters"),
                         use_reranker=RERANK_N > 0, rerank_n=max(RERANK_N, 5),
                         log=False, debug=debug)
    return {"rows": [_plain(r) for r in rows], "debug": debug}


def _text(msg) -> str:
    c = msg.content
    return c if isinstance(c, str) else "".join(b.get("text", "") for b in c if isinstance(b, dict))


def generate(state: dict) -> dict:
    rows = state.get("rows") or []
    if not rows:
        return {"answer": NO_ANSWER, "citations": EMPTY_CITES}
    msg = chat_model().invoke([("system", SYSTEM), ("user", build_prompt(state["question"], rows))])
    text = _text(msg)
    return {"answer": text, "citations": check_citations(text, len(rows))}
from findoc.agent.aggregate import run_aggregate

REFUSAL = "Câu hỏi này nằm ngoài phạm vi tra cứu chứng từ tài chính của hệ thống."


def aggregate(state: dict) -> dict:
    agg = run_aggregate(state.get("filters") or {})
    return {"agg": agg, "answer": agg["text"], "citations": EMPTY_CITES}


def refuse(state: dict) -> dict:
    return {"answer": REFUSAL, "citations": EMPTY_CITES}
from findoc.agent.checks import ungrounded_numbers
from findoc.confidence import classify as retrieval_confidence

REVIEW_LEVELS = set(os.getenv("FINDOC_REVIEW_LEVELS", "low").split(","))


def validate(state: dict) -> dict:
    route = state["route"]
    if route == "out_of_scope":
        return {"checks": {}, "confidence": {"level": "high", "reasons": []}}

    if route == "aggregate":
        f, agg = state.get("filters") or {}, state["agg"]
        reasons, level = [], "high"
        if not (f.get("mst") or f.get("date_from")):
            level = "low"
            reasons.append("câu hỏi tổng hợp nhưng không nêu MST hay khoảng thời gian — có thể hiểu sai phạm vi")
        if agg["n"] == 0:
            level = "medium" if level == "high" else level
            reasons.append("không có hóa đơn nào khớp bộ lọc")
        return {"checks": {"n": agg["n"]}, "confidence": {"level": level, "reasons": reasons}}

    # nhánh lookup
    rows = state.get("rows") or []
    answer, cites = state.get("answer", ""), state.get("citations") or {}
    base = retrieval_confidence(rows, answer, cites)
    level, reasons = base["level"], []
    bad = ungrounded_numbers(answer, " ".join(r["text"] for r in rows))
    if bad:
        level = "low"
        reasons.append("có số không xuất hiện trong nguồn: " + ", ".join(f"{x:,}".replace(",", ".") for x in bad[:3]))
    if cites.get("invalid"):
        level = "low"
        reasons.append("trích dẫn trỏ ra ngoài danh sách nguồn")
    if level == "medium":
        reasons.append("điểm liên quan của nguồn tốt nhất chỉ ở mức trung bình")
    if level == "low" and not reasons:
        reasons.append("điểm liên quan của nguồn tốt nhất thấp")
    return {"checks": {"ungrounded": bad, "top_score": base.get("top_score")},
            "confidence": {"level": level, "reasons": reasons}}


def after_validate(state: dict) -> str:
    return "review" if state["confidence"]["level"] in REVIEW_LEVELS else "done"


def finalize(state: dict) -> dict:
    return {"status": "answered"}
