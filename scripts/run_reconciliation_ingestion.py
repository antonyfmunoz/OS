"""Multi-document ingestion with reconciliation.

Processes 4 additional real documents through the full pipeline:
  bridge → decompose → candidates → reconcile → promote/skip/strengthen

Persists all artifacts to data/runtime/reconciliation_ingestion_set/
and reconciliation receipts to data/runtime/reconciliation_receipts/.

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
from substrate.state.memory.contracts.canonical_memory_reconciliation_engine_v1 import ReconciliationEngine
from substrate.state.memory.contracts.canonical_memory_store_v1 import CanonicalMemoryStore

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
    {
        "name": "Coaching_Philosophy_Methodology",
        "canonical": Path(
            "data/canonical_source_records/w0_001/Coaching_Philosophy_Methodology_1ult_kJP.json"
        ),
        "raw": Path(
            "data/drive_doc_ingestion_tab_aware/Coaching_Philosophy_Methodology_1ult_kJP.json"
        ),
    },
    {
        "name": "Systems_Inventory",
        "canonical": Path("data/canonical_source_records/w0_001/Systems_Inventory_1deFPswA.json"),
        "raw": Path("data/drive_doc_ingestion_tab_aware/Systems_Inventory_1deFPswA.json"),
    },
]

INGESTION_DIR = Path("data/runtime/reconciliation_ingestion_set")
RECEIPTS_DIR = Path("data/runtime/reconciliation_receipts")
STORE_DIR = Path("data/runtime/reconciliation_memory_store")


def run() -> dict:
    INGESTION_DIR.mkdir(parents=True, exist_ok=True)

    store = CanonicalMemoryStore(store_dir=STORE_DIR)
    engine = ReconciliationEngine(store_dir=STORE_DIR, receipts_dir=RECEIPTS_DIR)

    summary = {
        "documents_processed": 0,
        "total_observations": 0,
        "total_candidates": 0,
        "total_new": 0,
        "total_duplicates": 0,
        "total_strengthened": 0,
        "total_conflicts": 0,
        "per_document": [],
    }

    for doc_info in DOCUMENTS:
        name = doc_info["name"]
        print(f"\n{'=' * 60}")
        print(f"Processing: {name}")
        print(f"{'=' * 60}")

        # Step 1: Bridge
        print("  [1/5] Bridge: normalizing scanner output...")
        normalized = normalize_from_scanner_outputs(doc_info["canonical"], doc_info["raw"])
        print(f"        doc_id={normalized.document_id}, words={normalized.total_words}")

        bridge_path = INGESTION_DIR / f"{normalized.document_id}_normalized.json"
        with open(bridge_path, "w") as f:
            json.dump(normalized.to_dict(), f, indent=2)

        # Step 2: Decompose
        print("  [2/5] Decompose: extracting primitives...")
        decomposition = decompose_document(
            document_id=normalized.document_id,
            content_hash=normalized.content_hash,
            full_text=normalized.full_text,
            title=normalized.title,
        )
        print(
            f"        observations={len(decomposition.observations)}, "
            f"relationships={len(decomposition.relationships)}"
        )

        decomp_path = INGESTION_DIR / f"{normalized.document_id}_decomposition.json"
        with open(decomp_path, "w") as f:
            json.dump(decomposition.to_dict(), f, indent=2)

        # Step 3: Generate candidates
        print("  [3/5] Candidates: classifying canonical vs instance...")
        candidates = generate_candidates(decomposition, normalized.document_id)
        all_cands = [
            c.to_dict() for c in candidates.canonical_candidates + candidates.instance_candidates
        ]
        print(
            f"        canonical={len(candidates.canonical_candidates)}, "
            f"instance={len(candidates.instance_candidates)}"
        )

        cands_path = INGESTION_DIR / f"{normalized.document_id}_candidates.json"
        with open(cands_path, "w") as f:
            json.dump(candidates.to_dict(), f, indent=2)

        # Step 4: Reconcile
        print("  [4/5] Reconcile: checking against existing memories...")
        engine.load_existing_memories()
        receipt = engine.reconcile_candidates(all_cands, normalized.document_id)
        print(
            f"        new={receipt.new_count}, duplicates={receipt.duplicate_count}, "
            f"strengthen={receipt.strengthen_count}, conflicts={receipt.conflict_count}"
        )

        receipt_path = engine.save_receipt(receipt)
        print(f"        receipt saved: {receipt_path}")

        # Step 5: Apply decisions
        print("  [5/5] Apply: promoting new memories, strengthening existing...")
        apply_result = engine.apply_decisions(receipt, all_cands, store)
        print(
            f"        promoted={apply_result['promoted']}, "
            f"skipped={apply_result['skipped']}, "
            f"strengthened={apply_result['strengthened']}"
        )

        doc_summary = {
            "name": name,
            "document_id": normalized.document_id,
            "words": normalized.total_words,
            "observations": len(decomposition.observations),
            "candidates": len(all_cands),
            "reconciliation": {
                "new": receipt.new_count,
                "duplicates": receipt.duplicate_count,
                "strengthened": receipt.strengthen_count,
                "conflicts": receipt.conflict_count,
            },
        }
        summary["per_document"].append(doc_summary)
        summary["documents_processed"] += 1
        summary["total_observations"] += len(decomposition.observations)
        summary["total_candidates"] += len(all_cands)
        summary["total_new"] += receipt.new_count
        summary["total_duplicates"] += receipt.duplicate_count
        summary["total_strengthened"] += receipt.strengthen_count
        summary["total_conflicts"] += receipt.conflict_count

    # Save summary
    summary_path = INGESTION_DIR / "ingestion_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Build entity map
    print(f"\n{'=' * 60}")
    print("Building entity continuity map...")
    engine.load_existing_memories()
    entity_map = engine.get_entity_map()

    entity_dir = Path("data/runtime/canonical_entity_continuity")
    entity_dir.mkdir(parents=True, exist_ok=True)
    entity_path = entity_dir / "entity_continuity_map.json"

    entity_data = {
        "total_entities": len(entity_map),
        "cross_document_entities": sum(
            1 for e in entity_map.values() if len(e.source_document_ids) > 1
        ),
        "entities": {eid: e.to_dict() for eid, e in entity_map.items()},
    }
    with open(entity_path, "w") as f:
        json.dump(entity_data, f, indent=2)
    print(f"  entities={len(entity_map)}, cross_document={entity_data['cross_document_entities']}")

    print(f"\n{'=' * 60}")
    print("INGESTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Documents: {summary['documents_processed']}")
    print(f"  Total observations: {summary['total_observations']}")
    print(f"  Total candidates: {summary['total_candidates']}")
    print(f"  New memories: {summary['total_new']}")
    print(f"  Duplicates skipped: {summary['total_duplicates']}")
    print(f"  Strengthened: {summary['total_strengthened']}")
    print(f"  Conflicts: {summary['total_conflicts']}")
    print(f"  Entities: {len(entity_map)}")

    store_stats = store.get_stats()
    print(f"\n  Store totals: {store_stats}")

    return summary


if __name__ == "__main__":
    run()
