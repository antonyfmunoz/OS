"""Reconstruction record contracts — v1 immutable evidence/claim records.

NOT an ontology home. Imports canonical types only; defines run-scoped instance
record shapes for the codebase self-reconstruction subsystem. Records are
frozen dataclasses with deterministic, stable serialization (sorted-key
canonical JSON) so content hashing and identity derivation are reproducible.

Naming: ClaimLedgerEntry / ObservationRecord deliberately avoid the existing
substrate.organism.contradiction_engine Claim / Observation names.

Hash kinds are distinct and never conflated:
  - source_content_hash : sha256 of the ACTUAL acquired bytes (file body,
    redacted probe output). Empty only when hashing was skipped for a recorded
    reason (oversized / unreadable / sensitive), never a fabricated label hash.
  - extraction_hash     : sha256 of the canonical extracted payload derived
    from a source (optional).
  - derivation_key      : identity for derived artifacts, carried with
    input_record_ids + derivation_activity_id lineage.

Identity kinds are distinct:
  - source_identity_id  : stable across runs (path + kind + content hash +
    commit) — supports cross-run lineage, dedup, temporal comparison.
  - id                  : the run-scoped ACQUISITION record id (identity +
    run + activity).

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

SCHEMA_VERSION = "adl-v1"

# ── Evidence facets (the 12) ────────────────────────────────────────────────
# A claim about a code entity is graded by the strongest facet of evidence that
# supports it. Declaration facets are the WEAKEST — a design being declared or
# specified is NEVER proof it exists as running implementation.
EvidenceFacet = Literal[
    "declared",
    "specified",
    "source_present",
    "importable",
    "unit_tested",
    "integration_tested",
    "deployment_configured",
    "deployed",
    "running",
    "reachable",
    "live_path",
    "outcome_verified",
]

# Facet groups — evaluation uses these to enforce the normative invariant: a
# "declared"/"specified" observation may never be stored as proof of existence.
DECLARATION_FACETS: frozenset[str] = frozenset({"declared", "specified"})
IMPLEMENTATION_FACETS: frozenset[str] = frozenset(
    {
        "source_present",
        "importable",
        "unit_tested",
        "integration_tested",
        "deployment_configured",
    }
)
RUNTIME_FACETS: frozenset[str] = frozenset(
    {"deployed", "running", "reachable", "live_path", "outcome_verified"}
)

# Ordered strength ranking (weakest → strongest). Used by evaluators.
FACET_STRENGTH: dict[str, int] = {
    "declared": 0,
    "specified": 1,
    "source_present": 2,
    "importable": 3,
    "unit_tested": 4,
    "integration_tested": 5,
    "deployment_configured": 6,
    "deployed": 7,
    "running": 8,
    "reachable": 9,
    "live_path": 10,
    "outcome_verified": 11,
}

SourceModality = Literal["document", "code", "config", "runtime_probe", "derived"]
SourceKind = Literal[
    "repository_file",
    "runtime_probe",
    "external_document",
    "derived_artifact",
    "human_report",
]
RedactionStatus = Literal["none", "partial", "redacted"]
ClaimStatus = Literal[
    "proposed",
    "supported",
    "contested",
    "superseded",
    "falsified",
    "unresolved",
]
IdentityVerdict = Literal["merge", "link", "remain_separate", "unresolved"]
# Causal bases are TYPED CLASSES of evidence, not a globally ordinal ladder:
# "formal" proves a formal relation within a system (an import edge) but is not
# globally "stronger" than experimental evidence. Validity dimensions are
# modeled separately on CausalSupportRecord.
CausalBasis = Literal[
    "reported",
    "hypothesized",
    "temporal_association",
    "statistical",
    "quasi_experimental",
    "experimental",
    "formal",
]
ActivityKind = Literal["acquisition", "extraction", "transformation", "evaluation"]
# PARTIALLY_ANSWERED (v1.2): evidence exists but does not close the question —
# e.g. CQ5 with execution evidence and zero qualifying component mappings.
AnswerStatus = Literal["ANSWERED", "PARTIALLY_ANSWERED", "UNKNOWN"]


def _stable_dict(obj: Any) -> Any:
    """Recursively coerce a value into JSON-stable primitives.

    Tuples/sets → sorted lists (deterministic). Used so identity hashing does
    not depend on Python container ordering or identity.
    """
    if isinstance(obj, dict):
        return {k: _stable_dict(obj[k]) for k in sorted(obj)}
    if isinstance(obj, (list, tuple)):
        return [_stable_dict(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return [_stable_dict(v) for v in sorted(obj, key=repr)]
    return obj


def stable_id(namespace: str, identity_fields: dict[str, Any]) -> str:
    """Deterministic namespaced id: '<namespace>:<sha256(canonical-json)>'.

    identity_fields must contain only the fields that DEFINE identity (never
    record_time / mutable metadata), so the same logical record always hashes
    to the same id.
    """
    payload = json.dumps(
        _stable_dict(identity_fields),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"


@dataclass(frozen=True)
class ValidTime:
    """Bitemporal valid-time: when the asserted fact is true in the world.

    start / end are ISO-8601 strings or None. qualifier disambiguates open and
    unknown intervals so an absent bound is never silently read as 'now'.
    """

    start: Optional[str] = None
    end: Optional[str] = None
    qualifier: Literal["instant", "interval", "open", "unknown"] = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "qualifier": self.qualifier}


@dataclass(frozen=True)
class SourceRecord:
    """A single acquired evidence source (file, probe, doc, derived artifact).

    source_content_hash is the hash of the REAL acquired bytes; it is empty
    only when hashing was skipped for a recorded reason (metadata carries
    hash_recorded=False + why). Derived artifacts carry derivation_key +
    input_record_ids + derivation_activity_id instead of pretending to be an
    acquired file. Sensitive paths are recorded presence-only (metadata
    path_class="sensitive_configuration", content_recorded=False,
    hash_recorded=False) with redaction_status="redacted" and no size/mtime
    fingerprint.
    """

    subject_path: str
    source_kind: SourceKind
    modality: SourceModality
    activity_id: str
    run_id: str
    source_content_hash: str = ""
    extraction_hash: str = ""
    derivation_key: str = ""
    input_record_ids: tuple[str, ...] = ()
    derivation_activity_id: str = ""
    repository_commit: Optional[str] = None
    repository_commit_status: Literal["resolved", "unavailable", "not_applicable"] = (
        "not_applicable"
    )
    acquisition_context: str = ""
    probe_name: Optional[str] = None
    redaction_status: RedactionStatus = "none"
    acquired_at: Optional[str] = None
    recorded_at: Optional[str] = None
    schema_version: str = SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def source_identity_fields(self) -> dict[str, Any]:
        """Stable cross-run source identity — NO run/activity/time fields."""
        return {
            "subject_path": self.subject_path,
            "source_kind": self.source_kind,
            "modality": self.modality,
            "source_content_hash": self.source_content_hash,
            "extraction_hash": self.extraction_hash,
            "derivation_key": self.derivation_key,
            "repository_commit": self.repository_commit,
            "probe_name": self.probe_name,
        }

    @property
    def source_identity_id(self) -> str:
        return stable_id("srcident", self.source_identity_fields())

    def identity_fields(self) -> dict[str, Any]:
        """Run-scoped ACQUISITION identity = source identity + run + activity."""
        return {
            "source_identity": self.source_identity_fields(),
            "run_id": self.run_id,
            "activity_id": self.activity_id,
        }

    @property
    def id(self) -> str:
        return stable_id("source", self.identity_fields())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["input_record_ids"] = list(self.input_record_ids)
        d["id"] = self.id
        d["source_identity_id"] = self.source_identity_id
        return d


@dataclass(frozen=True)
class ObservationRecord:
    """A recorded observation: subject-predicate-value with a kind and an
    OPTIONAL maturity facet.

    observation_kind says WHAT KIND of fact this is ("maturity",
    "probe_status", "aggregate_count", ...). maturity_facet grades
    implementation maturity and is None whenever the observation does not
    describe implementation maturity — a probe failure is
    observation_kind="probe_status", maturity_facet=None, never facet
    "declared". A declared/specified maturity observation is a DESIGN
    assertion, never proof of existence.
    """

    subject: str
    predicate: str
    value: Any
    observation_kind: str
    source_id: str
    run_id: str
    maturity_facet: Optional[EvidenceFacet] = None
    scope: str = ""
    valid_time: ValidTime = field(default_factory=ValidTime)
    recorded_at: Optional[str] = None
    support: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def identity_fields(self) -> dict[str, Any]:
        val = self.value
        if isinstance(val, (dict, list, tuple, set, frozenset)):
            val = _stable_dict(val)
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "value": val,
            "observation_kind": self.observation_kind,
            "maturity_facet": self.maturity_facet,
            "source_id": self.source_id,
            "scope": self.scope,
            "run_id": self.run_id,
        }

    @property
    def id(self) -> str:
        return stable_id("obs", self.identity_fields())

    @property
    def is_declaration(self) -> bool:
        return self.maturity_facet in DECLARATION_FACETS

    @property
    def is_implementation(self) -> bool:
        return self.maturity_facet in IMPLEMENTATION_FACETS

    @property
    def is_runtime(self) -> bool:
        return self.maturity_facet in RUNTIME_FACETS

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["value"] = _stable_dict(self.value)
        d["valid_time"] = self.valid_time.to_dict()
        d["id"] = self.id
        return d


@dataclass(frozen=True)
class ClaimLedgerEntry:
    """An append-only ledger entry asserting a proposition about the codebase.

    Entries are never rewritten. Supersession appends a NEW entry that links back
    via supersedes; the prior entry stays intact for bitemporal replay.
    support_factors preserves RAW factors (including None for missing ones);
    support_score is a derived support_score, NOT a calibrated probability.

    claim_type is load-bearing: canonical ownership is asserted ONLY through
    claim_type="canonical_owner" entries (owned concern in `scope`, owner path
    in `object_ref`) — never mined from free text or uncertainty_reasons.
    """

    proposition: str
    claim_type: str
    scope: str
    status: ClaimStatus
    run_id: str
    object_ref: str = ""
    supporting_observation_ids: tuple[str, ...] = ()
    contradicting_observation_ids: tuple[str, ...] = ()
    valid_time: ValidTime = field(default_factory=ValidTime)
    recorded_at: Optional[str] = None
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    support_factors: dict[str, Any] = field(default_factory=dict)
    support_score: Optional[float] = None
    uncertainty_reasons: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def lineage_key(self) -> dict[str, Any]:
        """Fields that identify the CLAIM LINEAGE (stable across entries)."""
        return {
            "proposition": self.proposition,
            "claim_type": self.claim_type,
            "scope": self.scope,
            "object_ref": self.object_ref,
        }

    def lineage_id(self) -> str:
        return stable_id("claim", self.lineage_key())

    def identity_fields(self) -> dict[str, Any]:
        return {
            "lineage": self.lineage_key(),
            "status": self.status,
            "supporting": sorted(self.supporting_observation_ids),
            "contradicting": sorted(self.contradicting_observation_ids),
            "supersedes": self.supersedes,
            "recorded_at": self.recorded_at,
            "run_id": self.run_id,
        }

    @property
    def id(self) -> str:
        return stable_id("claimentry", self.identity_fields())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["valid_time"] = self.valid_time.to_dict()
        d["supporting_observation_ids"] = list(self.supporting_observation_ids)
        d["contradicting_observation_ids"] = list(self.contradicting_observation_ids)
        d["uncertainty_reasons"] = list(self.uncertainty_reasons)
        d["id"] = self.id
        d["lineage_id"] = self.lineage_id()
        return d


@dataclass(frozen=True)
class DerivedBelief:
    """A PROJECTION of a claim lineage's current epistemic state.

    Never authored independently — build via ledger.ClaimLedger.belief_state()
    from the latest non-superseded entry. derivation_version distinguishes a
    re-derivation under new weights.
    """

    claim_lineage_id: str
    status: ClaimStatus
    support_score: Optional[float]
    derivation_version: str
    derivation_factors: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IdentityResolution:
    """A resolution over candidate entity ids: merge/link/separate/unresolved.

    candidate_basis records HOW the pair was proposed: "seed_fixture" for the
    hand-curated known pairs, "mined:<rule>" for deterministic candidate
    mining. Candidate generation, evidence, and verdict are separate concerns —
    a mined candidate with no evidence is "unresolved", never auto-merged on
    names alone.
    """

    candidate_entity_ids: tuple[str, ...]
    verdict: IdentityVerdict
    run_id: str
    candidate_basis: str = "seed_fixture"
    supporting_evidence_ids: tuple[str, ...] = ()
    support_score: Optional[float] = None
    rationale: str = ""
    recorded_at: Optional[str] = None
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    schema_version: str = SCHEMA_VERSION

    def pair_key(self) -> dict[str, Any]:
        return {"candidates": sorted(self.candidate_entity_ids)}

    def lineage_id(self) -> str:
        return stable_id("identity", self.pair_key())

    def identity_fields(self) -> dict[str, Any]:
        return {
            "candidates": sorted(self.candidate_entity_ids),
            "verdict": self.verdict,
            "candidate_basis": self.candidate_basis,
            "evidence": sorted(self.supporting_evidence_ids),
            "supersedes": self.supersedes,
            "recorded_at": self.recorded_at,
            "run_id": self.run_id,
        }

    @property
    def id(self) -> str:
        return stable_id("identityentry", self.identity_fields())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["candidate_entity_ids"] = list(self.candidate_entity_ids)
        d["supporting_evidence_ids"] = list(self.supporting_evidence_ids)
        d["id"] = self.id
        d["lineage_id"] = self.lineage_id()
        return d


@dataclass(frozen=True)
class CausalSupportRecord:
    """The evidential basis for a causal/mechanistic assertion.

    basis is a TYPED evidence class, not a rank on a global ladder: "formal"
    is authoritative for a formal relation within a system (an import edge)
    yet says nothing about external validity, and experimental evidence can be
    internally weak. Validity is modeled per dimension; each dimension is None
    when not assessed, never guessed. limitations should be non-empty for
    anything not directly verified.
    """

    assertion_id: str
    basis: CausalBasis
    run_id: str
    evidence_ids: tuple[str, ...] = ()
    scope: str = ""
    method: str = ""
    internal_validity: Optional[float] = None
    external_validity: Optional[float] = None
    reproducibility: Optional[float] = None
    formal_soundness: Optional[float] = None
    limitations: tuple[str, ...] = ()
    recorded_at: Optional[str] = None
    schema_version: str = SCHEMA_VERSION

    def identity_fields(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "basis": self.basis,
            "evidence": sorted(self.evidence_ids),
            "scope": self.scope,
            "run_id": self.run_id,
        }

    @property
    def id(self) -> str:
        return stable_id("causal", self.identity_fields())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence_ids"] = list(self.evidence_ids)
        d["limitations"] = list(self.limitations)
        d["id"] = self.id
        return d
