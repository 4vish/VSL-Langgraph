from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from vsl_core.constructs import Invariant, PreNode
from vsl_core.exceptions import InvariantViolation
from vsl_core.metrics import AssuranceBasis, F2Modification, GammaEstimate

from vsl_langgraph import LangGraphAdapter, gated_node, route_on_denial

_ASSURANCE_BASIS = AssuranceBasis(f1_pre_commitment=True, f2_modification=F2Modification.FULL)


class GraphState(TypedDict, total=False):
    gamma: float
    ran_side_effect: bool
    vsl_denial: Any


async def _monitor(candidate_input: GraphState) -> GammaEstimate:
    return GammaEstimate(gamma_hat=candidate_input["gamma"])


def _build_graph():
    pre_node = PreNode(
        name="integration-test-pre-node",
        description="Requires gamma above 1.0 before the guarded node runs.",
        monitor=_monitor,
        assurance_basis=_ASSURANCE_BASIS,
        gamma_threshold=1.0,
    )
    gate = LangGraphAdapter().compile_pre_node(pre_node)

    def guarded(state: GraphState) -> dict:
        return {"ran_side_effect": True}

    graph = StateGraph(GraphState)
    graph.add_node("guarded", gated_node(gate, guarded))
    graph.add_node("blocked", lambda state: {})
    graph.add_node("allowed", lambda state: {})
    graph.add_edge(START, "guarded")
    graph.add_conditional_edges("guarded", route_on_denial("blocked", "allowed"))
    graph.add_edge("blocked", END)
    graph.add_edge("allowed", END)
    return graph.compile()


async def test_sufficient_gamma_runs_node_and_routes_to_allowed():
    result = await _build_graph().ainvoke({"gamma": 5.0})
    assert result.get("ran_side_effect") is True
    assert result.get("vsl_denial") is None


async def test_insufficient_gamma_skips_node_and_routes_to_blocked():
    result = await _build_graph().ainvoke({"gamma": 0.1})
    assert result.get("ran_side_effect") is None
    assert result.get("vsl_denial") is not None


class InvariantState(TypedDict, total=False):
    allowed: bool
    ran_side_effect: bool
    vsl_denial: Any


async def _rule(candidate_input: InvariantState) -> bool:
    return candidate_input["allowed"]


def _build_invariant_graph():
    invariant = Invariant(
        name="integration-test-invariant",
        description="Requires state['allowed'] to be True before the guarded node runs.",
        rule=_rule,
        assurance_basis=_ASSURANCE_BASIS,
    )
    gate = LangGraphAdapter().compile_invariant(invariant)

    def guarded(state: InvariantState) -> dict:
        return {"ran_side_effect": True}

    graph = StateGraph(InvariantState)
    graph.add_node("guarded", gated_node(gate, guarded))
    graph.add_node("blocked", lambda state: {})
    graph.add_node("allowed", lambda state: {})
    graph.add_edge(START, "guarded")
    graph.add_conditional_edges("guarded", route_on_denial("blocked", "allowed"))
    graph.add_edge("blocked", END)
    graph.add_edge("allowed", END)
    return graph.compile()


async def test_passing_invariant_runs_node_and_routes_to_allowed():
    result = await _build_invariant_graph().ainvoke({"allowed": True})
    assert result.get("ran_side_effect") is True
    assert result.get("vsl_denial") is None


async def test_violated_invariant_skips_node_and_routes_to_blocked():
    result = await _build_invariant_graph().ainvoke({"allowed": False})
    assert result.get("ran_side_effect") is None
    denial = result.get("vsl_denial")
    assert isinstance(denial, InvariantViolation)
