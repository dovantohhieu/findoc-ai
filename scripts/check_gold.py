import sys, re, yaml
from collections import Counter
from findoc.db import connect

def load_chunks():
    with connect() as c, c.cursor() as cur:
        cur.execute("SELECT doc_id, chunk_index, text FROM chunks")
        return {f"{d}#{i}": (d, t) for d, i, t in cur.fetchall()}

CH = load_chunks()

def norm(s):
    return re.sub(r"[.,\s]", "", (s or "").lower())

def ngrams(s, n=4):
    w = re.findall(r"\w+", (s or "").lower())
    return {" ".join(w[i:i+n]) for i in range(len(w)-n+1)}

def flags(d):
    out = []
    hit = CH.get(d.get("source_chunk", ""))
    if hit is None:
        return ["CHUNK_MISSING"]
    _, chunk = hit
    if not (d.get("question") or "").strip():
        return ["EMPTY"]
    if ngrams(d["question"]) & ngrams(chunk):
        out.append("LEAK")
    ans_raw = d.get("gold_answer") or ""
    ans = norm(ans_raw)
    if ans and d.get("kind") not in ("numeric", "negative"):
        c = norm(chunk)
        phan = [norm(x) for x in re.split(r"[,;/]| và ", ans_raw) if norm(x)]
        if phan:
            ty_le = sum(1 for x in phan if x in c) / len(phan)
            if ty_le < 0.6:
                out.append(f"ANS_NOT_IN_CHUNK({ty_le:.0%})")
    if ans and len(ans) >= 4:
        khop = {doc for doc, t in CH.values() if ans in norm(t)}
        if len(khop) > len(d.get("expected_doc_ids", [])):
            out.append(f"TOO_BROAD({len(khop)}doc)")
    return out

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "eval/gold30.draft.yaml"
    items = yaml.safe_load(open(p, encoding="utf-8"))
    print(f"DB có {len(CH)} chunk, ví dụ key: {list(CH)[:2]}")
    print(f"gold source_chunk ví dụ: {[x.get('source_chunk') for x in items[:2]]}\n")
    tally = Counter()
    for d in items:
        f = flags(d)
        tally.update(f or ["CLEAN"])
        print(f"{d['id']:4} {d['kind']:16} {'✗ ' + ', '.join(f) if f else '✓'}")
        print(f"     Q: {(d.get('question') or '')[:76]}")
        print(f"     A: {(d.get('gold_answer') or '')[:60]}")
    print("\n" + " | ".join(f"{k}={v}" for k, v in tally.most_common()))
    print("kind:", Counter(x["kind"] for x in items).most_common())
