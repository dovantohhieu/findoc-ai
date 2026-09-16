"""Chuẩn hóa text, số tiền, ngày tháng, MST cho dữ liệu hóa đơn tiếng Việt."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def normalize_text(s: str | None) -> str:
    """NFC + gộp khoảng trắng. 'Cà  phê' (NFD, 2 space) -> 'Cà phê' (NFC)."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFC", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_amount(s: str | int | float | Decimal | None) -> Decimal:
    """Đọc số tiền theo cả kiểu VN lẫn kiểu quốc tế.

    '1.234.567'    -> 1234567
    '1,234,567'    -> 1234567
    '1.234.567,5'  -> 1234567.5
    '1234567.00'   -> 1234567.00
    '12.500 đ'     -> 12500
    """
    if s is None:
        raise ValueError("amount is None")
    if isinstance(s, (int, Decimal)):
        return Decimal(s)
    if isinstance(s, float):
        return Decimal(str(s))

    t = normalize_text(s).lower()
    t = re.sub(r"(vnd|vnđ|đồng|đ)", "", t).replace(" ", "")
    neg = t.startswith("-")
    t = t.lstrip("+-")
    if not t or not re.fullmatch(r"[\d.,]+", t):
        raise ValueError(f"không đọc được số tiền: {s!r}")

    if "." in t and "," in t:
        dec = "." if t.rfind(".") > t.rfind(",") else ","
        thou = "," if dec == "." else "."
        t = t.replace(thou, "").replace(dec, ".")
    elif "." in t or "," in t:
        sep = "." if "." in t else ","
        parts = t.split(sep)
        # nhiều dấu, hoặc 1 dấu + đúng 3 chữ số phía sau -> dấu phân cách hàng nghìn
        if len(parts) > 2 or len(parts[1]) == 3:
            t = t.replace(sep, "")
        else:
            t = t.replace(sep, ".")
    try:
        v = Decimal(t)
    except InvalidOperation as e:
        raise ValueError(f"không đọc được số tiền: {s!r}") from e
    return -v if neg else v


_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y")
_VN_DATE = re.compile(r"ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", re.I)


def parse_date(s: str | None) -> str:
    """Trả về ISO 'YYYY-MM-DD'. Hỗ trợ ISO, dd/mm/yyyy, 'ngày 15 tháng 1 năm 2024'."""
    t = normalize_text(s)
    if not t:
        raise ValueError("ngày trống")
    m = _VN_DATE.search(t)
    if m:
        d, mo, y = map(int, m.groups())
        return date(y, mo, d).isoformat()
    t = t.split("T")[0]  # bỏ phần giờ của ISO datetime
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(t, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"không đọc được ngày: {s!r}")


def normalize_mst(s: str | None) -> str:
    """'0101 234 567' -> '0101234567'; '0101234567 - 001' -> '0101234567-001'."""
    return re.sub(r"[\s.]", "", normalize_text(s))


def parse_vat_rate(s: str | None) -> Decimal | None:
    """'10%' -> 0.10 ; '8' -> 0.08 ; 'KCT'/'KKKNT' (không chịu thuế) -> None."""
    t = normalize_text(s).upper().replace("%", "")
    if not t or t in {"KCT", "KKKNT", "KHAC"}:
        return None
    v = parse_amount(t)
    return v / 100 if v >= 1 else v
