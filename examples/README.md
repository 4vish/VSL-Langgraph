# Sample agents

Each subfolder is a self-contained example of `vsl-langgraph`'s gate-wiring
(`compile_pre_node`/`compile_invariant`, `gated_node`, `route_on_denial`)
applied to a specific domain. The wiring code is identical across all of
them -- what changes is what the gates are checking and what they're
guarding, which is the point: the domain doesn't change how VSL governs it.

## Built

- **`financial-agents/`** -- `purchase_approval_agent.py`. Synthetic, no
  LLM calls: a spending cap approval chaining a `PreNode` (confidence
  threshold) and an `Invariant` (hard cap, non-bypassable). The fastest way
  to read the gate-wiring pattern with nothing else competing for
  attention.
- **`marketing/`** -- `research_publish_agent.py`. Real LLM calls across
  three providers (Gemini research, OpenAI draft, three different Claude
  models for fact-check / compliance / final editorial), gated the same
  way. Falls back to `fake_providers.py`'s canned responses automatically
  if `OPENAI_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` aren't all
  set, so it's runnable with zero setup.

## Roadmap (not built yet)

- **`chat-conversation/`** -- governance on a conversational agent's
  *output*, not a backend action: an `Invariant` blocking any reply that
  contains an unverified legal/medical/refund guarantee, a `PreNode`
  gating hand-off-to-a-human when the agent's own confidence is low.
- **`simple/`** -- a single-gate "hello world," shorter than
  `financial-agents/purchase_approval_agent.py`, once one exists that's
  worth the extra folder.

Have a domain you want an example for? A new subfolder should follow the
same shape as the two above: a `build_agent()` function returning a
compiled `StateGraph`, real or fake provider calls kept in their own file
if it needs one, and a test in `../tests/` that exercises all of its gate
outcomes.
