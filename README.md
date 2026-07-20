# vsl-langgraph

A [LangGraph](https://github.com/langchain-ai/langgraph) adapter for
[`vsl-core`](https://github.com/4vish/VSL-Core): implements `vsl_core.conformance.protocol.VSLAdapter`
and provides the LangGraph-specific wiring to call a compiled gate from a
`StateGraph` node and route around a denial.

**Is:**
- A `VSLAdapter` implementation (`LangGraphAdapter`) that passes `vsl_core.conformance.suite.run_conformance_suite` with an empty result.
- A small set of wiring helpers (`gated_node`, `route_on_denial`) for calling a compiled gate immediately before a node's side effect and routing to a blocked/terminal node via `add_conditional_edges` on denial.

**Is not:**
- A replacement for `vsl-core` itself -- the PreNode/Invariant/Fallback/TerminalState constructs, the ledger, and the governance vocabulary all live in `vsl-core`. This package only compiles and wires those constructs into LangGraph.
- Automatic interception. LangGraph has no dedicated guardrail/hook type -- a node is a plain callable, so the gate is called explicitly inside `gated_node`, the same way `vsl-core`'s own docs describe calling a gate in plain Python.

## Install

```
pip install git+https://github.com/4vish/VSL-Core.git
pip install -e .   # from a local clone of this repo
```

## Usage

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from vsl_core.constructs import PreNode
from vsl_core.metrics import AssuranceBasis, F2Modification, GammaEstimate
from vsl_langgraph import LangGraphAdapter, gated_node, route_on_denial

async def monitor(candidate_input):
    return GammaEstimate(gamma_hat=candidate_input["gamma"])

pre_node = PreNode(
    name="my-pre-node",
    description="...",
    monitor=monitor,
    assurance_basis=AssuranceBasis(f1_pre_commitment=True, f2_modification=F2Modification.FULL),
    gamma_threshold=1.0,
)
gate = LangGraphAdapter().compile_pre_node(pre_node)

def do_the_thing(state):
    return {"ran": True}

class State(TypedDict, total=False):
    gamma: float
    ran: bool
    vsl_denial: object

graph = StateGraph(State)
graph.add_node("do_the_thing", gated_node(gate, do_the_thing))
graph.add_node("blocked", lambda state: {})
graph.add_node("allowed", lambda state: {})
graph.add_edge(START, "do_the_thing")
graph.add_conditional_edges("do_the_thing", route_on_denial("blocked", "allowed"))
graph.add_edge("blocked", END)
graph.add_edge("allowed", END)
app = graph.compile()
```

`gated_node` calls the gate before `do_the_thing` runs -- if it raises
`AutomationDeniedException`, `do_the_thing` never runs and the state update
sets `vsl_denial` to the caught exception instead; `route_on_denial` reads
that key to pick the next node. F1 pre-commitment (the gate completes
strictly before the guarded side effect) holds because `gated_node` calls
`gate(...)` and only calls `node(...)` after it returns without raising.

`compile_invariant` works the same way -- pass an `Invariant` instead of a
`PreNode`, wire the resulting gate through `gated_node` the same way. An
`Invariant` violation raises the more specific `InvariantViolation`
(a subclass of `AutomationDeniedException`), which `gated_node` also
catches.

## Sample agents

`examples/` is organized by domain -- see [examples/README.md](examples/README.md)
for the full list and the roadmap for domains not built yet. Two so far:

**`examples/financial-agents/purchase_approval_agent.py`** chains both
governance primitives in one graph, synthetic and LLM-free, to show how
they actually differ in behavior:

- a `PreNode` ("purchase-confidence") -- soft, threshold-based: a monitor's
  confidence signal must clear the robust Gamma threshold
- an `Invariant` ("purchase-hard-cap") -- non-bypassable: the amount must
  never exceed a fixed cap, no matter how confident the monitor is

```
python examples/financial-agents/purchase_approval_agent.py
```

runs three scenarios against a real compiled `StateGraph`: approved,
blocked by low confidence, and -- the interesting one -- blocked by the
hard cap even when confidence is high, proving the `Invariant` can't be
talked past by a passing `PreNode`. `tests/test_purchase_approval_agent.py`
asserts the same three outcomes.

**`examples/marketing/research_publish_agent.py`** is the same gate-wiring
pattern behind five real LLM calls across three providers -- Gemini
(research), OpenAI (draft), and three different Claude models (fact-check,
compliance review, final editorial), gated the same way as above. Falls
back to canned responses automatically with no API keys set:

```
python examples/marketing/research_publish_agent.py
```

## Layout

```
src/vsl_langgraph/
├── adapter.py       LangGraphAdapter (VSLAdapter conformance contract)
└── integration.py   gated_node, route_on_denial (StateGraph wiring)
examples/
├── README.md                 domain taxonomy and roadmap
├── financial-agents/
│   └── purchase_approval_agent.py   PreNode + Invariant, no LLM calls
└── marketing/
    ├── research_publish_agent.py    same pattern, 5 real LLM calls / 3 providers
    ├── providers.py, fake_providers.py, model_ids.py
tests/
├── test_conformance.py            run_conformance_suite(LangGraphAdapter()) == []
├── test_integration.py            exercises a real compiled StateGraph
└── test_purchase_approval_agent.py   exercises the financial-agents sample's three scenarios
```

## Status

Alpha. Conformance-suite green; integration tested against a real
`StateGraph` for both the `PreNode` and `Invariant` paths (pass-through and
denial routing), including a chained multi-gate graph in the sample agent.
Not yet tested against an LLM-driven agent graph with real tool calls, and
`gated_node` doesn't implement `Fallback`'s retry/intervention fields
(`delta_factor`, `max_retries`, `intervention`) -- those aren't consumed by
`vsl-core`'s own `PlainPythonReferenceAdapter` either, so this mirrors the
reference adapter's actual behavior rather than leaving out something
`vsl-core` itself defines a contract for.
