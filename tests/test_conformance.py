from vsl_core.conformance.suite import run_conformance_suite

from vsl_langgraph import LangGraphAdapter


def test_langgraph_adapter_is_conformant():
    failures = run_conformance_suite(LangGraphAdapter())
    assert failures == []
