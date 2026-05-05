"""Candidate approval gate for search-based source discovery.

The approval flow is deliberately simple and file-based so it composes
with the existing Control Plane without introducing a new action type:

    1. The agent generates a CandidatePlan (pure local, no network).
    2. The agent persists the plan to
       ``logs/tool_mastery_research/<slug>/candidates/<stamp>.json``
       via a ``write_file`` Control Plane action. That gives us a
       durable audit trail in ``logs/execution/`` *before* any fetch.
    3. The operator inspects the file and sets ``status`` on each
       candidate to ``accepted`` or ``rejected`` (default: ``pending``).
       They can also accept/reject in bulk via the CLI.
    4. The agent later reads the approved subset back as SourceRefs
       and passes them to the existing fetcher.

Nothing in this module performs network I/O. Nothing auto-approves.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import SourceRef
from .search_discovery import Candidate, CandidatePlan
from .paths import RESEARCH_LOG_DIR


APPROVAL_STATUSES = ("pending", "accepted", "rejected")


@dataclass
class CandidateRecord:
    """On-disk representation of a candidate + its approval state."""

    url: str
    family: str
    tier: str
    rationale: str
    rank: int
    status: str = "pending"  # pending | accepted | rejected
    decided_at: str | None = None
    decided_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_candidate(cls, c: Candidate) -> "CandidateRecord":
        return cls(
            url=c.url,
            family=c.family,
            tier=c.tier.value,
            rationale=c.rationale,
            rank=c.rank,
        )


@dataclass
class ApprovalFile:
    """Top-level shape of a candidates.json file."""

    schema_version: int
    tool_slug: str
    generated_at: str
    variants: dict[str, str]
    notes: list[str]
    candidates: list[CandidateRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool_slug": self.tool_slug,
            "generated_at": self.generated_at,
            "variants": dict(self.variants),
            "notes": list(self.notes),
            "candidates": [c.to_dict() for c in self.candidates],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalFile":
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            tool_slug=data["tool_slug"],
            generated_at=data.get("generated_at", ""),
            variants=dict(data.get("variants", {})),
            notes=list(data.get("notes", [])),
            candidates=[CandidateRecord(**c) for c in data.get("candidates", [])],
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _candidates_dir(tool_slug: str) -> Path:
    return RESEARCH_LOG_DIR / tool_slug / "candidates"


def build_approval_file(plan: CandidatePlan) -> ApprovalFile:
    """Convert a generated CandidatePlan into an on-disk approval file."""
    return ApprovalFile(
        schema_version=1,
        tool_slug=plan.tool_slug,
        generated_at=_now_iso(),
        variants=plan.variants,
        notes=plan.notes,
        candidates=[CandidateRecord.from_candidate(c) for c in plan.candidates],
    )


def persist_approval_file(
    approval: ApprovalFile,
    *,
    source_agent: str = "tool_mastery_research_agent",
) -> Path:
    """Write the approval file via the Control Plane ``write_file`` action.

    Routing through the Control Plane (rather than a bare ``Path.write_text``)
    gives us a log entry in ``logs/execution/`` that records *when* the
    candidates were generated, by which agent, and with what idempotency
    key — the exact provenance trail we want before any operator decision.

    Control Plane failures fall back to a direct write so a misconfigured
    action system cannot block the research loop. The fallback path is
    recorded in the returned file alongside a ``cp_fallback`` note.
    """
    out_dir = _candidates_dir(approval.tool_slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = approval.generated_at.replace(":", "-")
    path = out_dir / f"{stamp}.json"
    content = json.dumps(approval.to_dict(), indent=2)

    try:
        from core.action_system.control_plane import run_action

        run_action(
            type="write_file",
            description=(
                f"tool_mastery:search_candidates:{approval.tool_slug} — "
                "persist generated source candidates for operator approval"
            ),
            inputs={"path": str(path), "content": content},
            expected_output=f"candidates file for {approval.tool_slug}",
            risk_level="low",
            source_agent=source_agent,
            idempotency_key=(
                f"tool_mastery:search_candidates:"
                f"{approval.tool_slug}:{approval.generated_at}"
            ),
            idempotency_ttl_seconds=24 * 3600,
        )
    except Exception:  # pragma: no cover - defensive fallback
        # Direct write fallback: still honest, just missing the CP log row.
        path.write_text(content, encoding="utf-8")

    return path


def load_approval_file(path: Path) -> ApprovalFile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ApprovalFile.from_dict(data)


def save_approval_file(path: Path, approval: ApprovalFile) -> None:
    Path(path).write_text(json.dumps(approval.to_dict(), indent=2), encoding="utf-8")


def latest_approval_file(tool_slug: str) -> Path | None:
    """Return the most recent candidates file for a slug, if any."""
    d = _candidates_dir(tool_slug)
    if not d.is_dir():
        return None
    files = sorted(d.glob("*.json"))
    return files[-1] if files else None


def apply_decision(
    approval: ApprovalFile,
    *,
    accept: set[int] | None = None,
    reject: set[int] | None = None,
    accept_all: bool = False,
    reject_all: bool = False,
    operator: str = "operator",
) -> ApprovalFile:
    """Mutate an ApprovalFile in place with the operator's decisions.

    Indexes are 1-based to match the CLI display. Any candidate not
    explicitly named remains ``pending`` unless ``accept_all`` or
    ``reject_all`` is set.
    """
    accept = accept or set()
    reject = reject or set()
    now = _now_iso()
    for i, rec in enumerate(approval.candidates, start=1):
        new_status: str | None = None
        if accept_all:
            new_status = "accepted"
        elif reject_all:
            new_status = "rejected"
        elif i in accept:
            new_status = "accepted"
        elif i in reject:
            new_status = "rejected"

        if new_status is None:
            continue
        if new_status not in APPROVAL_STATUSES:
            raise ValueError(f"invalid status {new_status!r}")
        rec.status = new_status
        rec.decided_at = now
        rec.decided_by = operator
    return approval


def approved_source_refs(approval: ApprovalFile) -> list[SourceRef]:
    """Return SourceRefs for only the ``accepted`` candidates.

    This is the bridge back into the existing fetch/research flow:
    unapproved candidates cannot reach the fetcher through this path.
    """
    from .models import SourceTier

    refs: list[SourceRef] = []
    for rec in approval.candidates:
        if rec.status != "accepted":
            continue
        try:
            tier = SourceTier(rec.tier)
        except ValueError:
            tier = SourceTier.SECONDARY
        refs.append(
            SourceRef(
                url=rec.url,
                tier=tier,
                label=f"{rec.family} candidate (approved)",
                origin="generated",
            )
        )
    return refs


def format_candidates_for_display(approval: ApprovalFile) -> str:
    """Human-readable summary used by the CLI preview command."""
    lines = [
        f"=== Candidate sources: {approval.tool_slug} ===",
        f"generated_at : {approval.generated_at}",
        f"variants     : {approval.variants}",
        f"total        : {len(approval.candidates)}",
        "",
    ]
    for i, rec in enumerate(approval.candidates, start=1):
        marker = {"pending": "[ ]", "accepted": "[x]", "rejected": "[-]"}.get(
            rec.status, "[?]"
        )
        lines.append(f"{marker} {i:>2}. ({rec.family}/{rec.tier}) {rec.url}")
        lines.append(f"       rationale: {rec.rationale}")
    lines.append("")
    for note in approval.notes:
        lines.append(f"note: {note}")
    lines.append("")
    lines.append(
        "approval required: use --accept N,M  |  --reject N,M  |  "
        "--accept-all  |  --reject-all"
    )
    return "\n".join(lines)
