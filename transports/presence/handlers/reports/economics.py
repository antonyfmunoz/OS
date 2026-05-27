"""Economics report handler."""

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


async def _handle_economics_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.constitutional_resource_economics_engine_v1 import (
        ECONOMICS_MATURITY_LEVELS,
        ECONOMICS_HARD_CEILINGS,
        RESOURCE_PRIMITIVES,
        EXECUTION_ECONOMICS_DIMENSIONS,
        CONSTRAINED_NODE_TYPES,
        DEGRADED_MODE_TYPES,
        SCARCITY_SIMULATION_TYPES,
        RESOURCE_GRAPH_DIMENSIONS,
        build_full_economics_proof,
        persist_economics_proof,
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
    trace_id = f"W0-economics-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-ECON-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!economics-report** -- analyzing constitutional resource economics\n"
        f"maturity levels: `{len(ECONOMICS_MATURITY_LEVELS)}` | "
        f"resource primitives: `{len(RESOURCE_PRIMITIVES)}`\n"
        f"economics dimensions: `{len(EXECUTION_ECONOMICS_DIMENSIONS)}` | "
        f"constrained node types: `{len(CONSTRAINED_NODE_TYPES)}`\n"
        f"degraded modes: `{len(DEGRADED_MODE_TYPES)}` | "
        f"scarcity simulations: `{len(SCARCITY_SIMULATION_TYPES)}`\n"
        f"hard ceilings: `{len(ECONOMICS_HARD_CEILINGS)}` | "
        f"graph dimensions: `{len(RESOURCE_GRAPH_DIMENSIONS)}`\n"
        f"Loading upstream proofs and building resource economics graph..."
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

    constitutional_proof = build_full_constitutional_proof(
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

    federation_proof = build_full_federation_proof(
        constitutional_proof=constitutional_proof,
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

    proof = build_full_economics_proof(
        federation_proof=federation_proof,
        orchestration_proof=orchestration_proof,
        continuity_proof=continuity_proof,
        constitutional_proof=constitutional_proof,
        governance_proof=governance_proof,
        capability_proof=capability_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
        base_dir=base,
    )

    rg = proof.resource_graph
    ee = proof.execution_economics
    dt = proof.delegation_topology
    dm = proof.degraded_mode

    lines = [
        f"**!economics-report** -- analysis complete",
        f"resource graph: `{len(rg.node_profiles)}` nodes, compute=`{rg.total_compute:.2f}` bandwidth=`{rg.total_bandwidth:.2f}`"
        if rg
        else "resource graph: pending",
        f"economics: composite=`{ee.composite_economics():.3f}` leverage=`{ee.leverage_score:.3f}` efficiency=`{ee.resource_efficiency:.3f}`"
        if ee
        else "economics: pending",
        f"delegation: `{dt.safe_path_count}` safe / `{dt.unsafe_path_count}` unsafe paths, avg_trust=`{dt.average_trust:.3f}`"
        if dt
        else "delegation: pending",
        f"degraded modes: `{dm.ready_count}` ready / `{len(DEGRADED_MODE_TYPES)}` total"
        if dm
        else "degraded: pending",
        f"simulations: `{len(proof.simulations)}`",
        f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`",
        f"strategy: `{proof.execution_strategy}`",
    ]
    await message.channel.send("\n".join(lines))

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve economics proof generation?\n"
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

    proof_final = build_full_economics_proof(
        federation_proof=federation_proof,
        orchestration_proof=orchestration_proof,
        continuity_proof=continuity_proof,
        constitutional_proof=constitutional_proof,
        governance_proof=governance_proof,
        capability_proof=capability_proof,
        founder_confirmed=confirmed,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
        base_dir=base,
    )

    proof_path = persist_economics_proof(proof_final, base_dir=base)

    ev_final = proof_final.evidence
    lines = [
        f"**!economics-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(
        f"nodes: `{ev_final.node_count}` | online: `{ev_final.online_count}` | constrained: `{ev_final.constrained_count}`"
        if ev_final
        else "nodes: unknown"
    )
    lines.append(
        f"economics: `{ev_final.composite_economics:.3f}`" if ev_final else "economics: unknown"
    )
    lines.append(
        f"delegation: safe=`{ev_final.safe_delegation_paths}` unsafe=`{ev_final.unsafe_delegation_paths}`"
        if ev_final
        else "delegation: unknown"
    )
    lines.append(
        f"degraded ready: `{ev_final.degraded_mode_ready_count}`"
        if ev_final
        else "degraded: unknown"
    )
    lines.append(
        f"simulations: `{ev_final.simulation_count}`" if ev_final else "simulations: unknown"
    )
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!economics-report completed: maturity={proof_final.maturity_level} "
        f"nodes={ev_final.node_count if ev_final else 0} "
        f"economics={ev_final.composite_economics if ev_final else 0:.3f} "
        f"founder={founder_answer}"
    )
