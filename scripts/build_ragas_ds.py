import json, pathlib, yaml
from findoc.answer import answer

gold = yaml.safe_load(pathlib.Path("eval/gold30.yaml").read_text(encoding="utf-8"))
rows = []
for q in gold:
    if not q.get("gold_answer"):
        continue
    res = answer(q["question"])
    rows.append({
        "question": q["question"],
        "answer": res["answer"],
        "contexts": res["contexts"],
        "ground_truth": q["gold_answer"],
        "kind": q["kind"],
    })

out = pathlib.Path("eval/ragas_dataset.jsonl")
out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
print(f"{len(rows)} mẫu → {out}")
