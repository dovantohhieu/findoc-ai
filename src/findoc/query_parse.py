from __future__ import annotations
import re, datetime as dt

MST_RE     = re.compile(r"\b(\d{10})(?:-(\d{3}))?\b")
INVOICE_RE = re.compile(r"(?:hóa đơn|hoá đơn|hđ|số)\s*[:#]?\s*(\d{5,8})\b", re.I)
DATE_RE    = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
MONTH_RE   = re.compile(r"tháng\s*(\d{1,2})(?:\s*(?:năm|/)\s*(\d{4}))?", re.I)

DOC_TYPES = {
    "hóa đơn": "invoice", "hoá đơn": "invoice", "hợp đồng": "contract",
    "biên lai": "receipt", "sao kê": "statement",
}


def parse_filters(q: str, default_year: int = 2026) -> dict:
    f: dict = {}

    if m := MST_RE.search(q):
        f["mst"] = m.group(1) + (f"-{m.group(2)}" if m.group(2) else "")

    if m := INVOICE_RE.search(q):
        f["invoice_no"] = m.group(1).zfill(7)

    if m := DATE_RE.search(q):
        d, mo, y = map(int, m.groups())
        f["date_from"] = f["date_to"] = dt.date(y, mo, d).isoformat()
    elif m := MONTH_RE.search(q):
        mo = int(m.group(1))
        y = int(m.group(2) or default_year)
        last = dt.date(y + mo // 12, mo % 12 + 1, 1) - dt.timedelta(days=1)
        f["date_from"] = dt.date(y, mo, 1).isoformat()
        f["date_to"] = last.isoformat()

    for kw, dtp in DOC_TYPES.items():
        if kw in q.lower():
            f["doc_type"] = dtp
            break
    return f


if __name__ == "__main__":
    tests = [
        "hóa đơn của MST 0101243150 trong tháng 3 năm 2026",
        "hoá đơn số 0000123 mua những gì",
        "các hợp đồng ký ngày 12/03/2026",
        "tổng tiền thanh toán là bao nhiêu",
    ]
    for t in tests:
        print(f"{t}\n  -> {parse_filters(t)}\n")
