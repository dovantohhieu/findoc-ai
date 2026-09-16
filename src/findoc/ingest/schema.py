"""Schema chuẩn của 1 hóa đơn sau ingest. Mỗi dòng docs.jsonl = 1 InvoiceDoc."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_serializer

DocType = Literal["vat_invoice", "sales_invoice", "other_invoice"]


def _num(v: Decimal | None):
    if v is None:
        return None
    return int(v) if v == v.to_integral_value() else float(v)


class Item(BaseModel):
    line_no: int
    name: str
    unit: str = ""
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    vat_rate: Decimal | None = None  # 0.1 = 10%; None = không chịu thuế

    @field_serializer("quantity", "unit_price", "amount", "vat_rate")
    def _ser(self, v):
        return _num(v)


class InvoiceDoc(BaseModel):
    # --- 9 trường bắt buộc cho chunking (Bước 7) ---
    doc_id: str
    doc_type: DocType
    invoice_no: str
    issue_date: str  # ISO YYYY-MM-DD
    seller_mst: str
    seller_name: str
    buyer_name: str
    total: Decimal
    items: list[Item] = Field(default_factory=list)
    # --- trường bổ sung ---
    invoice_symbol: str = ""
    currency: str = "VND"
    seller_address: str = ""
    buyer_mst: str = ""
    buyer_address: str = ""
    subtotal: Decimal = Decimal(0)
    vat_amount: Decimal = Decimal(0)
    source_file: str = ""

    @field_serializer("total", "subtotal", "vat_amount")
    def _ser(self, v):
        return _num(v)
