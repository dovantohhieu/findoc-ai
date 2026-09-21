from __future__ import annotations
import pathlib, pickle
from rank_bm25 import BM25Okapi
from findoc.db import connect
from findoc.vitoken import tokenize

INDEX_PATH = pathlib.Path("data/bm25.pkl")
_CACHE: dict | None = None


def build_index(path: pathlib.Path = INDEX_PATH) -> int:
    with connect() as c, c.cursor() as cur:
        cur.execute("SELECT id, text FROM chunks ORDER BY id;")
        rows = cur.fetchall()
    ids = [r[0] for r in rows]
    corpus = [tokenize(r[1]) for r in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump({"ids": ids, "bm25": BM25Okapi(corpus)}, f)
    return len(ids)


def load_index(path: pathlib.Path = INDEX_PATH) -> dict:
    global _CACHE
    if _CACHE is None:
        with path.open("rb") as f:
            _CACHE = pickle.load(f)
    return _CACHE


def bm25_search(question: str, top_n: int = 50) -> list[tuple[int, float]]:
    """Trả về [(chunk_id, score)] xếp giảm dần, đã bỏ score = 0."""
    idx = load_index()
    scores = idx["bm25"].get_scores(tokenize(question))
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
    return [(idx["ids"][i], float(scores[i])) for i in order if scores[i] > 0]


if __name__ == "__main__":
    print("đã index", build_index(), "chunks")
