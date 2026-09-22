# Quyết định kỹ thuật — retrieval (tuần 6)

Số liệu: `eval/gold30.yaml`, k = 5, RTX 4060 fp16. Chênh một câu = 0.033.

## D1 — Gộp dense và BM25 bằng RRF, không chuẩn hóa điểm rồi cộng

**Bối cảnh.** Dense trả cosine trong [0, 1]. BM25 không chặn trên và phụ thuộc câu hỏi:
"hóa đơn 5707" cho 5.46, "thiết bị lưu trữ Samsung" chỉ 2.76.

**Lựa chọn.** Reciprocal Rank Fusion, k = 60, chỉ dùng thứ hạng.

**Kết quả thật.** RRF một mình KHÔNG cải thiện: Recall@5 0.600 so với 0.633 của cả hai
nhánh đơn (trong vùng nhiễu). Ở item_lookup nó còn làm mất điểm của dense (0.667 → 0.000),
ở semantic làm mất điểm của BM25 (0.500 → 0.250). Giả thuyết: filter MST khiến hai nhánh
chung một tập hóa đơn cùng công ty; hóa đơn sai có mặt ở cả hai danh sách được hai phiếu,
vượt hóa đơn đúng chỉ một nhánh xếp cao.

**Vì sao vẫn giữ.** RRF gom ứng viên của cả hai nhánh vào top-N. Reranker sau đó khôi phục
được cả item_lookup 0.667 (của dense) lẫn semantic 0.500 (của BM25). Giá trị của hybrid
nằm ở tập ứng viên, không ở thứ tự RRF.

**Đánh đổi.** Điểm RRF không đo độ liên quan, không dùng làm ngưỡng từ chối được.

## D2 — Reranker bge-reranker-v2-m3, rerank_n = 10

**Bối cảnh.** Baseline dense: Hit@5 0.633 nhưng MRR 0.541, tức tài liệu đúng có mặt nhưng
thường không ở hạng 1.

**Lựa chọn.** Cross-encoder chấm lại 10 ứng viên đầu của RRF.

**Lý do.** Cross-encoder đọc câu hỏi và chunk cùng lúc. "Hóa đơn 5707 do công ty nào
phát hành": 0.977 cho hóa đơn đúng, 0.043 cho hóa đơn kế tiếp.

**Bằng chứng chọn n.**

| rerank_n | Recall@5 | Hit@1 | MRR | p50 |
|---|---|---|---|---|
| 0 (chỉ RRF) | 0.600 | 0.500 | 0.544 | 113 ms |
| 10 | 0.700 | 0.600 | 0.639 | 231 ms |
| 20 | 0.700 | 0.600 | 0.639 | 282 ms |
| 50 | 0.733 | 0.600 | 0.646 | 511 ms |

n = 10 và n = 20 giống hệt nhau. n = 50 hơn đúng một câu semantic, trong vùng nhiễu,
với độ trễ gấp đôi. Chi phí ~9 ms mỗi ứng viên, tuyến tính.

**Cần xem lại.** Câu semantic mà n = 50 cứu được cho thấy RRF có lúc đẩy tài liệu đúng
xuống hạng 21–50. Đo lại khi gold set lên 100 câu (tuần 9).

## D3 — Không sửa tokenizer cho ngày tháng và số tiền

**Bối cảnh.** vitoken tách `2025-09-01` thành `2025`, `09`, `01`; `10%` thành `10`;
`11.363.636` thành `11363636`.

**Lựa chọn.** Giữ nguyên. Lọc ngày và MST bằng SQL trên cột `issue_date`, `mst`.

**Lý do.** Tokenizer đối xứng giữa index và query nên không vỡ. Token ngày quá phổ biến để
BM25 phân biệt; đó là việc của bộ lọc có cấu trúc, chính xác tuyệt đối. Sửa tokenizer bắt
buộc reindex và chỉ khớp một định dạng ngày.

**Bằng chứng.** BM25 thô: date_range 0.000. BM25 + SQL filter: 0.500, và
"tìm hóa đơn từ tháng 2 năm 2025" trả đúng 3 hóa đơn tháng 2.
