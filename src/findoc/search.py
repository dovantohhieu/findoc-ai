from __future__ import annotations
import time
from findoc.db import connect
from findoc.embed import embed
from findoc.qlog import log_query
# from findoc.qlog import log_query      # mở comment ở Bước 24

SQL = """
SELECT id, doc_id, chunk_index, text, doc_type, mst, invoice_no, issue_date,
       1 - (embedding <=> %s) AS score
FROM chunks
WHERE {where}
ORDER BY embedding <=> %s
LIMIT %s;
"""

COLS = ["id", "doc_id", "chunk_index", "text", "doc_type",
        "mst", "invoice_no", "issue_date", "score"]

from findoc.fusion import rrf_fuse


def hybrid_search(question: str, top_k: int = 5, filters: dict | None = None,
                  candidates: int = 50, rerank_n: int = 20,
                  use_reranker: bool = False, log: bool = True) -> list[dict]:
    import time
    t0 = time.perf_counter()
    f = {**parse_filters(question), **(filters or {})}

    dense_ids = [r["id"] for r in search(question, top_k=candidates,
                                         filters=f, ef_search=200, log=False)]
    lex_ids = _filter_ids([cid for cid, _ in bm25_search(question, top_n=candidates)], f)

    fused = rrf_fuse([dense_ids, lex_ids], k=60, top_k=rerank_n)
    rows = fetch_chunks([cid for cid, _ in fused])
    rrf = dict(fused)
    for r in rows:
        r["score"] = rrf[r["id"]]

    if use_reranker:
        from findoc.rerank import rerank
        rows = rerank(question, rows, top_k=top_k)
    else:
        rows = rows[:top_k]

    if log:
        log_query(question, f, rows, (time.perf_counter() - t0) * 1000, top_k,
                  extra={"mode": "hybrid_rerank" if use_reranker else "hybrid_rrf",
                         "n_dense": len(dense_ids), "n_lexical": len(lex_ids)})
    return rows
def _build_where(f: dict) -> tuple[str, list]:
    clauses, params = ["TRUE"], []
    if f.get("mst"):
        clauses.append("mst = %s"); params.append(f["mst"])
    if f.get("doc_type"):
        clauses.append("doc_type = %s"); params.append(f["doc_type"])
    if f.get("invoice_no"):
        clauses.append("invoice_no = %s"); params.append(f["invoice_no"])
    if f.get("date_from"):
        clauses.append("issue_date >= %s"); params.append(f["date_from"])
    if f.get("date_to"):
        clauses.append("issue_date <= %s"); params.append(f["date_to"])
    return " AND ".join(clauses), params


def search(question: str, top_k: int = 5, filters: dict | None = None,
           ef_search: int = 100, log: bool = True) -> list[dict]:
    filters = filters or {}
    qv = embed([question])[0]
    where, wparams = _build_where(filters)

    t0 = time.perf_counter()
    with connect() as conn, conn.cursor() as cur:
        cur.execute(f"SET LOCAL hnsw.ef_search = {int(ef_search)};")
        # thứ tự tham số: SELECT trước, rồi WHERE, rồi ORDER BY, rồi LIMIT
        cur.execute(SQL.format(where=where), [qv, *wparams, qv, top_k])
        rows = [dict(zip(COLS, r)) for r in cur.fetchall()]
    latency_ms = (time.perf_counter() - t0) * 1000

    # if log:
    #     log_query(question, filters, rows, latency_ms, top_k)
    return rows
from findoc.query_parse import parse_filters


def smart_search(question: str, top_k: int = 5, **kw) -> list[dict]:
    """Tự trích filter từ câu hỏi rồi mới tìm."""
    auto = parse_filters(question)
    merged = {**auto, **(kw.pop("filters", None) or {})}   # filter truyền tay thắng
    selective = bool(merged.get("mst") or merged.get("invoice_no"))
    return search(question, top_k=top_k, filters=merged,
                  ef_search=100 if selective else 200, **kw)

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "tổng tiền thanh toán là bao nhiêu"
    for r in search(q):
        print(f"{r['score']:.3f}  {r['doc_id']}#{r['chunk_index']}  {r['text'][:90]}…")


# ── BM25 (tuần 6) ────────────────────────────────────────────────
from findoc.bm25 import bm25_search


def _filter_ids(ids: list[int], f: dict) -> list[int]:
    """Giữ nguyên thứ tự xếp hạng, bỏ các chunk không thỏa filter."""
    if not ids or not f:
        return ids
    where, params = _build_where(f)
    with connect() as c, c.cursor() as cur:
        cur.execute(f"SELECT id FROM chunks WHERE id = ANY(%s) AND {where}",
                    [ids] + params)
        keep = {r[0] for r in cur.fetchall()}
    return [i for i in ids if i in keep]


def fetch_chunks(ids: list[int]) -> list[dict]:
    """Lấy nội dung chunk, giữ ĐÚNG thứ tự của `ids`."""
    if not ids:
        return []
    with connect() as c, c.cursor() as cur:
        cur.execute("SELECT id, doc_id, chunk_index, text, doc_type, mst, "
                    "issue_date, invoice_no FROM chunks WHERE id = ANY(%s)", [ids])
        cols = [d.name for d in cur.description]
        theo_id = {r[0]: dict(zip(cols, r)) for r in cur.fetchall()}
    return [theo_id[i] for i in ids if i in theo_id]


def lexical_search(question: str, top_k: int = 5,
                   filters: dict | None = None, **kw) -> list[dict]:
    """BM25 đơn lẻ, có áp metadata filter. Cùng chữ ký với search()."""
    if filters is None:
        filters = parse_filters(question)
    ids = [cid for cid, _ in bm25_search(question, top_n=200)]
    ids = _filter_ids(ids, filters or {})
    return fetch_chunks(ids[:top_k * 10])


# ── BM25 (tuần 6) ────────────────────────────────────────────────
from findoc.bm25 import bm25_search


def _filter_ids(ids: list[int], f: dict) -> list[int]:
    """Giữ nguyên thứ tự xếp hạng, bỏ các chunk không thỏa filter."""
    if not ids or not f:
        return ids
    where, params = _build_where(f)
    with connect() as c, c.cursor() as cur:
        cur.execute(f"SELECT id FROM chunks WHERE id = ANY(%s) AND {where}",
                    [ids] + params)
        keep = {r[0] for r in cur.fetchall()}
    return [i for i in ids if i in keep]


def fetch_chunks(ids: list[int]) -> list[dict]:
    """Lấy nội dung chunk, giữ ĐÚNG thứ tự của `ids`."""
    if not ids:
        return []
    with connect() as c, c.cursor() as cur:
        cur.execute("SELECT id, doc_id, chunk_index, text, doc_type, mst, "
                    "issue_date, invoice_no FROM chunks WHERE id = ANY(%s)", [ids])
        cols = [d.name for d in cur.description]
        theo_id = {r[0]: dict(zip(cols, r)) for r in cur.fetchall()}
    return [theo_id[i] for i in ids if i in theo_id]


def lexical_search(question: str, top_k: int = 5,
                   filters: dict | None = None, **kw) -> list[dict]:
    """BM25 đơn lẻ, có áp metadata filter. Cùng chữ ký với search()."""
    if filters is None:
        filters = parse_filters(question)
    ids = [cid for cid, _ in bm25_search(question, top_n=200)]
    ids = _filter_ids(ids, filters or {})
    return fetch_chunks(ids[:top_k * 10])
