"""Claim ledger — append-preserving, bitemporal, with deterministic scoring.

The ledger NEVER rewrites history. Status changes and supersession append NEW
entries; belief_state() and reconstruct_as_of() are pure projections over the
append log. support_score() is a DETERMINISTIC support score in [0,1] — it is a
support score, NOT a calibrated probability, and it can never hide
counterevidence.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from substrate.understanding.reconstruction.contracts import (
    ClaimLedgerEntry,
    ClaimStatus,
    DerivedBelief,
)
from substrate.understanding.reconstruction.provenance import JsonlAppender

DERIVATION_VERSION = "adl-derive-v1"

# Explicit legal status transitions. Any transition not listed is rejected.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "proposed": frozenset({"supported", "contested", "unresolved", "falsified"}),
    "supported": frozenset({"contested", "superseded", "falsified"}),
    "contested": frozenset({"supported", "superseded", "falsified", "unresolved"}),
    "unresolved": frozenset({"supported", "contested", "falsified", "superseded"}),
    "superseded": frozenset(),  # terminal for the superseded entry
    "falsified": frozenset({"superseded"}),  # re-openable only via supersession
}

# ── Deterministic support scoring (documented weights) ──────────────────────
# Positive factors are in [0,1]; 'contradiction' is a penalty in [0,1] applied
# negatively. Missing factors (None) are preserved and EXCLUDED from weighting
# with a completeness note; the score is the weighted mean over PRESENT factors.
SUPPORT_WEIGHTS: dict[str, float] = {
    "directness": 0.18,
    "source_authority": 0.12,
    "method_strength": 0.16,
    "independence": 0.14,
    "scope_match": 0.10,
    "recency": 0.06,
    "runtime_verification": 0.14,
    "contradiction": 0.10,  # weight of the penalty term
}
_POSITIVE_FACTORS = frozenset(
    {
        "directness",
        "source_authority",
        "method_strength",
        "independence",
        "scope_match",
        "recency",
        "runtime_verification",
    }
)
CONTRADICTED_SCORE_CAP = 0.7


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def support_score(factors: dict[str, Any]) -> dict[str, Any]:
    """Deterministic support score in [0,1] from a factor dict.

    Returns {'score', 'factors' (raw, missing preserved as None), 'completeness',
    'contradicted', 'notes'}. This is a SUPPORT SCORE, not a calibrated
    probability. If any contradicting evidence is present the score is capped at
    CONTRADICTED_SCORE_CAP and 'contradicted' is set — counterevidence is never
    hidden by aggregation. Missing factors are preserved as None and excluded
    from weighting with a completeness note.
    """
    raw: dict[str, Any] = {}
    notes: list[str] = []
    present_weight = 0.0
    weighted_sum = 0.0

    for name in _POSITIVE_FACTORS:
        val = factors.get(name)
        raw[name] = val
        if val is None:
            notes.append(f"missing:{name}")
            continue
        w = SUPPORT_WEIGHTS[name]
        present_weight += w
        weighted_sum += w * _clamp(float(val))

    contradiction = factors.get("contradiction")
    raw["contradiction"] = contradiction
    contradicted = bool(contradiction)
    if contradiction is not None:
        w = SUPPORT_WEIGHTS["contradiction"]
        present_weight += w
        # penalty term contributes (1 - contradiction) so heavy contradiction
        # drags the mean down rather than being silently dropped.
        weighted_sum += w * _clamp(1.0 - float(contradiction))

    if present_weight <= 0.0:
        score = 0.0
        notes.append("no-present-factors")
    else:
        score = weighted_sum / present_weight

    if contradicted:
        score = min(score, CONTRADICTED_SCORE_CAP)

    total = sum(SUPPORT_WEIGHTS.values())
    completeness = _clamp(present_weight / total) if total else 0.0
    raw["contradicted"] = contradicted

    return {
        "score": round(_clamp(score), 6),
        "factors": raw,
        "completeness": round(completeness, 6),
        "contradicted": contradicted,
        "notes": notes,
    }


class ClaimLedger:
    """Append-preserving claim ledger over a JSONL log.

    Every mutation appends a new ClaimLedgerEntry. Supersession links a NEW entry
    back to the one it replaces via `supersedes`; the replaced entry is left
    intact. belief_state() derives the current DerivedBelief per lineage;
    reconstruct_as_of() replays the log up to a record time (bitemporal).
    """

    def __init__(self, appender: Optional[JsonlAppender] = None) -> None:
        self._appender = appender
        self._entries: list[ClaimLedgerEntry] = []

    # ── mutation (append-only) ──────────────────────────────────────────
    def append(self, entry: ClaimLedgerEntry) -> ClaimLedgerEntry:
        self._entries.append(entry)
        if self._appender is not None:
            self._appender.append(entry.to_dict())
        return entry

    def transition(
        self, prior: ClaimLedgerEntry, new_status: ClaimStatus, **overrides: Any
    ) -> ClaimLedgerEntry:
        """Append a same-lineage entry with a validated status change."""
        allowed = ALLOWED_TRANSITIONS.get(prior.status, frozenset())
        if new_status not in allowed:
            raise ValueError(
                f"illegal status transition {prior.status!r} -> {new_status!r} "
                f"(allowed: {sorted(allowed)})"
            )
        return self.append(
            ClaimLedgerEntry(
                proposition=prior.proposition,
                claim_type=prior.claim_type,
                scope=prior.scope,
                status=new_status,
                run_id=overrides.get("run_id", prior.run_id),
                supporting_observation_ids=overrides.get(
                    "supporting_observation_ids", prior.supporting_observation_ids
                ),
                contradicting_observation_ids=overrides.get(
                    "contradicting_observation_ids",
                    prior.contradicting_observation_ids,
                ),
                valid_time=overrides.get("valid_time", prior.valid_time),
                recorded_at=overrides.get("recorded_at"),
                support_factors=overrides.get("support_factors", {}),
                support_score=overrides.get("support_score"),
                uncertainty_reasons=overrides.get("uncertainty_reasons", ()),
            )
        )

    def supersede(self, prior: ClaimLedgerEntry, replacement: ClaimLedgerEntry) -> ClaimLedgerEntry:
        """Append `replacement` linked to `prior` via supersedes (history intact)."""
        if replacement.supersedes not in (None, prior.id):
            raise ValueError("replacement.supersedes must be None or prior.id")
        return self.append(
            ClaimLedgerEntry(
                proposition=replacement.proposition,
                claim_type=replacement.claim_type,
                scope=replacement.scope,
                status=replacement.status,
                run_id=replacement.run_id,
                supporting_observation_ids=replacement.supporting_observation_ids,
                contradicting_observation_ids=replacement.contradicting_observation_ids,
                valid_time=replacement.valid_time,
                recorded_at=replacement.recorded_at,
                supersedes=prior.id,
                support_factors=replacement.support_factors,
                support_score=replacement.support_score,
                uncertainty_reasons=replacement.uncertainty_reasons,
            )
        )

    # ── projections (pure reads) ────────────────────────────────────────
    @property
    def entries(self) -> list[ClaimLedgerEntry]:
        return list(self._entries)

    def _superseded_ids(self, entries: Iterable[ClaimLedgerEntry]) -> set[str]:
        return {e.supersedes for e in entries if e.supersedes}

    def _latest_per_lineage(self, entries: list[ClaimLedgerEntry]) -> dict[str, ClaimLedgerEntry]:
        superseded = self._superseded_ids(entries)
        latest: dict[str, ClaimLedgerEntry] = {}
        for e in entries:
            if e.id in superseded or e.status == "superseded":
                continue
            latest[e.lineage_id()] = e  # last write wins (append order)
        return latest

    def belief_state(self) -> list[DerivedBelief]:
        """Derive the current DerivedBelief for each non-superseded lineage."""
        latest = self._latest_per_lineage(self._entries)
        beliefs: list[DerivedBelief] = []
        for lineage_id, e in sorted(latest.items()):
            beliefs.append(
                DerivedBelief(
                    claim_lineage_id=lineage_id,
                    status=e.status,
                    support_score=e.support_score,
                    derivation_version=DERIVATION_VERSION,
                    derivation_factors=dict(e.support_factors),
                )
            )
        return beliefs

    def reconstruct_as_of(self, record_time: str) -> list[DerivedBelief]:
        """Belief state as it stood at a past record_time (bitemporal replay).

        Only entries whose recorded_at <= record_time are considered. Entries
        with recorded_at=None are treated as always-present (pre-dated seed).
        """
        visible = [
            e for e in self._entries if e.recorded_at is None or e.recorded_at <= record_time
        ]
        latest = self._latest_per_lineage(visible)
        return [
            DerivedBelief(
                claim_lineage_id=lineage_id,
                status=e.status,
                support_score=e.support_score,
                derivation_version=DERIVATION_VERSION,
                derivation_factors=dict(e.support_factors),
            )
            for lineage_id, e in sorted(latest.items())
        ]


def independence_report(
    claims: list[ClaimLedgerEntry],
    observation_to_source: dict[str, str],
    source_to_root: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Group supporting observations by upstream source lineage per claim.

    Two observations sharing an upstream source ANCESTOR count as ONE independent
    line. `observation_to_source` maps obs id → its source id; `source_to_root`
    optionally maps a source id → its upstream root (default: the source is its
    own root). Returns per-lineage independent line counts.
    """
    root_of = source_to_root or {}
    report: dict[str, Any] = {}
    for c in claims:
        roots: set[str] = set()
        unmapped = 0
        for obs_id in c.supporting_observation_ids:
            src = observation_to_source.get(obs_id)
            if src is None:
                unmapped += 1
                continue
            roots.add(root_of.get(src, src))
        report[c.lineage_id()] = {
            "supporting_observations": len(c.supporting_observation_ids),
            "independent_lines": len(roots),
            "roots": sorted(roots),
            "unmapped_observations": unmapped,
        }
    return report
