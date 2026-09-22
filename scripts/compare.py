"""Bảng 4 cột: dense | bm25 | hybrid_rrf | hybrid_rerank trên cùng gold set."""
import pathlib, statistics, sys, yaml
from findoc.eval.run import run_one, _metrics
from findoc.search import smart_search, lexical_search, hybrid_search

K = 5
GOLD = sys.argv[1] if len(sys.argv) > 1 else "eval/gold30.yaml"
CONFIGS = {
    "dense":         smart_search,
    "bm25":          lexical_search,
    "hybrid_rrf":    lambda q, top_k=K, **kw: hybrid_search(q, top_k=top_k, log=False),
    "hybrid_rerank": lambda q, top_k=K, **kw: hybrid_search(q, top_k=top_k,
                                                            use_reranker=True, log=False),
    "rerank_10": lambda q, top_k=K, **kw: hybrid_search(q, top_k=top_k, use_reranker=True, rerank_n=10, log=False),
    "rerank_50": lambda q, top_k=K, **kw: hybrid_search(q, top_k=top_k, use_reranker=True, rerank_n=50, log=False),
}

def tb(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else 0.0

qs = yaml.safe_load(pathlib.Path(GOLD).read_text(encoding="utf-8"))
kq = {}
for name, fn in CONFIGS.items():
    rows = []
    for q in qs:
        exp = set(q.get("expected_doc_ids") or [])
        got, ms = run_one(fn, q["question"], K)
        m = _metrics(got, exp, K)
        uniq = list(dict.fromkeys(d for d in got if d))
        m["hit1"] = float(bool(uniq) and uniq[0] in exp)
        m["kind"], m["ms"] = q["kind"], ms
        rows.append(m)
    kq[name] = rows
    print(f"  xong {name}", file=sys.stderr)

names = list(CONFIGS)
lines = [f"# So sánh retrieval — {GOLD}, k={K}", "",
         "| chỉ số | " + " | ".join(names) + " |",
         "|---|" + "---|" * len(names)]
for key, label in [("recall", f"Recall@{K}"), ("hit", f"Hit@{K}"),
                   ("hit1", "Hit@1"), ("mrr", "MRR")]:
    lines.append(f"| {label} | " + " | ".join(
        f"{tb(r[key] for r in kq[n]):.3f}" for n in names) + " |")
lines.append("| p50 ms | " + " | ".join(
    f"{statistics.median(r['ms'] for r in kq[n]):.0f}" for n in names) + " |")

lines += ["", f"## Recall@{K} theo loại câu hỏi", "",
          "| kind | n | " + " | ".join(names) + " |",
          "|---|---|" + "---|" * len(names)]
for k in sorted({q["kind"] for q in qs}):
    n = sum(1 for q in qs if q["kind"] == k)
    lines.append(f"| {k} | {n} | " + " | ".join(
        f"{tb(r['recall'] for r in kq[nm] if r['kind'] == k):.3f}"
        for nm in names) + " |")

out = "\n".join(lines)
pathlib.Path("reports").mkdir(exist_ok=True)
pathlib.Path("reports/w6_05_rerank_n.md").write_text(out, encoding="utf-8")
print(out)
