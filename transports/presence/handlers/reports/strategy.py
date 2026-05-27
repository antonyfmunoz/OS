"""Strategy report handler."""

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


async def _handle_strategy_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.constitutional_strategic_intelligence_engine_v1 import (
        STRATEGY_MATURITY_LEVELS,
        STRATEGIC_FORECASTING_PRIMITIVES,
        RECURSIVE_LEVERAGE_DIMENSIONS,
        STRATEGIC_BOTTLENECK_TYPES,
        LONG_HORIZON_SIMULATION_TYPES,
        STRATEGIC_SEQUENCING_PRIORITIES,
        STRATEGIC_TOPOLOGY_TYPES,
        STRATEGIC_HARD_CEILINGS,
        STRATEGIC_ADAPTATION_TYPES,
        build_full_strategy_proof,
        persist_strategy_proof,
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
    trace_id = f"W0-strategy-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-STRAT-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!strategy-report** -- analyzing constitutional strategic intelligence\n"
        f"maturity levels: `{len(STRATEGY_MATURITY_LEVELS)}` | "
        f"forecasting primitives: `{len(STRATEGIC_FORECASTING_PRIMITIVES)}`\n"
        f"leverage dimensions: `{len(RECURSIVE_LEVERAGE_DIMENSIONS)}` | "
        f"bottleneck types: `{len(STRATEGIC_BOTTLENECK_TYPES)}`\n"
        f"simulation types: `{len(LONG_HORIZON_SIMULATION_TYPES)}` | "
        f"sequencing priorities: `{len(STRATEGIC_SEQUENCING_PRIORITIES)}`\n"
        f"topology types: `{len(STRATEGIC_TOPOLOGY_TYPES)}` | "
        f"hard ceilings: `{len(STRATEGIC_HARD_CEILINGS)}`\n"
        f"adaptation types: `{len(STRATEGIC_ADAPTATION_TYPES)}`\n"
        f"Loading upstream proofs and building strategic intelligence..."
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

    economics_proof = build_full_economics_proof(
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

    proof = build_full_strategy_proof(
        economics_proof=economics_proof,
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

    fc = proof.forecasts
    lm = proof.leverage_model
    bf = proof.bottleneck_forecasts
    ss = proof.strategic_sequence
    tp = proof.topology

    lines = [
        f"**!strategy-report** -- analysis complete",
        f"forecasts: `{fc.forecast_count}` primitives, trajectory=`{fc.composite_trajectory:.3f}` stability=`{fc.trajectory_stability:.3f}`"
        if fc
        else "forecasts: pending",
        f"leverage: `{lm.safe_chain_count}` safe / `{lm.unsafe_chain_count}` unsafe chains, total=`{lm.total_leverage:.3f}`"
        if lm
        else "leverage: pending",
        f"bottlenecks: `{bf.total_count}` predicted, `{bf.critical_count}` critical"
        if bf
        else "bottlenecks: pending",
        f"simulations: `{len(proof.simulations)}`",
        f"sequence: `{len(ss.items)}` items, stability=`{ss.sequence_stability:.3f}`"
        if ss
        else "sequence: pending",
        f"topology: `{tp.topology_types_covered}` types, avg_stability=`{tp.average_stability:.3f}`"
        if tp
        else "topology: pending",
        f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`",
        f"strategy: `{proof.execution_strategy}`",
    ]
    await message.channel.send("\n".join(lines))

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve strategy proof generation?\n"
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

    proof_final = build_full_strategy_proof(
        economics_proof=economics_proof,
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

    proof_path = persist_strategy_proof(proof_final, base_dir=base)

    ev_final = proof_final.evidence
    lines = [
        f"**!strategy-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(
        f"forecasts: `{ev_final.forecast_count}` | trajectory: `{ev_final.composite_trajectory:.3f}`"
        if ev_final
        else "forecasts: unknown"
    )
    lines.append(
        f"leverage: `{ev_final.total_leverage:.3f}` | compounding: `{ev_final.compounding_score:.3f}`"
        if ev_final
        else "leverage: unknown"
    )
    lines.append(
        f"bottlenecks: `{ev_final.bottleneck_count}` | critical: `{ev_final.critical_bottleneck_count}`"
        if ev_final
        else "bottlenecks: unknown"
    )
    lines.append(
        f"recursive_leverage_score: `{ev_final.recursive_leverage_score:.4f}`"
        if ev_final
        else "leverage score: unknown"
    )
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!strategy-report completed: maturity={proof_final.maturity_level} "
        f"leverage={ev_final.total_leverage if ev_final else 0:.3f} "
        f"trajectory={ev_final.composite_trajectory if ev_final else 0:.3f} "
        f"founder={founder_answer}"
    )
