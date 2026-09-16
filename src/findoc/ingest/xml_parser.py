"""Parser XML hóa đơn điện tử theo cấu trúc TT78/2021 (HDon/DLHDon/TTChung + NDHDon)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from .normalize import normalize_mst, normalize_text, parse_amount, parse_date, parse_vat_rate
from .schema import InvoiceDoc, Item

# KHMSHDon (ký hiệu mẫu số) -> loại hóa đơn
DOC_TYPES = {"1": "vat_invoice", "2": "sales_invoice"}


class ParseError(Exception):
    pass


def _strip_ns(root: ET.Element) -> None:
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]


def _text(node: ET.Element | None, path: str, required: bool = False) -> str:
    el = node.find(path) if node is not None else None
    val = normalize_text(el.text) if el is not None else ""
    if required and not val:
        raise ParseError(f"missing_field:{path}")
    return val


def _parse_items(ds: ET.Element | None) -> list[Item]:
    items: list[Item] = []
    if ds is None:
        return items
    for i, h in enumerate(ds.findall("HHDVu"), 1):
        # TChat: 1=hàng hóa, 2=khuyến mại, 3=chiết khấu, 4=dòng ghi chú -> bỏ ghi chú
        if _text(h, "TChat") == "4":
            continue
        amount = _text(h, "ThTien", required=True)
        items.append(
            Item(
                line_no=int(_text(h, "STT") or i),
                name=_text(h, "THHDVu", required=True),
                unit=_text(h, "DVTinh"),
                quantity=parse_amount(_text(h, "SLuong") or "1"),
                unit_price=parse_amount(_text(h, "DGia") or amount),
                amount=parse_amount(amount),
                vat_rate=parse_vat_rate(_text(h, "TSuat")),
            )
        )
    return items


def parse_invoice_xml(path: str | Path) -> InvoiceDoc:
    path = Path(path)
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        raise ParseError(f"xml_broken:{e}") from e
    _strip_ns(root)

    dl = root if root.tag == "DLHDon" else root.find("DLHDon")
    if dl is None:
        raise ParseError("missing_field:DLHDon")
    tt, nd = dl.find("TTChung"), dl.find("NDHDon")
    if tt is None or nd is None:
        raise ParseError("missing_field:TTChung/NDHDon")
    nban, nmua, ttoan = nd.find("NBan"), nd.find("NMua"), nd.find("TToan")

    try:
        form = _text(tt, "KHMSHDon")
        symbol = _text(tt, "KHHDon")
        invoice_no = _text(tt, "SHDon", required=True)
        seller_mst = normalize_mst(_text(nban, "MST", required=True))
        subtotal = _text(ttoan, "TgTCThue")
        vat = _text(ttoan, "TgTThue")
        return InvoiceDoc(
            doc_id=f"{seller_mst}_{form}{symbol}_{invoice_no.zfill(8)}",
            doc_type=DOC_TYPES.get(form, "other_invoice"),
            invoice_no=invoice_no,
            invoice_symbol=f"{form}{symbol}",
            issue_date=parse_date(_text(tt, "NLap", required=True)),
            currency=_text(tt, "DVTTe") or "VND",
            seller_mst=seller_mst,
            seller_name=_text(nban, "Ten", required=True),
            seller_address=_text(nban, "DChi"),
            buyer_name=_text(nmua, "Ten", required=True),
            buyer_mst=normalize_mst(_text(nmua, "MST")),
            buyer_address=_text(nmua, "DChi"),
            items=_parse_items(nd.find("DSHHDVu")),
            subtotal=parse_amount(subtotal) if subtotal else Decimal(0),
            vat_amount=parse_amount(vat) if vat else Decimal(0),
            total=parse_amount(_text(ttoan, "TgTTTBSo", required=True)),
            source_file=path.name,
        )
    except (ValueError, ValidationError) as e:
        raise ParseError(f"normalize_error:{e}") from e
