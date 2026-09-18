from __future__ import annotations
import time
from findoc.db import connect
from findoc.embed import embed
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
