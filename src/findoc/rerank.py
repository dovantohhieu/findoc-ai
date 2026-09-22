from __future__ import annotations
from functools import lru_cache
from FlagEmbedding import FlagReranker

MODEL_NAME = "BAAI/bge-reranker-v2-m3"


@lru_cache(maxsize=1)
def get_reranker() -> FlagReranker:
    return FlagReranker(MODEL_NAME, use_fp16=True)


def rerank(question: str, rows: list[dict], top_k: int = 5) -> list[dict]:
    if not rows:
        return []
    pairs = [[question, r["text"]] for r in rows]
    scores = get_reranker().compute_score(pairs, normalize=True)   # sigmoid → 0..1
    if isinstance(scores, float):
        scores = [scores]
    for r, s in zip(rows, scores):
        r["rerank_score"] = float(s)
        r["score"] = float(s)          # score hiển thị = điểm reranker
    rows.sort(key=lambda r: -r["rerank_score"])
    return rows[:top_k]

