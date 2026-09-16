import unicodedata
from decimal import Decimal

import pytest

from findoc.ingest import ParseError, parse_invoice_xml, validate_invoice
from findoc.ingest.normalize import normalize_mst, normalize_text, parse_amount, parse_date, parse_vat_rate
from findoc.ingest.validators import mst_is_valid


@pytest.mark.parametrize("raw,expected", [
    ("1.234.567", Decimal("1234567")),
    ("1,234,567", Decimal("1234567")),
    ("1.234.567,5", Decimal("1234567.5")),
    ("1,234,567.50", Decimal("1234567.50")),
    ("1234567.00", Decimal("1234567.00")),
    ("12.500 đ", Decimal("12500")),
    ("0,5", Decimal("0.5")),
    ("-50.000", Decimal("-50000")),
])
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("bad", ["", "abc", "12a"])
def test_parse_amount_bad(bad):
    with pytest.raises(ValueError):
        parse_amount(bad)


@pytest.mark.parametrize("raw", ["2025-03-07", "07/03/2025", "07-03-2025",
                                 "Ngày 07 tháng 03 năm 2025", "2025-03-07T10:20:00"])
def test_parse_date(raw):
    assert parse_date(raw) == "2025-03-07"


def test_normalize_text_nfc():
    nfd = unicodedata.normalize("NFD", "Công  ty   Cổ phần ")
    assert normalize_text(nfd) == "Công ty Cổ phần"
    assert unicodedata.is_normalized("NFC", normalize_text(nfd))


def test_vat_rate():
    assert parse_vat_rate("10%") == Decimal("0.1")
    assert parse_vat_rate("0%") == 0
    assert parse_vat_rate("KCT") is None


def test_mst():
    assert mst_is_valid("0100109106")          # MST 10 số hợp lệ
    assert mst_is_valid("0100109106-001")      # đơn vị phụ thuộc
    assert not mst_is_valid("0100109107")      # sai chữ số kiểm tra
    assert not mst_is_valid("010010910")       # thiếu số
    assert normalize_mst("0100 109 106") == "0100109106"


XML = """<?xml version="1.0" encoding="utf-8"?>
<HDon><DLHDon>
 <TTChung><KHMSHDon>1</KHMSHDon><KHHDon>C25TAA</KHHDon><SHDon>{no}</SHDon>
  <NLap>15/01/2025</NLap><DVTTe>VND</DVTTe></TTChung>
 <NDHDon>
  <NBan><Ten>Công ty A</Ten><MST>0100109106</MST></NBan>
  <NMua><Ten>Công ty B</Ten></NMua>
  <DSHHDVu>
   <HHDVu><TChat>1</TChat><STT>1</STT><THHDVu>Giấy A4</THHDVu><SLuong>10</SLuong>
    <DGia>72.000</DGia><ThTien>720.000</ThTien><TSuat>10%</TSuat></HHDVu>
   <HHDVu><TChat>4</TChat><THHDVu>Ghi chú</THHDVu></HHDVu>
  </DSHHDVu>
  <TToan><TgTCThue>720000</TgTCThue><TgTThue>72000</TgTThue><TgTTTBSo>{total}</TgTTTBSo></TToan>
 </NDHDon>
</DLHDon></HDon>"""


def _write(tmp_path, no="42", total="792000"):
    p = tmp_path / "x.xml"
    p.write_text(XML.format(no=no, total=total), encoding="utf-8")
    return p


def test_parse_valid(tmp_path):
    doc = parse_invoice_xml(_write(tmp_path))
    assert doc.doc_id == "0100109106_1C25TAA_00000042"
    assert doc.doc_type == "vat_invoice"
    assert doc.issue_date == "2025-01-15"
    assert doc.total == 792000
    assert len(doc.items) == 1  # dòng ghi chú bị bỏ
    assert validate_invoice(doc) == []


def test_total_mismatch(tmp_path):
    doc = parse_invoice_xml(_write(tmp_path, total="800000"))
    assert any(e.startswith("total_mismatch") for e in validate_invoice(doc))


def test_missing_invoice_no(tmp_path):
    with pytest.raises(ParseError, match="SHDon"):
        parse_invoice_xml(_write(tmp_path, no=""))


def test_broken_xml(tmp_path):
    p = tmp_path / "bad.xml"
    p.write_text("<HDon><DLHDon>", encoding="utf-8")
    with pytest.raises(ParseError):
        parse_invoice_xml(p)
