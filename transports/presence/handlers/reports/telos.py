"""Telos report handler."""

from __future__ import annotations

from typing import Any

from ._common import (
    json,
    uuid,
    logger,
    Path,
    _REPO_ROOT,
    _wait_for_founder_confirmation,
)


async def _handle_telos_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
        TELOS_MATURITY_LEVELS,
        TELOS_PRIMITIVES,
        MISSION_CONTINUITY_DIMENSIONS,
        OPTIMIZATION_DIRECTION_TYPES,
        VALUE_HIERARCHY_TYPES,
        PURPOSE_CONFLICT_TYPES,
        ALIGNMENT_TOPOLOGY_TYPES,
        TELOS_HARD_CEILINGS,
        TELOS_ADAPTATION_TYPES,
        build_full_telos_proof,
        persist_telos_proof,
    )
    from substrate.execution.workers.workstation.constitutional_identity_continuity_engine_v1 import (
        build_full_identity_proof,
    )
    from substrate.execution.workers.workstation.constitutional_epistemic_intelligence_engine_v1 import (
        build_full_epistemic_proof,
    )
    from substrate.execution.workers.workstation.constitutional_strategic_intelligence_engine_v1 import (
        build_full_strategy_proof,
    )
    from substrate.execution.workers.workstation.constitutional_resource_economics_engine_v1 import (
        build_full_economics_proof,
    )
    from substrate.execution.workers.workstation.distributed_constitutional_substrate_federation_v1 import (
        build_full_federation_proof,
    )
    from substrate.execution.workers.workstation.constitutional_substrate_governance_layer_v1 import (
        build_full_constitutional_proof,
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
    trace_id = f"W0-telos-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-TELS-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!telos-report** -- analyzing constitutional telos alignment\n"
        f"maturity levels: `{len(TELOS_MATURITY_LEVELS)}` | "
        f"primitives: `{len(TELOS_PRIMITIVES)}`\n"
        f"mission dims: `{len(MISSION_CONTINUITY_DIMENSIONS)}` | "
        f"optimization types: `{len(OPTIMIZATION_DIRECTION_TYPES)}`\n"
        f"value hierarchy: `{len(VALUE_HIERARCHY_TYPES)}` | "
        f"conflict types: `{len(PURPOSE_CONFLICT_TYPES)}`\n"
        f"topology types: `{len(ALIGNMENT_TOPOLOGY_TYPES)}` | "
        f"hard ceilings: `{len(TELOS_HARD_CEILINGS)}`\n"
        f"adaptation types: `{len(TELOS_ADAPTATION_TYPES)}`\n"
        f"Loading upstream proofs and building telos alignment..."
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
                    ad = json.load(f)
                aev_data = ad.get("evidence", {})
                adapter_proof = AdapterAutogenProof(
                    proof_id=ad.get("proof_id", ""),
                    maturity_level=ad.get("maturity_level", "L0_NO_GENERATION"),
                    evidence=AdapterAutogenEvidence(
                        **{
                            k: v
                            for k, v in aev_data.items()
                            if k in AdapterAutogenEvidence.__dataclass_fields__
                        }
                    ),
                )
            except (json.JSONDecodeError, OSError, TypeError):
                pass

    cap = build_full_capability_proof(
        environment_proof=env_proof,
        adapter_generation_proof=adapter_proof,
    )
    orch = build_full_orchestration_proof(capability_proof=cap)
    cont = build_full_continuity_proof(orchestration_proof=orch, capability_proof=cap)
    gov_intel = build_full_governance_intelligence_proof(
        orchestration_proof=orch, capability_proof=cap
    )
    const_gov = build_full_constitutional_proof(
        governance_proof=gov_intel,
        orchestration_proof=orch,
        continuity_proof=cont,
        capability_proof=cap,
    )
    fed = build_full_federation_proof(
        orchestration_proof=orch,
        capability_proof=cap,
        continuity_proof=cont,
        governance_proof=gov_intel,
        constitutional_proof=const_gov,
    )
    econ = build_full_economics_proof(
        federation_proof=fed,
        orchestration_proof=orch,
        capability_proof=cap,
    )
    strat = build_full_strategy_proof(
        economics_proof=econ,
        federation_proof=fed,
        orchestration_proof=orch,
        capability_proof=cap,
        founder_confirmed=False,
    )
    epis = build_full_epistemic_proof(
        strategy_proof=strat,
        economics_proof=econ,
        federation_proof=fed,
        orchestration_proof=orch,
        continuity_proof=cont,
        constitutional_proof=const_gov,
        governance_proof=gov_intel,
        capability_proof=cap,
        founder_confirmed=False,
    )
    iden = build_full_identity_proof(
        epistemic_proof=epis,
        strategy_proof=strat,
        economics_proof=econ,
        federation_proof=fed,
        orchestration_proof=orch,
        continuity_proof=cont,
        constitutional_proof=const_gov,
        governance_proof=gov_intel,
        capability_proof=cap,
        founder_confirmed=False,
    )

    proof = build_full_telos_proof(
        identity_proof=iden,
        epistemic_proof=epis,
        strategy_proof=strat,
        economics_proof=econ,
        federation_proof=fed,
        orchestration_proof=orch,
        continuity_proof=cont,
        constitutional_proof=const_gov,
        governance_proof=gov_intel,
        capability_proof=cap,
        founder_confirmed=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    ev = proof.evidence
    lines = [
        f"**Telos Alignment Report**",
        f"proof_id: `{proof.proof_id}`",
        f"maturity: **{proof.maturity_level}** (ceiling: {proof.maturity_ceiling})",
        f"",
        f"**Primitives** — confidence: `{ev.composite_confidence:.4f}` | stability: `{ev.composite_stability:.4f}` | alignment: `{ev.composite_alignment:.4f}`",
        f"**Mission** — alignment: `{ev.mission_alignment:.4f}` | intact: `{ev.intact_dimensions}` | divergent: `{ev.divergent_dimensions}`",
        f"**Optimization** — drift: `{ev.optimization_drift_count}` | critical: `{ev.critical_optimization_drift}` | composite: `{ev.optimization_composite_drift:.4f}`",
        f"**Value Hierarchy** — stability: `{ev.value_stability:.4f}` | enforced: `{ev.enforced_values}` | violated: `{ev.violated_values}`",
        f"**Conflicts** — count: `{ev.conflict_count}` | reconciled: `{ev.reconciled_count}` | unreconciled: `{ev.unreconciled_count}`",
        f"**Topology** — types: `{ev.topology_types_covered}` | stability: `{ev.topology_stability:.4f}`",
        f"**Adaptations** — preservations: `{ev.preservations_applied}` | quarantines: `{ev.quarantines_applied}` | reconciliations: `{ev.reconciliations_applied}`",
        f"**Civilizational purpose score:** `{ev.civilizational_purpose_score:.4f}`",
        f"invariants: `{ev.all_invariants_preserved}` | ceilings: `{ev.hard_ceilings_enforced}`",
        f"mission_safe: `{ev.mission_continuity_safe}` | recursive_stable: `{ev.recursive_alignment_stable}`",
        f"purpose_coherent: `{ev.purpose_coherent}`",
        f"",
        f"Awaiting founder confirmation to escalate to L5...",
    ]
    await message.channel.send("\n".join(lines))

    founder_answer = await _wait_for_founder_confirmation(message, "telos-report")

    if founder_answer == "yes":
        proof2 = build_full_telos_proof(
            identity_proof=iden,
            epistemic_proof=epis,
            strategy_proof=strat,
            economics_proof=econ,
            federation_proof=fed,
            orchestration_proof=orch,
            continuity_proof=cont,
            constitutional_proof=const_gov,
            governance_proof=gov_intel,
            capability_proof=cap,
            founder_confirmed=True,
            trace_id=trace_id,
            request_id=request_id,
        )
        persist_telos_proof(proof2, base_dir=base)
        ev2 = proof2.evidence
        await message.channel.send(
            f"**FOUNDER CONFIRMED** — re-ran telos pipeline\n"
            f"maturity: **{proof2.maturity_level}**\n"
            f"civilizational purpose: `{ev2.civilizational_purpose_score:.4f}`\n"
            f"proof persisted: `{proof2.proof_id}`"
        )
        confirm_artifact = FounderConfirmationArtifact(
            trace_id=trace_id,
            request_id=request_id,
            confirmed=True,
            confirmation_scope="telos_report_full_pipeline",
            founder_message="founder confirmed telos report",
        )
        persist_founder_confirmation(confirm_artifact, base_dir=base)
    else:
        persist_telos_proof(proof, base_dir=base)
        await message.channel.send(
            f"Telos report persisted without founder confirmation.\n"
            f"maturity: **{proof.maturity_level}** | proof: `{proof.proof_id}`"
        )

    logger.info(
        f"telos_report complete trace=%s maturity=%s founder={founder_answer}",
        trace_id,
        proof.maturity_level,
    )
