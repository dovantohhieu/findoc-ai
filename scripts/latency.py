import statistics, time, yaml, pathlib
from findoc.search import hybrid_search

qs = yaml.safe_load(pathlib.Path("eval/gold30.yaml").read_text(encoding="utf-8"))
questions = [q["question"] for q in qs]

for n in (0, 10, 20, 50):
    hybrid_search(questions[0], use_reranker=bool(n), rerank_n=max(n, 5), log=False)  # warm-up
    lats = []
    for q in questions:
        t0 = time.perf_counter()
        hybrid_search(q, use_reranker=bool(n), rerank_n=max(n, 5), log=False)
        lats.append((time.perf_counter() - t0) * 1000)
    lats.sort()
    label = "không rerank" if n == 0 else f"rerank_n={n}"
    print(f"{label:16} p50={statistics.median(lats):7.1f}ms  p95={lats[int(.95*len(lats))]:7.1f}ms")
