"""Migration test suite — fixtures and markers."""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")


def pytest_configure(config):
    config.addinivalue_line("markers", "migration: migration safety-net test")
    config.addinivalue_line("markers", "external: touches network or external service")
    config.addinivalue_line("markers", "llm: uses LLM (slow, costs tokens)")
    config.addinivalue_line("markers", "db: needs database connection")


FIXTURE_PATH = Path("/opt/OS/tests/fixtures/ingestion_fixture.md")

MOCK_LLM_RESPONSE = json.dumps(
    {
        "observations": [
            {
                "primitive_type": "state",
                "label": "System uses 4-layer navigation hierarchy",
                "description": "Palace, Wing, Room, Locus form structured navigation layers.",
                "confidence": 0.95,
                "source_reference": "test.md:lines 1-5",
                "evidence": "Palace — the whole system. Wing — a top-level module.",
                "is_inferred": False,
            },
            {
                "primitive_type": "constraint",
                "label": "AI must translate questions to concerns first",
                "description": "Agents map questions to concerns before navigating rooms.",
                "confidence": 0.90,
                "source_reference": "test.md:lines 10-15",
                "evidence": "Translate the user's question into a concern.",
                "is_inferred": False,
            },
            {
                "primitive_type": "action",
                "label": "Navigate by concern then room then purpose then loci",
                "description": "The retrieval sequence is: concern, room, purpose, core loci.",
                "confidence": 0.88,
                "source_reference": "test.md:lines 12-18",
                "evidence": "1. Translate. 2. Open room. 3. Read purpose. 4. Core loci.",
                "is_inferred": False,
            },
        ],
        "relationships": [
            {
                "from_index": 0,
                "to_index": 1,
                "relationship_type": "constrains",
                "confidence": 0.85,
                "description": "Navigation hierarchy constrains query translation.",
            },
        ],
    }
)


@pytest.fixture
def temp_memory_store(tmp_path: Path) -> Path:
    """Minimal canonical memory store with seed data."""
    store = tmp_path / "canonical_memory_store"
    store.mkdir()
    seed = {
        "memory_id": "mem-seed-001",
        "candidate_id": "cand-seed-001",
        "memory_type": "canonical",
        "primitive_type": "resource",
        "label": "Seed entry for testing",
        "content": "This is a seed memory entry.",
        "confidence": 0.8,
        "source_document_id": "test-seed",
        "source_content_hash": "abc123",
        "source_decomposition_id": "decomp-seed",
        "promotion_receipt_id": "receipt-seed",
        "provenance": {
            "source_reference": "test",
            "evidence": "seed",
            "is_inferred": False,
        },
        "lineage": {
            "candidate_id": "cand-seed-001",
            "decomposition_id": "decomp-seed",
            "document_id": "test-seed",
            "content_hash": "abc123",
            "classification_reason": "seed",
        },
        "timestamp": "2026-05-12T00:00:00+00:00",
    }
    (store / "memories.jsonl").write_text(json.dumps(seed) + "\n")
    (store / "promotion_receipts.jsonl").write_text(
        json.dumps(
            {
                "receipt_id": "receipt-seed",
                "candidate_id": "cand-seed-001",
                "decision": "promoted",
                "reason": "Seed",
                "confidence": 0.8,
                "promoter": "test",
                "timestamp": "2026-05-12T00:00:00+00:00",
                "rollback_reference": "candidate:cand-seed-001",
            }
        )
        + "\n"
    )
    (store / "index.json").write_text(
        json.dumps(
            {
                "entries": {
                    "mem-seed-001": {
                        "memory_type": "canonical",
                        "primitive_type": "resource",
                        "label": "Seed entry for testing",
                        "source_document_id": "test-seed",
                        "timestamp": "2026-05-12T00:00:00+00:00",
                    }
                }
            }
        )
    )
    (store / "promotion_summary.json").write_text(
        json.dumps(
            {
                "promoted_canonical": [
                    {
                        "memory_id": "mem-seed-001",
                        "receipt_id": "receipt-seed",
                        "label": "Seed entry for testing",
                        "type": "resource",
                    }
                ]
            }
        )
    )
    return store


@pytest.fixture
def fixture_file() -> Path:
    return FIXTURE_PATH
