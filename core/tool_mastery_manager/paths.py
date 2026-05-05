"""Path resolution for the Tool Mastery Manager.

Centralised so portability work can replace hardcoded /opt/OS with an
EOS_ROOT env var in exactly one place. Everything in the manager imports
paths from here rather than hardcoding.
"""

from __future__ import annotations

import os
from pathlib import Path

EOS_ROOT = Path(os.environ.get("EOS_ROOT", "/opt/OS"))

SKILLS_TOOLS_DIR = EOS_ROOT / "skills" / "tools"
CONFIG_DIR = EOS_ROOT / "config"
SEED_LIST_PATH = CONFIG_DIR / "tool_mastery_seeds.yaml"
EXCLUDE_LIST_PATH = CONFIG_DIR / "tool_mastery_exclude.yaml"
SCRIPTS_DIR = EOS_ROOT / "scripts"
RESEARCH_DISPATCHER = SCRIPTS_DIR / "tool_mastery_research_dispatcher.py"
SCAFFOLD_SCRIPT = (
    EOS_ROOT / "skills" / "meta" / "tool_mastery_engine" / "scripts" / "scaffold_tool_skill.py"
)
BACKLOG_DIR = EOS_ROOT / "logs" / "tool_mastery_manager"
CLAUDE_JSON = Path(os.environ.get("CLAUDE_JSON", str(Path.home() / ".claude.json")))
