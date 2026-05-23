"""Path resolution for the Tool Mastery Author Agent.

Root resolution delegated to core.paths (UMH_ROOT → OS_ROOT → EOS_ROOT → /opt/OS).
"""

from __future__ import annotations

import os
from pathlib import Path

from core.paths import ROOT as EOS_ROOT

SKILLS_TOOLS_DIR = EOS_ROOT / "skills" / "tools"
RESEARCH_LOG_DIR = EOS_ROOT / "logs" / "tool_mastery_research"
AUTHOR_LOG_DIR = EOS_ROOT / "logs" / "tool_mastery_author"
SCAFFOLD_SCRIPT = (
    EOS_ROOT / "skills" / "meta" / "tool_mastery_engine" / "scripts" / "scaffold_tool_skill.py"
)
VERIFY_SCRIPT = EOS_ROOT / "scripts" / "verify_tool_skill.py"
