"""Reconciliation query validation.

Validates that reconciled memories are queryable, provenanced,
and correctly reconciled across documents.

Phase 96.8BM.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from state.memory.contracts.canonical_memory_reconciliation_engine_v1 import ReconciliationEngine
from state.memory.contracts.canonical_memory_store_v1 import CanonicalMemoryStore

STORE_DIR = Path("data/runtime/reconciliation_memory_store")
RECEIPTS_DIR = Path("data/runtime/reconciliation_receipts")
PROOF_DIR = Path("data/runtime/reconciliation_query_proofs")


def run() -> dict:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)

    store = CanonicalMemoryStore(store_dir=STORE_DIR)
    engine = ReconciliationEngine(store_dir=STORE_DIR, receipts_dir=RECEIPTS_DIR)
    loaded = engine.load_existing_memories()

    proof: dict = {
        "validation_type": "reconciliation_query_validation",
        "store_dir": str(STORE_DIR),
        "total_memories_loaded": loaded,
        "tests": [],
    }

    # Test 1: Query by document — all 4 documents should have memories
    doc_ids = [
        "doc-1kKBGCS9kewNMwOB",
        "doc-1e6E8OxCmVfZW2Yk",
        "doc-1ult_kJPpvcG_NzR",
        "doc-1deFPswAzsZYLYyA",
    ]
    for doc_id in doc_ids:
        results = store.query_by_document(doc_id)
        test = {
            "test": f"query_by_document_{doc_id[:12]}",
            "document_id": doc_id,
            "result_count": len(results),
            "pass": len(results) > 0,
        }
        proof["tests"].append(test)
        print(
            f"  query_by_document({doc_id[:16]}...): {len(results)} memories — {'PASS' if test['pass'] else 'FAIL'}"
        )

    # Test 2: Query by type — both canonical and instance
    for mtype in ["canonical", "instance"]:
        results = store.query_by_type(mtype)
        test = {
            "test": f"query_by_type_{mtype}",
            "result_count": len(results),
            "pass": len(results) > 0,
        }
        proof["tests"].append(test)
        print(f"  query_by_type({mtype}): {len(results)} — {'PASS' if test['pass'] else 'FAIL'}")

    # Test 3: Query specific memory by ID
    first_mem = store.query_by_document(doc_ids[0])
    if first_mem:
        mem_id = first_mem[0]["memory_id"]
        result = store.query_by_id(mem_id)
        test = {
            "test": "query_by_id",
            "memory_id": mem_id,
            "has_provenance": bool(result and result.get("provenance")),
            "has_lineage": bool(result and result.get("lineage")),
            "pass": result is not None and result.get("provenance") is not None,
        }
        proof["tests"].append(test)
        print(f"  query_by_id({mem_id[:16]}...): {'PASS' if test['pass'] else 'FAIL'}")

    # Test 4: Reconciliation receipts exist for all docs
    for doc_id in doc_ids:
        receipt_path = RECEIPTS_DIR / f"{doc_id}_reconciliation.json"
        exists = receipt_path.exists()
        if exists:
            with open(receipt_path) as f:
                receipt = json.load(f)
            has_decisions = len(receipt.get("decisions", [])) > 0
        else:
            has_decisions = False
        test = {
            "test": f"receipt_exists_{doc_id[:12]}",
            "receipt_path": str(receipt_path),
            "exists": exists,
            "has_decisions": has_decisions,
            "pass": exists and has_decisions,
        }
        proof["tests"].append(test)
        print(f"  receipt_exists({doc_id[:16]}...): {'PASS' if test['pass'] else 'FAIL'}")

    # Test 5: Entity continuity map exists and has content
    entity_path = Path("data/runtime/canonical_entity_continuity/entity_continuity_map.json")
    entity_exists = entity_path.exists()
    entity_count = 0
    if entity_exists:
        with open(entity_path) as f:
            entity_data = json.load(f)
        entity_count = entity_data.get("total_entities", 0)
    test = {
        "test": "entity_continuity_map",
        "exists": entity_exists,
        "entity_count": entity_count,
        "pass": entity_exists and entity_count > 0,
    }
    proof["tests"].append(test)
    print(
        f"  entity_continuity_map: {entity_count} entities — {'PASS' if test['pass'] else 'FAIL'}"
    )

    # Test 6: Store stats match expected
    stats = store.get_stats()
    test = {
        "test": "store_stats_consistency",
        "stats": stats,
        "pass": stats.get("total", 0) == loaded,
    }
    proof["tests"].append(test)
    print(
        f"  store_stats: total={stats.get('total', 0)}, canonical={stats.get('canonical', 0)}, instance={stats.get('instance', 0)} — {'PASS' if test['pass'] else 'FAIL'}"
    )

    # Test 7: Duplicate detection worked (Systems Inventory had 27 dups)
    systems_receipt_path = RECEIPTS_DIR / "doc-1deFPswAzsZYLYyA_reconciliation.json"
    if systems_receipt_path.exists():
        with open(systems_receipt_path) as f:
            systems_receipt = json.load(f)
        dup_count = systems_receipt.get("duplicate_count", 0)
        test = {
            "test": "duplicate_detection_systems_inventory",
            "duplicate_count": dup_count,
            "pass": dup_count > 0,
        }
        proof["tests"].append(test)
        print(
            f"  duplicate_detection (Systems Inventory): {dup_count} dups — {'PASS' if test['pass'] else 'FAIL'}"
        )

    # Summary
    all_pass = all(t["pass"] for t in proof["tests"])
    proof["all_pass"] = all_pass
    proof["total_tests"] = len(proof["tests"])
    proof["passed"] = sum(1 for t in proof["tests"] if t["pass"])

    proof_path = PROOF_DIR / "query_validation_proof.json"
    with open(proof_path, "w") as f:
        json.dump(proof, f, indent=2)

    print(f"\n  RESULT: {proof['passed']}/{proof['total_tests']} PASS")
    print(f"  Proof saved: {proof_path}")

    return proof


if __name__ == "__main__":
    run()
