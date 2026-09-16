"""Sinh bộ hóa đơn điện tử XML giả lập (cấu trúc TT78) + nhãn ground truth.

Chạy:  python scripts/generate_invoices.py --n 80 --seed 42
Ra:    data/raw/xml/*.xml
       data/raw/labels.jsonl   (giá trị đúng + lỗi đã cố ý chèn -> dùng để đo validator)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from findoc.ingest.validators import mst_check_digit  # noqa: E402

SELLERS = [
    ("Công ty TNHH Thương mại Minh Phát", "Số 12 Trần Duy Hưng, Cầu Giấy, Hà Nội", "vpp"),
    ("Công ty Cổ phần Công nghệ Sao Việt", "Tầng 5, 88 Láng Hạ, Đống Đa, Hà Nội", "it"),
    ("Công ty TNHH Thực phẩm Hưng Yên Xanh", "KCN Phố Nối A, Văn Lâm, Hưng Yên", "food"),
    ("Công ty Cổ phần Vật tư Nông nghiệp Đồng Bằng", "45 Nguyễn Văn Linh, Ninh Kiều, Cần Thơ", "agri"),
    ("Công ty TNHH Dịch vụ Vận tải Bắc Nam", "210 Giải Phóng, Hoàng Mai, Hà Nội", "logistics"),
    ("Công ty TNHH Điện máy Hoàng Long", "67 Lê Lợi, Quận 1, TP. Hồ Chí Minh", "it"),
]
BUYERS = [
    "Công ty Cổ phần Đầu tư Phúc Thịnh",
    "Công ty TNHH Sản xuất Bao bì An Khang",
    "Trường Đại học Công nghiệp Hà Nội",
    "Công ty TNHH Nhà hàng Quê Hương",
    "Hợp tác xã Nông nghiệp Tiên Tiến",
    "Công ty Cổ phần Xây dựng Thăng Long",
]
PRODUCTS = {
    "vpp": [("Giấy in A4 Double A 70gsm", "Ram", 72000, 10), ("Bút bi Thiên Long TL-027", "Hộp", 55000, 10),
            ("Sổ tay bìa da", "Cuốn", 38000, 10), ("Mực in HP 12A", "Hộp", 450000, 10)],
    "it": [("Máy tính xách tay Dell Latitude 5440", "Chiếc", 21500000, 10), ("Chuột không dây Logitech M331", "Chiếc", 320000, 10),
           ("Dịch vụ bảo trì máy chủ tháng", "Tháng", 5000000, 10), ("Ổ cứng SSD Samsung 1TB", "Chiếc", 2150000, 8),
           ("Phần mềm kế toán bản quyền 1 năm", "Gói", 6000000, 0)],
    "food": [("Gạo ST25 túi 5kg", "Túi", 185000, 5), ("Nước mắm Nam Ngư 750ml", "Chai", 42000, 8),
             ("Cà phê rang xay Buôn Ma Thuột", "Kg", 260000, 8), ("Dầu ăn Tường An 1L", "Chai", 58000, 8)],
    "agri": [("Phân bón NPK 16-16-8", "Bao", 620000, 5), ("Giống lúa OM18", "Kg", 28000, None),
             ("Thuốc bảo vệ thực vật sinh học", "Chai", 145000, 5), ("Máy bơm nước 2HP", "Chiếc", 3900000, 10)],
    "logistics": [("Cước vận chuyển Hà Nội - TP.HCM", "Chuyến", 18000000, 8), ("Phí bốc xếp hàng hóa", "Lần", 1200000, 8),
                  ("Phí lưu kho", "Pallet/tháng", 350000, 8)],
}
DEFECTS = ["bad_seller_mst", "total_mismatch", "line_amount_mismatch", "missing_invoice_no"]


def make_mst(rng: random.Random) -> str:
    while True:
        first9 = f"0{rng.randint(10_000_000, 99_999_999)}"
        c = mst_check_digit(first9)
        if c is not None:
            return first9 + str(c)


def money(x: Decimal) -> Decimal:
    return x.quantize(Decimal(1), rounding=ROUND_HALF_UP)


def fmt_amount(v: Decimal, rng: random.Random, noisy: bool) -> str:
    """XML chuẩn là số trơn; nhiễu = kiểu hiển thị '1.234.567' hoặc '1,234,567'."""
    s = str(int(v))
    if not noisy:
        return s
    sep = rng.choice([".", ","])
    return f"{int(v):,}".replace(",", sep)


def fmt_date(d: date, rng: random.Random, noisy: bool) -> str:
    if not noisy:
        return d.isoformat()
    return rng.choice([d.strftime("%d/%m/%Y"), d.strftime("%d-%m-%Y"),
                       f"Ngày {d.day:02d} tháng {d.month:02d} năm {d.year}"])


def maybe_nfd(s: str, noisy: bool) -> str:
    return unicodedata.normalize("NFD", s) if noisy else s


def sub(parent: ET.Element, tag: str, text=None) -> ET.Element:
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    return el


def build_invoice(idx: int, rng: random.Random, sellers, buyers, noise: float, defect_rate: float):
    s_name, s_addr, s_mst, cat = rng.choice(sellers)
    b_name, b_mst = rng.choice(buyers)
    form = rng.choices(["1", "2"], weights=[4, 1])[0]
    year = 2025
    symbol = f"C{str(year)[2:]}T{rng.choice(['AA', 'BB', 'MP', 'SV'])}"
    inv_no = str(rng.randint(1, 9999))
    issue = date(year, 1, 1) + timedelta(days=rng.randint(0, 364))

    lines = []
    for p_name, unit, price, rate in rng.sample(PRODUCTS[cat], k=rng.randint(1, min(4, len(PRODUCTS[cat])))):
        qty = Decimal(rng.choice([1, 2, 3, 5, 10, 20, 50]))
        price = Decimal(price)
        vat_rate = None if (rate is None or form == "2") else Decimal(rate) / 100
        lines.append(dict(name=p_name, unit=unit, qty=qty, price=price, amount=qty * price, rate=vat_rate))
    subtotal = sum(l["amount"] for l in lines)
    vat = sum(money(l["amount"] * (l["rate"] or 0)) for l in lines)
    total = subtotal + vat

    defect = rng.choice(DEFECTS) if rng.random() < defect_rate else None
    n = lambda: rng.random() < noise  # noqa: E731

    root = ET.Element("HDon")
    dl = sub(root, "DLHDon", None)
    dl.set("Id", f"data-{idx}")
    tt = sub(dl, "TTChung")
    sub(tt, "PBan", "2.1.0")
    sub(tt, "THDon", "Hóa đơn giá trị gia tăng" if form == "1" else "Hóa đơn bán hàng")
    sub(tt, "KHMSHDon", form)
    sub(tt, "KHHDon", symbol)
    if defect != "missing_invoice_no":
        sub(tt, "SHDon", inv_no)
    sub(tt, "NLap", fmt_date(issue, rng, n()))
    sub(tt, "DVTTe", "VND")
    sub(tt, "HTTToan", rng.choice(["TM/CK", "CK", "TM"]))

    nd = sub(dl, "NDHDon")
    nban = sub(nd, "NBan")
    sub(nban, "Ten", maybe_nfd(s_name, n()) + ("   " if n() else ""))
    seller_mst_out = s_mst
    if defect == "bad_seller_mst":
        seller_mst_out = s_mst[:9] + str((int(s_mst[9]) + rng.randint(1, 9)) % 10)
    sub(nban, "MST", seller_mst_out if not n() else f"{seller_mst_out[:4]} {seller_mst_out[4:7]} {seller_mst_out[7:]}")
    sub(nban, "DChi", maybe_nfd(s_addr, n()))
    nmua = sub(nd, "NMua")
    sub(nmua, "Ten", maybe_nfd(b_name, n()))
    if b_mst:
        sub(nmua, "MST", b_mst)

    ds = sub(nd, "DSHHDVu")
    bad_line = rng.randrange(len(lines)) if defect == "line_amount_mismatch" else -1
    for i, l in enumerate(lines, 1):
        h = sub(ds, "HHDVu")
        sub(h, "TChat", 1)
        sub(h, "STT", i)
        sub(h, "THHDVu", maybe_nfd(l["name"], n()))
        sub(h, "DVTinh", l["unit"])
        sub(h, "SLuong", int(l["qty"]))
        sub(h, "DGia", fmt_amount(l["price"], rng, n()))
        amt = l["amount"] + (Decimal(rng.choice([1000, 10000, -5000])) if i - 1 == bad_line else 0)
        sub(h, "ThTien", fmt_amount(amt, rng, n()))
        sub(h, "TSuat", "KCT" if l["rate"] is None else f"{int(l['rate'] * 100)}%")
    if n():  # dòng ghi chú, parser phải bỏ qua
        h = sub(ds, "HHDVu")
        sub(h, "TChat", 4)
        sub(h, "THHDVu", "Giao hàng tận nơi trong nội thành")

    tto = sub(nd, "TToan")
    sub(tto, "TgTCThue", fmt_amount(subtotal, rng, n()))
    sub(tto, "TgTThue", fmt_amount(vat, rng, n()))
    total_out = total + (Decimal(rng.choice([100000, -50000])) if defect == "total_mismatch" else 0)
    sub(tto, "TgTTTBSo", fmt_amount(total_out, rng, n()))
    sub(root, "MCCQT", f"00{rng.getrandbits(64):016X}")

    label = {
        "source_file": f"inv_{idx:04d}.xml",
        "defect": defect,
        "expected": {
            "doc_type": "vat_invoice" if form == "1" else "sales_invoice",
            "invoice_no": inv_no, "issue_date": issue.isoformat(),
            "seller_mst": s_mst, "seller_name": s_name, "buyer_name": b_name,
            "total": int(total), "n_items": len(lines),
        },
    }
    return root, label


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--noise", type=float, default=0.3, help="xác suất nhiễu định dạng mỗi trường")
    ap.add_argument("--defect-rate", type=float, default=0.15, help="tỷ lệ hóa đơn bị chèn lỗi")
    ap.add_argument("--out", default="data/raw")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    sellers = [(nm, addr, make_mst(rng), cat) for nm, addr, cat in SELLERS]
    buyers = [(nm, make_mst(rng) if rng.random() < 0.8 else "") for nm in BUYERS]

    out = Path(a.out)
    xml_dir = out / "xml"
    xml_dir.mkdir(parents=True, exist_ok=True)
    for old in xml_dir.glob("inv_*.xml"):
        old.unlink()

    with open(out / "labels.jsonl", "w", encoding="utf-8") as f:
        for i in range(1, a.n + 1):
            root, label = build_invoice(i, rng, sellers, buyers, a.noise, a.defect_rate)
            ET.indent(root)
            ET.ElementTree(root).write(xml_dir / label["source_file"], encoding="utf-8", xml_declaration=True)
            f.write(json.dumps(label, ensure_ascii=False) + "\n")

    n_def = sum(1 for l in open(out / "labels.jsonl", encoding="utf-8") if json.loads(l)["defect"])
    print(f"Đã sinh {a.n} hóa đơn -> {xml_dir}  ({n_def} hóa đơn có lỗi cố ý)")


if __name__ == "__main__":
    main()
