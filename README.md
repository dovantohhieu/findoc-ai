
## Kết quả đo

Corpus: 68 hóa đơn → 136 chunk. Bộ đề: 20 câu, 4 nhóm (exact_lookup, metadata_filter, semantic, entity).

| | Hit@5 | MRR | Recall@5 |
|---|---|---|---|
| search (không filter) | _điền_ | _điền_ | _điền_ |
| smart_search (có filter) | _điền_ | _điền_ | _điền_ |

Các quyết định có đo đạc:

- **Context header cho mỗi chunk**: với câu hỏi theo số hóa đơn, similarity tăng **0.435 → 0.499**.
- **Filter MST/số HĐ → ép exact scan** thay vì HNSW: lý do và đánh đổi ghi trong `docs/decisions.md`.
- **Sửa regex số hóa đơn (5–8 → 1–8 chữ số)**: nhóm exact_lookup Hit@5 _điền_ → _điền_.

Báo cáo đầy đủ: [`reports/week5_eval.md`](reports/week5_eval.md)

## Chạy thử

```bash
python -m venv .venv && source .venv/bin/activate
pip install pydantic pytest FlagEmbedding "psycopg[binary]" pgvector pyyaml

python scripts/generate_invoices.py --n 80 --seed 42   # sinh dữ liệu giả lập
python scripts/export_docs.py                          # -> data/processed/docs.jsonl
make db-up && make migrate && make reindex-full        # nạp pgvector
make eval                                              # chấm điểm -> reports/
pytest -q
```

## Giới hạn hiện tại

- Dữ liệu là **hóa đơn giả lập** sinh bằng script, chưa phải hóa đơn thật.
- Chưa xử lý câu hỏi "không có kết quả" (negative): hệ thống luôn trả về top-k.
- Chỉ có dense retrieval; BM25 + RRF + reranker là việc của tuần 6.
EOF

## Retrieval — tuần 6 (hybrid)

| Cấu hình | Recall@5 | Hit@1 | MRR | p50 |
|---|---|---|---|---|
| dense (bge-m3) | 0.633 | 0.500 | 0.541 | 75 ms |
| bm25 (pyvi) + SQL filter | 0.633 | 0.500 | 0.547 | 41 ms |
| hybrid RRF (k=60) | 0.600 | 0.500 | 0.544 | 113 ms |
| **+ bge-reranker-v2-m3 (n=10) — đang dùng** | **0.700** | **0.600** | **0.639** | **231 ms** |
| + bge-reranker-v2-m3 (n=50) | 0.733 | 0.600 | 0.646 | 511 ms |

Đo trên `eval/gold30.yaml`, k = 5, RTX 4060 fp16. Số gốc: `reports/w6_05_rerank_n.md`.

**Kết luận.** RRF một mình không cải thiện (0.600 so với 0.633, trong vùng nhiễu một câu).
Giá trị của hybrid nằm ở tập ứng viên: dense tìm được item_lookup (0.667), BM25 tìm được
semantic (0.500), và reranker khôi phục được cả hai, điều không nhánh đơn nào làm được.

Gold set: 30 câu, 9 loại truy vấn, sinh nháp bằng Claude Haiku rồi duyệt tay;
kiểm tra tự động rò rỉ từ ngữ (4-gram) và câu hỏi quá rộng.
Cổng hồi quy: `make test-eval` (Recall@5 của hybrid + reranker ≥ 0.65).

Hạn chế đã biết:
- Corpus 68 hóa đơn tổng hợp; n = 30 nên chênh lệch dưới ~0.07 chưa kết luận được.
- Gold set còn ghi thiếu `expected_doc_ids` ở metadata_filter (0.500 ở mọi cấu hình).
- `parse_filters` hiểu nhầm số trong "biên lai 606" là số hóa đơn → paraphrase kẹt ở 0.800.
- Hệ thống luôn trả top-5 kể cả khi không có đáp án. Reranker nhận ra (điểm 0.002 với câu
  hỏi về máy in, corpus không có máy in) nhưng chưa có ngưỡng từ chối.

Lý do từng lựa chọn: [docs/decisions.md](docs/decisions.md)
