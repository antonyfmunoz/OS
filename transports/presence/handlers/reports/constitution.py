"""Constitution report handler."""

from __future__ import annotations

from typing import Any

from ._common import (
    asyncio,
    json,
    uuid,
    Path,
    _REPO_ROOT,
    _log,
)


async def _handle_constitution_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.constitutional_substrate_governance_layer_v1 import (
        CONSTITUTIONAL_MATURITY_LEVELS,
        CONSTITUTIONAL_HARD_CEILINGS,
        CONSTITUTIONAL_SAFETY_INVARIANTS,
        CONSTITUTIONAL_AUTHORITY_BOUNDARIES,
        CONSTITUTIONAL_CONTINUITY_CONTRACTS,
        CONSTITUTIONAL_EMERGENCY_ACTIONS,
        CONSTITUTIONAL_SIMULATION_TYPES,
        build_full_constitutional_proof,
        persist_constitutional_proof,
    )
    from substrate.execution.workers.workstation.adaptive_governance_intelligence_engine_v1 import (
        build_full_governance_intelligence_proof,
    )
    from substrate.execution.workers.workstation.governed_recursive_orchestration_engine_v1 import (
        build_full_orchestration_proof,
    )
    from substrate.execution.workers.workstation.persistent_substrate_continuity_engine_v1 import (
        build_full_continuity_proof,
    )
    from substrate.execution.workers.workstation.recursive_capability_planning_engine_v1 import (
        build_full_capability_proof,
    )
    from substrate.execution.workers.workstation.adapter_autogeneration_engine_v1 import (
        AdapterAutogenProof,
        AdapterAutogenEvidence,
    )
    from substrate.execution.workers.workstation.environment_mapping_engine_v1 import (
        ENVIRONMENT_MAP_DIR,
        EnvironmentMappingProof,
        EnvironmentTopology,
        EnvironmentMappingEvidence,
        DiscoveredPlatform,
    )
    from substrate.execution.workers.workstation.visible_actuation_proof_v1 import (
        FounderConfirmationArtifact,
        persist_founder_confirmation,
    )

    base = Path(_REPO_ROOT)
    trace_id = f"W0-constitution-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-CONST-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!constitution-report** -- analyzing constitutional governance\n"
        f"maturity levels: `{len(CONSTITUTIONAL_MATURITY_LEVELS)}` | "
        f"invariants: `{len(CONSTITUTIONAL_SAFETY_INVARIANTS)}`\n"
        f"authority boundaries: `{len(CONSTITUTIONAL_AUTHORITY_BOUNDARIES)}` | "
        f"hard ceilings: `{len(CONSTITUTIONAL_HARD_CEILINGS)}`\n"
        f"emergency actions: `{len(CONSTITUTIONAL_EMERGENCY_ACTIONS)}` | "
        f"simulation types: `{len(CONSTITUTIONAL_SIMULATION_TYPES)}`\n"
        f"Loading upstream proofs and building constitutional graph..."
    )

    env_proof = None
    env_map_dir = base / ENVIRONMENT_MAP_DIR
    if env_map_dir.exists():
        proof_files = sorted(env_map_dir.glob("ENVMAP-*.json"), reverse=True)
        if proof_files:
            try:
                with open(proof_files[0], encoding="utf-8-sig") as f:
                    proof_data = json.load(f)
                topo_data = proof_data.get("topology")
                topology = None
                if topo_data:
                    platforms = [
                        DiscoveredPlatform(
                            **{
                                k: v
                                for k, v in p.items()
                                if k in DiscoveredPlatform.__dataclass_fields__
                            }
                        )
                        for p in topo_data.get("platforms", [])
                    ]
                    topology = EnvironmentTopology(
                        topology_id=topo_data.get("topology_id", ""),
                        platforms=platforms,
                    )
                evidence_data = proof_data.get("evidence", {})
                env_evidence = (
                    EnvironmentMappingEvidence(
                        **{
                            k: v
                            for k, v in evidence_data.items()
                            if k in EnvironmentMappingEvidence.__dataclass_fields__
                        }
                    )
                    if evidence_data
                    else None
                )
                env_proof = EnvironmentMappingProof(
                    proof_id=proof_data.get("proof_id", ""),
                    maturity_level=proof_data.get("maturity_level", "L0_NO_MAPPING"),
                    evidence=env_evidence,
                    topology=topology,
                )
            except (json.JSONDecodeError, OSError, TypeError):
                pass

    adapter_proof = None
    adapter_dir = base / "data/runtime/workstation_relay/adapter_reports"
    if adapter_dir.exists():
        adapter_files = sorted(adapter_dir.glob("ADPTGEN-*.json"), reverse=True)
        if adapter_files:
            try:
                with open(adapter_files[0], encoding="utf-8-sig") as f:
                    adapter_data = json.load(f)
                ev_data = adapter_data.get("evidence", {})
                adapter_evidence = (
                    AdapterAutogenEvidence(
                        **{
                            k: v
                            for k, v in ev_data.items()
                            if k in AdapterAutogenEvidence.__dataclass_fields__
                        }
                    )
                    if ev_data
                    else None
                )
                adapter_proof = AdapterAutogenProof(
                    proof_id=adapter_data.get("proof_id", ""),
                    maturity_level=adapter_data.get("maturity_level", "L0_SIMULATED"),
                    evidence=adapter_evidence,
                )
            except (json.JSONDecodeError, OSError, TypeError):
                pass

    capability_proof = build_full_capability_proof(
        env_proof=env_proof,
        adapter_proof=adapter_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    orchestration_proof = build_full_orchestration_proof(
        capability_proof=capability_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    continuity_proof = build_full_continuity_proof(
        orchestration_proof=orchestration_proof,
        capability_proof=capability_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
        base_dir=base,
    )

    governance_proof = build_full_governance_intelligence_proof(
        orchestration_proof=orchestration_proof,
        continuity_proof=continuity_proof,
        capability_proof=capability_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
        base_dir=base,
    )

    proof = build_full_constitutional_proof(
        orchestration_proof=orchestration_proof,
        continuity_proof=continuity_proof,
        governance_proof=governance_proof,
        capability_proof=capability_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
        base_dir=base,
    )

    si = proof.safety_invariants
    ab = proof.authority_boundaries
    cc = proof.continuity_contracts
    eg = proof.emergency_governance
    ir = proof.integrity_result
    cr = proof.constitutional_risk

    lines = [
        f"**!constitution-report** -- analysis complete",
        f"safety invariants: `{si.active_count}/{si.invariant_count}` active"
        if si
        else "safety invariants: pending",
        f"authority boundaries: `{ab.enforced_count}/{ab.boundary_count}` enforced"
        if ab
        else "authority boundaries: pending",
        f"continuity contracts: `{cc.enforced_count}/{cc.contract_count}` enforced"
        if cc
        else "continuity contracts: pending",
        f"emergency governance: `{eg.available_count}/{eg.emergency_action_count}` available"
        if eg
        else "emergency governance: pending",
        f"integrity: `{ir.passed_count}/{ir.check_count}` checks pass"
        if ir
        else "integrity: pending",
        f"constitutional risk: `{cr.composite_risk():.3f}`" if cr else "risk: pending",
        f"simulations: `{len(proof.simulations)}`",
        f"governance contracts: `{len(proof.governance_contracts)}`",
        f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`",
        f"strategy: `{proof.execution_strategy}`",
    ]
    await message.channel.send("\n".join(lines))

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve constitutional governance proof generation?\n"
        "Reply **YES** or **NO** within 60 seconds."
    )

    def check_response(m: Any) -> bool:
        return (
            m.author.id == message.author.id
            and m.channel.id == message.channel.id
            and m.content.strip().upper() in ("YES", "NO")
        )

    try:
        client = message.channel._state._get_client()
        response = await client.wait_for("message", check=check_response, timeout=60.0)
        founder_answer = response.content.strip().upper()
    except asyncio.TimeoutError:
        founder_answer = "TIMEOUT"
    except AttributeError:
        await message.channel.send("Could not access bot for confirmation — skipping.")
        founder_answer = "TIMEOUT"

    confirmed = founder_answer == "YES"

    confirmation = FounderConfirmationArtifact(
        confirmed=confirmed,
        trace_id=trace_id,
        request_id=request_id,
        channel="discord",
        founder_response=founder_answer,
    )
    persist_founder_confirmation(confirmation, base_dir=base)

    proof_final = build_full_constitutional_proof(
        orchestration_proof=orchestration_proof,
        continuity_proof=continuity_proof,
        governance_proof=governance_proof,
        capability_proof=capability_proof,
        founder_confirmed=confirmed,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
        base_dir=base,
    )

    proof_path = persist_constitutional_proof(proof_final, base_dir=base)

    ev_final = proof_final.evidence
    lines = [
        f"**!constitution-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(
        f"invariants: `{ev_final.safety_invariants_active}/{ev_final.safety_invariant_count}`"
        if ev_final
        else "invariants: unknown"
    )
    lines.append(
        f"boundaries: `{ev_final.authority_boundaries_enforced}/{ev_final.authority_boundary_count}`"
        if ev_final
        else "boundaries: unknown"
    )
    lines.append(
        f"contracts: `{ev_final.continuity_contracts_enforced}/{ev_final.continuity_contract_count}`"
        if ev_final
        else "contracts: unknown"
    )
    lines.append(
        f"risk: `{ev_final.constitutional_risk_composite:.3f}`" if ev_final else "risk: unknown"
    )
    lines.append(
        f"ceilings enforced: `{ev_final.hard_ceilings_enforced}`"
        if ev_final
        else "ceilings: unknown"
    )
    lines.append(
        f"bypass blocked: `{ev_final.governance_bypass_blocked}`" if ev_final else "bypass: unknown"
    )
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!constitution-report completed: maturity={proof_final.maturity_level} "
        f"invariants={ev_final.safety_invariants_active if ev_final else 0} "
        f"risk={ev_final.constitutional_risk_composite if ev_final else 0:.3f} "
        f"founder={founder_answer}"
    )
