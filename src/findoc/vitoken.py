from __future__ import annotations
import re, unicodedata
from pyvi import ViTokenizer

_PUNCT = re.compile(r"[^\w]", flags=re.UNICODE)   # giữ chữ, số, gạch dưới


def tokenize(text: str) -> list[str]:
    """NFC → pyvi tách từ → hạ chữ thường → bỏ dấu câu. Dùng CHUNG cho index và query."""
    text = unicodedata.normalize("NFC", text)
    seg = ViTokenizer.tokenize(text)
    out = []
    for tok in seg.lower().split():
        tok = _PUNCT.sub("", tok)
        if tok:
            out.append(tok)
    return out


if __name__ == "__main__":
    tests = [
        "[invoice | HĐ 0000123 | MST 0101243150 | 2026-03-12]",
        "Hóa đơn số 0000123 mua những mặt hàng gì?",
        "Cộng tiền hàng 11.363.636 VND, thuế GTGT 10%.",
    ]
    for t in tests:
        print(t, "\n ->", tokenize(t), "\n")
