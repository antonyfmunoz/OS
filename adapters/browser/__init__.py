"""Browser adapter — re-exports from substrate execution layer.

ARCHITECTURE.md specifies adapters/browser/ as the adapter-layer entry point.
The implementation lives at substrate/execution/agents/browser_agent.py (Playwright).
This module re-exports the public API so consumers import from the adapter layer.
"""

from substrate.execution.agents.browser_agent import BrowserAgent, run_browser_task

__all__ = ["BrowserAgent", "run_browser_task"]
