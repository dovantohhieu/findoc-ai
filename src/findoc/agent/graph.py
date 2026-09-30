from __future__ import annotations
from langgraph.graph import END, START, StateGraph

from findoc.agent import nodes as n
from findoc.agent.state import AgentState


def build_graph(checkpointer=None):
    g = StateGraph(AgentState)
    for name in ("classify", "retrieve", "generate", "aggregate", "refuse", "validate", "finalize"):
        g.add_node(name, getattr(n, name))

    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", lambda s: s["route"],
                            {"lookup": "retrieve", "aggregate": "aggregate",
                             "out_of_scope": "refuse"})
    g.add_edge("retrieve", "generate")
    for src in ("generate", "aggregate", "refuse"):
        g.add_edge(src, "validate")
    # tuần 8: "review" tạm thời cũng đi tới finalize — tuần 9 mới rẽ sang người duyệt
    g.add_conditional_edges("validate", n.after_validate,
                            {"review": "finalize", "done": "finalize"})
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)
