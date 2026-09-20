"""Sinh câu hỏi ứng viên cho gold set. Output là BẢN NHÁP, phải duyệt tay."""
import json, random, yaml
from pathlib import Path
from findoc.db import connect

import os, sys, time
from anthropic import Anthropic

_client = Anthropic()
MODEL = os.getenv("GOLD_MODEL", "claude-haiku-4-5-20251001")

def ask(prompt: str) -> dict:
    for lan in range(3):
        try:
            r = _client.messages.create(
                model=MODEL, max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": "{"},
                ],
            )
            return json.loads("{" + r.content[0].text)
        except Exception as e:
            print(f"  !! lỗi lần {lan+1}: {e}", file=sys.stderr)
            time.sleep(2 ** lan)
    return {"question": "", "gold_answer": ""}
random.seed(42)
N_DOCS = int(os.getenv("N_DOCS", 30))

KINDS = {  # phân bổ ép buộc — không để model tự chọn
    "exact_lookup": 5, "metadata_filter": 4, "numeric": 4, "paraphrase": 5,
    "semantic": 4, "item_lookup": 3, "date_range": 2, "synonym": 2, "negative": 1,
}

PROMPT = """Bạn đang tạo bộ test cho hệ thống tìm kiếm tài liệu tài chính tiếng Việt.

Đoạn tài liệu:
---
{chunk}
---

Đặt MỘT câu hỏi loại "{kind}" mà đoạn trên trả lời được.

Ràng buộc bắt buộc:
- KHÔNG dùng lại nguyên cụm từ dài (>3 từ) có trong đoạn. Phải diễn đạt lại.
- Viết như người dùng thật gõ vào ô tìm kiếm, không như đề thi.
- Với loại "paraphrase" và "synonym": dùng từ ngữ nghiệp vụ KHÁC hẳn đoạn gốc.
- Với loại "exact_lookup": được phép nhắc số hóa đơn hoặc MST.

Trả về JSON thuần, không markdown:
{{"question": "...", "gold_answer": "...", "kind": "{kind}"}}"""


def main():
    with connect() as c, c.cursor() as cur:
        cur.execute("SELECT doc_id, chunk_index, text FROM chunks ORDER BY random() LIMIT %s;",
                    (sum(KINDS.values()),))
        rows = cur.fetchall()

    plan = [k for k, n in KINDS.items() for _ in range(n)]
    random.shuffle(plan)

    draft = []
    for i, ((doc_id, ci, text), kind) in enumerate(zip(rows, plan), start=1):
        kq = ask(PROMPT.format(chunk=text[:1200], kind=kind))
        print(f"[{i:02d}] {kind:16} {kq.get('question','')[:60]}")
        draft.append({
            "id": f"g{i:02d}",
            "kind": kind,
            "expected_doc_ids": [doc_id],
            "source_chunk": f"{doc_id}#{ci}",
            "question": kq.get("question", ""),
            "gold_answer": kq.get("gold_answer", ""),
            "reviewed": False,
        })

    Path("eval").mkdir(exist_ok=True)
    Path("eval/gold30.draft.yaml").write_text(
        yaml.safe_dump(draft, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"đã tạo {len(draft)} prompt → eval/gold30.draft.yaml")


if __name__ == "__main__":
    main()
