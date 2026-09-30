from __future__ import annotations
import os, re

# Ngưỡng điểm liên quan. PHẢI hiệu chuẩn lại trên dữ liệu thật (bước 2), rồi ghi vào .env
HIGH = float(os.getenv("FINDOC_CONF_HIGH", "0.5"))
MED = float(os.getenv("FINDOC_CONF_MED", "0.2"))
SCORE_KEYS = ("rerank_score", "score", "rrf_score", "rrf")


def _score(r: dict) -> float | None:
    for k in SCORE_KEYS:
        if isinstance(r.get(k), (int, float)):
            return float(r[k])
    return None


def classify(rows: list[dict], answer: str = "", cites: dict | None = None) -> dict:
    """Mức tin cậy dựa trên nguồn: none / low / medium / high."""
    if not rows:
        return {"level": "none", "best_score": None, "reason": "không có nguồn"}
    scores = [s for s in (_score(r) for r in rows) if s is not None]
    best = max(scores) if scores else None
    cited = {int(x) for x in re.findall(r"\[(\d+)\]", answer or "")}
    if any(c < 1 or c > len(rows) for c in cited):
        return {"level": "low", "best_score": best,
                "reason": "trích dẫn trỏ ra ngoài danh sách nguồn"}
    if best is None:
        return {"level": "medium", "best_score": None, "reason": "nguồn không có điểm liên quan"}
    if best >= HIGH:
        return {"level": "high", "best_score": best, "reason": f"nguồn tốt nhất {best:.3f} ≥ {HIGH}"}
    if best >= MED:
        return {"level": "medium", "best_score": best, "reason": f"nguồn tốt nhất {best:.3f} dưới {HIGH}"}
    return {"level": "low", "best_score": best, "reason": f"nguồn tốt nhất {best:.3f} dưới {MED}"}
