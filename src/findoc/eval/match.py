from __future__ import annotations
import re
from rapidfuzz import fuzz
from findoc.vnparse import norm_text, parse_amounts, parse_dates

FUZZY_THRESHOLD = 90
REFUSAL_MARKERS = ("không tìm thấy", "ngoài phạm vi", "không đủ căn cứ")


def is_refusal(answer: str) -> bool:
    a = norm_text(answer)
    return any(m in a for m in REFUSAL_MARKERS)


def check_fact(fact: dict, answer: str) -> dict:
    t, v = fact["type"], fact["value"]
    if t == "amount":
        ok, how = any(abs(x - int(v)) <= 1 for x in parse_amounts(answer)), "exact"
    elif t == "mst":
        ok, how = str(v) in re.sub(r"\s", "", answer), "exact"
    elif t == "invoice_no":
        runs = re.findall(r"\d+", answer)
        ok, how = any(r.lstrip("0") == str(v).lstrip("0") for r in runs), "exact"
    elif t == "date":
        ok, how = str(v) in parse_dates(answer), "exact"
    else:
        score = fuzz.partial_ratio(norm_text(str(v)), norm_text(answer))
        ok, how = score >= FUZZY_THRESHOLD, f"fuzzy:{score:.0f}"
    return {"type": t, "value": v, "ok": ok, "how": how}


def score_item(item: dict, answer: str) -> dict:
    refused = is_refusal(answer)
    if item.get("expect_refusal"):
        return {"facts": [], "ok": refused}
    facts = [check_fact(f, answer) for f in item.get("key_facts") or []]
    return {"facts": facts, "ok": (not refused) and all(f["ok"] for f in facts)}
