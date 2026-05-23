"""Report handler functions extracted from substrate_command_handler.

Each async function generates a substrate maturity proof report,
collects founder confirmation, and persists the classified proof.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

logger = logging.getLogger(__name__)


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [substrate-handler] {msg}", flush=True)


async def _wait_for_founder_confirmation(message: Any, report_name: str) -> str:
    """Wait for founder YES/NO reply within 60 seconds."""
    await message.channel.send(
        "**Founder confirmation required.**\n"
        f"Approve {report_name} proof escalation?\n"
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
        return response.content.strip().lower()
    except asyncio.TimeoutError:
        await message.channel.send(f"{report_name} confirmation timed out.")
        return "timeout"
    except AttributeError:
        await message.channel.send("Could not access bot for confirmation — skipping.")
        return "timeout"


async def _handle_adapter_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.adapter_autogeneration_engine_v1 import (
        build_full_adapter_proof,
        persist_adapter_proof,
        persist_blueprints,
        ADAPTER_TARGET_PLATFORMS,
    )
    from substrate.execution.workers.workstation.environment_mapping_engine_v1 import (
        ENVIRONMENT_MAP_DIR,
        EnvironmentMappingProof,
        EnvironmentTopology,
        build_environment_topology,
    )
    from substrate.execution.workers.workstation.visible_actuation_proof_v1 import (
        FounderConfirmationArtifact,
        persist_founder_confirmation,
    )

    base = Path(_REPO_ROOT)

    env_map_dir = base / ENVIRONMENT_MAP_DIR
    env_proof = None
    topology = None

    if env_map_dir.exists():
        proof_files = sorted(env_map_dir.glob("ENVMAP-*.json"), reverse=True)
        if proof_files:
            try:
                with open(proof_files[0], encoding="utf-8-sig") as f:
                    proof_data = json.load(f)
                topo_data = proof_data.get("topology")
                if topo_data:
                    from substrate.execution.workers.workstation.environment_mapping_engine_v1 import (
                        DiscoveredPlatform,
                        DiscoveredAccount,
                        DiscoveredWorkspace,
                        RelationshipEdge,
                        IngestionLane,
                        EnvironmentMappingEvidence,
                    )
                    from substrate.execution.actuation.actuator_maturity_v1 import ActuatorMaturityLevel

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
                _log(f"!adapter-report loaded env proof: {proof_files[0].name}")
            except (json.JSONDecodeError, OSError, TypeError) as e:
                _log(f"!adapter-report env proof load failed: {e}")

    has_env = env_proof is not None and env_proof.maturity_level != "L0_NO_MAPPING"
    env_label = env_proof.maturity_level if env_proof else "none"

    await message.channel.send(
        f"**!adapter-report** -- analyzing topology\n"
        f"environment proof: `{env_label}`\n"
        f"target platforms: `{len(ADAPTER_TARGET_PLATFORMS)}`\n"
        f"Generating adapter blueprints..."
    )

    trace_id = f"W0-adapter-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-ADAPTER-RPT-{uuid.uuid4().hex[:8]}"

    proof = build_full_adapter_proof(
        topology=topology,
        env_proof=env_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    bp_count = len(proof.blueprints)
    detected = sum(1 for bp in proof.blueprints if bp.detected_on_workstation)
    cu_required = sum(1 for bp in proof.blueprints if bp.requires_cu)
    local_only = sum(1 for bp in proof.blueprints if not bp.requires_cu)

    eval_result = proof.maturity_evaluation
    missing_str = (
        ", ".join(eval_result.missing_evidence)
        if eval_result and eval_result.missing_evidence
        else "none"
    )
    risk_str = (
        ", ".join(eval_result.execution_risks[:3])
        if eval_result and eval_result.execution_risks
        else "none"
    )

    await message.channel.send(
        f"**!adapter-report** -- blueprints generated\n"
        f"blueprints: `{bp_count}` | detected: `{detected}` | "
        f"CU required: `{cu_required}` | local only: `{local_only}`\n"
        f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`\n"
        f"strategy: `{proof.execution_strategy}`\n"
        f"missing: `{missing_str}`\n"
        f"risks: `{risk_str}`"
    )

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve adapter blueprint generation?\n"
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

    proof_final = build_full_adapter_proof(
        topology=topology,
        env_proof=env_proof,
        founder_confirmed=confirmed,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    proof_path = persist_adapter_proof(proof_final, base_dir=base)
    bp_dir = persist_blueprints(proof_final.blueprints, base_dir=base)

    canonical_bps = sum(1 for bp in proof_final.blueprints if bp.canonical_likelihood > 0.4)
    instance_bps = len(proof_final.blueprints) - canonical_bps
    replay_count = sum(
        1 for bp in proof_final.blueprints if bp.replay_contract and bp.replay_contract.replayable
    )
    gov_count = sum(1 for bp in proof_final.blueprints if bp.governance is not None)

    lines = [
        f"**!adapter-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(f"blueprints: `{len(proof_final.blueprints)}`")
    lines.append(f"replay contracts: `{replay_count}`")
    lines.append(f"governance: `{gov_count}`")
    lines.append(f"canonical patterns: `{canonical_bps}`")
    lines.append(f"instance scoped: `{instance_bps}`")
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!adapter-report completed: maturity={proof_final.maturity_level} "
        f"blueprints={len(proof_final.blueprints)} founder={founder_answer}"
    )


async def _handle_capability_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.recursive_capability_planning_engine_v1 import (
        build_full_capability_proof,
        persist_capability_proof,
        SUBSTRATE_CAPABILITIES,
        BOTTLENECK_CATEGORIES,
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
    trace_id = f"W0-capability-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-CAP-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!capability-report** -- analyzing substrate\n"
        f"capabilities: `{len(SUBSTRATE_CAPABILITIES)}`\n"
        f"bottleneck categories: `{len(BOTTLENECK_CATEGORIES)}`\n"
        f"Loading proofs and building capability graph..."
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

    proof = build_full_capability_proof(
        env_proof=env_proof,
        adapter_proof=adapter_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    graph = proof.capability_graph
    bottleneck_count = len(proof.bottlenecks)
    proposal_count = len(proof.upgrade_proposals)
    top_proposal = proof.upgrade_proposals[0] if proof.upgrade_proposals else None

    lines = [
        f"**!capability-report** -- analysis complete",
        f"capabilities: `{len(graph.nodes)}` | "
        f"proven: `{graph.proven_count}` | missing: `{graph.missing_count}`",
        f"bottlenecks: `{bottleneck_count}`",
        f"upgrade proposals: `{proposal_count}`",
    ]
    if top_proposal:
        lines.append(
            f"top proposal: `{top_proposal.proposal_id}` "
            f"(leverage: `{top_proposal.leverage_score.composite_score:.3f}`)"
        )
    lines.append(f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`")
    lines.append(f"strategy: `{proof.execution_strategy}`")

    await message.channel.send("\n".join(lines))

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve capability planning proof generation?\n"
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

    proof_final = build_full_capability_proof(
        env_proof=env_proof,
        adapter_proof=adapter_proof,
        founder_confirmed=confirmed,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
    )

    proof_path = persist_capability_proof(proof_final, base_dir=base)

    graph_final = proof_final.capability_graph
    lines = [
        f"**!capability-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(
        f"graph: `{len(graph_final.nodes)}` capabilities | "
        f"proven=`{graph_final.proven_count}` missing=`{graph_final.missing_count}`"
    )
    lines.append(f"bottlenecks: `{len(proof_final.bottlenecks)}`")
    lines.append(f"proposals: `{len(proof_final.upgrade_proposals)}`")
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!capability-report completed: maturity={proof_final.maturity_level} "
        f"capabilities={len(graph_final.nodes)} "
        f"bottlenecks={len(proof_final.bottlenecks)} "
        f"proposals={len(proof_final.upgrade_proposals)} "
        f"founder={founder_answer}"
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


async def _handle_governance_intelligence_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.adaptive_governance_intelligence_engine_v1 import (
        GOVERNANCE_INTELLIGENCE_MATURITY_LEVELS,
        GOVERNANCE_INTELLIGENCE_HARD_CEILINGS,
        PROPOSAL_TYPES,
        SIMULATION_POLICY_TYPES,
        build_full_governance_intelligence_proof,
        persist_governance_intelligence_proof,
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
    trace_id = f"W0-gov-intel-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-GOVINT-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!governance-intelligence-report** -- analyzing governance intelligence\n"
        f"maturity levels: `{len(GOVERNANCE_INTELLIGENCE_MATURITY_LEVELS)}` | "
        f"proposal types: `{len(PROPOSAL_TYPES)}`\n"
        f"hard ceilings: `{len(GOVERNANCE_INTELLIGENCE_HARD_CEILINGS)}` | "
        f"simulation types: `{len(SIMULATION_POLICY_TYPES)}`\n"
        f"Loading upstream proofs and building intelligence graph..."
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

    proof = build_full_governance_intelligence_proof(
        orchestration_proof=orchestration_proof,
        continuity_proof=continuity_proof,
        capability_proof=capability_proof,
        founder_confirmed=False,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
        base_dir=base,
    )

    ev = proof.evidence
    gi = proof.governance_integrity
    oi = proof.orchestration_intelligence
    ci = proof.continuity_intelligence
    ei = proof.epistemic_intelligence
    ar = proof.adaptive_risk

    lines = [
        f"**!governance-intelligence-report** -- analysis complete",
        f"governance integrity: gate=`{gi.gate_effectiveness:.3f}` "
        f"replay=`{gi.replay_contract_stability:.3f}` "
        f"rollback=`{gi.rollback_safety_effectiveness:.3f}`"
        if gi
        else "governance integrity: pending",
        f"orchestration: seq_eff=`{oi.sequencing_efficiency:.3f}` "
        f"entropy=`{oi.orchestration_entropy:.3f}` "
        f"safety=`{oi.rollout_safety_trend:.3f}`"
        if oi
        else "orchestration: pending",
        f"continuity: drift=`{ci.drift_signal_count}` "
        f"(max=`{ci.max_drift_severity:.3f}`) "
        f"lineage_breaks=`{ci.lineage_breakage_count}`"
        if ci
        else "continuity: pending",
        f"epistemic: evidence=`{ei.evidence_integrity_score:.3f}` "
        f"confidence=`{ei.maturity_confidence_score:.3f}`"
        if ei
        else "epistemic: pending",
        f"adaptive risk: `{ar.composite_risk():.3f}` "
        f"(gov=`{ar.governance_fragility:.3f}` orch=`{ar.orchestration_instability:.3f}`)"
        if ar
        else "adaptive risk: pending",
        f"proposals: `{len(proof.proposals)}`",
        f"simulations: `{len(proof.policy_simulations)}`",
        f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`",
        f"strategy: `{proof.execution_strategy}`",
    ]
    await message.channel.send("\n".join(lines))

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve governance intelligence proof generation?\n"
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

    proof_final = build_full_governance_intelligence_proof(
        orchestration_proof=orchestration_proof,
        continuity_proof=continuity_proof,
        capability_proof=capability_proof,
        founder_confirmed=confirmed,
        is_dry_run=False,
        trace_id=trace_id,
        request_id=request_id,
        base_dir=base,
    )

    proof_path = persist_governance_intelligence_proof(proof_final, base_dir=base)

    ev_final = proof_final.evidence
    lines = [
        f"**!governance-intelligence-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(
        f"proposals: `{ev_final.governance_proposal_count}`" if ev_final else "proposals: unknown"
    )
    lines.append(f"risk: `{ev_final.adaptive_risk_composite:.3f}`" if ev_final else "risk: unknown")
    lines.append(
        f"simulations: `{ev_final.policy_simulation_count}`" if ev_final else "simulations: unknown"
    )
    lines.append(
        f"ceilings enforced: `{ev_final.governance_ceilings_enforced}`"
        if ev_final
        else "ceilings: unknown"
    )
    lines.append(
        f"mutation blocked: `{ev_final.autonomous_mutation_blocked}`"
        if ev_final
        else "mutation: unknown"
    )
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!governance-intelligence-report completed: maturity={proof_final.maturity_level} "
        f"proposals={ev_final.governance_proposal_count if ev_final else 0} "
        f"risk={ev_final.adaptive_risk_composite if ev_final else 0:.3f} "
        f"founder={founder_answer}"
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


async def _handle_federation_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.distributed_constitutional_substrate_federation_v1 import (
        FEDERATION_MATURITY_LEVELS,
        FEDERATION_HARD_CEILINGS,
        FEDERATION_TRUST_DIMENSIONS,
        FEDERATION_DRIFT_TYPES,
        FEDERATION_EMERGENCY_ACTIONS,
        FEDERATION_SIMULATION_TYPES,
        FEDERATION_LINEAGE_TYPES,
        build_full_federation_proof,
        persist_federation_proof,
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
    trace_id = f"W0-federation-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-FEDRT-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!federation-report** -- analyzing distributed federation\n"
        f"maturity levels: `{len(FEDERATION_MATURITY_LEVELS)}` | "
        f"trust dimensions: `{len(FEDERATION_TRUST_DIMENSIONS)}`\n"
        f"drift types: `{len(FEDERATION_DRIFT_TYPES)}` | "
        f"hard ceilings: `{len(FEDERATION_HARD_CEILINGS)}`\n"
        f"emergency actions: `{len(FEDERATION_EMERGENCY_ACTIONS)}` | "
        f"simulation types: `{len(FEDERATION_SIMULATION_TYPES)}`\n"
        f"lineage types: `{len(FEDERATION_LINEAGE_TYPES)}`\n"
        f"Loading upstream proofs and building federation graph..."
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

    proof = build_full_federation_proof(
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

    nr = proof.node_registry
    rc = proof.replay_coordination
    cc = proof.continuity_coordination
    cg = proof.constitutional_governance
    ts = proof.trust_scores

    lines = [
        f"**!federation-report** -- analysis complete",
        f"nodes: `{nr.node_count()}` registered, `{nr.online_count()}` online"
        if nr
        else "nodes: pending",
        f"replay coordination: coverage=`{rc.node_replay_coverage}` determinism=`{rc.replay_determinism_score:.3f}`"
        if rc
        else "replay: pending",
        f"continuity coordination: coverage=`{cc.node_continuity_coverage}` preservation=`{cc.continuity_preservation_score:.3f}`"
        if cc
        else "continuity: pending",
        f"constitutional governance: compatible=`{cg.compatible_node_count}` invariant=`{cg.constitutional_invariant_score:.3f}`"
        if cg
        else "governance: pending",
        f"trust composite: `{ts.composite_trust():.3f}`" if ts else "trust: pending",
        f"drift signals: `{len(proof.drift_signals)}`",
        f"simulations: `{len(proof.simulations)}`",
        f"maturity: `{proof.maturity_level}` | ceiling: `{proof.maturity_ceiling}`",
        f"strategy: `{proof.execution_strategy}`",
    ]
    await message.channel.send("\n".join(lines))

    await message.channel.send(
        "**Founder confirmation required.**\n"
        "Approve federation proof generation?\n"
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

    proof_final = build_full_federation_proof(
        constitutional_proof=constitutional_proof,
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

    proof_path = persist_federation_proof(proof_final, base_dir=base)

    ev_final = proof_final.evidence
    lines = [
        f"**!federation-report** -- PROOF CLASSIFIED",
        f"maturity: `{proof_final.maturity_level}`",
        f"ceiling: `{proof_final.maturity_ceiling}`",
        f"escalation_blocked: `{proof_final.escalation_blocked}`",
    ]
    if proof_final.escalation_reason:
        lines.append(f"reason: `{proof_final.escalation_reason}`")
    lines.append(f"founder: `{founder_answer}`")
    lines.append(
        f"nodes: `{ev_final.node_count}` | online: `{ev_final.online_count}`"
        if ev_final
        else "nodes: unknown"
    )
    lines.append(f"trust: `{ev_final.trust_composite:.3f}`" if ev_final else "trust: unknown")
    lines.append(
        f"drift signals: `{ev_final.drift_signal_count}`" if ev_final else "drift: unknown"
    )
    lines.append(
        f"ceilings enforced: `{ev_final.hard_ceilings_enforced}`"
        if ev_final
        else "ceilings: unknown"
    )
    lines.append(f"strategy: `{proof_final.execution_strategy}`")
    lines.append(f"proof: `{proof_path.name}`")

    await message.channel.send("\n".join(lines))
    _log(
        f"!federation-report completed: maturity={proof_final.maturity_level} "
        f"nodes={ev_final.node_count if ev_final else 0} "
        f"trust={ev_final.trust_composite if ev_final else 0:.3f} "
        f"founder={founder_answer}"
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


async def _handle_epistemic_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.constitutional_epistemic_intelligence_engine_v1 import (
        EPISTEMIC_MATURITY_LEVELS,
        EPISTEMIC_PRIMITIVES,
        EVIDENCE_INTEGRITY_DIMENSIONS,
        REALITY_COHERENCE_DETECTORS,
        PROBABILISTIC_REASONING_TYPES,
        CONTRADICTION_TYPES,
        EPISTEMIC_TOPOLOGY_TYPES,
        EPISTEMIC_HARD_CEILINGS,
        EPISTEMIC_ADAPTATION_TYPES,
        build_full_epistemic_proof,
        persist_epistemic_proof,
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
    trace_id = f"W0-epistemic-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-EPIS-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!epistemic-report** -- analyzing constitutional epistemic intelligence\n"
        f"maturity levels: `{len(EPISTEMIC_MATURITY_LEVELS)}` | "
        f"primitives: `{len(EPISTEMIC_PRIMITIVES)}`\n"
        f"integrity dimensions: `{len(EVIDENCE_INTEGRITY_DIMENSIONS)}` | "
        f"coherence detectors: `{len(REALITY_COHERENCE_DETECTORS)}`\n"
        f"probabilistic types: `{len(PROBABILISTIC_REASONING_TYPES)}` | "
        f"contradiction types: `{len(CONTRADICTION_TYPES)}`\n"
        f"topology types: `{len(EPISTEMIC_TOPOLOGY_TYPES)}` | "
        f"hard ceilings: `{len(EPISTEMIC_HARD_CEILINGS)}`\n"
        f"adaptation types: `{len(EPISTEMIC_ADAPTATION_TYPES)}`\n"
        f"Loading upstream proofs and building epistemic intelligence..."
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

    proof = build_full_epistemic_proof(
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
        f"**Epistemic Intelligence Report**",
        f"proof_id: `{proof.proof_id}`",
        f"maturity: **{proof.maturity_level}** (ceiling: {proof.maturity_ceiling})",
        f"",
        f"**Primitives** — confidence: `{ev.composite_confidence:.4f}` | certainty: `{ev.composite_certainty:.4f}`",
        f"**Integrity** — score: `{ev.integrity_score:.4f}` | corrupted: `{ev.corrupted_dimensions}`",
        f"**Coherence** — score: `{ev.coherence_score:.4f}` | drift: `{ev.drift_count}` | hallucination risk: `{ev.hallucination_risk:.4f}`",
        f"**Probabilistic** — uncertainty: `{ev.total_uncertainty:.4f}`",
        f"**Contradictions** — total: `{ev.contradiction_count}` | critical: `{ev.critical_contradiction_count}` | quarantined: `{ev.quarantined_count}`",
        f"**Topology** — types: `{ev.topology_types_covered}` | stability: `{ev.topology_stability:.4f}`",
        f"**Adaptations** — downgrades: `{ev.downgrades_applied}` | quarantines: `{ev.quarantines_applied}` | isolations: `{ev.isolations_applied}`",
        f"**Epistemic stability score:** `{ev.epistemic_stability_score:.4f}`",
        f"invariants: `{ev.all_invariants_preserved}` | ceilings: `{ev.hard_ceilings_enforced}`",
        f"replay_valid: `{ev.replay_epistemically_valid}` | continuity_stable: `{ev.continuity_epistemically_stable}`",
        f"hallucination_prevented: `{ev.hallucination_prevented}`",
        f"",
        f"Awaiting founder confirmation to escalate to L5...",
    ]
    await message.channel.send("\n".join(lines))

    founder_answer = await _wait_for_founder_confirmation(message, "epistemic-report")

    if founder_answer == "yes":
        proof2 = build_full_epistemic_proof(
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
        persist_epistemic_proof(proof2, base_dir=base)
        ev2 = proof2.evidence
        await message.channel.send(
            f"**FOUNDER CONFIRMED** — re-ran epistemic pipeline\n"
            f"maturity: **{proof2.maturity_level}**\n"
            f"epistemic stability: `{ev2.epistemic_stability_score:.4f}`\n"
            f"proof persisted: `{proof2.proof_id}`"
        )
        confirm_artifact = FounderConfirmationArtifact(
            trace_id=trace_id,
            request_id=request_id,
            confirmed=True,
            confirmation_scope="epistemic_report_full_pipeline",
            founder_message="founder confirmed epistemic report",
        )
        persist_founder_confirmation(confirm_artifact, base_dir=base)
    else:
        persist_epistemic_proof(proof, base_dir=base)
        await message.channel.send(
            f"Epistemic report persisted without founder confirmation.\n"
            f"maturity: **{proof.maturity_level}** | proof: `{proof.proof_id}`"
        )

    logger.info(
        f"epistemic_report complete trace=%s maturity=%s founder={founder_answer}",
        trace_id,
        proof.maturity_level,
    )


async def _handle_identity_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.constitutional_identity_continuity_engine_v1 import (
        IDENTITY_MATURITY_LEVELS,
        IDENTITY_PRIMITIVES,
        SOVEREIGN_MEMORY_LAYERS,
        NARRATIVE_CONTINUITY_DIMENSIONS,
        IDENTITY_DRIFT_TYPES,
        HISTORICAL_RECONCILIATION_TYPES,
        TEMPORAL_TOPOLOGY_TYPES,
        IDENTITY_HARD_CEILINGS,
        IDENTITY_ADAPTATION_TYPES,
        build_full_identity_proof,
        persist_identity_proof,
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
    trace_id = f"W0-identity-report-{uuid.uuid4().hex[:8]}"
    request_id = f"REQ-W0-IDEN-RPT-{uuid.uuid4().hex[:8]}"

    await message.channel.send(
        f"**!identity-report** -- analyzing constitutional identity continuity\n"
        f"maturity levels: `{len(IDENTITY_MATURITY_LEVELS)}` | "
        f"primitives: `{len(IDENTITY_PRIMITIVES)}`\n"
        f"memory layers: `{len(SOVEREIGN_MEMORY_LAYERS)}` | "
        f"narrative dims: `{len(NARRATIVE_CONTINUITY_DIMENSIONS)}`\n"
        f"drift types: `{len(IDENTITY_DRIFT_TYPES)}` | "
        f"reconciliation types: `{len(HISTORICAL_RECONCILIATION_TYPES)}`\n"
        f"topology types: `{len(TEMPORAL_TOPOLOGY_TYPES)}` | "
        f"hard ceilings: `{len(IDENTITY_HARD_CEILINGS)}`\n"
        f"adaptation types: `{len(IDENTITY_ADAPTATION_TYPES)}`\n"
        f"Loading upstream proofs and building identity continuity..."
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

    proof = build_full_identity_proof(
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
        f"**Identity Continuity Report**",
        f"proof_id: `{proof.proof_id}`",
        f"maturity: **{proof.maturity_level}** (ceiling: {proof.maturity_ceiling})",
        f"",
        f"**Primitives** — confidence: `{ev.composite_confidence:.4f}` | stability: `{ev.composite_stability:.4f}` | drift: `{ev.composite_drift:.4f}`",
        f"**Memory** — integrity: `{ev.memory_integrity:.4f}` | immutable: `{ev.immutable_layers}` | mutable: `{ev.mutable_layers}`",
        f"**Narrative** — coherence: `{ev.narrative_coherence:.4f}` | intact: `{ev.intact_narratives}` | divergent: `{ev.divergent_narratives}`",
        f"**Drift** — count: `{ev.drift_count}` | critical: `{ev.critical_drift_count}`",
        f"**Reconciliation** — conflicts: `{ev.conflict_count}` | reconciled: `{ev.reconciled_count}` | unreconciled: `{ev.unreconciled_count}`",
        f"**Topology** — types: `{ev.topology_types_covered}` | stability: `{ev.topology_stability:.4f}`",
        f"**Adaptations** — preservations: `{ev.preservations_applied}` | quarantines: `{ev.quarantines_applied}` | reconciliations: `{ev.reconciliations_applied}`",
        f"**Civilizational continuity score:** `{ev.civilizational_continuity_score:.4f}`",
        f"invariants: `{ev.all_invariants_preserved}` | ceilings: `{ev.hard_ceilings_enforced}`",
        f"replay_safe: `{ev.replay_safe_lineage}` | continuity_safe: `{ev.continuity_safe_memory}`",
        f"selfhood_stable: `{ev.selfhood_stable}`",
        f"",
        f"Awaiting founder confirmation to escalate to L5...",
    ]
    await message.channel.send("\n".join(lines))

    founder_answer = await _wait_for_founder_confirmation(message, "identity-report")

    if founder_answer == "yes":
        proof2 = build_full_identity_proof(
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
        persist_identity_proof(proof2, base_dir=base)
        ev2 = proof2.evidence
        await message.channel.send(
            f"**FOUNDER CONFIRMED** — re-ran identity pipeline\n"
            f"maturity: **{proof2.maturity_level}**\n"
            f"civilizational continuity: `{ev2.civilizational_continuity_score:.4f}`\n"
            f"proof persisted: `{proof2.proof_id}`"
        )
        confirm_artifact = FounderConfirmationArtifact(
            trace_id=trace_id,
            request_id=request_id,
            confirmed=True,
            confirmation_scope="identity_report_full_pipeline",
            founder_message="founder confirmed identity report",
        )
        persist_founder_confirmation(confirm_artifact, base_dir=base)
    else:
        persist_identity_proof(proof, base_dir=base)
        await message.channel.send(
            f"Identity report persisted without founder confirmation.\n"
            f"maturity: **{proof.maturity_level}** | proof: `{proof.proof_id}`"
        )

    logger.info(
        f"identity_report complete trace=%s maturity=%s founder={founder_answer}",
        trace_id,
        proof.maturity_level,
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


async def _handle_resilience_report(message: Any, spine: Any) -> None:
    from substrate.execution.workers.workstation.constitutional_antifragility_resilience_engine_v1 import (
        RESILIENCE_MATURITY_LEVELS,
        RESILIENCE_PRIMITIVES,
        CATASTROPHIC_SCENARIO_TYPES,
        ANTIFRAGILITY_DIMENSIONS,
        EVOLUTIONARY_RESILIENCE_FORECASTS,
        EXISTENTIAL_RISK_TYPES,
        RESILIENCE_TOPOLOGY_TYPES,
        RESILIENCE_HARD_CEILINGS,
        RESILIENCE_ADAPTATION_TYPES,
        build_full_resilience_proof,
        persist_resilience_proof,
    )
    from substrate.execution.workers.workstation.recursive_capability_planning_engine_v1 import (
        build_full_capability_proof,
    )
    from substrate.execution.workers.workstation.governed_recursive_orchestration_engine_v1 import (
        build_full_orchestration_proof,
    )
    from substrate.execution.workers.workstation.persistent_substrate_continuity_engine_v1 import (
        build_full_continuity_proof,
    )
    from substrate.execution.workers.workstation.adaptive_governance_intelligence_engine_v1 import (
        build_full_governance_intelligence_proof,
    )
    from substrate.execution.workers.workstation.constitutional_substrate_governance_layer_v1 import (
        build_full_constitutional_proof,
    )
    from substrate.execution.workers.workstation.distributed_constitutional_substrate_federation_v1 import (
        build_full_federation_proof,
    )
    from substrate.execution.workers.workstation.constitutional_resource_economics_engine_v1 import (
        build_full_economics_proof,
    )
    from substrate.execution.workers.workstation.constitutional_strategic_intelligence_engine_v1 import (
        build_full_strategy_proof,
    )
    from substrate.execution.workers.workstation.constitutional_epistemic_intelligence_engine_v1 import (
        build_full_epistemic_proof,
    )
    from substrate.execution.workers.workstation.constitutional_identity_continuity_engine_v1 import (
        build_full_identity_proof,
    )
    from substrate.execution.workers.workstation.constitutional_telos_alignment_engine_v1 import (
        build_full_telos_proof,
    )

    trace_id = f"W0-resilience-report-{uuid.uuid4().hex[:8]}"
    await message.channel.send(
        f"**!resilience-report** -- analyzing constitutional antifragility and resilience\n"
        f"trace: `{trace_id}`\n"
        f"layers: capability → orchestration → continuity → governance → constitutional → "
        f"federation → economics → strategy → epistemic → identity → telos → resilience\n"
        f"primitives: {len(RESILIENCE_PRIMITIVES)} | "
        f"scenarios: {len(CATASTROPHIC_SCENARIO_TYPES)} | "
        f"antifragility: {len(ANTIFRAGILITY_DIMENSIONS)} | "
        f"forecasts: {len(EVOLUTIONARY_RESILIENCE_FORECASTS)} | "
        f"risks: {len(EXISTENTIAL_RISK_TYPES)} | "
        f"topology: {len(RESILIENCE_TOPOLOGY_TYPES)} | "
        f"ceilings: {len(RESILIENCE_HARD_CEILINGS)} | "
        f"adaptations: {len(RESILIENCE_ADAPTATION_TYPES)} | "
        f"maturity: {len(RESILIENCE_MATURITY_LEVELS)} levels"
    )

    try:
        cap_proof = build_full_capability_proof(founder_confirmed=True)
        orch_proof = build_full_orchestration_proof(
            capability_proof=cap_proof, founder_confirmed=True
        )
        cont_proof = build_full_continuity_proof(
            orchestration_proof=orch_proof, founder_confirmed=True
        )
        gov_proof = build_full_governance_intelligence_proof(
            continuity_proof=cont_proof, founder_confirmed=True
        )
        const_proof = build_full_constitutional_proof(
            governance_proof=gov_proof, founder_confirmed=True
        )
        fed_proof = build_full_federation_proof(
            constitutional_proof=const_proof, founder_confirmed=True
        )
        econ_proof = build_full_economics_proof(
            federation_proof=fed_proof, founder_confirmed=True
        )
        strat_proof = build_full_strategy_proof(
            economics_proof=econ_proof, founder_confirmed=True
        )
        epis_proof = build_full_epistemic_proof(
            strategy_proof=strat_proof, founder_confirmed=True
        )
        iden_proof = build_full_identity_proof(
            epistemic_proof=epis_proof, founder_confirmed=True
        )
        telos_proof = build_full_telos_proof(
            identity_proof=iden_proof, founder_confirmed=True
        )

        founder_answer = await _wait_for_founder_confirmation(message, "resilience-report")
        founder_confirmed = founder_answer == "yes"

        proof = build_full_resilience_proof(
            telos_proof=telos_proof,
            identity_proof=iden_proof,
            epistemic_proof=epis_proof,
            strategy_proof=strat_proof,
            economics_proof=econ_proof,
            federation_proof=fed_proof,
            orchestration_proof=orch_proof,
            continuity_proof=cont_proof,
            constitutional_proof=const_proof,
            governance_proof=gov_proof,
            capability_proof=cap_proof,
            founder_confirmed=founder_confirmed,
            trace_id=trace_id,
        )

        proof_path = persist_resilience_proof(proof)
        ev = proof.evidence

        await message.channel.send(
            f"**RESILIENCE PROOF**\n"
            f"```\n"
            f"proof_id:     {proof.proof_id}\n"
            f"maturity:     {proof.maturity_level}\n"
            f"ceiling:      {proof.maturity_ceiling}\n"
            f"score:        {ev.resilience_maturity_score:.4f}\n"
            f"tolerance:    {ev.composite_tolerance:.4f}\n"
            f"fragility:    {ev.composite_fragility:.4f}\n"
            f"antifragility:{ev.composite_antifragility:.4f}\n"
            f"survivability:{ev.composite_survivability:.4f}\n"
            f"brittleness:  {ev.composite_brittleness:.4f}\n"
            f"vulnerability:{ev.composite_vulnerability:.4f}\n"
            f"civ_survive:  {ev.civilization_survivability_score:.4f}\n"
            f"scenarios:    {ev.total_scenarios} ({ev.critical_scenarios} critical)\n"
            f"risks:        {ev.total_risk_count} ({ev.critical_risk_count} critical)\n"
            f"topology:     {ev.topology_types_covered} types, {ev.total_spof_count} SPOFs\n"
            f"redundancy:   {ev.composite_redundancy:.4f}\n"
            f"invariants:   {'preserved' if ev.all_invariants_preserved else 'VIOLATED'}\n"
            f"existential:  {'SAFE' if ev.existential_safe else 'AT RISK'}\n"
            f"const_safe:   {'YES' if ev.resilience_constitutionally_safe else 'NO'}\n"
            f"founder:      {'confirmed' if ev.founder_confirmed else 'not confirmed'}\n"
            f"persisted:    {proof_path}\n"
            f"```",
            confirmation_scope="resilience_report_full_pipeline",
        )

    except Exception:
        logger.exception("resilience_report failed trace=%s", trace_id)
        await message.channel.send(f"resilience-report FAILED — trace: `{trace_id}`")

    logger.info(
        f"resilience_report complete trace=%s maturity=%s founder={founder_answer}",
        trace_id,
        proof.maturity_level,
    )
