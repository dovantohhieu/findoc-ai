import os, sys, json, yaml, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_gold import flags, CH

IN  = "eval/gold30.draft.yaml"
OUT = "eval/gold30.reviewed.yaml"

def mo_sua(d):
    with tempfile.NamedTemporaryFile("w+", suffix=".json",
                                     delete=False, encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        p = f.name
    subprocess.run([os.getenv("EDITOR", "nano"), p])
    return json.load(open(p, encoding="utf-8"))

def luu(giu):
    yaml.safe_dump(giu, open(OUT, "w", encoding="utf-8"),
                   allow_unicode=True, sort_keys=False)

def main():
    items = yaml.safe_load(open(IN, encoding="utf-8"))
    giu = []
    if os.path.exists(OUT):
        giu = yaml.safe_load(open(OUT, encoding="utf-8")) or []
        xong = {x["id"] for x in giu}
        items = [d for d in items if d["id"] not in xong]

    for i, d in enumerate(items, 1):
        hit = CH.get(d.get("source_chunk", ""))
        chunk = hit[1] if hit else "!! KHÔNG TÌM THẤY"
        os.system("clear")
        print(f"═══ {d['id']}  ({i}/{len(items)} còn lại, đã giữ {len(giu)}) ═══\n")
        print("CHUNK GỐC:")
        print("  " + chunk[:800].replace("\n", "\n  "))
        print(f"\nQ    : {d.get('question','')}")
        print(f"A    : {d.get('gold_answer','')}")
        print(f"KIND : {d.get('kind')}")
        print(f"DOCS : {d.get('expected_doc_ids')}")
        f = flags(d)
        if f:
            print(f"\n⚠  {', '.join(f)}")
        print("\n[a] giữ   [e] sửa   [d] xóa   [q] dừng")
        while True:
            k = input("> ").strip().lower()
            if k == "a":
                d["reviewed"] = True; giu.append(d); break
            if k == "e":
                d = mo_sua(d); d["reviewed"] = True; giu.append(d); break
            if k == "d":
                break
            if k == "q":
                luu(giu); print(f"\nDừng, đã lưu {len(giu)} mục."); return
    luu(giu)
    print(f"\nXong. Giữ {len(giu)} mục -> {OUT}")

if __name__ == "__main__":
    main()
