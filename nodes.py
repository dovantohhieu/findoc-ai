from findoc.agent.aggregate import run_aggregate

REFUSAL = "Câu hỏi này nằm ngoài phạm vi tra cứu chứng từ tài chính của hệ thống."


def aggregate(state: dict) -> dict:
    agg = run_aggregate(state.get("filters") or {})
    return {"agg": agg, "answer": agg["text"], "citations": EMPTY_CITES}


def refuse(state: dict) -> dict:
    return {"answer": REFUSAL, "citations": EMPTY_CITES}
