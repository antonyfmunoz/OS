"""Bounded grounding — the minimum decision-relevant evidence for one objective.

Deterministic, budget-capped, and failure-tolerant: every collector failure or
timeout lands in ``unknown_sources`` (missing evidence is a recorded state,
never an exception), and the byte/source budget clips with ``truncated=True``.

Reuses the canonical ``substrate.organism.grounding_registry`` collectors for
runtime evidence and adds objective-derived filesystem probes (bounded listing
— never a repository crawl).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from substrate.execution.intent.intent_spec import IntentSpec
from substrate.execution.planning.records import GroundingSnapshot

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GroundingBudget:
    max_sources: int = 8
    max_bytes: int = 64_000
    per_source_timeout_s: float = 2.0

    def to_dict(self) -> dict[str, float | int]:
        return {
            "max_sources": self.max_sources,
            "max_bytes": self.max_bytes,
            "per_source_timeout_s": self.per_source_timeout_s,
        }


DEFAULT_BUDGET = GroundingBudget()

# Runtime collectors reused from the canonical grounding registry, in
# decision-relevance order for planning objectives.
_RUNTIME_COLLECTOR_IDS = ("work_packets", "blocked_packets", "approvals", "docker")

_SUBSYSTEM_TOKEN_RE = re.compile(r"[a-z][a-z0-9_]{2,}")

_MAX_DIR_ENTRIES = 40


# This module lives at <repo>/substrate/execution/planning/grounding.py, so the
# repository root is four parents up. That derivation is instance-independent:
# it holds wherever the checkout is placed, with no hardcoded deployment path.
_DERIVED_REPO_ROOT = Path(__file__).resolve().parents[3]


def _repo_root() -> str:
    """Resolve the repository root instance-independently.

    Explicit ``UMH_ROOT`` wins (deployment override); otherwise the root is
    derived from this module's own on-disk location — never a hardcoded
    ``/opt/OS`` fallback. Works from any checkout path (worktree, container
    mount, CI clone) with no environment set.
    """
    override = os.environ.get("UMH_ROOT")
    if override and override.strip():
        return override
    return str(_DERIVED_REPO_ROOT)


def _bounded_dir_probe(path: str) -> dict[str, object]:
    """Existence + bounded listing for one directory. Never raises."""
    try:
        if not os.path.isdir(path):
            return {"path": path, "exists": False, "entries": [], "entry_count": 0}
        entries = sorted(os.listdir(path))[:_MAX_DIR_ENTRIES]
        return {
            "path": path,
            "exists": True,
            "entries": entries,
            "entry_count": len(entries),
        }
    except OSError as exc:
        logger.debug("grounding dir probe failed for %s: %s", path, exc)
        return {"path": path, "exists": False, "entries": [], "error": str(exc)}


def _objective_subsystem_tokens(spec: IntentSpec, text: str) -> list[str]:
    """Candidate subsystem names mentioned by the objective, deterministic.

    Tokens are validated against the legacy runtime root's actual directory
    listing — the objective's words select among real directories; nothing is
    fabricated from prose.
    """
    legacy_root = os.path.join(_repo_root(), "data", "umh")
    try:
        real_dirs = {
            d for d in os.listdir(legacy_root) if os.path.isdir(os.path.join(legacy_root, d))
        }
    except OSError as exc:
        logger.debug("legacy runtime root listing failed: %s", exc)
        real_dirs = set()

    tokens: list[str] = []
    seen: set[str] = set()
    for token in _SUBSYSTEM_TOKEN_RE.findall((text or "").lower()):
        if token in real_dirs and token not in seen:
            seen.add(token)
            tokens.append(token)
    for value in spec.extracted_entities.values():
        v = str(value).lower().strip()
        if v in real_dirs and v not in seen:
            seen.add(v)
            tokens.append(v)
    return tokens


def build_grounding_snapshot(
    spec: IntentSpec,
    conversation_id: str,
    message_id: str,
    objective_text: str = "",
    budget: GroundingBudget | None = None,
) -> GroundingSnapshot:
    """Assemble the bounded grounding packet for one objective. Never raises."""
    budget = budget or DEFAULT_BUDGET
    snapshot = GroundingSnapshot(
        intent_id=spec.intent_id,
        conversation_id=conversation_id,
        message_id=message_id,
        budget=budget.to_dict(),
    )
    text = objective_text or spec.raw_text
    bytes_used = 0

    def _add_source(source: str, status: str, summary: str, evidence: dict) -> bool:
        """Append one source within budget. Returns False when budget clipped."""
        nonlocal bytes_used
        if len(snapshot.sources) >= budget.max_sources:
            snapshot.truncated = True
            return False
        payload = {"source": source, "status": status, "summary": summary, "evidence": evidence}
        size = len(json.dumps(payload, default=str))
        if bytes_used + size > budget.max_bytes:
            snapshot.truncated = True
            payload["evidence"] = {"clipped": True}
            payload["summary"] = summary[:200]
            size = len(json.dumps(payload, default=str))
            if bytes_used + size > budget.max_bytes:
                return False
        bytes_used += size
        payload["collected_at"] = time.time()
        snapshot.sources.append(payload)
        return True

    # 1. Objective-derived filesystem probes: legacy runtime path vs the
    #    runtime-state boundary, per subsystem the objective names.
    subsystems = _objective_subsystem_tokens(spec, text)
    if subsystems:
        from substrate.state.runtime_paths import runtime_state_dir

        probes: dict[str, dict[str, object]] = {}
        for name in subsystems:
            legacy = _bounded_dir_probe(os.path.join(_repo_root(), "data", "umh", name))
            try:
                boundary_dir = str(runtime_state_dir(name, create=False))
                boundary = _bounded_dir_probe(boundary_dir)
            except Exception as exc:  # containment/validation errors recorded
                logger.debug("runtime_state_dir probe failed for %s: %s", name, exc)
                boundary = {"path": "", "exists": False, "error": str(exc)}
            probes[name] = {"legacy": legacy, "runtime_state": boundary}
        migrated = [n for n, p in probes.items() if not p["legacy"]["exists"]]
        pending = [n for n, p in probes.items() if p["legacy"]["exists"]]
        _add_source(
            "subsystem_paths",
            "ok",
            f"{len(pending)} subsystem(s) still under legacy data/umh, "
            f"{len(migrated)} with no legacy dir",
            {"probes": probes, "legacy_pending": pending, "legacy_absent": migrated},
        )
    else:
        snapshot.unknown_sources.append("subsystem_paths")

    # 2. Canonical runtime collectors, individually failure-isolated and timed.
    try:
        from substrate.organism.grounding_registry import _COLLECTORS  # noqa: PLC2701
    except Exception as exc:  # registry unavailable → all runtime sources unknown
        logger.debug("grounding registry unavailable: %s", exc)
        snapshot.unknown_sources.extend(_RUNTIME_COLLECTOR_IDS)
        return snapshot

    for source_id in _RUNTIME_COLLECTOR_IDS:
        if len(snapshot.sources) >= budget.max_sources:
            snapshot.truncated = True
            break
        collector = _COLLECTORS.get(source_id)
        if collector is None:
            snapshot.unknown_sources.append(source_id)
            continue
        start = time.monotonic()
        try:
            data, summary = collector()
        except Exception as exc:
            logger.debug("grounding collector %s failed: %s", source_id, exc)
            snapshot.unknown_sources.append(source_id)
            continue
        elapsed = time.monotonic() - start
        if elapsed > budget.per_source_timeout_s:
            # Collected but over budget — evidence kept, timeout recorded.
            snapshot.unknown_sources.append(f"{source_id}:timeout")
            _add_source(source_id, "timeout", summary, {"elapsed_s": round(elapsed, 2)})
            continue
        _add_source(source_id, "ok", summary, data)

    return snapshot


def snapshot_to_evidence_refs(snapshot: GroundingSnapshot, tenant_id: str = "") -> list[dict]:
    """Project a GroundingSnapshot into typed EvidenceRef dicts (Wave 1 §4).

    New code consumes evidence as EvidenceRefs — provenance with an explicit
    epistemic status — instead of untyped grounding dicts. Collected sources
    are OBSERVED runtime evidence; unknown/failed sources surface as UNKNOWN
    refs so missing evidence stays a recorded state.
    """
    from substrate.contracts.work_context import EpistemicStatus, EvidenceRef

    refs: list[dict] = []
    for source in snapshot.sources:
        source_id = str(source.get("source", ""))
        refs.append(
            EvidenceRef(
                evidence_id=snapshot.evidence_ref(source_id),
                source_system="umh_runtime",
                source_object_type="grounding_source",
                source_object_id=source_id,
                locator=f"grounding:{snapshot.grounding_snapshot_id}#{source_id}",
                epistemic_status=(
                    EpistemicStatus.OBSERVED.value
                    if source.get("status") == "ok"
                    else EpistemicStatus.UNKNOWN.value
                ),
                observed_at=float(source.get("collected_at", snapshot.created_at)),
                freshness_status="fresh" if source.get("status") == "ok" else "stale",
                tenant_id=tenant_id,
                extraction_summary=str(source.get("summary", ""))[:400],
            ).to_dict()
        )
    for unknown in snapshot.unknown_sources:
        refs.append(
            EvidenceRef(
                evidence_id=snapshot.evidence_ref(unknown),
                source_system="umh_runtime",
                source_object_type="grounding_source",
                source_object_id=unknown,
                locator=f"grounding:{snapshot.grounding_snapshot_id}#{unknown}",
                epistemic_status=EpistemicStatus.UNKNOWN.value,
                tenant_id=tenant_id,
                extraction_summary="source unavailable — missing evidence recorded",
            ).to_dict()
        )
    return refs


__all__ = [
    "DEFAULT_BUDGET",
    "GroundingBudget",
    "build_grounding_snapshot",
    "snapshot_to_evidence_refs",
]
