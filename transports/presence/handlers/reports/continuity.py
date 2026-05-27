"""Continuity report handler."""

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


async def _handle_continuity_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.persistent_substrate_continuity_engine_v1 import (
        CONTINUITY_MATURITY_LEVELS,
        DRIFT_TYPES,
        CONTINUITY_GOVERNANCE_VIOLATIONS,
        CONTINUITY_REJECTION_TRIGGERS,
        build_full_continuity_proof,
        persist_continuity_proof,
    )
    from substrate.execution.workers.workstation.governed_recursive_orchestration_engine_v1 import (
        build_full_orchestration_proof,
        ORCHESTRATION_REPORT_DIR,
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
    trace_id = f"W0-continuity-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-CONT-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!continuity-report** -- analyzing substrate continuity\n"
        f"maturity levels: `{len(CONTINUITY_MATURITY_LEVELS)}` | "
        f"drift types: `{len(DRIFT_TYPES)}`\n"
        f"governance violations: `{len(CONTINUITY_GOVERNANCE_VIOLATIONS)}` | "
        f"rejection triggers: `{len(CONTINUITY_REJECTION_TRIGGERS)}`\n"
        f"Loading upstream proofs and building continuity graph..."
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

    proof = build_full_continuity_proof(
        orchestration_proof=orchestration_proof,
        capability_proof=capability_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
        base_dir=base,
    )

    ev = proof.evidence
    lines = [
        f"**!continuity-report** -- analysis complete",
        f"execution lineage depth: `{ev.execution_lineage_depth}`"
        if ev
        else "execution lineage: none",
        f"orchestration history: `{ev.orchestration_history_count}`"
        if ev
        else "orchestration history: none",
        f"capability evolution: `{ev.capability_evolution_count}`"
        if ev
        else "capability evolution: none",
        f"maturity transitions: `{ev.maturity_transition_count}`"
        if ev
        else "maturity transitions: none",
        f"topology evolution: `{ev.topology_evolution_count}`"
        if ev
        else "topology evolution: none",
        f"registry evolution: `{ev.registry_evolution_count}`"
        if ev
        else "registry evolution: none",
        f"drift signals: `{ev.drift_signal_count}` (max severity: `{ev.drift_max_severity:.3f}`)"
        if ev
        else "drift: none",
        f"replay continuity: `{ev.replay_continuity_validated}`" if ev else "replay: unknown",
        f"rollback continuity: `{ev.rollback_continuity_validated}`" if ev else "rollback: unknown",
        f"governance continuity: `{ev.governance_continuity_enforced}`"
        if ev
        else "governance: unknown",
        f"evolution score: `{ev.evolution_composite_score:.3f}`" if ev else "evolution: none",
        f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`",
        f"strategy: `{proof.execution_strategy}`",
    ]
    await message.channel.send("\n".join(lines))

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve continuity proof generation?\n"
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

    proof_final = build_full_continuity_proof(
        orchestration_proof=orchestration_proof,
        capability_proof=capability_proof,
        founder_confirmed=confirmed,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
        base_dir=base,
    )

    proof_path = persist_continuity_proof(proof_final, base_dir=base)

    ev_final = proof_final.evidence
    lines = [
        f"**!continuity-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(
        f"execution lineage: depth=`{ev_final.execution_lineage_depth}`"
        if ev_final
        else "execution lineage: unknown"
    )
    lines.append(
        f"drift: `{ev_final.drift_signal_count}` signals (max=`{ev_final.drift_max_severity:.3f}`)"
        if ev_final
        else "drift: unknown"
    )
    lines.append(
        f"replay: `{ev_final.replay_continuity_validated}` | "
        f"rollback: `{ev_final.rollback_continuity_validated}` | "
        f"governance: `{ev_final.governance_continuity_enforced}`"
        if ev_final
        else "continuity: unknown"
    )
    lines.append(
        f"evolution: `{ev_final.evolution_composite_score:.3f}`"
        if ev_final
        else "evolution: unknown"
    )
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!continuity-report completed: maturity={proof_final.maturity_level} "
        f"drift={ev_final.drift_signal_count if ev_final else 0} "
        f"evolution={ev_final.evolution_composite_score if ev_final else 0:.3f} "
        f"founder={founder_answer}"
    )
