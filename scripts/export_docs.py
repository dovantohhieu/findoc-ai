"""XML hóa đơn -> parse -> normalize -> validate -> data/processed/docs.jsonl

Chạy:  python scripts/export_docs.py
Ra:    data/processed/docs.jsonl       hóa đơn sạch (input cho chunking Bước 8)
       data/processed/rejected.jsonl   hóa đơn bị loại + lý do
       Nếu có data/raw/labels.jsonl -> in thêm độ chính xác trường + precision/recall validator
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from findoc.ingest import ParseError, parse_invoice_xml, validate_invoice  # noqa: E402

REQUIRED = ["doc_id", "doc_type", "invoice_no", "issue_date", "seller_mst",
            "seller_name", "buyer_name", "total", "items"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/raw/xml")
    ap.add_argument("--out", default="data/processed")
    a = ap.parse_args()

    files = sorted(Path(a.src).glob("*.xml"))
    if not files:
        print(f"Không có file XML trong {a.src}. Chạy scripts/generate_invoices.py trước.")
        return 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    ok, rejected, parsed = [], [], {}
    reasons = Counter()
    for fp in files:
        try:
            doc = parse_invoice_xml(fp)
        except ParseError as e:
            rejected.append({"source_file": fp.name, "stage": "parse", "errors": [str(e)]})
            reasons[str(e).split(":")[0]] += 1
            continue
        parsed[fp.name] = doc
        errs = validate_invoice(doc)
        if errs:
            rejected.append({"source_file": fp.name, "stage": "validate", "doc_id": doc.doc_id, "errors": errs})
            reasons.update(e.split(":")[0] for e in errs)
        else:
            ok.append(doc)

    ids = Counter(d.doc_id for d in ok)
    dups = {k for k, v in ids.items() if v > 1}
    if dups:
        print(f"CẢNH BÁO: doc_id trùng: {sorted(dups)}")

    with open(out / "docs.jsonl", "w", encoding="utf-8") as f:
        for d in ok:
            f.write(json.dumps(d.model_dump(mode="json"), ensure_ascii=False) + "\n")
    with open(out / "rejected.jsonl", "w", encoding="utf-8") as f:
        for r in rejected:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Tổng XML: {len(files)} | docs.jsonl: {len(ok)} | rejected: {len(rejected)}")
    for k, v in reasons.most_common():
        print(f"  - {k}: {v}")

    labels_fp = Path(a.src).parent / "labels.jsonl"
    if labels_fp.exists():
        report(labels_fp, parsed, {r["source_file"] for r in rejected})
    return 0


def report(labels_fp: Path, parsed: dict, rejected_files: set[str]) -> None:
    labels = [json.loads(l) for l in open(labels_fp, encoding="utf-8")]
    # 1) validator có bắt đúng hóa đơn lỗi không
    tp = sum(1 for l in labels if l["defect"] and l["source_file"] in rejected_files)
    fp = sum(1 for l in labels if not l["defect"] and l["source_file"] in rejected_files)
    fn = sum(1 for l in labels if l["defect"] and l["source_file"] not in rejected_files)
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    print(f"\nValidator  precision={prec:.3f}  recall={rec:.3f}  (TP={tp} FP={fp} FN={fn})")

    # 2) độ chính xác từng trường trên hóa đơn sạch (so với ground truth)
    fields = ["doc_type", "invoice_no", "issue_date", "seller_mst", "seller_name", "buyer_name", "total", "n_items"]
    hit, n = Counter(), 0
    for l in labels:
        d = parsed.get(l["source_file"])
        if l["defect"] or d is None:
            continue
        n += 1
        got = d.model_dump(mode="json")
        got["n_items"] = len(d.items)
        for k in fields:
            hit[k] += got[k] == l["expected"][k]
    print(f"Field accuracy trên {n} hóa đơn sạch:")
    for k in fields:
        print(f"  {k:<12} {hit[k] / n:.3f}" if n else f"  {k}: n/a")


if __name__ == "__main__":
    sys.exit(main())
