import os, re, time, statistics, yaml, requests
from pathlib import Path
from rapidfuzz import fuzz
from findoc.agent.graph import build_graph
from findoc.agent.nodes import REVIEW_LEVELS
from findoc.vnparse import norm_text, parse_amounts, parse_dates

MARKERS = ("không tìm thấy", "ngoài phạm vi", "không đủ căn cứ")

def refused(ans): return any(m in ans.lower() for m in MARKERS)
def ints(ans): return {int(x) for x in re.findall(r"\d+", ans)}

def fact_ok(f, ans):
    t, v = f["type"], f["value"]
    if t == "amount":
        return int(v) in set(parse_amounts(ans)) | ints(ans)
    if t == "date":
        return str(v) in {str(d) for d in parse_dates(ans)}
    if t == "invoice_no":
        return str(v).lstrip("0") in {x.lstrip("0") for x in re.findall(r"\d+", ans)}
    if t == "mst":
        return str(v) in re.findall(r"\d+", ans)
    return fuzz.partial_ratio(norm_text(str(v)), norm_text(ans)) >= 90

def is_flagged(s):
    if "needs_review" in s: return bool(s["needs_review"]), "needs_review"
    for k in ("level", "confidence"):
        v = s.get(k)
        if isinstance(v, dict): v = v.get("level")
        if v is not None: return v in REVIEW_LEVELS, k
    return False, None

app = build_graph()
qs = yaml.safe_load(open("eval/gold38.yaml", encoding="utf-8"))
res, flag_key = [], None
for q in qs:
    t0 = time.perf_counter()
    s = app.invoke({"question": q["question"]})
    ms = (time.perf_counter() - t0) * 1000
    ans = str(s.get("answer") or "")
    flagged, k = is_flagged(s); flag_key = flag_key or k
    fok = [fact_ok(f, ans) for f in (q.get("key_facts") or [])]
    ok = refused(ans) if q.get("expect_refusal") else (not refused(ans) and all(fok))
    top5 = [r.get("doc_id") for r in (s.get("rows") or [])[:5]]
    exp = q.get("expected_doc_ids") or []
    res.append(dict(id=q["id"], gold=q["route"], route=s.get("route"), by=s.get("route_by"),
                    ms=ms, ok=ok, fok=fok, flagged=flagged,
                    hit=(any(d in top5 for d in exp) if q["route"] == "lookup" and exp else None)))
    print(f"{q['id']:4} {str(s.get('route')):13} {'OK ' if ok else 'SAI'} {ms:6.0f}ms")

def frac(a, b): return f"{a}/{b} ({a/b:.0%})" if b else "n/a"
n = len(res)
route_ok = sum(r["route"] == r["gold"] for r in res)
n_rule = sum(r["by"] == "rule" for r in res); n_llm = sum(r["by"] == "llm" for r in res)
n_ok = sum(r["ok"] for r in res)
facts = [x for r in res for x in r["fok"]]
hits = [r["hit"] for r in res if r["hit"] is not None]
flagged = [r for r in res if r["flagged"]]; wrong = [r for r in res if not r["ok"]]
catch = sum(r["flagged"] for r in wrong); prec = sum(not r["ok"] for r in flagged)
def p50(route):
    xs = [r["ms"] for r in res if r["route"] == route]
    return f"{statistics.median(xs):.0f}" if xs else "n/a"

cost = "n/a"
try:
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    auth = (os.getenv("LANGFUSE_PUBLIC_KEY"), os.getenv("LANGFUSE_SECRET_KEY"))
    data = requests.get(f"{host}/api/public/traces", params={"limit": 100}, auth=auth, timeout=10).json()["data"]
    cs = [t.get("totalCost") or 0 for t in data
          if isinstance(t.get("output"), dict) and t["output"].get("route") == "lookup"]
    if cs: cost = f"${sum(cs)/len(cs):.5f} (trung bình {len(cs)} trace)"
except Exception as e:
    cost = f"n/a (lỗi Langfuse: {e.__class__.__name__})"

section = f"""## Tuần 8 — gold38, agent chưa có HITL
- route accuracy: {frac(route_ok, n)}   (luật: {n_rule} câu, LLM: {n_llm} câu)
- answer_ok: {frac(n_ok, n)}   | fact_acc: {frac(sum(facts), len(facts))}
- recall@5 (lookup): {frac(sum(hits), len(hits))}
- review_rate / catch_rate / precision (REVIEW_LEVELS={','.join(sorted(REVIEW_LEVELS))}): {frac(len(flagged), n)} / {frac(catch, len(wrong))} / {frac(prec, len(flagged))}
- p50: lookup {p50('lookup')} ms · aggregate {p50('aggregate')} ms · out_of_scope {p50('out_of_scope')} ms
- Chi phí trung bình 1 câu lookup (Langfuse): {cost}
- Sai route: {[r['id'] for r in res if r['route'] != r['gold']]}
- Trả lời sai: {[r['id'] for r in wrong]}
"""
p = Path("docs/khoiA-notes.md")
old = p.read_text(encoding="utf-8") if p.exists() else ""
new = re.sub(r"## Tuần 8.*?(?=\n## |\Z)", section.rstrip(), old, flags=re.S) if "## Tuần 8" in old else (old + "\n" + section).lstrip()
p.write_text(new, encoding="utf-8")
print("\n" + section)
if flag_key is None:
    print("⚠️ Không tìm thấy trường mức tin cậy trong state → review/catch/precision chưa đúng. Chụp gửi lên.")
