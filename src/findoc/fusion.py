from __future__ import annotations


def rrf_fuse(rankings: list[list[int]], k: int = 60,
             top_k: int = 20, weights: list[float] | None = None) -> list[tuple[int, float]]:
    """Trộn nhiều danh sách đã xếp hạng. Đầu vào là id theo thứ tự, KHÔNG phải score."""
    weights = weights or [1.0] * len(rankings)
    scores: dict[int, float] = {}
    for ranking, w in zip(rankings, weights):
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + w / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])[:top_k]


if __name__ == "__main__":
    dense = [101, 103, 102]
    lexical = [103, 105, 101]
    for cid, s in rrf_fuse([dense, lexical], top_k=5):
        print(f"chunk {cid}: {s:.5f}")
