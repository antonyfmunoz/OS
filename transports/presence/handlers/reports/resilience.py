"""Resilience report handler."""

from __future__ import annotations

from typing import Any

from ._common import (
    uuid,
    logger,
    _wait_for_founder_confirmation,
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
