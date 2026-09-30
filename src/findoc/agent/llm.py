from __future__ import annotations
import os
from functools import lru_cache
from langchain.chat_models import init_chat_model

# Đổi model không cần sửa code, ví dụ: "google_genai:gemini-2.5-flash-lite"
CHAT_MODEL = os.getenv("FINDOC_CHAT_MODEL", "anthropic:claude-haiku-4-5-20251001")


@lru_cache(maxsize=1)
def chat_model():
    return init_chat_model(CHAT_MODEL, max_tokens=500)
