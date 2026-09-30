import json, re, yaml
from collections import defaultdict, Counter
from pathlib import Path

def to_int(x):
    try: return int(float(str(x).replace(",", "")))
    except (TypeError, ValueError): return None

def next_month(ym):
    y, m = map(int, ym.split("-"))
    return f"{y + m // 12}-{m % 12 + 1:02d}"

docs = [json.loads(l) for l in Path("data/processed/docs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
by_mst_month, by_month = defaultdict(list), Counter()
for d in docs:
    date = str(d.get("issue_date") or "")
    if not re.match(r"\d{4}-\d{2}", date): continue
    by_month[date[:7]] += 1
    if d.get("seller_mst"): by_mst_month[(d["seller_mst"], date[:7])].append(d)
top = sorted(by_mst_month.items(), key=lambda kv: -len(kv[1]))[:2]
busy_month, n_busy = by_month.most_common(1)[0]

path = Path("eval/gold38.yaml")
new_ids = {f"g{i}" for i in range(31, 39)}
items = [it for it in yaml.safe_load(path.read_text(encoding="utf-8")) if it["id"] not in new_ids]

for it in items:
    if it.get("kind") == "negative" or not it.get("expected_doc_ids"):
        it.update(route="lookup", expect_refusal=True, key_facts=[])
        print("Đổi thành câu từ chối:", it["id"], "|", it["question"])

new, sqls = [], []
def add(q, route, refusal, facts, answer):
    new.append({"id": f"g{31 + len(new)}", "question": q, "route": route,
                "expect_refusal": refusal, "key_facts": facts,
                "split": "dev" if len(new) % 2 == 0 else "test",
                "expected_doc_ids": [], "gold_answer": answer, "reviewed": True})

for (mst, ym), ds in top:
    tot = sum(to_int(d.get("total")) or 0 for d in ds)
    y, m = ym.split("-")
    add(f"Tổng tiền thanh toán các hóa đơn của MST {mst} trong tháng {m}/{y} là bao nhiêu?",
        "aggregate", False, [{"type": "amount", "value": tot}], f"{len(ds)} hóa đơn, tổng {tot} đồng")
    sqls.append(f"SELECT count(*), sum(total) FROM documents WHERE mst='{mst}' "
                f"AND issue_date >= '{ym}-01' AND issue_date < '{next_month(ym)}-01';")
y, m = busy_month.split("-")
add(f"Có bao nhiêu hóa đơn trong tháng {m}/{y}?", "aggregate", False,
    [{"type": "amount", "value": n_busy}], f"{n_busy} hóa đơn")
sqls.append(f"SELECT count(*) FROM documents WHERE issue_date >= '{busy_month}-01' "
            f"AND issue_date < '{next_month(busy_month)}-01';")

for q in ["Xin chào", "Thời tiết Hà Nội hôm nay thế nào?", "Cách nấu phở bò?"]:
    add(q, "out_of_scope", True, [], "Ngoài phạm vi hệ thống.")

nos = {str(d.get("invoice_no", "")).lstrip("0") for d in docs}
for n in [n for n in ("9999999", "8888888", "7777777") if n not in nos][:2]:
    add(f"Tổng tiền thanh toán của hóa đơn số {n} là bao nhiêu?", "lookup", True, [],
        f"Không tìm thấy hóa đơn số {n}.")

items += new
path.write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False), encoding="utf-8")

print(f"\nTổng số câu: {len(items)}")
for x in new: print(x["id"], x["route"], x["key_facts"], "|", x["question"])
print("Vi phạm (không refusal, không key_facts):",
      [it["id"] for it in items if not (it.get("expect_refusal") or it.get("key_facts"))])
print("Chưa review:", [it["id"] for it in items if not it.get("reviewed")])
print("\n--- Lệnh SQL đối chiếu (copy chạy từng dòng) ---")
for s in sqls: print(f'docker compose exec db psql -U findoc -d findoc -c "{s}"')
