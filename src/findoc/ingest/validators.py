"""Business validators: MST checksum, khớp tổng tiền từng dòng / tạm tính / thuế / tổng."""
from __future__ import annotations

import re
from decimal import Decimal

from .schema import InvoiceDoc

_MST_WEIGHTS = (31, 29, 23, 19, 17, 13, 7, 5, 3)
_MST_RE = re.compile(r"^(\d{10})(-\d{3})?$")


def mst_check_digit(first9: str) -> int | None:
    """Chữ số kiểm tra (số thứ 10) của MST. None nếu 9 số đầu không tạo được MST hợp lệ."""
    s = sum(int(d) * w for d, w in zip(first9, _MST_WEIGHTS))
    c = 10 - (s % 11)
    if c == 10:
        return None
    return 0 if c == 11 else c


def mst_is_valid(mst: str) -> bool:
    """MST 10 số, hoặc 13 số dạng '0101234567-001' (đơn vị phụ thuộc)."""
    m = _MST_RE.match(mst or "")
    if not m:
        return False
    base = m.group(1)
    return mst_check_digit(base[:9]) == int(base[9])


def validate_invoice(doc: InvoiceDoc, tol: Decimal = Decimal("1")) -> list[str]:
    """Trả về danh sách lỗi; rỗng = hợp lệ. tol = sai số làm tròn cho phép (VND)."""
    errors: list[str] = []

    if not mst_is_valid(doc.seller_mst):
        errors.append(f"seller_mst_invalid:{doc.seller_mst}")
    if doc.buyer_mst and not mst_is_valid(doc.buyer_mst):
        errors.append(f"buyer_mst_invalid:{doc.buyer_mst}")
    if not doc.items:
        errors.append("items_empty")

    for it in doc.items:
        expect = it.quantity * it.unit_price
        if abs(expect - it.amount) > tol:
            errors.append(f"line_amount_mismatch:line{it.line_no}:{it.quantity}x{it.unit_price}!={it.amount}")

    items_sum = sum((it.amount for it in doc.items), Decimal(0))
    if abs(items_sum - doc.subtotal) > tol:
        errors.append(f"subtotal_mismatch:items={items_sum},subtotal={doc.subtotal}")

    vat_sum = sum((it.amount * (it.vat_rate or 0) for it in doc.items), Decimal(0))
    if abs(vat_sum - doc.vat_amount) > tol * max(1, len(doc.items)):  # làm tròn theo dòng
        errors.append(f"vat_mismatch:computed={vat_sum:.0f},declared={doc.vat_amount}")

    if abs(doc.subtotal + doc.vat_amount - doc.total) > tol:
        errors.append(f"total_mismatch:{doc.subtotal}+{doc.vat_amount}!={doc.total}")

    return errors
