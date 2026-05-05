"""Path resolution for the Tool Mastery Research Agent.

Centralised so portability work can replace hardcoded /opt/OS with an
EOS_ROOT env var in exactly one place. Mirrors the Manager's paths.py
pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

EOS_ROOT = Path(os.environ.get("EOS_ROOT", "/opt/OS"))

SKILLS_TOOLS_DIR = EOS_ROOT / "skills" / "tools"
TME_DIR = EOS_ROOT / "skills" / "meta" / "tool_mastery_engine"
TOOL_DOC_REGISTRY = TME_DIR / "references" / "tool_doc_registry.md"

RESEARCH_LOG_DIR = EOS_ROOT / "logs" / "tool_mastery_research"
DEFERRED_DIR = EOS_ROOT / "logs" / "deferred"

CLAUDE_JSON = Path(os.environ.get("CLAUDE_JSON", str(Path.home() / ".claude.json")))
