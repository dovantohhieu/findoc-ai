from __future__ import annotations
from typing import TypedDict


class AgentState(TypedDict, total=False):
    question: str
    route: str          # lookup | aggregate | out_of_scope
    route_by: str       # rule | llm — để biết lỗi route đến từ đâu
    filters: dict
    rows: list[dict]    # chunk truy xuất được (nhánh lookup)
    debug: dict         # danh sách ứng viên trước rerank — cho error analysis tuần 10
    agg: dict           # kết quả SQL (nhánh aggregate)
    answer: str
    citations: dict
    checks: dict
    confidence: dict    # {"level": ..., "reasons": [...]}
    review: dict        # quyết định của người duyệt (tuần 9)
    status: str         # answered | pending_review | approved | edited | rejected
