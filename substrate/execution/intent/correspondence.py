"""Source correspondence + grounding adjudication — Wave 1 canonical resolution.

Two DISTINCT concerns (plan §5), both deterministic and bounded:

- **SourceCorrespondenceResolution**: do multiple typed evidence candidates
  (a GitHub review comment, an email, an existing Task, ...) refer to the SAME
  underlying finding/entity? Groups candidates so one real-world finding never
  fans out into duplicate Tasks. No universal connector platform — matching is
  over the typed EvidenceRef fields only.

- **GroundingAdjudication**: for one CLAIM, which evidence wins? Claim-
  SENSITIVE precedence — there is deliberately NO single global source
  ranking. Running-behavior claims prefer runtime observation over documents;
  source-implementation claims prefer checked-out code over old reports;
  ratified-architecture claims prefer canon; user-decision claims prefer the
  current authenticated instruction over old memory.

Evidence is provenance, never mutation authority.
UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from substrate.contracts.work_context import EpistemicStatus, EvidenceRef

# ── Source correspondence ────────────────────────────────────────────────────


@dataclass
class SourceCorrespondenceResolution:
    """Result of matching evidence candidates to shared underlying findings."""

    groups: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    ambiguities: list[dict[str, Any]] = field(default_factory=list)
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceCorrespondenceResolution:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


_TOKEN_RE = re.compile(r"[a-z0-9_]{3,}")
_STOPWORDS = frozenset(
    "the and for with that this from into over your our are was were has have "
    "been being will would should could about there their them they when what "
    "which while where after before because between during under above".split()
)


def _summary_tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOPWORDS)


def _token_similarity(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


_SIMILARITY_MATCH = 0.5
_SIMILARITY_AMBIGUOUS = 0.3


def resolve_source_correspondence(
    candidates: list[EvidenceRef],
) -> SourceCorrespondenceResolution:
    """Group evidence candidates that refer to the same underlying finding.

    Deterministic, bounded matching in precedence order:
      1. identical ``canonical_entity_id`` (explicit correspondence),
      2. identical ``content_hash`` (same content, different transport),
      3. extraction-summary token similarity ≥ 0.5 (same described finding).
    Similarity in [0.3, 0.5) is reported as an ambiguity, never silently
    merged. Cross-tenant candidates are never grouped.
    """
    resolution = SourceCorrespondenceResolution()
    groups: list[dict[str, Any]] = []

    def _try_join(ref: EvidenceRef, tokens: frozenset[str]) -> bool:
        for group in groups:
            if ref.tenant_id and group["tenant_id"] and ref.tenant_id != group["tenant_id"]:
                continue
            if ref.canonical_entity_id and ref.canonical_entity_id == group["canonical_entity_id"]:
                group["member_evidence_ids"].append(ref.evidence_id)
                group["reasons"].append(f"{ref.evidence_id}: canonical_entity_id match")
                return True
            if ref.content_hash and ref.content_hash in group["content_hashes"]:
                group["member_evidence_ids"].append(ref.evidence_id)
                group["reasons"].append(f"{ref.evidence_id}: content_hash match")
                return True
            similarity = _token_similarity(tokens, group["tokens"])
            if similarity >= _SIMILARITY_MATCH:
                group["member_evidence_ids"].append(ref.evidence_id)
                group["tokens"] = group["tokens"] | tokens
                group["reasons"].append(f"{ref.evidence_id}: summary similarity {similarity:.2f}")
                return True
            if similarity >= _SIMILARITY_AMBIGUOUS:
                resolution.ambiguities.append(
                    {
                        "evidence_id": ref.evidence_id,
                        "group_of": list(group["member_evidence_ids"]),
                        "similarity": round(similarity, 2),
                        "reason": "similarity below match threshold — not merged",
                    }
                )
        return False

    for ref in candidates:
        tokens = _summary_tokens(ref.extraction_summary)
        if _try_join(ref, tokens):
            # Disputed evidence joining a group is a recorded conflict.
            if ref.epistemic_status == EpistemicStatus.DISPUTED.value:
                resolution.conflicts.append(
                    {"evidence_id": ref.evidence_id, "reason": "disputed member"}
                )
            continue
        groups.append(
            {
                "finding_key": f"finding-{len(groups) + 1}",
                "tenant_id": ref.tenant_id,
                "canonical_entity_id": ref.canonical_entity_id,
                "content_hashes": {ref.content_hash} if ref.content_hash else set(),
                "tokens": tokens,
                "member_evidence_ids": [ref.evidence_id],
                "reasons": [f"{ref.evidence_id}: group seed"],
            }
        )

    resolution.groups = [
        {
            "finding_key": g["finding_key"],
            "tenant_id": g["tenant_id"],
            "canonical_entity_id": g["canonical_entity_id"],
            "member_evidence_ids": g["member_evidence_ids"],
            "reasons": g["reasons"],
        }
        for g in groups
    ]
    return resolution


# ── Grounding adjudication ───────────────────────────────────────────────────


@dataclass
class GroundingAdjudication:
    """The adjudicated answer to one claim from competing evidence."""

    claim: str = ""
    claim_kind: str = ""
    selected_evidence_ids: list[str] = field(default_factory=list)
    rejected_evidence: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    authority_reasoning: str = ""
    conclusion: str = ""
    confidence: float = 0.0
    unresolved_uncertainty: list[str] = field(default_factory=list)
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GroundingAdjudication:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# Claim-sensitive precedence: claim_kind → ordered (source_system_class,
# epistemic_status) preference. First matching tier wins. There is NO default
# global ranking — unknown claim kinds fall back to freshness + observed-first,
# with the fallback recorded in authority_reasoning.
_RUNTIME_SYSTEMS = frozenset({"umh_runtime", "docker", "process", "service", "telemetry"})
_CODE_SYSTEMS = frozenset({"repository", "filesystem", "git", "worktree"})
_CANON_SYSTEMS = frozenset({"architecture_canon", "platform_spec", "ratified_docs"})
_INSTRUCTION_SYSTEMS = frozenset({"conversation", "operator_instruction"})
_DOCUMENT_SYSTEMS = frozenset({"docs", "report", "memory", "notes", "email"})

CLAIM_KIND_PRECEDENCE: dict[str, tuple[frozenset[str], ...]] = {
    "running_behavior": (_RUNTIME_SYSTEMS, _CODE_SYSTEMS, _DOCUMENT_SYSTEMS),
    "source_implementation": (_CODE_SYSTEMS, _RUNTIME_SYSTEMS, _DOCUMENT_SYSTEMS),
    "ratified_architecture": (_CANON_SYSTEMS, _CODE_SYSTEMS, _DOCUMENT_SYSTEMS),
    "user_decision": (_INSTRUCTION_SYSTEMS, _DOCUMENT_SYSTEMS),
}

_EPISTEMIC_WEIGHT = {
    EpistemicStatus.OBSERVED.value: 3,
    EpistemicStatus.DECLARED.value: 2,
    EpistemicStatus.INFERRED.value: 1,
    EpistemicStatus.SIMULATED.value: 0,
    EpistemicStatus.DISPUTED.value: -1,
    EpistemicStatus.SUPERSEDED.value: -2,
    EpistemicStatus.UNKNOWN.value: 0,
}


def adjudicate_claim(
    claim: str,
    claim_kind: str,
    evidence: list[EvidenceRef],
) -> GroundingAdjudication:
    """Deterministically adjudicate one claim across competing evidence."""
    adjudication = GroundingAdjudication(claim=claim, claim_kind=claim_kind)
    if not evidence:
        adjudication.unresolved_uncertainty.append("no evidence provided")
        adjudication.authority_reasoning = "no evidence — claim unresolved"
        return adjudication

    tiers = CLAIM_KIND_PRECEDENCE.get(claim_kind)
    if tiers is None:
        adjudication.authority_reasoning = (
            f"unknown claim_kind {claim_kind!r} — fallback: epistemic weight, "
            f"then freshness (no global source ranking exists)"
        )
        ranked = sorted(
            evidence,
            key=lambda r: (_EPISTEMIC_WEIGHT.get(r.epistemic_status, 0), r.observed_at),
            reverse=True,
        )
    else:

        def _tier_rank(ref: EvidenceRef) -> int:
            for i, tier in enumerate(tiers):
                if ref.source_system in tier:
                    return len(tiers) - i
            return 0

        ranked = sorted(
            evidence,
            key=lambda r: (
                _tier_rank(r),
                _EPISTEMIC_WEIGHT.get(r.epistemic_status, 0),
                r.observed_at,
            ),
            reverse=True,
        )
        adjudication.authority_reasoning = (
            f"claim_kind {claim_kind!r} precedence applied over {len(evidence)} evidence item(s)"
        )

    winner = ranked[0]
    adjudication.selected_evidence_ids = [winner.evidence_id]
    # Peers agreeing with the winner strengthen it; disagreement is recorded,
    # never silently dropped.
    winner_tokens = _summary_tokens(winner.extraction_summary)
    for ref in ranked[1:]:
        similarity = _token_similarity(winner_tokens, _summary_tokens(ref.extraction_summary))
        if similarity >= _SIMILARITY_MATCH:
            adjudication.selected_evidence_ids.append(ref.evidence_id)
        else:
            adjudication.rejected_evidence.append(
                {
                    "evidence_id": ref.evidence_id,
                    "reason": "outranked by claim-sensitive precedence",
                }
            )
            if ref.epistemic_status == EpistemicStatus.OBSERVED.value:
                adjudication.contradictions.append(
                    {
                        "evidence_id": ref.evidence_id,
                        "against": winner.evidence_id,
                        "note": "observed evidence disagrees with selected answer",
                    }
                )

    adjudication.conclusion = winner.extraction_summary
    base = 0.5 + 0.1 * min(len(adjudication.selected_evidence_ids), 3)
    if adjudication.contradictions:
        base -= 0.2
        adjudication.unresolved_uncertainty.append("contradicting observed evidence present")
    adjudication.confidence = round(max(0.1, min(base, 0.9)), 2)
    return adjudication


__all__ = [
    "CLAIM_KIND_PRECEDENCE",
    "GroundingAdjudication",
    "SourceCorrespondenceResolution",
    "adjudicate_claim",
    "resolve_source_correspondence",
]
