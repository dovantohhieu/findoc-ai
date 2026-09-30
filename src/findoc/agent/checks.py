from __future__ import annotations
from findoc.vnparse import parse_amounts


def ungrounded_numbers(answer: str, contexts: str, min_value: int = 1000) -> list[int]:
    """Các số trong câu trả lời KHÔNG xuất hiện ở bất kỳ nguồn nào."""
    ctx = set(parse_amounts(contexts))
    return sorted({x for x in parse_amounts(answer) if x >= min_value and x not in ctx})
