"""Phase 86 — EOS Tomorrow Operating Loop v1.

Unified daily operating cycle that threads open_day, close_day, daily briefing,
workflow tracking, review, and handoff into a single orchestrated loop.

The Tomorrow Loop is the minimum EOS functionality needed for the user to
wake up and use EOS to run and improve the first operating workflow.

No direct execution of external tools. No LLM calls in contracts.
Orchestrator may call adapters through the execution spine only.
"""
