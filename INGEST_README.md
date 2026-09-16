# FinDoc AI — Ingest layer (tuần 1–4, dựng lại)

Mục đích cuối cùng: tạo `data/processed/docs.jsonl`, mỗi dòng là 1 hóa đơn đã
parse → chuẩn hóa → validate, đủ 9 trường cho chunking:
doc_id, doc_type, invoice_no, issue_date, seller_mst, seller_name, buyer_name, total, items.

Luồng dữ liệu:
  scripts/generate_invoices.py  →  data/raw/xml/*.xml  +  data/raw/labels.jsonl
  scripts/export_docs.py        →  data/processed/docs.jsonl  +  rejected.jsonl

Module (src/findoc/ingest/):
  normalize.py   NFC, số tiền kiểu VN/quốc tế, ngày (ISO, dd/mm/yyyy, "ngày..tháng..năm"), MST, thuế suất
  validators.py  MST checksum (10/13 số), khớp dòng / tạm tính / thuế / tổng
  schema.py      Pydantic InvoiceDoc, Item
  xml_parser.py  XML theo cấu trúc TT78 (HDon/DLHDon/TTChung/NDHDon), bỏ dòng ghi chú TChat=4

Chạy:
  python scripts/generate_invoices.py --n 80 --seed 42
  python scripts/export_docs.py
  pytest -q
