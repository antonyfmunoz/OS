"""W0 Dry Validation with Coherence Envelope.

Generates the W0-001 packet and validates it through every gate
without executing any actions, launching any GUI, or accessing
any external service.

Validation-only. Never executes. Never launches Chrome.
Never opens Drive/Docs. Never captures secrets.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from core.coherence.coherence_gate import (
    coherence_gate_allows_execution,
    evaluate_coherence_before_execution,
)
from core.coherence.spine_lineage_contracts import (
    CoherenceStatus,
    SpineStage,
    SpineStageStatus,
)
from core.environment_bridge.execution_binding_validator import (
    validate_execution_binding_dict,
)
from core.environment_bridge.packet_validator import validate_w0_packet_dict
from core.environment_bridge.w0_packet_builder import build_w0_001_packet

REPORT_DIR = Path(_ROOT) / "data" / "dry_validation"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_STAGE_NAMES = [s.value for s in SpineStage]


def run_dry_validation() -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    results: dict = {
        "timestamp": ts,
        "validation_type": "dry_validation_only",
        "execution_occurred": False,
        "chrome_launched": False,
        "drive_docs_accessed": False,
        "secrets_captured": False,
        "checks": {},
    }

    print("=" * 60)
    print("W0 DRY VALIDATION WITH COHERENCE ENVELOPE")
    print("=" * 60)
    print()

    # 1. Generate packet
    print("[1/6] Generating W0-001 packet...")
    packet = build_w0_001_packet()
    results["packet_id"] = packet.get("packet_id", "")
    print(f"  Packet ID: {packet['packet_id']}")
    print(f"  Action:    {packet['action_type']}")
    print()

    # 2. Check coherence envelope exists
    print("[2/6] Checking coherence envelope presence...")
    envelope = packet.get("coherence_envelope")
    has_envelope = envelope is not None and bool(envelope)
    results["checks"]["coherence_envelope_present"] = has_envelope
    print(f"  Coherence envelope present: {has_envelope}")

    if not has_envelope:
        print("  BLOCKED: No coherence envelope. Cannot proceed.")
        results["overall_status"] = "BLOCKED"
        _write_report(results)
        return results

    # 3. Validate all 15 stages
    print()
    print("[3/6] Validating canonical spine stages...")
    lineage = envelope.get("lineage", {})
    stages = lineage.get("stages", [])
    stage_names_present = [s.get("stage_name") for s in stages]
    missing = [n for n in REQUIRED_STAGE_NAMES if n not in stage_names_present]
    all_present = len(missing) == 0

    results["checks"]["all_15_stages_present"] = all_present
    results["checks"]["stages_found"] = len(stage_names_present)
    results["checks"]["stages_missing"] = missing

    print(f"  Stages found:   {len(stage_names_present)}/15")
    print(f"  All present:    {all_present}")
    if missing:
        print(f"  Missing:        {missing}")

    # Check MVP stubs
    mvp_stubs = []
    complete_stages = []
    for s in stages:
        name = s.get("stage_name", "")
        status = s.get("status", "")
        if status == SpineStageStatus.MVP_STUB.value:
            reason = s.get("reason", "")
            trace = s.get("trace_id", "")
            artifact = s.get("artifact_id", "")
            mvp_stubs.append(
                {
                    "stage": name,
                    "reason": reason,
                    "has_trace_id": bool(trace),
                    "has_artifact_id": bool(artifact),
                }
            )
        elif status == SpineStageStatus.COMPLETE.value:
            complete_stages.append(name)

    results["checks"]["mvp_stub_stages"] = mvp_stubs
    results["checks"]["complete_stages"] = complete_stages
    results["checks"]["mvp_stub_allowed"] = lineage.get("mvp_stub_allowed", False)

    print()
    print(f"  Complete stages: {complete_stages}")
    print(f"  MVP stub stages: {len(mvp_stubs)}")
    print(f"  mvp_stub_allowed: {lineage.get('mvp_stub_allowed', False)}")

    all_stubs_labeled = all(
        s["reason"] and s["has_trace_id"] and s["has_artifact_id"] for s in mvp_stubs
    )
    results["checks"]["all_mvp_stubs_labeled"] = all_stubs_labeled
    print(f"  All stubs labeled with reason + trace_id + artifact_id: {all_stubs_labeled}")

    # 4. Run coherence gate
    print()
    print("[4/6] Running coherence gate...")
    gate_allowed, gate_result = coherence_gate_allows_execution(packet)
    results["checks"]["coherence_gate_allowed"] = gate_allowed
    results["checks"]["coherence_gate_status"] = gate_result.status
    results["checks"]["coherence_gate_errors"] = gate_result.errors

    print(f"  Gate allowed:  {gate_allowed}")
    print(f"  Gate status:   {gate_result.status}")
    if gate_result.errors:
        print(f"  Gate errors:   {gate_result.errors}")

    # 5. Run execution binding validator
    print()
    print("[5/6] Validating execution binding...")
    binding = packet.get("execution_binding", {})
    has_binding = bool(binding)
    results["checks"]["execution_binding_present"] = has_binding

    if has_binding:
        binding_result = validate_execution_binding_dict(binding)
        results["checks"]["execution_binding_valid"] = binding_result.valid
        results["checks"]["execution_binding_errors"] = binding_result.errors

        has_env = bool(binding.get("environment"))
        has_app = bool(binding.get("application"))
        has_svc = bool(binding.get("target_services"))
        has_cap = bool(binding.get("capabilities"))
        has_proof = bool(binding.get("proof"))
        has_surfaces = bool(binding.get("execution_surfaces"))

        results["checks"]["binding_layers"] = {
            "environment": has_env,
            "execution_surfaces": has_surfaces,
            "application": has_app,
            "target_services": has_svc,
            "capabilities": has_cap,
            "proof": has_proof,
        }

        print(f"  Binding valid:         {binding_result.valid}")
        print(f"  Environment layer:     {has_env}")
        print(f"  Execution surfaces:    {has_surfaces}")
        print(f"  Application layer:     {has_app}")
        print(f"  Target services:       {has_svc}")
        print(f"  Capabilities:          {has_cap}")
        print(f"  Proof layer:           {has_proof}")
        if binding_result.errors:
            print(f"  Binding errors:        {binding_result.errors}")
    else:
        print("  BLOCKED: No execution binding.")
        results["checks"]["execution_binding_valid"] = False

    # 6. Run full packet validator
    print()
    print("[6/6] Running packet validator (validate_w0_packet_dict)...")
    pv_result = validate_w0_packet_dict(packet)
    results["checks"]["packet_validator_status"] = pv_result.status.value
    results["checks"]["packet_validator_can_execute"] = pv_result.can_execute
    results["checks"]["packet_validator_errors"] = pv_result.validation_errors

    print(f"  Status:       {pv_result.status.value}")
    print(f"  Can execute:  {pv_result.can_execute}")
    if pv_result.validation_errors:
        print(f"  Errors:       {pv_result.validation_errors}")

    # Overall
    all_pass = (
        has_envelope
        and all_present
        and all_stubs_labeled
        and gate_allowed
        and has_binding
        and results["checks"].get("execution_binding_valid", False)
        and pv_result.can_execute
    )

    results["dry_validation_passed"] = all_pass
    results["overall_status"] = "PASS" if all_pass else "FAIL"

    print()
    print("=" * 60)
    print(f"DRY VALIDATION RESULT: {results['overall_status']}")
    print("=" * 60)
    print()
    print("Safety confirmation:")
    print(f"  Execution occurred:   {results['execution_occurred']}")
    print(f"  Chrome launched:      {results['chrome_launched']}")
    print(f"  Drive/Docs accessed:  {results['drive_docs_accessed']}")
    print(f"  Secrets captured:     {results['secrets_captured']}")

    _write_report(results)
    return results


def _write_report(results: dict) -> None:
    report_path = REPORT_DIR / "w0_coherence_dry_validation_result.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print()
    print(f"Report written: {report_path}")


if __name__ == "__main__":
    result = run_dry_validation()
    sys.exit(0 if result.get("dry_validation_passed") else 1)
