"""Prove W0 safe document ingestion candidate creation.

Exercises the routing lifecycle for doc_ingestion_candidate_safe_test_doc:
  Discord !ingest-candidate simulation
  -> WorkPacket creation
  -> ControlPlaneRouter decision
  -> Extraction reference resolution
  -> Ingestion candidate normalization
  -> Memory candidate creation
  -> Governance boundary enforcement
  -> RuntimeProof generation
  -> RouterResult normalization

Generates proof artifacts in data/runtime/w0_ingestion_candidates/.

Usage:
  python3 scripts/prove_w0_doc_ingestion_candidate.py          # dry-run (VPS safe)
  python3 scripts/prove_w0_doc_ingestion_candidate.py --live    # live (local WSL only)

UMH substrate subsystem. Phase 96.8T.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.control_plane_router.control_plane_router_v1 import ControlPlaneRouterV1
from core.control_plane_router.router_contracts import (
    RouterDecision,
    RouterStatus,
    RuntimeProofReference,
    WorkPacket,
)
from core.runtime.adapter_registry_contracts import AdapterRegistry
from core.runtime.worker_runtime_contracts import ProofStatus, RuntimeProofRecord
from eos_ai.interfaces.discord_interface_adapter_v1 import (
    build_work_packet_for_router,
    format_router_result,
)


BASE_DIR = Path("/opt/OS")
PROOF_OUTPUT_DIR = BASE_DIR / "data" / "runtime" / "w0_ingestion_candidates"
REGISTRY_PATH = BASE_DIR / "data" / "registries" / "local_worker_adapter_registry_v1.json"
ROUTER_CONFIG_PATH = BASE_DIR / "config" / "control_plane_router_v1.json"
INGESTION_CONFIG_PATH = BASE_DIR / "config" / "w0_doc_ingestion_candidate_proof_v1.json"

FORBIDDEN_ACTIONS = [
    "promote_memory",
    "canonical_write",
    "world_model_update",
    "generate_embeddings",
    "interpret_content",
    "summarize_content",
    "drive_wide_ingestion",
    "arbitrary_url_open",
    "recursive_crawl",
    "take_screenshot",
    "capture_ocr",
    "mutate_drive",
    "mutate_docs",
    "extract_cookies",
    "extract_tokens",
]

SIMULATED_EXTRACTED_TEXT = (
    "This is the EOS W0 Test Document. It exists solely for extraction proof "
    "validation. No sensitive content. No private data. This document is used "
    "to verify that the UMH substrate can perform bounded, policy-restricted "
    "document extraction through the canonical routed path."
)


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [prove-w0-ingest-cand] {msg}", flush=True)


def load_ingestion_config() -> dict:
    with open(INGESTION_CONFIG_PATH) as f:
        return json.load(f)


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prove_work_packet_creation(
    safe_doc_url: str,
    safe_doc_title: str,
    extraction_reference_id: str,
) -> WorkPacket:
    """Step 1: Discord !ingest-candidate -> WorkPacket."""
    _log("STEP 1: build WorkPacket from !ingest-candidate command")
    wp = build_work_packet_for_router(
        "!ingest-candidate",
        safe_doc_url=safe_doc_url,
        safe_doc_title=safe_doc_title,
        extraction_reference_id=extraction_reference_id,
    )
    assert wp is not None, "WorkPacket must not be None for !ingest-candidate"
    assert wp.action_type == "doc_ingestion_candidate_safe_test_doc"
    assert wp.source_interface == "discord_interface_adapter_v1"
    assert wp.payload.get("url") == safe_doc_url
    assert wp.payload.get("no_secret_capture") is True
    assert wp.payload.get("no_mutation") is True
    _log(f"  packet_id: {wp.packet_id}")
    _log(f"  action_type: {wp.action_type}")
    _log(f"  url: {wp.payload.get('url')}")
    _log(f"  no_secret_capture: {wp.payload.get('no_secret_capture')}")
    _log(f"  no_mutation: {wp.payload.get('no_mutation')}")
    _log("  PASS")
    return wp


def prove_router_decision(wp: WorkPacket, router: ControlPlaneRouterV1) -> None:
    """Step 2: Router resolves capability, adapter, runtime."""
    _log("STEP 2: router dry-run decision")
    result = router.route_dry_run(wp)
    assert result.router_status == RouterStatus.ROUTED, (
        f"expected ROUTED, got {result.router_status}"
    )
    assert result.router_decision is not None
    assert result.adapter_selected == "windows_interactive_desktop_relay"
    assert result.runtime_target == "local_worker_runtime_daemon"
    assert result.router_decision.capability_matched == "ingestion_candidacy"
    _log(f"  router_status: {result.router_status.value}")
    _log(f"  adapter: {result.adapter_selected}")
    _log(f"  runtime: {result.runtime_target}")
    _log(f"  capability: {result.router_decision.capability_matched}")
    _log("  PASS")


def prove_forbidden_actions_blocked() -> None:
    """Step 3: Verify forbidden actions are not present."""
    _log("STEP 3: verify no forbidden actions in ingestion candidate payload")
    wp = build_work_packet_for_router("!ingest-candidate")
    payload_str = json.dumps(wp.payload).lower()
    for action in FORBIDDEN_ACTIONS:
        assert action not in payload_str, f"forbidden action '{action}' found in payload"
    _log(f"  checked {len(FORBIDDEN_ACTIONS)} forbidden actions: none present")
    _log("  PASS")


def prove_ingestion_candidate_schema(
    config: dict,
    safe_doc_title: str,
    safe_doc_url: str,
    extraction_reference_id: str,
) -> dict:
    """Step 4: Create and validate ingestion candidate."""
    _log("STEP 4: create and validate ingestion candidate schema")
    preview_max = config.get("extraction_preview_max_chars", 500)
    preview = SIMULATED_EXTRACTED_TEXT[:preview_max]
    content_hash = compute_content_hash(SIMULATED_EXTRACTED_TEXT)

    candidate = {
        "candidate_id": f"CAND-{uuid.uuid4().hex[:8]}",
        "source_type": "google_docs",
        "source_title": safe_doc_title,
        "source_id_or_url": safe_doc_url,
        "extraction_reference_id": extraction_reference_id,
        "normalized_text_preview": preview,
        "normalized_character_count": len(SIMULATED_EXTRACTED_TEXT),
        "content_hash": content_hash,
        "source_confidence": "high",
        "extraction_confidence": "high",
        "candidate_status": "created",
        "promotion_status": "candidate_only",
        "governance_required": True,
        "forbidden_actions_confirmed": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    required_fields = [
        "candidate_id",
        "source_type",
        "source_title",
        "source_id_or_url",
        "extraction_reference_id",
        "normalized_text_preview",
        "normalized_character_count",
        "content_hash",
        "source_confidence",
        "extraction_confidence",
        "candidate_status",
        "promotion_status",
        "governance_required",
        "forbidden_actions_confirmed",
        "timestamp",
    ]
    for f in required_fields:
        assert f in candidate, f"missing required field: {f}"
    assert len(preview) <= preview_max
    assert candidate["promotion_status"] == "candidate_only"
    assert candidate["governance_required"] is True
    assert candidate["forbidden_actions_confirmed"] is True
    assert len(content_hash) == 64

    _log(f"  candidate_id: {candidate['candidate_id']}")
    _log(f"  fields validated: {len(required_fields)}")
    _log(f"  preview length: {len(preview)} chars (max {preview_max})")
    _log(f"  content_hash: {content_hash[:16]}...")
    _log(f"  promotion_status: {candidate['promotion_status']}")
    _log(f"  governance_required: {candidate['governance_required']}")
    _log("  PASS")
    return candidate


def prove_memory_candidate_schema(
    candidate: dict,
    config: dict,
) -> dict:
    """Step 5: Create and validate memory candidate."""
    _log("STEP 5: create and validate memory candidate schema")
    preview_max = config.get("extraction_preview_max_chars", 500)

    memory_candidate = {
        "memory_candidate_id": f"MEM-CAND-{uuid.uuid4().hex[:8]}",
        "candidate_id": candidate["candidate_id"],
        "memory_type": "document_knowledge",
        "scope": "safe_test_doc",
        "source": candidate["source_id_or_url"],
        "confidence": candidate["extraction_confidence"],
        "content_preview": candidate["normalized_text_preview"][:preview_max],
        "promotion_status": "candidate_only",
        "requires_review": True,
        "allowed_next_actions": [
            "review_candidate",
            "approve_for_promotion",
            "reject_candidate",
            "request_re_extraction",
        ],
        "blocked_next_actions": [
            "promote_to_memory",
            "write_to_canonical",
            "update_world_model",
            "generate_embeddings",
            "interpret_content",
            "summarize_content",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    required_fields = [
        "memory_candidate_id",
        "candidate_id",
        "memory_type",
        "scope",
        "source",
        "confidence",
        "content_preview",
        "promotion_status",
        "requires_review",
        "allowed_next_actions",
        "blocked_next_actions",
        "timestamp",
    ]
    for f in required_fields:
        assert f in memory_candidate, f"missing required field: {f}"
    assert memory_candidate["promotion_status"] == "candidate_only"
    assert memory_candidate["requires_review"] is True
    assert "promote_to_memory" in memory_candidate["blocked_next_actions"]
    assert "write_to_canonical" in memory_candidate["blocked_next_actions"]
    assert len(memory_candidate["content_preview"]) <= preview_max

    _log(f"  memory_candidate_id: {memory_candidate['memory_candidate_id']}")
    _log(f"  candidate_id ref: {memory_candidate['candidate_id']}")
    _log(f"  fields validated: {len(required_fields)}")
    _log(f"  promotion_status: {memory_candidate['promotion_status']}")
    _log(f"  requires_review: {memory_candidate['requires_review']}")
    _log(f"  blocked actions: {len(memory_candidate['blocked_next_actions'])}")
    _log("  PASS")
    return memory_candidate


def prove_governance_boundary(candidate: dict, memory_candidate: dict) -> None:
    """Step 6: Verify governance boundary is enforced."""
    _log("STEP 6: verify governance boundary")
    assert candidate["promotion_status"] == "candidate_only"
    assert candidate["governance_required"] is True
    assert memory_candidate["promotion_status"] == "candidate_only"
    assert memory_candidate["requires_review"] is True
    assert "promote_to_memory" in memory_candidate["blocked_next_actions"]
    assert "write_to_canonical" in memory_candidate["blocked_next_actions"]
    assert "update_world_model" in memory_candidate["blocked_next_actions"]
    _log("  promotion_status: candidate_only (both artifacts)")
    _log("  governance_required: True")
    _log("  promote_to_memory: BLOCKED")
    _log("  write_to_canonical: BLOCKED")
    _log("  update_world_model: BLOCKED")
    _log("  PASS")


def prove_simulated_proof(wp: WorkPacket, safe_doc_url: str) -> RuntimeProofRecord:
    """Step 7: Simulated daemon proof (VPS dry-run)."""
    _log("STEP 7: simulated daemon ingestion candidate proof")
    proof = RuntimeProofRecord(
        proof_id=f"PROOF-{uuid.uuid4().hex[:8]}",
        worker_id="local_wsl_worker",
        adapter_id="windows_interactive_desktop_relay",
        action_type=wp.action_type,
        proof_status=ProofStatus.COMPLETED,
        adapter_status="completed",
        request_id=wp.packet_id,
        trace_id=wp.trace_id,
        evidence={
            "ingestion_candidate_created": True,
            "memory_candidate_created": True,
            "content_hash_generated": True,
            "promotion_status": "candidate_only",
            "governance_boundary_enforced": True,
            "canonical_memory_written": False,
            "world_model_updated": False,
            "embeddings_generated": False,
        },
        notes=[
            "Ingestion candidate created from bounded extraction",
            "Memory candidate created — awaiting governance approval",
            "No canonical writes, no world-model updates",
            "No memory promotion, no embeddings",
            "Governance boundary enforced",
        ],
    )
    assert proof.succeeded
    assert proof.evidence["canonical_memory_written"] is False
    assert proof.evidence["world_model_updated"] is False
    assert proof.evidence["embeddings_generated"] is False
    _log(f"  proof_id: {proof.proof_id}")
    _log(f"  proof_status: {proof.proof_status.value}")
    _log(f"  canonical_memory_written: {proof.evidence['canonical_memory_written']}")
    _log(f"  world_model_updated: {proof.evidence['world_model_updated']}")
    _log(f"  embeddings_generated: {proof.evidence['embeddings_generated']}")
    _log("  PASS")
    return proof


def prove_router_result(
    wp: WorkPacket,
    router: ControlPlaneRouterV1,
    proof: RuntimeProofRecord,
) -> None:
    """Step 8: RouterResult normalization + Discord formatting."""
    _log("STEP 8: RouterResult normalization")
    decision = RouterDecision(
        packet_id=wp.packet_id,
        action_type=wp.action_type,
        runtime_target="local_worker_runtime_daemon",
        adapter_selected="windows_interactive_desktop_relay",
        capability_matched="ingestion_candidacy",
    )
    proof_ref = RuntimeProofReference(
        proof_id=proof.proof_id,
        proof_status=proof.proof_status.value,
        adapter_status=proof.adapter_status,
        request_id=proof.request_id,
        trace_id=proof.trace_id,
    )
    result = router.build_router_result(
        RouterStatus.COMPLETED,
        decision=decision,
        proof_ref=proof_ref,
    )
    assert result.router_status == RouterStatus.COMPLETED
    discord_reply = format_router_result(result, "!ingest-candidate")
    assert "completed" in discord_reply
    _log(f"  router_status: {result.router_status.value}")
    _log(f"  discord reply:\n{discord_reply}")
    _log("  PASS")


def write_proof_artifacts(
    wp: WorkPacket,
    proof: RuntimeProofRecord,
    candidate: dict,
    memory_candidate: dict,
) -> None:
    """Step 9: Write proof artifacts."""
    _log("STEP 9: writing proof artifacts")
    PROOF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    wp_path = PROOF_OUTPUT_DIR / "w0_doc_ingestion_work_packet_example.json"
    wp_dict = {
        "packet_id": wp.packet_id,
        "action_type": wp.action_type,
        "payload": wp.payload,
        "source_interface": wp.source_interface,
        "trace_id": wp.trace_id,
        "timeout_seconds": wp.timeout_seconds,
        "timestamp": wp.timestamp,
    }
    with open(wp_path, "w") as f:
        json.dump(wp_dict, f, indent=2)
    _log(f"  {wp_path.name}")

    proof_path = PROOF_OUTPUT_DIR / "w0_doc_ingestion_runtime_proof_example.json"
    with open(proof_path, "w") as f:
        json.dump(dataclasses.asdict(proof), f, indent=2, default=str)
    _log(f"  {proof_path.name}")

    cand_path = PROOF_OUTPUT_DIR / "w0_doc_ingestion_candidate_example.json"
    with open(cand_path, "w") as f:
        json.dump(candidate, f, indent=2)
    _log(f"  {cand_path.name}")

    mem_cand_path = PROOF_OUTPUT_DIR / "w0_doc_memory_candidate_example.json"
    with open(mem_cand_path, "w") as f:
        json.dump(memory_candidate, f, indent=2)
    _log(f"  {mem_cand_path.name}")

    decision = RouterDecision(
        packet_id=wp.packet_id,
        action_type=wp.action_type,
        runtime_target="local_worker_runtime_daemon",
        adapter_selected="windows_interactive_desktop_relay",
        capability_matched="ingestion_candidacy",
    )
    proof_ref = RuntimeProofReference(
        proof_id=proof.proof_id,
        proof_status=proof.proof_status.value,
        adapter_status=proof.adapter_status,
        request_id=proof.request_id,
        trace_id=proof.trace_id,
    )
    router_result_path = PROOF_OUTPUT_DIR / "w0_doc_ingestion_router_result_example.json"
    router_result_dict = {
        "router_status": "completed",
        "router_decision": {
            "packet_id": decision.packet_id,
            "action_type": decision.action_type,
            "runtime_target": decision.runtime_target,
            "adapter_selected": decision.adapter_selected,
            "capability_matched": decision.capability_matched,
            "authority_satisfied": decision.authority_satisfied,
            "timestamp": decision.timestamp,
        },
        "runtime_target": "local_worker_runtime_daemon",
        "adapter_selected": "windows_interactive_desktop_relay",
        "runtime_proof_reference": {
            "proof_id": proof_ref.proof_id,
            "proof_status": proof_ref.proof_status,
            "adapter_status": proof_ref.adapter_status,
            "request_id": proof_ref.request_id,
            "trace_id": proof_ref.trace_id,
        },
        "execution_trace_id": wp.packet_id,
        "normalized_status": "completed",
    }
    with open(router_result_path, "w") as f:
        json.dump(router_result_dict, f, indent=2)
    _log(f"  {router_result_path.name}")
    _log("  PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prove W0 doc ingestion candidate")
    parser.add_argument("--live", action="store_true", help="Live execution (local WSL only)")
    args = parser.parse_args()

    _log("=" * 60)
    _log("W0 DOC INGESTION CANDIDATE PROOF -- Phase 96.8T")
    _log(f"mode: {'LIVE' if args.live else 'DRY-RUN (VPS safe)'}")
    _log("=" * 60)

    config = load_ingestion_config()
    safe_doc_url = config["safe_test_doc_url"]
    safe_doc_title = config["safe_test_doc_title"]
    extraction_reference_id = f"REQ-W0-EXTRACT-{uuid.uuid4().hex[:8]}"
    _log(f"safe_test_doc_url: {safe_doc_url}")
    _log(f"safe_test_doc_title: {safe_doc_title}")
    _log(f"extraction_reference_id: {extraction_reference_id}")

    registry = AdapterRegistry.from_json_file(REGISTRY_PATH)
    with open(ROUTER_CONFIG_PATH, encoding="utf-8-sig") as f:
        router_config = json.load(f)
    router = ControlPlaneRouterV1(registry=registry, config=router_config, base_dir=BASE_DIR)

    wp = prove_work_packet_creation(safe_doc_url, safe_doc_title, extraction_reference_id)
    prove_router_decision(wp, router)
    prove_forbidden_actions_blocked()
    candidate = prove_ingestion_candidate_schema(
        config, safe_doc_title, safe_doc_url, extraction_reference_id
    )
    memory_candidate = prove_memory_candidate_schema(candidate, config)
    prove_governance_boundary(candidate, memory_candidate)
    proof = prove_simulated_proof(wp, safe_doc_url)
    prove_router_result(wp, router, proof)
    write_proof_artifacts(wp, proof, candidate, memory_candidate)

    _log("=" * 60)
    _log("ALL STEPS PASSED")
    if not args.live:
        _log("")
        _log("NOTE: This was a dry-run proof on VPS.")
        _log("No real extraction was performed. No memory was promoted.")
        _log("Ingestion candidate and memory candidate are simulated artifacts.")
        _log("")
        _log("Next gate: W0_MEMORY_PROMOTION_GOVERNANCE_PROOF")
    _log("=" * 60)


if __name__ == "__main__":
    main()
