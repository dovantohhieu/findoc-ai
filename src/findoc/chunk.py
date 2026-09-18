from __future__ import annotations
import re
from dataclasses import dataclass
from itertools import islice


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def chunk_text(text: str, max_chars: int = 900, overlap: int = 150) -> list[str]:
    """Cắt văn bản dài (hợp đồng, phụ lục) theo ranh giới đoạn, có overlap."""
    chunks: list[str] = []
    buf = ""

    def flush():
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for p in _paragraphs(text):
        while len(p) > max_chars:                 # đoạn khổng lồ: cắt cứng
            flush()
            chunks.append(p[:max_chars])
            p = p[max_chars - overlap:]
        if len(buf) + len(p) + 1 > max_chars:
            tail = buf[-overlap:] if overlap else ""
            flush()
            buf = (tail + "\n" + p).strip()
        else:
            buf = (buf + "\n" + p).strip()
    flush()
    return chunks
def _batched(it, n):
    it = iter(it)
    while batch := list(islice(it, n)):
        yield batch


def chunk_invoice(inv: dict, items_per_chunk: int = 4) -> list[str]:
    """Cắt hóa đơn theo cấu trúc. `inv` là dict đã parse từ XML ở tuần 1-4."""
    money = lambda x: f"{int(x):,}".replace(",", ".") if x is not None else "-"

    head = (
        f"Hóa đơn số {inv.get('invoice_no','-')} "
        f"ký hiệu {inv.get('serial','-')} ngày {inv.get('issue_date','-')}. "
        f"Người bán: {inv.get('seller_name','-')}, MST {inv.get('seller_mst','-')}. "
        f"Người mua: {inv.get('buyer_name','-')}, MST {inv.get('buyer_mst','-')}. "
        f"Cộng tiền hàng {money(inv.get('subtotal'))} VND, "
        f"thuế GTGT {money(inv.get('vat_amount'))} VND "
        f"(thuế suất {inv.get('vat_rate','-')}), "
        f"tổng tiền thanh toán {money(inv.get('total'))} VND."
    )
    out = [head]

    for group in _batched(inv.get("items", []), items_per_chunk):
        lines = "; ".join(
            f"{it.get('name','-')} — số lượng {it.get('qty','-')} {it.get('unit','')}"
            f", đơn giá {money(it.get('price'))}, thành tiền {money(it.get('amount'))}"
            for it in group
        )
        out.append(f"Hàng hóa, dịch vụ: {lines}.")
    return out


def with_context(text: str, meta: dict) -> str:
    """Gắn nhãn metadata vào đầu chunk để query nhắc MST/ngày/số HĐ vẫn match."""
    tag = (
        f"[{meta.get('doc_type','doc')} | HĐ {meta.get('invoice_no','-')} "
        f"| MST {meta.get('mst','-')} | {meta.get('issue_date','-')}]"
    )
    return f"{tag}\n{text}"
