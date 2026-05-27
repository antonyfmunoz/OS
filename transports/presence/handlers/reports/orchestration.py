"""Orchestration report handler."""

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


async def _handle_orchestration_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.governed_recursive_orchestration_engine_v1 import (
        build_full_orchestration_proof,
        persist_orchestration_proof,
        DAG_TYPES,
        SIMULATION_OUTCOMES,
        ORCHESTRATION_MATURITY_LEVELS,
    )
    from substrate.execution.workers.workstation.recursive_capability_planning_engine_v1 import (
        build_full_capability_proof,
        SUBSTRATE_CAPABILITIES,
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
    trace_id = f"W0-orchestration-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-ORCH-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!orchestration-report** -- analyzing orchestration\n"
        f"DAG types: `{len(DAG_TYPES)}` | simulation outcomes: `{len(SIMULATION_OUTCOMES)}`\n"
        f"maturity levels: `{len(ORCHESTRATION_MATURITY_LEVELS)}`\n"
        f"Loading upstream proofs and building orchestration graph..."
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

    proof = build_full_orchestration_proof(
        capability_proof=capability_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    ev = proof.evidence
    sim_success = ev.simulation_success_count if ev else 0
    sim_total = ev.simulation_count if ev else 0
    unsafe_count = ev.unsafe_chains_detected if ev else 0

    lines = [
        f"**!orchestration-report** -- analysis complete",
        f"DAGs: `{len(proof.dags)}`",
        f"blast radii: `{len(proof.blast_radii)}` (max risk: `{ev.max_blast_radius:.3f}`)"
        if ev
        else f"blast radii: `{len(proof.blast_radii)}`",
        f"rollback plans: `{len(proof.rollback_plans)}` "
        f"(safe: `{ev.rollback_safe_count}` unsafe: `{ev.rollback_unsafe_count}`)"
        if ev
        else f"rollback plans: `{len(proof.rollback_plans)}`",
        f"simulations: `{sim_total}` (success: `{sim_success}`)",
        f"unsafe chains: `{unsafe_count}`",
        f"sequenced upgrades: `{len(proof.sequenced_upgrades)}`",
        f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`",
        f"strategy: `{proof.execution_strategy}`",
    ]
    if proof.governance_bottlenecks:
        lines.append(f"governance bottlenecks: `{len(proof.governance_bottlenecks)}`")

    await message.channel.send("\n".join(lines))

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve orchestration proof generation?\n"
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

    proof_final = build_full_orchestration_proof(
        capability_proof=capability_proof,
        founder_confirmed=confirmed,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    proof_path = persist_orchestration_proof(proof_final, base_dir=base)

    ev_final = proof_final.evidence
    lines = [
        f"**!orchestration-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(f"DAGs: `{len(proof_final.dags)}`")
    lines.append(
        f"blast radii: `{len(proof_final.blast_radii)}` (max: `{ev_final.max_blast_radius:.3f}`)"
        if ev_final
        else f"blast radii: `{len(proof_final.blast_radii)}`"
    )
    lines.append(
        f"rollback: safe=`{ev_final.rollback_safe_count}` unsafe=`{ev_final.rollback_unsafe_count}`"
        if ev_final
        else "rollback: unknown"
    )
    lines.append(
        f"simulations: `{ev_final.simulation_count}` "
        f"(success=`{ev_final.simulation_success_count}`)"
        if ev_final
        else "simulations: none"
    )
    lines.append(f"sequenced: `{', '.join(proof_final.sequenced_upgrades[:5])}`")
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!orchestration-report completed: maturity={proof_final.maturity_level} "
        f"dags={len(proof_final.dags)} "
        f"simulations={ev_final.simulation_count if ev_final else 0} "
        f"founder={founder_answer}"
    )
