from __future__ import annotations
import os


def callbacks() -> list:
    """Trả về handler Langfuse nếu đã cấu hình key, ngược lại trả list rỗng (chạy không cần Langfuse vẫn được)."""
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        return []
    from langfuse.langchain import CallbackHandler
    return [CallbackHandler()]


def flush() -> None:
    """Gọi ở cuối script ngắn — nếu không, trace có thể chưa kịp gửi thì tiến trình đã thoát."""
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        return
    from langfuse import get_client
    get_client().flush()
