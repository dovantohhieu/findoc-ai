import numpy as np
from findoc.embed import embed

sents = [
    "Tổng tiền thanh toán: 12.500.000 đồng",             # 0
    "Số tiền phải trả là mười hai triệu năm trăm nghìn",  # 1  ~ giống 0
    "Thành tiền sau thuế: 12,5 triệu VND",                # 2  ~ giống 0
    "Thuế suất giá trị gia tăng 10%",                     # 3
    "Địa chỉ bên mua: số 5 Lê Duẩn, Hà Nội",              # 4
    "Trụ sở của người mua đặt tại Hà Nội",                # 5  ~ giống 4
]

V = embed(sents)
print("shape:", V.shape, "| norm mẫu:", round(float(np.linalg.norm(V[0])), 4))

S = V @ V.T
np.set_printoptions(precision=3, suppress=True)
print("\nMa trận cosine similarity:")
print(S)

print("\nCác cặp gần nhất:")
n = len(sents)
pairs = sorted(((S[i, j], i, j) for i in range(n) for j in range(i + 1, n)), reverse=True)
for s, i, j in pairs[:4]:
    print(f"  {s:.3f}  [{i}] {sents[i][:38]:38}  ||  [{j}] {sents[j][:38]}")
