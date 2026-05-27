"""Sprint 5 — Documentation Truth verification.

Validates that critical docs reflect post-convergence reality:
  - README.md has correct directory structure
  - No stale eos_ai/.env or runtime/.env in active instructions
  - Session resume snippet uses try_load_context_from_env
  - current_system_status.md has post-convergence directory table
  - SYSTEM_ARCHITECTURE.md has correct .env path
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

REPO = Path(__file__).resolve().parents[1]


class TestReadmeAccuracy:
    def test_no_eos_ai_env_reference(self):
        readme = (REPO / "README.md").read_text()
        assert "eos_ai/.env" not in readme

    def test_has_post_convergence_structure(self):
        readme = (REPO / "README.md").read_text()
        assert "substrate/" in readme
        assert "adapters/" in readme
        assert "transports/" in readme

    def test_no_stale_core_dir(self):
        readme = (REPO / "README.md").read_text()
        assert "core/" not in readme or "core/" in readme.split("##")[-1]

    def test_no_placeholder_urls(self):
        readme = (REPO / "README.md").read_text()
        assert "[repo]" not in readme


class TestClaudeMdAccuracy:
    def test_session_resume_uses_try_load(self):
        claude_md = (REPO / ".claude" / "CLAUDE.md").read_text()
        assert "try_load_context_from_env" in claude_md

    def test_session_resume_no_ctx_stage(self):
        claude_md = (REPO / ".claude" / "CLAUDE.md").read_text()
        assert "ctx.stage" not in claude_md


class TestSystemArchitecture:
    def test_no_runtime_env_path(self):
        path = REPO / "docs" / "SYSTEM_ARCHITECTURE.md"
        if not path.exists():
            pytest.skip("SYSTEM_ARCHITECTURE.md not found")
        content = path.read_text()
        assert "runtime/.env" not in content


class TestCurrentSystemStatus:
    def test_has_post_convergence_dirs(self):
        path = REPO / "docs" / "system" / "current_system_status.md"
        if not path.exists():
            pytest.skip("current_system_status.md not found")
        content = path.read_text()
        assert "substrate/" in content
        assert "adapters/" in content
        assert "post-convergence" in content.lower()


class TestCorporateStructure:
    def test_no_agentOS_reference(self):
        path = REPO / "docs" / "corporate-structure.md"
        if not path.exists():
            pytest.skip("corporate-structure.md not found")
        content = path.read_text()
        assert "AgentOS" not in content
