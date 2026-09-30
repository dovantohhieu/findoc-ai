"""Hàm gọi LLM thật, truyền vào answer(llm=...)."""
from __future__ import annotations
import os
from functools import lru_cache
from anthropic import Anthropic

MODEL = os.getenv("ANSWER_MODEL", "claude-haiku-4-5-20251001")


@lru_cache(maxsize=1)
def _client() -> Anthropic:
    return Anthropic()


def claude_llm(system: str, user: str, max_tokens: int = 600) -> str:
    r = _client().messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in r.content if b.type == "text")
