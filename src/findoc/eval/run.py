"""Chấm điểm retrieval trên bộ câu hỏi vàng.

Chạy:  python -m findoc.eval.run --queries eval/queries.yaml --k 5 --out reports/week5_eval.md
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml

from findoc.search import search, smart_search

DOC_KEYS = ("doc_id", "docid", "id")


def _doc_id(row: dict) -> str | None:
    for k in DOC_KEYS:
        if k in row:
            return str(row[k])
    return None


def _metrics(got: list[str], expected: set[str], k: int) -> dict:
    """got: doc_id theo thứ tự hạng (đã bỏ trùng). expected: tập doc_id đúng."""
    seen, ranked = set(), []
    for d in got:                                   # 1 hóa đơn có nhiều chunk -> chỉ giữ lần đầu
        if d and d not in seen:
            seen.add(d)
            ranked.append(d)
    ranked = ranked[:k]
    hit = any(d in expected for d in ranked)
    rr = next((1 / i for i, d in enumerate(ranked, 1) if d in expected), 0.0)
    recall = len(expected & set(ranked)) / len(expected) if expected else 0.0
    return {"hit": float(hit), "mrr": rr, "recall": recall, "n_ret": len(ranked)}


def run_one(fn, q: str, k: int) -> tuple[list[str], float]:
    t0 = time.perf_counter()
    rows = fn(q, top_k=k * 3)          # lấy dư vì nhiều chunk cùng 1 hóa đơn
    ms = (time.perf_counter() - t0) * 1000
    return [_doc_id(r) for r in rows], ms

def recall_at_k(got_doc_ids, gold, k):
    if not gold:
        return None
    return len(set(got_doc_ids[:k]) & gold) / len(gold)
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", default="eval/queries.yaml")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", default="reports/week5_eval.md")
    ap.add_argument("--baseline", action="store_true", help="chạy thêm search() không filter để so sánh")
    a = ap.parse_args()

    qs = yaml.safe_load(Path(a.queries).read_text(encoding="utf-8"))
    runs = {"smart_search": smart_search}
    if a.baseline:
        runs["search (no filter)"] = search

    results: dict[str, list[dict]] = defaultdict(list)
    for name, fn in runs.items():
        for q in qs:
            expected = set(q.get("expected_doc_ids") or [])
            got, ms = run_one(fn, q["question"], a.k)
            m = _metrics(got, expected, a.k)
            m |= {"id": q.get("id"), "kind": q.get("kind", "?"), "ms": ms,
                  "question": q["question"], "expected": sorted(expected), "got": got[: a.k]}
            results[name].append(m)

    lines = [f"# Eval retrieval — k={a.k}", "", f"_{datetime.now():%Y-%m-%d %H:%M}_ · "
             f"{len(qs)} câu · corpus: xem `make count`", ""]
    for name, rows in results.items():
        lines += [f"## {name}", "", "| nhóm | n | Hit@k | MRR | Recall@k | p50 ms |",
                  "|---|---|---|---|---|---|"]
        by_kind = defaultdict(list)
        for r in rows:
            by_kind[r["kind"]].append(r)
        for kind in sorted(by_kind) + ["TỔNG"]:
            rs = rows if kind == "TỔNG" else by_kind[kind]
            lines.append(
                f"| {kind} | {len(rs)} | {statistics.mean(r['hit'] for r in rs):.3f} "
                f"| {statistics.mean(r['mrr'] for r in rs):.3f} "
                f"| {statistics.mean(r['recall'] for r in rs):.3f} "
                f"| {statistics.median(r['ms'] for r in rs):.0f} |")
        miss = [r for r in rows if not r["hit"]]
        lines += ["", f"**Câu trượt ({len(miss)}):**", ""]
        lines += [f"- `{r['id']}` [{r['kind']}] {r['question']}  \n"
                  f"  cần: `{', '.join(r['expected']) or '-'}`  \n"
                  f"  được: `{', '.join(x for x in r['got'] if x) or '(rỗng)'}`" for r in miss] or ["- (không có)"]
        lines.append("")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    for name, rows in results.items():
        print(f"{name:22s} Hit@{a.k}={statistics.mean(r['hit'] for r in rows):.3f} "
              f"MRR={statistics.mean(r['mrr'] for r in rows):.3f} "
              f"Recall@{a.k}={statistics.mean(r['recall'] for r in rows):.3f}")
    print("->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
