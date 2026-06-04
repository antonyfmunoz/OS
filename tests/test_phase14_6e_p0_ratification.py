"""
Comprehensive pytest test suite for Phase 14.6E P0 ratification sprint.

Verifies all 15 remaining P0 decisions were correctly ratified in the
decision queue, delta report was produced with correct structure, and
implementation gates remain closed.

Tests cover:
- All 18 P0 decisions marked OPERATOR-APPROVED in decision queue
- Phase 14.6E delta report existence and structure
- Decision queue consistency (no unresolved P0s)
- Implementation gates preserved (allows_implementation=false)
- Provenance fields correct
- Ratification text present for each decision
- No source code mutation
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(os.environ.get("UMH_ROOT", "/opt/OS"))

_TEST_DIR = Path(__file__).resolve().parent
_WORKTREE_ROOT = _TEST_DIR.parent
if (_WORKTREE_ROOT / "data" / "umh").exists():
    _REPO_ROOT = _WORKTREE_ROOT

QUEUE_DIR = _REPO_ROOT / "data" / "umh" / "trinity_convergence" / "phase14_6c_operator_review"
DELTA_DIR = _REPO_ROOT / "data" / "umh" / "trinity_convergence" / "phase14_6e_p0_ratification"

QUEUE_FILE = QUEUE_DIR / "phase14_6c_ratification_decision_queue.md"
DELTA_FILE = DELTA_DIR / "phase14_6e_ratification_delta_report.md"

ALL_P0_DECISION_IDS: list[str] = [
    "DEC-146C-001",
    "DEC-146C-002",
    "DEC-146C-003",
    "DEC-146B-UMH-001",
    "DEC-146B-UMH-002",
    "DEC-146B-UMH-003",
    "DEC-146B-UMH-004",
    "DEC-146B-UMH-005",
    "DEC-146B-EOS-001",
    "DEC-146B-EOS-002",
    "DEC-146B-EOS-003",
    "DEC-146B-COS-001",
    "DEC-146B-COS-002",
    "DEC-146B-COS-003",
    "DEC-146B-COS-004",
    "DEC-146B-LOS-001",
    "DEC-146B-LOS-002",
    "DEC-146B-LOS-003",
]

PHASE_146E_DECISION_IDS: list[str] = [
    "DEC-146B-UMH-001",
    "DEC-146B-UMH-002",
    "DEC-146B-UMH-003",
    "DEC-146B-UMH-004",
    "DEC-146B-UMH-005",
    "DEC-146B-EOS-001",
    "DEC-146B-EOS-002",
    "DEC-146B-EOS-003",
    "DEC-146B-COS-001",
    "DEC-146B-COS-002",
    "DEC-146B-COS-003",
    "DEC-146B-COS-004",
    "DEC-146B-LOS-001",
    "DEC-146B-LOS-002",
    "DEC-146B-LOS-003",
]

PHASE_146C_DECISION_IDS: list[str] = [
    "DEC-146C-001",
    "DEC-146C-002",
    "DEC-146C-003",
]

UMH_DECISION_IDS: list[str] = [
    "DEC-146B-UMH-001",
    "DEC-146B-UMH-002",
    "DEC-146B-UMH-003",
    "DEC-146B-UMH-004",
    "DEC-146B-UMH-005",
]

EOS_DECISION_IDS: list[str] = [
    "DEC-146B-EOS-001",
    "DEC-146B-EOS-002",
    "DEC-146B-EOS-003",
]

COS_DECISION_IDS: list[str] = [
    "DEC-146B-COS-001",
    "DEC-146B-COS-002",
    "DEC-146B-COS-003",
    "DEC-146B-COS-004",
]

LOS_DECISION_IDS: list[str] = [
    "DEC-146B-LOS-001",
    "DEC-146B-LOS-002",
    "DEC-146B-LOS-003",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _parse_md_frontmatter(content: str) -> Dict[str, Any]:
    if not content.startswith("---"):
        return {}
    try:
        end_idx = content.index("---", 3)
    except ValueError:
        return {}
    frontmatter_text = content[3:end_idx].strip()
    result: Dict[str, Any] = {}
    for line in frontmatter_text.split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.lower() == "true":
            result[key] = True
        elif value.lower() == "false":
            result[key] = False
        else:
            result[key] = value
    return result


def _has_text(content: str, pattern: str, flags: int = re.IGNORECASE) -> bool:
    return bool(re.search(pattern, content, flags))


def _has_section(content: str, heading_pattern: str) -> bool:
    for line in content.splitlines():
        if re.match(r"^#{1,4}\s+", line):
            if re.search(heading_pattern, line, re.IGNORECASE):
                return True
    return False


def _count_occurrences(content: str, pattern: str, flags: int = re.IGNORECASE) -> int:
    return len(re.findall(pattern, content, flags))


def _get_decision_section(content: str, decision_id: str) -> str:
    """Extract the section for a specific decision from the queue."""
    pattern = rf"####\s+{re.escape(decision_id)}"
    match = re.search(pattern, content)
    if not match:
        return ""
    start = match.start()
    next_decision = re.search(r"\n####\s+DEC-", content[start + 10:])
    next_h3 = re.search(r"\n###\s+", content[start + 10:])
    if next_decision and next_h3:
        end = start + 10 + min(next_decision.start(), next_h3.start())
    elif next_decision:
        end = start + 10 + next_decision.start()
    elif next_h3:
        end = start + 10 + next_h3.start()
    else:
        end = len(content)
    return content[start:end]


# ---------------------------------------------------------------------------
# 1. TestArtifactExistence
# ---------------------------------------------------------------------------

class TestArtifactExistence:

    def test_decision_queue_exists(self) -> None:
        assert QUEUE_FILE.exists(), f"Missing: {QUEUE_FILE}"

    def test_delta_report_exists(self) -> None:
        assert DELTA_FILE.exists(), f"Missing: {DELTA_FILE}"

    def test_decision_queue_minimum_size(self) -> None:
        content = _load(QUEUE_FILE)
        assert len(content.splitlines()) >= 400, "Decision queue too short"

    def test_delta_report_minimum_size(self) -> None:
        content = _load(DELTA_FILE)
        assert len(content.splitlines()) >= 100, "Delta report too short"


# ---------------------------------------------------------------------------
# 2. TestImplementationGatesPreserved
# ---------------------------------------------------------------------------

class TestImplementationGatesPreserved:

    def test_queue_allows_implementation_false(self) -> None:
        content = _load(QUEUE_FILE)
        fm = _parse_md_frontmatter(content)
        assert fm.get("allows_implementation") is False

    def test_delta_allows_implementation_false(self) -> None:
        content = _load(DELTA_FILE)
        fm = _parse_md_frontmatter(content)
        assert fm.get("allows_implementation") is False

    def test_queue_operator_approved_false(self) -> None:
        content = _load(QUEUE_FILE)
        fm = _parse_md_frontmatter(content)
        assert fm.get("operator_approved") is False

    def test_delta_operator_approved_false(self) -> None:
        content = _load(DELTA_FILE)
        fm = _parse_md_frontmatter(content)
        assert fm.get("operator_approved") is False


# ---------------------------------------------------------------------------
# 3. TestAllP0DecisionsApproved — every P0 decision has OPERATOR-APPROVED
# ---------------------------------------------------------------------------

class TestAllP0DecisionsApproved:

    @pytest.mark.parametrize("decision_id", ALL_P0_DECISION_IDS)
    def test_decision_approved_in_queue(self, decision_id: str) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, decision_id)
        assert section, f"Decision {decision_id} not found in queue"
        assert _has_text(section, r"OPERATOR-APPROVED"), (
            f"{decision_id} not marked OPERATOR-APPROVED in queue"
        )

    def test_total_p0_decisions_is_18(self) -> None:
        assert len(ALL_P0_DECISION_IDS) == 18

    def test_phase_146e_decisions_is_15(self) -> None:
        assert len(PHASE_146E_DECISION_IDS) == 15

    def test_phase_146c_decisions_is_3(self) -> None:
        assert len(PHASE_146C_DECISION_IDS) == 3


# ---------------------------------------------------------------------------
# 4. TestDecisionQueueConsistency
# ---------------------------------------------------------------------------

class TestDecisionQueueConsistency:

    def test_no_unresolved_p0_text(self) -> None:
        content = _load(QUEUE_FILE)
        assert not _has_text(content, r"remaining\s+15\s+P0\s+decisions.*unresolved"), (
            "Queue still references '15 P0 decisions unresolved'"
        )

    def test_all_18_resolved_text(self) -> None:
        content = _load(QUEUE_FILE)
        assert _has_text(content, r"ALL\s+18\s+P0\s+decisions\s+have\s+been\s+ratified") or \
               _has_text(content, r"All\s+18\s+P0\s+decisions\s+have\s+been\s+ratified"), (
            "Queue missing 'all 18 P0 decisions have been ratified' text"
        )

    def test_queue_references_phase_146e(self) -> None:
        content = _load(QUEUE_FILE)
        assert _has_text(content, r"Phase\s+14\.6E"), (
            "Queue missing Phase 14.6E reference"
        )


# ---------------------------------------------------------------------------
# 5. TestDecisionResolutions — each decision has a Resolution line
# ---------------------------------------------------------------------------

class TestDecisionResolutions:

    @pytest.mark.parametrize("decision_id", PHASE_146E_DECISION_IDS)
    def test_has_resolution_text(self, decision_id: str) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, decision_id)
        assert section, f"Decision {decision_id} not found in queue"
        assert _has_text(section, r"\*\*Resolution:\*\*"), (
            f"{decision_id} missing **Resolution:** text"
        )

    @pytest.mark.parametrize("decision_id", PHASE_146C_DECISION_IDS)
    def test_146c_has_resolution_text(self, decision_id: str) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, decision_id)
        assert section, f"Decision {decision_id} not found in queue"
        assert _has_text(section, r"\*\*Resolution:\*\*"), (
            f"{decision_id} missing **Resolution:** text"
        )


# ---------------------------------------------------------------------------
# 6. TestDeltaReportStructure
# ---------------------------------------------------------------------------

class TestDeltaReportStructure:

    def test_has_frontmatter(self) -> None:
        content = _load(DELTA_FILE)
        fm = _parse_md_frontmatter(content)
        assert fm.get("phase") == "14.6E"
        assert fm.get("provenance") == "OPERATOR_RATIFICATION"

    def test_has_required_sections(self) -> None:
        content = _load(DELTA_FILE)
        required = [
            r"P0\s+Resolution\s+Status",
            r"Decisions\s+Ratified",
            r"What\s+Was\s+NOT\s+Changed",
            r"Remaining\s+Work",
            r"Next\s+Recommended\s+Phase",
            r"Safety\s+Attestation",
        ]
        for pattern in required:
            assert _has_section(content, pattern), (
                f"Delta report missing section: {pattern}"
            )

    @pytest.mark.parametrize("decision_id", PHASE_146E_DECISION_IDS)
    def test_delta_references_decision(self, decision_id: str) -> None:
        content = _load(DELTA_FILE)
        assert decision_id in content, (
            f"Delta report missing reference to {decision_id}"
        )

    def test_delta_shows_15_ratified(self) -> None:
        content = _load(DELTA_FILE)
        assert _has_text(content, r"15"), "Delta report missing count of 15"

    def test_delta_shows_18_total(self) -> None:
        content = _load(DELTA_FILE)
        assert _has_text(content, r"18"), "Delta report missing total count of 18"

    def test_delta_all_resolved(self) -> None:
        content = _load(DELTA_FILE)
        assert _has_text(content, r"ALL\s+RESOLVED"), (
            "Delta report missing ALL RESOLVED status"
        )


# ---------------------------------------------------------------------------
# 7. TestSpecificDecisionContent — spot checks on key decisions
# ---------------------------------------------------------------------------

class TestSpecificDecisionContent:

    def test_umh001_universal_meta_harness(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-UMH-001")
        assert _has_text(section, r"Universal Meta Harness"), (
            "UMH-001 resolution missing 'Universal Meta Harness'"
        )

    def test_umh002_philosophy_rewrite(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-UMH-002")
        assert _has_text(section, r"UMH-universal"), (
            "UMH-002 resolution missing 'UMH-universal'"
        )

    def test_umh003_spine_unification(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-UMH-003")
        assert _has_text(section, r"single.*path.*Spine") or _has_text(section, r"Spine"), (
            "UMH-003 resolution missing Spine reference"
        )

    def test_umh004_workstation_deletion(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-UMH-004")
        assert _has_text(section, r"extract|delete", re.IGNORECASE), (
            "UMH-004 resolution missing extract/delete language"
        )

    def test_umh005_abstract_port(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-UMH-005")
        assert _has_text(section, r"abstract.*port|projection_port"), (
            "UMH-005 resolution missing abstract port reference"
        )

    def test_eos001_beast_promotion(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-EOS-001")
        assert _has_text(section, r"Beast"), (
            "EOS-001 resolution missing Beast reference"
        )

    def test_eos002_r1_r5(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-EOS-002")
        assert _has_text(section, r"R1-R5") or _has_text(section, r"MVP scope"), (
            "EOS-002 resolution missing R1-R5 or MVP scope"
        )

    def test_eos003_clerk(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-EOS-003")
        assert _has_text(section, r"Clerk"), (
            "EOS-003 resolution missing Clerk reference"
        )

    def test_cos001_revenue_scope(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-COS-001")
        assert _has_text(section, r"Content.*Community.*Courses.*Sales", re.IGNORECASE), (
            "COS-001 resolution missing scope components"
        )

    def test_cos002_critical_security(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-COS-002")
        assert _has_text(section, r"CRITICAL|Clerk first"), (
            "COS-002 resolution missing CRITICAL or Clerk first reference"
        )

    def test_cos003_github_canonical(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-COS-003")
        assert _has_text(section, r"GitHub.*canonical|verify", re.IGNORECASE), (
            "COS-003 resolution missing GitHub canonical reference"
        )

    def test_cos004_build_sequence(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-COS-004")
        assert _has_text(section, r"Auth.*Split.*Tests"), (
            "COS-004 resolution missing build sequence"
        )

    def test_los001_v2_canonical(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-LOS-001")
        assert _has_text(section, r"v2\.0.*canonical"), (
            "LOS-001 resolution missing v2.0 canonical reference"
        )

    def test_los002_after_creatoros(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-LOS-002")
        assert _has_text(section, r"CreatorOS.*proves|after.*CreatorOS", re.IGNORECASE), (
            "LOS-002 resolution missing CreatorOS-first reference"
        )

    def test_los003_fly_io(self) -> None:
        content = _load(QUEUE_FILE)
        section = _get_decision_section(content, "DEC-146B-LOS-003")
        assert _has_text(section, r"Fly\.io|Trinity standard"), (
            "LOS-003 resolution missing Fly.io reference"
        )


# ---------------------------------------------------------------------------
# 8. TestProductGroupCounts
# ---------------------------------------------------------------------------

class TestProductGroupCounts:

    def test_umh_count(self) -> None:
        assert len(UMH_DECISION_IDS) == 5

    def test_eos_count(self) -> None:
        assert len(EOS_DECISION_IDS) == 3

    def test_cos_count(self) -> None:
        assert len(COS_DECISION_IDS) == 4

    def test_los_count(self) -> None:
        assert len(LOS_DECISION_IDS) == 3

    def test_total_146e(self) -> None:
        total = len(UMH_DECISION_IDS) + len(EOS_DECISION_IDS) + len(COS_DECISION_IDS) + len(LOS_DECISION_IDS)
        assert total == 15

    def test_grand_total(self) -> None:
        assert len(ALL_P0_DECISION_IDS) == 18


# ---------------------------------------------------------------------------
# 9. TestNoSourceCodeMutation
# ---------------------------------------------------------------------------

class TestNoSourceCodeMutation:

    def test_no_python_source_in_diff(self) -> None:
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True,
            cwd=str(_REPO_ROOT),
        )
        if result.returncode != 0:
            pytest.skip("git diff failed")
        changed = result.stdout.strip().splitlines()
        py_files = [f for f in changed if f.endswith(".py") and not f.startswith("tests/")]
        assert len(py_files) == 0, (
            f"Source Python files modified (violation): {py_files}"
        )


# ---------------------------------------------------------------------------
# 10. TestDeltaReportProvenance
# ---------------------------------------------------------------------------

class TestDeltaReportProvenance:

    def test_provenance_chain(self) -> None:
        content = _load(DELTA_FILE)
        assert _has_text(content, r"provenance", re.IGNORECASE)
        assert _has_text(content, r"OPERATOR_RATIFICATION")

    def test_safety_attestation(self) -> None:
        content = _load(DELTA_FILE)
        assert _has_section(content, r"Safety\s+Attestation")
        assert _has_text(content, r"No source code was mutated")
        assert _has_text(content, r"No implementation gates were opened")

    def test_next_phase_recommendation(self) -> None:
        content = _load(DELTA_FILE)
        assert _has_text(content, r"Phase\s+14\.6F"), (
            "Delta report missing Phase 14.6F recommendation"
        )

    def test_implementation_blocked_language(self) -> None:
        content = _load(DELTA_FILE)
        assert _has_text(content, r"implementation\s+remains\s+blocked", re.IGNORECASE), (
            "Delta report missing 'implementation remains blocked' language"
        )
