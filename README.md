
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
