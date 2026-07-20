"""Reconstruction subsystem — the domain-reconstruction evidence/claim/identity data layer.

NOT an ontology home. This package imports canonical substrate types and writes
ONLY run-scoped instance artifacts under data/world_models/self/runs/<run_id>/.
It never registers a new ontology/domain-model registry and never contaminates
the L2 metamodel surface.

Public API: record contracts, provenance/persistence primitives, the append-
preserving claim ledger, and the identity-resolution log.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

from substrate.understanding.reconstruction.contracts import (
    DECLARATION_FACETS,
    FACET_STRENGTH,
    IMPLEMENTATION_FACETS,
    RUNTIME_FACETS,
    SCHEMA_VERSION,
    ActivityKind,
    AnswerStatus,
    CausalBasis,
    CausalSupportRecord,
    ClaimLedgerEntry,
    ClaimStatus,
    DerivedBelief,
    EvidenceFacet,
    IdentityResolution,
    IdentityVerdict,
    ObservationRecord,
    RedactionStatus,
    SourceKind,
    SourceModality,
    SourceRecord,
    ValidTime,
    stable_id,
)
from substrate.understanding.reconstruction.identity import (
    IdentityResolutionLog,
    candidate_pair,
)
from substrate.understanding.reconstruction.import_evidence import (
    ImportEvidenceResult,
    module_dotted_name,
    scan_import_evidence,
)
from substrate.understanding.reconstruction.ledger import (
    ALLOWED_TRANSITIONS,
    CONTRADICTED_SCORE_CAP,
    DERIVATION_VERSION,
    SUPPORT_WEIGHTS,
    ClaimLedger,
    independence_report,
    support_score,
)
from substrate.understanding.reconstruction.provenance import (
    RUN_ARTIFACTS,
    ActivityRecord,
    JsonlAppender,
    RunLayout,
    atomic_write_json,
    canonical_json,
    content_hash,
    file_sha256,
)
from substrate.understanding.reconstruction.test_evidence import (
    SELECTION_TEMPLATES,
    TEST_EVIDENCE_SCHEMA_VERSION,
    TestEvidenceResult,
    classify_test,
    collect_test_evidence,
    derive_tested_facets,
    ingest_test_report,
    normalize_execution,
    scan_test_inventory,
)

__all__ = [
    "ActivityKind",
    "AnswerStatus",
    "CausalBasis",
    "CausalSupportRecord",
    "ClaimLedgerEntry",
    "ClaimStatus",
    "DECLARATION_FACETS",
    "DerivedBelief",
    "EvidenceFacet",
    "FACET_STRENGTH",
    "IMPLEMENTATION_FACETS",
    "IdentityResolution",
    "IdentityVerdict",
    "ObservationRecord",
    "RUNTIME_FACETS",
    "RedactionStatus",
    "SCHEMA_VERSION",
    "SourceKind",
    "SourceModality",
    "SourceRecord",
    "ValidTime",
    "stable_id",
    "IdentityResolutionLog",
    "ImportEvidenceResult",
    "module_dotted_name",
    "scan_import_evidence",
    "SELECTION_TEMPLATES",
    "TEST_EVIDENCE_SCHEMA_VERSION",
    "TestEvidenceResult",
    "classify_test",
    "collect_test_evidence",
    "derive_tested_facets",
    "ingest_test_report",
    "normalize_execution",
    "scan_test_inventory",
    "candidate_pair",
    "ALLOWED_TRANSITIONS",
    "CONTRADICTED_SCORE_CAP",
    "DERIVATION_VERSION",
    "SUPPORT_WEIGHTS",
    "ClaimLedger",
    "independence_report",
    "support_score",
    "RUN_ARTIFACTS",
    "ActivityRecord",
    "JsonlAppender",
    "RunLayout",
    "atomic_write_json",
    "canonical_json",
    "content_hash",
    "file_sha256",
]
