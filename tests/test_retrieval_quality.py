"""Cổng hồi quy chất lượng retrieval. Chạy: pytest -m eval (từ thư mục gốc dự án)."""
import pathlib, statistics
import pytest, yaml
from findoc.eval.run import run_one, _metrics
from findoc.search import hybrid_search

pytestmark = pytest.mark.eval
GOLD = pathlib.Path("eval/gold30.yaml")
K = 5

# Ngưỡng = số đo thật − 0.05 (n=30, một câu = 0.033). Chỉ được NÂNG, không bao giờ hạ.
MIN_RECALL5_HYBRID = 0.65   # hybrid_rerank đo được 0.700 − 0.05


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else 0.0


def _score(fn) -> dict:
    qs = yaml.safe_load(GOLD.read_text(encoding="utf-8"))
    rows = []
    for q in qs:
        exp = set(q.get("expected_doc_ids") or [])
        got, _ = run_one(fn, q["question"], K)
        m = _metrics(got, exp, K)
        uniq = list(dict.fromkeys(d for d in got if d))
        m["hit1"] = float(bool(uniq) and uniq[0] in exp)
        rows.append(m)
    return {k: round(_mean(r[k] for r in rows), 3) for k in ("recall", "hit1", "mrr")}


@pytest.fixture(scope="module")
def rrf():
    return _score(lambda q, top_k=K, **kw: hybrid_search(q, top_k=top_k, log=False))


@pytest.fixture(scope="module")
def rerank():
    return _score(lambda q, top_k=K, **kw:
                  hybrid_search(q, top_k=top_k, use_reranker=True, log=False))


def test_hybrid_recall_khong_tut(rerank):
    assert rerank["recall"] >= MIN_RECALL5_HYBRID, f"hybrid_rerank tụt: {rerank}"


def test_reranker_khong_lam_hai_hit1(rrf, rerank):
    assert rerank["hit1"] >= rrf["hit1"] - 0.034, f"rrf={rrf} rerank={rerank}"


def test_tra_cuu_so_hoa_don_5707():
    rows = hybrid_search("hóa đơn 5707 do công ty nào phát hành",
                         top_k=5, use_reranker=True, log=False)
    assert rows, "không trả về gì"
    assert rows[0]["doc_id"] == "0469138107_1C25TSV_00005707", rows[0]["doc_id"]
    assert rows[0]["score"] > 0.5, rows[0]["score"]


def test_cau_khong_co_dap_an_diem_thap():
    rows = hybrid_search("bên nào phải trả tiền cho lô máy in",
                         top_k=5, use_reranker=True, log=False)
    assert not rows or rows[0]["score"] < 0.1, rows[0]["score"]
