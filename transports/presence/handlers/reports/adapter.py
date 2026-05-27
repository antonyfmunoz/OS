"""Adapter report handler."""

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
