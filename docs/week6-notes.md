# Tuần 6 — Hybrid retrieval

## Gold set 30 câu
- duyệt tay 2026-09-22, sinh bằng Haiku 4.5 từ 136 chunk / 68 tài liệu
- còn 2 câu chưa sạch: g20 (LEAK), g23 (TOO_BROAD 8doc) — chấp nhận, ghi lại để biết
- n=30 nên chênh lệch dưới ~0.07 giữa hai cấu hình chưa kết luận được
- corpus nhỏ (68 doc), số sẽ đẹp hơn thực tế

## B4 — baseline dense only (bge-m3 + pgvector), gold30
ngày   : 2026-09-22
commit : b4e8058
Hit@5    = 0.633
MRR      = 0.541
Recall@5 = 0.633

Ghi chú: Hit@5 == Recall@5 vì gần như mọi câu chỉ có 1 expected_doc_id.
Mục tiêu tuần: Recall@5 >= 0.80
