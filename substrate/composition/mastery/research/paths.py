"""Path resolution for the Tool Mastery Research Agent.

Root resolution delegated to core.paths (UMH_ROOT → OS_ROOT → EOS_ROOT → /opt/OS).
"""

from __future__ import annotations

import os
from pathlib import Path

from core.paths import ROOT as EOS_ROOT

SKILLS_TOOLS_DIR = EOS_ROOT / "skills" / "tools"
TME_DIR = EOS_ROOT / "skills" / "meta" / "tool_mastery_engine"
TOOL_DOC_REGISTRY = TME_DIR / "references" / "tool_doc_registry.md"

RESEARCH_LOG_DIR = EOS_ROOT / "logs" / "tool_mastery_research"
DEFERRED_DIR = EOS_ROOT / "logs" / "deferred"

CLAUDE_JSON = Path(os.environ.get("CLAUDE_JSON", str(Path.home() / ".claude.json")))
