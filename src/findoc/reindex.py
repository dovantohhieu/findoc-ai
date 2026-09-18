from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path

from findoc.db import connect
from findoc.embed import embed
from findoc.chunk import chunk_invoice, chunk_text, with_context

def _dtype(doc: dict) -> str:
    """vat_invoice / sales_invoice -> invoice (khớp schema)."""
    t = doc.get("doc_type") or "doc"
    return "invoice" if t.endswith("invoice") else t


UPSERT_DOC = """
INSERT INTO documents (doc_id, doc_type, mst, buyer_mst, issue_date, invoice_no,
                       source_path, content_hash, n_chunks, indexed_at)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
ON CONFLICT (doc_id) DO UPDATE SET
  doc_type=EXCLUDED.doc_type, mst=EXCLUDED.mst, buyer_mst=EXCLUDED.buyer_mst,
  issue_date=EXCLUDED.issue_date, invoice_no=EXCLUDED.invoice_no,
  source_path=EXCLUDED.source_path, content_hash=EXCLUDED.content_hash,
  n_chunks=EXCLUDED.n_chunks, indexed_at=now();
"""

INSERT_CHUNK = """
INSERT INTO chunks (doc_id, chunk_index, text, n_chars, embedding,
                    doc_type, mst, issue_date, invoice_no)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);
"""


def content_hash(doc: dict) -> str:
    payload = json.dumps(doc, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def build_chunks(doc: dict) -> list[str]:
    meta = {
        "doc_type": _dtype(doc),
        "invoice_no": doc.get("invoice_no"),
        "issue_date": doc.get("issue_date"),
        "mst": doc.get("seller_mst"),
    }
    raw = chunk_invoice(doc) if _dtype(doc) == "invoice" \
        else chunk_text(doc.get("text", ""))
    return [with_context(c, meta) for c in raw]


def load_docs(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="data/processed/docs.jsonl")
    ap.add_argument("--full", action="store_true", help="xóa sạch và index lại")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    docs = load_docs(Path(args.source))
    if args.limit:
        docs = docs[: args.limit]

    t0 = time.perf_counter()
    n_docs = n_chunks = n_skip = 0

    with connect() as conn, conn.cursor() as cur:
        if args.full:
            cur.execute("TRUNCATE chunks, documents RESTART IDENTITY CASCADE;")
            print("[full] đã xóa sạch chunks + documents")

        cur.execute("SELECT doc_id, content_hash FROM documents;")
        known = dict(cur.fetchall())

        for doc in docs:
            doc_id = doc["doc_id"]
            h = content_hash(doc)
            if known.get(doc_id) == h:
                n_skip += 1
                continue

            texts = build_chunks(doc)
            if not texts:
                continue
            vecs = embed(texts, batch_size=args.batch_size)

            cur.execute(UPSERT_DOC, (
                doc_id, _dtype(doc), doc.get("seller_mst"),
                doc.get("buyer_mst"), doc.get("issue_date"), doc.get("invoice_no"),
                doc.get("source_path"), h, len(texts),
            ))
            cur.execute("DELETE FROM chunks WHERE doc_id = %s;", (doc_id,))
            cur.executemany(INSERT_CHUNK, [
                (doc_id, i, t, len(t), vecs[i],
                 _dtype(doc), doc.get("seller_mst"),
                 doc.get("issue_date"), doc.get("invoice_no"))
                for i, t in enumerate(texts)
            ])
            n_docs += 1
            n_chunks += len(texts)

        conn.commit()

    dt = time.perf_counter() - t0
    print(f"docs mới/đổi : {n_docs}")
    print(f"docs bỏ qua  : {n_skip}")
    print(f"chunks ghi   : {n_chunks}")
    print(f"thời gian    : {dt:.2f}s  ({n_chunks / max(dt, 1e-9):.1f} chunks/s)")


if __name__ == "__main__":
    main()

