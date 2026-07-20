import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples" / "financial-agents"))

from purchase_approval_agent import build_agent  # noqa: E402


async def test_high_confidence_under_cap_is_approved():
    result = await build_agent().ainvoke({"amount": 250.0, "confidence": 5.0})
    assert result.get("approved") is True
    assert result.get("confidence_denial") is None
    assert result.get("cap_denial") is None


async def test_low_confidence_is_blocked_before_cap_check_runs():
    result = await build_agent().ainvoke({"amount": 250.0, "confidence": 0.2})
    assert result.get("approved") is None
    assert result.get("confidence_denial") is not None
    assert result.get("cap_denial") is None


async def test_high_confidence_cannot_bypass_hard_cap():
    result = await build_agent().ainvoke({"amount": 5000.0, "confidence": 5.0})
    assert result.get("approved") is None
    assert result.get("confidence_denial") is None
    assert result.get("cap_denial") is not None
