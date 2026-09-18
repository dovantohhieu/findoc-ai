from findoc.search import search, smart_search

MST, MONTH = "0469138107", "2025-08"
q = f"hóa đơn của MST {MST} trong tháng 8 năm 2025"


def show(name, rows):
    hit = 0
    print(f"=== {name} ===")
    for r in rows:
        ok = r["mst"] == MST and str(r["issue_date"]).startswith(MONTH)
        hit += ok
        print(f"{'✓' if ok else '✗'} {r['score']:.3f} mst={r['mst']} ngày={r['issue_date']}")
    print(f"-> đúng {hit}/{len(rows)}\n")


show("search() - KHÔNG filter", search(q))
show("smart_search() - CÓ filter", smart_search(q))
