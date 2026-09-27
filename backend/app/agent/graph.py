"""LangGraph wiring of the assessment pipeline.

Two engines share every node except the decider:
- "llm"   (Phase 1 baseline): LLM judges eligibility, then the verifier prunes
          any claim it cannot match to retrieved official text.
- "rules" (Phase 2, default): the deterministic rules engine decides; the LLM
          only extracts facts and phrases the explanations.
"""

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import assess, build_profile, retrieve, verify_and_compose
from app.agent.rules_nodes import rules_assess_and_compose
from app.agent.state import AgentState
from app.config import settings


def _route_after_profile(state: AgentState) -> str:
    return "retrieve" if state["status"] == "ok" else END


def build_graph(engine: str):
    graph = StateGraph(AgentState)
    graph.add_node("build_profile", build_profile)
    graph.add_node("retrieve", retrieve)
    graph.add_edge(START, "build_profile")
    graph.add_conditional_edges("build_profile", _route_after_profile)

    if engine == "rules":
        graph.add_node("rules_assess", rules_assess_and_compose)
        graph.add_edge("retrieve", "rules_assess")
        graph.add_edge("rules_assess", END)
    else:
        graph.add_node("assess", assess)
        graph.add_node("verify_and_compose", verify_and_compose)
        graph.add_edge("retrieve", "assess")
        graph.add_edge("assess", "verify_and_compose")
        graph.add_edge("verify_and_compose", END)
    return graph.compile()


_pipelines: dict[str, object] = {}


def get_pipeline(engine: str):
    if engine not in _pipelines:
        _pipelines[engine] = build_graph(engine)
    return _pipelines[engine]


def run_assessment(
    message: str, prior_profile: dict | None = None, engine: str | None = None
) -> AgentState:
    engine = engine or settings.eligibility_engine
    return get_pipeline(engine).invoke({"message": message, "prior_profile": prior_profile})
