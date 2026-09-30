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
