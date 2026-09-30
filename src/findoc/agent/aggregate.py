from __future__ import annotations
from findoc.db import connect
from findoc.search import _build_where


def _money(x) -> str:
    return f"{int(x):,}".replace(",", ".")


def _describe(f: dict) -> str:
    parts = []
    if f.get("mst"):
        parts.append(f"của MST {f['mst']}")
    if f.get("date_from") and f.get("date_to"):
        parts.append(f"từ {f['date_from']} đến {f['date_to']}")
    return " ".join(parts) or "trong toàn bộ dữ liệu"


def run_aggregate(f: dict) -> dict:
    where, params = _build_where(f)
    sql = f"""SELECT count(*), coalesce(sum(total), 0), coalesce(sum(vat_amount), 0),
                     coalesce(max(total), 0),
                     coalesce(array_agg(doc_id ORDER BY total DESC NULLS LAST), '{{}}')
              FROM documents WHERE {where};"""
    with connect() as c, c.cursor() as cur:
        cur.execute(sql, params)
        n, total, vat, biggest, ids = cur.fetchone()
    n, total, vat, biggest = int(n), int(total), int(vat), int(biggest)
    desc = _describe(f)
    if n == 0:
        text = f"Không tìm thấy hóa đơn nào {desc}."
    else:
        text = (f"Có {n} hóa đơn {desc}. Tổng tiền thanh toán {_money(total)} VND, "
                f"trong đó thuế GTGT {_money(vat)} VND. Trung bình {_money(total / n)} VND "
                f"mỗi hóa đơn; lớn nhất là {ids[0]} với {_money(biggest)} VND.")
    return {"n": n, "total": total, "vat": vat, "doc_ids": list(ids), "text": text}
