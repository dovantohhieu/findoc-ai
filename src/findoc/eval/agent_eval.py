from __future__ import annotations
import argparse, json, statistics, time
from collections import Counter
from pathlib import Path

import yaml

from findoc.agent.graph import build_graph
from findoc.agent.nodes import REVIEW_LEVELS
from findoc.eval.match import is_refusal, score_item


def run(items: list[dict]) -> list[dict]:
    graph, outs = build_graph(), []
    for g in items:
        t0 = time.perf_counter()
        st = graph.invoke({"question": g["question"]})
        ms = (time.perf_counter() - t0) * 1000
        rows = st.get("rows") or []
        answer = st.get("answer", "")
        sc = score_item(g, answer)
        conf = st.get("confidence") or {}
        outs.append({
            "id": g["id"], "split": g.get("split", "dev"), "question": g["question"],
            "route_gold": g["route"], "route_pred": st.get("route"), "route_by": st.get("route_by"),
            "filters": st.get("filters") or {}, "answer": answer,
            "contexts": [r["text"] for r in rows],
            "doc_ids": list(dict.fromkeys(r["doc_id"] for r in rows)) or (st.get("agg") or {}).get("doc_ids", []),
            "candidate_doc_ids": (st.get("debug") or {}).get("candidate_doc_ids", []),
            "expected_doc_ids": g.get("expected_doc_ids") or [],
            "gold_answer": g.get("gold_answer", ""),
            "level": conf.get("level"), "reasons": conf.get("reasons", []),
            "facts": sc["facts"], "ok": sc["ok"], "refused": is_refusal(answer),
            "expect_refusal": bool(g.get("expect_refusal")), "latency_ms": round(ms, 1),
        })
    return outs


def metrics(outs: list[dict], review_levels: set[str]) -> dict:
    mean = lambda xs: statistics.mean(xs) if xs else 0.0
    facts = [f for o in outs for f in o["facts"]]
    lookup = [o for o in outs if o["route_gold"] == "lookup" and o["expected_doc_ids"]]
    flagged = [o for o in outs if o["level"] in review_levels]
    wrong = [o for o in outs if not o["ok"]]
    caught = [o for o in wrong if o["level"] in review_levels]
    return {
        "n": len(outs),
        "route_acc": mean([o["route_pred"] == o["route_gold"] for o in outs]),
        "answer_ok": mean([o["ok"] for o in outs]),
        "fact_acc": {t: mean([f["ok"] for f in facts if f["type"] == t])
                     for t in sorted({f["type"] for f in facts})},
        "refusal_acc": mean([o["refused"] == o["expect_refusal"] for o in outs]),
        "recall@5": mean([len(set(o["doc_ids"][:5]) & set(o["expected_doc_ids"]))
                          / len(set(o["expected_doc_ids"])) for o in lookup]),
        "review_rate": len(flagged) / max(len(outs), 1),
        "catch_rate": len(caught) / len(wrong) if wrong else 1.0,
        "review_precision": len(caught) / len(flagged) if flagged else 0.0,
        "p50_ms": {r: statistics.median([o["latency_ms"] for o in outs if o["route_gold"] == r])
                   for r in sorted({o["route_gold"] for o in outs})},
        "confusion": {f"{a}→{b}": c for (a, b), c in
                      Counter((o["route_gold"], o["route_pred"]) for o in outs).items() if a != b},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="eval/gold38.yaml")
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--out", default="reports/agent_outputs.jsonl")
    a = ap.parse_args()

    items = [q for q in yaml.safe_load(Path(a.gold).read_text(encoding="utf-8"))
             if a.split == "all" or q.get("split", "dev") == a.split]
    outs = run(items)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in outs), encoding="utf-8")

    m = metrics(outs, REVIEW_LEVELS)
    print(json.dumps(m, ensure_ascii=False, indent=2))
    print("\nCâu sai:")
    for o in outs:
        if not o["ok"]:
            bad = [f"{f['type']}={f['value']}({f['how']})" for f in o["facts"] if not f["ok"]]
            print(f"  {o['id']} [{o['route_gold']}→{o['route_pred']}] {o['question'][:60]} | {bad or 'từ chối sai'}")


if __name__ == "__main__":
    main()
