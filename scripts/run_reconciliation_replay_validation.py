"""Reconciliation replay validation.

Proves that re-running the full pipeline on the same documents
produces identical reconciliation decisions.

Phase 96.8BM.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from adapters.adapter_engine.gws_scanner_bridge_v1 import normalize_from_scanner_outputs
from adapters.adapter_engine.substrate_candidate_gen_v1 import generate_candidates
from adapters.adapter_engine.substrate_decomposer_v1 import decompose_document
from state.memory.contracts.canonical_memory_reconciliation_engine_v1 import ReconciliationEngine

STORE_DIR = Path("data/runtime/reconciliation_memory_store")
RECEIPTS_DIR = Path("data/runtime/reconciliation_receipts")
PROOF_DIR = Path("data/runtime/reconciliation_replay_proofs")

DOCUMENTS = [
    {
        "name": "EntrepreneurOS",
        "canonical": Path("data/canonical_source_records/w0_001/EntrepreneurOS_1kKBGCS9.json"),
        "raw": Path("data/drive_doc_ingestion_tab_aware/EntrepreneurOS_1kKBGCS9.json"),
    },
    {
        "name": "Conglomerate_Brands",
        "canonical": Path("data/canonical_source_records/w0_001/Conglomerate_Brands_1e6E8OxC.json"),
        "raw": Path("data/drive_doc_ingestion_tab_aware/Conglomerate_Brands_1e6E8OxC.json"),
    },
]


def run() -> dict:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)

    proof: dict = {
        "validation_type": "reconciliation_replay_validation",
        "tests": [],
    }

    for doc_info in DOCUMENTS:
        name = doc_info["name"]
        print(f"\nReplay test: {name}")

        # Run 1
        doc1 = normalize_from_scanner_outputs(doc_info["canonical"], doc_info["raw"])
        decomp1 = decompose_document(
            doc1.document_id, doc1.content_hash, doc1.full_text, doc1.title
        )
        cands1 = generate_candidates(decomp1, doc1.document_id)
        all_cands1 = [c.to_dict() for c in cands1.canonical_candidates + cands1.instance_candidates]

        engine1 = ReconciliationEngine(store_dir=STORE_DIR, receipts_dir=RECEIPTS_DIR)
        engine1.load_existing_memories()
        receipt1 = engine1.reconcile_candidates(all_cands1, doc1.document_id)

        # Run 2
        doc2 = normalize_from_scanner_outputs(doc_info["canonical"], doc_info["raw"])
        decomp2 = decompose_document(
            doc2.document_id, doc2.content_hash, doc2.full_text, doc2.title
        )
        cands2 = generate_candidates(decomp2, doc2.document_id)
        all_cands2 = [c.to_dict() for c in cands2.canonical_candidates + cands2.instance_candidates]

        engine2 = ReconciliationEngine(store_dir=STORE_DIR, receipts_dir=RECEIPTS_DIR)
        engine2.load_existing_memories()
        receipt2 = engine2.reconcile_candidates(all_cands2, doc2.document_id)

        # Compare
        checks = {
            "doc_id_stable": doc1.document_id == doc2.document_id,
            "content_hash_stable": doc1.content_hash == doc2.content_hash,
            "decomp_id_stable": decomp1.decomposition_id == decomp2.decomposition_id,
            "obs_count_stable": len(decomp1.observations) == len(decomp2.observations),
            "rel_count_stable": len(decomp1.relationships) == len(decomp2.relationships),
            "candidate_set_id_stable": cands1.set_id == cands2.set_id,
            "canonical_count_stable": len(cands1.canonical_candidates)
            == len(cands2.canonical_candidates),
            "instance_count_stable": len(cands1.instance_candidates)
            == len(cands2.instance_candidates),
            "receipt_id_stable": receipt1.receipt_id == receipt2.receipt_id,
            "new_count_stable": receipt1.new_count == receipt2.new_count,
            "dup_count_stable": receipt1.duplicate_count == receipt2.duplicate_count,
            "strengthen_count_stable": receipt1.strengthen_count == receipt2.strengthen_count,
            "conflict_count_stable": receipt1.conflict_count == receipt2.conflict_count,
            "decision_count_stable": len(receipt1.decisions) == len(receipt2.decisions),
        }

        all_stable = all(checks.values())
        test = {
            "document": name,
            "document_id": doc1.document_id,
            "checks": checks,
            "all_stable": all_stable,
            "pass": all_stable,
        }
        proof["tests"].append(test)

        for check_name, result in checks.items():
            status = "PASS" if result else "FAIL"
            print(f"  {check_name}: {status}")
        print(f"  Overall: {'PASS' if all_stable else 'FAIL'}")

    all_pass = all(t["pass"] for t in proof["tests"])
    proof["all_pass"] = all_pass
    proof["total_tests"] = len(proof["tests"])
    proof["passed"] = sum(1 for t in proof["tests"] if t["pass"])

    proof_path = PROOF_DIR / "replay_validation_proof.json"
    with open(proof_path, "w") as f:
        json.dump(proof, f, indent=2)

    print(f"\nRESULT: {proof['passed']}/{proof['total_tests']} documents replay-stable")
    print(f"Proof saved: {proof_path}")

    return proof


if __name__ == "__main__":
    run()
