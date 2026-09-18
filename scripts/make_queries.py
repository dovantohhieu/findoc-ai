"""Sinh BẢN NHÁP eval/queries.yaml từ docs.jsonl (ground truth lấy thẳng từ dữ liệu).

Chạy:  python scripts/make_queries.py > eval/queries.draft.yaml
Sau đó ĐỌC LẠI, sửa câu hỏi cho tự nhiên, bỏ câu vô lý -> lưu thành eval/queries.yaml
"""
import json
import random
from collections import defaultdict

rng = random.Random(7)
docs = [json.loads(l) for l in open("data/processed/docs.jsonl", encoding="utf-8")]

by_mst_month = defaultdict(list)
by_seller = defaultdict(list)
by_item = defaultdict(set)
for d in docs:
    by_mst_month[(d["seller_mst"], d["issue_date"][:7])].append(d)
    by_seller[d["seller_name"]].append(d)
    for it in d["items"]:
        by_item[it["name"]].add(d["doc_id"])

out = []


def add(kind, q, ids):
    out.append((kind, q, sorted(ids)))


# 1) exact_lookup: hỏi theo số hóa đơn (số có thể trùng giữa các người bán -> gom hết)
same_no = defaultdict(set)
for d in docs:
    same_no[d["invoice_no"]].add(d["doc_id"])
for d in rng.sample(docs, 6):
    add("exact_lookup", f"Hóa đơn số {d['invoice_no']} gồm những mặt hàng nào?", same_no[d["invoice_no"]])

# 2) metadata_filter: MST + tháng
for (mst, ym), ds in rng.sample(sorted(by_mst_month.items()), 6):
    y, m = ym.split("-")
    add("metadata_filter", f"Các hóa đơn của MST {mst} trong tháng {int(m)} năm {y}",
        [d["doc_id"] for d in ds])

# 3) semantic: hỏi theo mặt hàng, không có số
for name in rng.sample(sorted(by_item), 5):
    add("semantic", f"Đã mua {name.lower()} ở những hóa đơn nào?", by_item[name])

# 4) entity: hỏi theo tên người bán
for seller in rng.sample(sorted(by_seller), 3):
    add("entity", f"Liệt kê hóa đơn do {seller} xuất",
        [d["doc_id"] for d in by_seller[seller]])

for i, (kind, q, ids) in enumerate(out, 1):
    print(f"- id: q{i:02d}")
    print(f"  question: {json.dumps(q, ensure_ascii=False)}")
    print(f"  expected_doc_ids: {json.dumps(ids)}")
    print(f"  kind: {kind}\n")
