import pytest
from findoc.vnparse import parse_amounts, parse_dates, norm_text


@pytest.mark.parametrize("text,expected", [
    ("Tổng tiền 12.500.000 đồng", 12_500_000),
    ("khoảng 12,5 triệu", 12_500_000),
    ("12.5tr", 12_500_000),
    ("1,2 tỷ", 1_200_000_000),
    ("500k", 500_000),
    ("12500000 VND", 12_500_000),
])
def test_amounts(text, expected):
    assert expected in parse_amounts(text)


def test_dates():
    assert "2026-03-12" in parse_dates("ngày 12/03/2026")
    assert "2026-03-12" in parse_dates("phát hành 2026-03-12")
    assert "2026-03-12" in parse_dates("ngày 12 tháng 3 năm 2026")


def test_norm_text():
    assert norm_text("Cty TNHH  Minh Anh!") == "công ty tnhh minh anh"
