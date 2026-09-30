from __future__ import annotations
import re, unicodedata

_NUM = re.compile(r"(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(tỷ|triệu|tr\b|nghìn|ngàn|k\b)?", re.I)
_UNIT = {"tỷ": 10**9, "triệu": 10**6, "tr": 10**6, "nghìn": 10**3, "ngàn": 10**3, "k": 10**3}
_THOUSANDS = re.compile(r"\d{1,3}(?:[.,]\d{3})+")


def parse_amounts(text: str) -> list[int]:
    """Mọi số xuất hiện trong text, đã quy về số nguyên (đồng)."""
    out = []
    for m in _NUM.finditer(text):
        raw, unit = m.group(1), (m.group(2) or "").lower()
        if _THOUSANDS.fullmatch(raw):                 # 12.500.000 hoặc 12,500,000
            val = float(re.sub(r"[.,]", "", raw))
        else:                                         # 12,5 · 12.5 · 1250
            val = float(raw.replace(",", "."))
        out.append(round(val * _UNIT.get(unit, 1)))
    return out


def parse_dates(text: str) -> set[str]:
    """Mọi ngày trong text, dạng YYYY-MM-DD."""
    out = set()
    for d, m, y in re.findall(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text):
        out.add(f"{int(y):04d}-{int(m):02d}-{int(d):02d}")
    for y, m, d in re.findall(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
        out.add(f"{y}-{m}-{d}")
    for d, m, y in re.findall(r"ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", text, re.I):
        out.add(f"{int(y):04d}-{int(m):02d}-{int(d):02d}")
    return out


def norm_text(s: str) -> str:
    """Chuẩn hóa để so khớp mờ: NFC, chữ thường, bung viết tắt, bỏ dấu câu."""
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"\bcty\b", "công ty", s)
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()
