"""Path resolution for the Tool Mastery Author Agent."""

from __future__ import annotations

import os
from pathlib import Path

EOS_ROOT = Path(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

SKILLS_TOOLS_DIR = EOS_ROOT / "skills" / "tools"
RESEARCH_LOG_DIR = EOS_ROOT / "logs" / "tool_mastery_research"
AUTHOR_LOG_DIR = EOS_ROOT / "logs" / "tool_mastery_author"
SCAFFOLD_SCRIPT = (
    EOS_ROOT / "skills" / "meta" / "tool_mastery_engine" / "scripts" / "scaffold_tool_skill.py"
)
VERIFY_SCRIPT = EOS_ROOT / "scripts" / "verify_tool_skill.py"
