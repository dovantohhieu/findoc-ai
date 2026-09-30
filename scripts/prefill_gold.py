import json, yaml
from pathlib import Path

def to_int(x):
    try: return int(float(str(x).replace(",", "")))
    except (TypeError, ValueError): return None

docs = {}
for line in Path("data/processed/docs.jsonl").read_text(encoding="utf-8").splitlines():
    if line.strip():
        d = json.loads(line)
        docs[d.get("doc_id") or d.get("id")] = d

raw = yaml.safe_load(Path("eval/gold30.yaml").read_text(encoding="utf-8"))
items = raw if isinstance(raw, list) else (raw.get("items") or raw.get("questions"))

found = 0
for i, it in enumerate(items):
    q = it["question"].lower()
    ids = it.get("expected_doc_ids") or []
    d = docs.get(ids[0]) if ids else None
    facts = []
    if d:
        found += 1
        if "vat" in q or "tiền thuế" in q or "thuế gtgt" in q:
            facts.append({"type": "amount", "value": to_int(d.get("vat_amount"))})
        elif "tiền" in q or "bao nhiêu" in q:
            facts.append({"type": "amount", "value": to_int(d.get("total"))})
        if "ngày" in q:
            facts.append({"type": "date", "value": d.get("issue_date")})
        if "mst" in q or "mã số thuế" in q:
            facts.append({"type": "mst", "value": d.get("buyer_mst" if "mua" in q else "seller_mst")})
        if d.get("invoice_no"):
            facts.append({"type": "invoice_no", "value": str(d["invoice_no"])})
    new = {"id": it["id"], "question": it["question"], "route": "lookup",
           "expect_refusal": False, "key_facts": facts[:3],
           "split": "dev" if i % 2 == 0 else "test"}
    new.update({k: v for k, v in it.items() if k not in new})
    new["reviewed"] = False
    items[i] = new

Path("eval/gold38.yaml").write_text(
    yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
print(f"Đã ghi eval/gold38.yaml — {len(items)} câu, khớp doc: {found}/{len(items)}")
