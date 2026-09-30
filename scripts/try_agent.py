import sys
from findoc.agent.graph import build_graph
from findoc.tracing import callbacks, flush

QUESTIONS = sys.argv[1:] or [
    "Hóa đơn 0000123 mua những mặt hàng gì?",                             # lookup
    "Tổng tiền thanh toán của hóa đơn 0000123 là bao nhiêu?",             # lookup có chữ "tổng"
    "Tổng tiền các hóa đơn của MST 0101243150 trong tháng 3 năm 2026",   # aggregate
    "Có bao nhiêu hóa đơn trong tháng 4?",                                # aggregate
    "Thời tiết Hà Nội hôm nay thế nào?",                                  # out_of_scope
]

graph = build_graph()
for q in QUESTIONS:
    out = graph.invoke({"question": q}, config={"callbacks": callbacks(), "run_name": "findoc-agent"})
    c = out.get("confidence", {})
    print(f"\n[{out['route']}/{out.get('route_by')}] {q}")
    print(f"  tin cậy: {c.get('level')}  {c.get('reasons')}")
    print(f"  → {out['answer'][:200]}")
flush()
