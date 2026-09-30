from __future__ import annotations
import re
from findoc.search import hybrid_search

CITE_RE = re.compile(r"\[(\d+)\]")

SYSTEM = """Bạn trả lời câu hỏi về tài liệu tài chính tiếng Việt.

Quy tắc bắt buộc:
- CHỈ dùng thông tin trong các đoạn được cung cấp. Không suy đoán, không bổ sung kiến thức ngoài.
- Mỗi câu khẳng định phải kèm trích dẫn dạng [1], [2] trỏ tới đoạn nguồn.
- Nếu các đoạn không đủ để trả lời, nói đúng một câu: "Không tìm thấy thông tin trong tài liệu."
- Trả lời ngắn gọn, giữ nguyên con số và đơn vị như trong tài liệu."""


def build_prompt(question: str, rows: list[dict]) -> str:
    ctx = "\n\n".join(f"[{i}] {r['text']}" for i, r in enumerate(rows, start=1))
    return f"{ctx}\n\nCâu hỏi: {question}"


def check_citations(answer: str, n_contexts: int) -> dict:
    used = [int(m) for m in CITE_RE.findall(answer)]
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", answer.strip()) if s]
    cited = sum(1 for s in sentences if CITE_RE.search(s))
    return {
        "used": sorted(set(used)),
        "invalid": sorted({u for u in used if not 1 <= u <= n_contexts}),
        "coverage": round(cited / max(len(sentences), 1), 3),
        "n_sentences": len(sentences),
    }


def answer(question: str, top_k: int = 5, llm=None) -> dict:
    rows = hybrid_search(question, top_k=top_k, use_reranker=True, log=False)
    prompt = build_prompt(question, rows)
    text = llm(SYSTEM, prompt) if llm else "(chưa nối LLM)"
    return {
        "question": question,
        "answer": text,
        "contexts": [r["text"] for r in rows],
        "doc_ids": [r["doc_id"] for r in rows],
        "citations": check_citations(text, len(rows)),
    }
