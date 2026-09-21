"""Ghi mỗi lần truy vấn thành một dòng JSONL — đầu vào cho RAGAS tuần 8."""
from __future__ import annotations
import json, pathlib, datetime

LOG_PATH = pathlib.Path("logs/queries.jsonl")


def log_query(question: str, filters: dict, rows: list[dict], ms: float,
              top_k: int, **extra) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "filters": {k: str(v) for k, v in (filters or {}).items()},
        "top_k": top_k,
        "ms": round(ms, 1),
        "hits": [{"doc_id": r.get("doc_id"), "chunk_index": r.get("chunk_index"),
                  "score": r.get("score")} for r in rows[:top_k]],
        **extra,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
