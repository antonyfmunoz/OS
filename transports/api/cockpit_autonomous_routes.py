"""Cockpit autonomous PR factory and cadence scheduler routes.

Extracted from cockpit.py (Phase 10.0). Auth model: configure() must be called
before include_router(). Most routes require operator token — see _build_router
for full breakdown.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import asyncio
import glob
import json
import logging
import os
import re as _re
import time as _time
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger(__name__)

autonomous_router: APIRouter = APIRouter()

_get_organism: Callable[[], Any] = lambda: None
_configured: bool = False


def configure(
    get_organism_fn: Callable[[], Any],
    require_operator_dep: Any,
) -> None:
    """Wire organism accessor and operator auth into the autonomous router.

    Must be called once from cockpit.py before include_router(). Rebuilds
    the router so privileged routes carry the real auth dependency.
    """
    global _get_organism, _configured, autonomous_router

    _get_organism = get_organism_fn
    _configured = True

    autonomous_router = _build_router(require_operator_dep)


def _get_pr_factory():
    from substrate.organism.worktree_sandbox import SandboxManager
    from substrate.organism.autonomous_pr_factory import AutonomousPRFactory
    daemon = _get_organism()
    if daemon is None:
        return None, None
    manager = getattr(daemon, "_sandbox_manager", None)
    if manager is None:
        manager = SandboxManager()
        daemon._sandbox_manager = manager
    factory = getattr(daemon, "_pr_factory", None)
    if factory is None:
        factory = AutonomousPRFactory(sandbox_manager=manager)
        daemon._pr_factory = factory
    return manager, factory


def _build_router(require_operator_dep: Any) -> APIRouter:
    """Construct the autonomous router with operator auth on privileged routes."""
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ── Read-only endpoints (no auth required) ─────────────────────────────

    r.add_api_route("/organism/autonomous-pr-factory", _autonomous_pr_factory_status, methods=["GET"])
    r.add_api_route("/organism/autonomous-pr-factory/sandboxes", _autonomous_pr_factory_sandboxes, methods=["GET"])
    r.add_api_route("/organism/autonomous-pr-factory/sandboxes/{sandbox_id}", _autonomous_pr_factory_sandbox_detail, methods=["GET"])
    r.add_api_route("/organism/autonomous-pr-factory/manifests", _autonomous_pr_factory_manifests, methods=["GET"])
    r.add_api_route("/organism/autonomous-pr-factory/manifests/{manifest_id}", _autonomous_pr_factory_manifest_detail, methods=["GET"])
    r.add_api_route("/organism/autonomous-pr-factory/parallel-dry-run", _autonomous_pr_factory_parallel_dry_run, methods=["GET"])

    # ── Privileged endpoints (operator auth required) ──────────────────────

    r.add_api_route("/organism/autonomous-pr-factory/create-pr", _autonomous_pr_factory_create_pr, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/autonomous-pr-factory/cleanup/{sandbox_id}", _autonomous_pr_factory_cleanup, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/autonomous-pr-factory/production-truth", _autonomous_pr_factory_production_truth, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/autonomous-pr-factory/verify-merge/{sandbox_id}", _autonomous_pr_factory_verify_merge, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/autonomous-pr-factory/production-truth/{delta_id}", _autonomous_pr_factory_production_truth_detail, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/autonomous-pr-factory/merge-verifications", _autonomous_pr_factory_merge_verifications, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/autonomous-pr-factory/merge-verifications/{verification_id}", _autonomous_pr_factory_merge_verification_detail, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/autonomous-pr-factory/cleanup-eligible", _autonomous_pr_factory_cleanup_eligible, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/autonomous-cadence", _autonomous_cadence_status, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/autonomous-cadence/run-dry-run", _autonomous_cadence_run_dry_run, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/autonomous-cadence/set-mode", _autonomous_cadence_set_mode, methods=["POST"], dependencies=auth)

    # ── Template registry + Candidate supply + Governance routes ──────────
    r.add_api_route("/organism/template-registry", _template_registry_summary, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/template-registry/promoted", _template_registry_promoted, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/template-registry/candidates", _template_registry_candidates, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/candidate-supply", _candidate_supply_scan, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/candidate-supply/run", _candidate_supply_run, methods=["POST"], dependencies=auth)
    r.add_api_route("/organism/template-governance/evaluate", _template_governance_evaluate, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/pr-factory-preview", _pr_factory_preview, methods=["GET"], dependencies=auth)

    # ── Phase 10.5: Reliability-weighted cadence routes ───────────────────
    r.add_api_route("/organism/reliability-signals", _reliability_signals, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/cadence-ranked-candidates", _cadence_ranked_candidates, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/promotion-thresholds", _promotion_thresholds, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/template-reliability", _template_reliability, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/agent-reliability", _agent_reliability, methods=["GET"], dependencies=auth)
    r.add_api_route("/organism/candidate-source-reliability", _candidate_source_reliability, methods=["GET"], dependencies=auth)

    return r


# ── Autonomous PR Factory handlers ────────────────────────────────────────────


async def _autonomous_pr_factory_status():
    manager, factory = _get_pr_factory()
    if factory is None:
        return {"error": "organism not running"}
    return factory.to_dict()


async def _autonomous_pr_factory_sandboxes():
    manager, factory = _get_pr_factory()
    if manager is None:
        return {"error": "organism not running"}
    return manager.to_dict()


async def _autonomous_pr_factory_sandbox_detail(sandbox_id: str):
    manager, factory = _get_pr_factory()
    if manager is None:
        return {"error": "organism not running"}
    sb = manager.get_sandbox(sandbox_id)
    if sb is None:
        return {"error": f"sandbox {sandbox_id} not found"}
    return sb.to_dict()


async def _autonomous_pr_factory_manifests():
    _root = os.environ.get("UMH_ROOT", "/opt/OS")
    manifest_dir = os.path.join(_root, "data", "umh", "autonomous_lane", "manifests")
    manifests = []
    for path in sorted(glob.glob(os.path.join(manifest_dir, "*.json"))):
        try:
            with open(path) as f:
                manifests.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    return {"manifests": manifests, "count": len(manifests)}


async def _autonomous_pr_factory_manifest_detail(manifest_id: str):
    _root = os.environ.get("UMH_ROOT", "/opt/OS")
    path = os.path.join(
        _root, "data", "umh", "autonomous_lane", "manifests", f"{manifest_id}.json"
    )
    if not os.path.isfile(path):
        return {"error": f"manifest {manifest_id} not found"}
    with open(path) as f:
        return json.load(f)


async def _autonomous_pr_factory_create_pr(payload: dict, request: Request):
    manager, factory = _get_pr_factory()
    if factory is None:
        return {"error": "organism not running"}
    from substrate.organism.autonomous_pr_factory import AutonomousPRRequest
    from substrate.organism.autonomous_improvement_lane import AutonomousImprovementCandidate
    candidate = AutonomousImprovementCandidate(
        candidate_id=payload.get("candidate_id", ""),
        description=payload.get("description", ""),
        affected_files=payload.get("affected_files", []),
        risk_class=payload.get("risk_class", "low"),
        matching_template_id=payload.get("template_id", ""),
        validation_method=payload.get("validation_method", "py_compile"),
        rollback_method=payload.get("rollback_method", "git revert"),
        reversible=True,
    )
    req = AutonomousPRRequest(
        candidate=candidate,
        candidate_slug=payload.get("slug", candidate.description[:40]),
        description=payload.get("description", ""),
    )
    import asyncio
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, factory.create_pr, req)
    return result.to_dict()


async def _autonomous_pr_factory_cleanup(sandbox_id: str):
    manager, factory = _get_pr_factory()
    if manager is None:
        return {"error": "organism not running"}
    ok = manager.cleanup_sandbox(sandbox_id)
    return {"ok": ok, "sandbox_id": sandbox_id}


async def _autonomous_pr_factory_parallel_dry_run():
    manager, factory = _get_pr_factory()
    if factory is None:
        return {"error": "organism not running"}
    from substrate.organism.autonomous_improvement_lane import (
        AutonomousCandidateSelector,
        AutonomousImprovementCandidate,
    )
    from substrate.organism.template_registry import TemplateRegistry
    from substrate.organism.agent_capability_model import AgentCapabilityModel
    tr = TemplateRegistry()
    acm = AgentCapabilityModel()
    selector = AutonomousCandidateSelector(
        template_registry=tr,
        agent_capability_model=acm,
    )
    candidates = selector.build_candidates(max_candidates=5)
    return factory.conflict_detector.parallel_dry_run(candidates)


async def _autonomous_pr_factory_production_truth():
    manager, factory = _get_pr_factory()
    if manager is None:
        return {"error": "organism not running"}
    return manager.production_truth()


async def _autonomous_pr_factory_verify_merge(sandbox_id: str):
    if not _re.fullmatch(r"sb-[a-f0-9]{8}", sandbox_id):
        raise HTTPException(status_code=400, detail="invalid sandbox_id format")
    manager, factory = _get_pr_factory()
    if factory is None:
        return {"error": "organism not running"}
    from substrate.organism.production_merge_verifier import ProductionMergeVerifier
    verifier = ProductionMergeVerifier(sandbox_manager=manager)
    sb = manager.get_sandbox(sandbox_id)
    pr_number = sb.pr_number if sb else 0
    expected_files: list = []
    manifest_id = ""
    if factory:
        for rp in factory.review_packets:
            if rp.sandbox_id == sandbox_id:
                manifest_id = rp.manifest_id
                if rp.manifest:
                    expected_files = [cf.path for cf in rp.manifest.changed_files]
                break
    import asyncio
    loop = asyncio.get_running_loop()
    verification = await loop.run_in_executor(
        None, verifier.verify_merge, sandbox_id, pr_number, manifest_id, expected_files
    )
    return verification.to_dict()


async def _autonomous_pr_factory_production_truth_detail(delta_id: str):
    if not _re.fullmatch(r"ptd-[a-f0-9]{8}", delta_id):
        raise HTTPException(status_code=400, detail="invalid delta_id format")
    _root = os.environ.get("UMH_ROOT", "/opt/OS")
    mv_dir = Path(_root, "data", "umh", "autonomous_lane", "merge_verifications").resolve()
    direct = Path(mv_dir, f"{delta_id}.json").resolve()
    if direct.is_relative_to(mv_dir) and direct.is_file():
        with open(direct) as f:
            return json.load(f)
    if mv_dir.is_dir():
        for pmv_file in mv_dir.iterdir():
            if not pmv_file.name.endswith(".json"):
                continue
            try:
                with open(pmv_file) as f:
                    data = json.load(f)
                td = data.get("truth_delta") or {}
                if td.get("delta_id") == delta_id:
                    return td
            except (json.JSONDecodeError, OSError):
                continue
    return {"error": f"delta {delta_id} not found"}


async def _autonomous_pr_factory_merge_verifications():
    _root = os.environ.get("UMH_ROOT", "/opt/OS")
    mv_dir = os.path.join(_root, "data", "umh", "autonomous_lane", "merge_verifications")
    verifications = []
    if os.path.isdir(mv_dir):
        for path in sorted(glob.glob(os.path.join(mv_dir, "pmv-*.json"))):
            try:
                with open(path) as f:
                    verifications.append(json.load(f))
            except (json.JSONDecodeError, OSError):
                continue
    return {"verifications": verifications, "count": len(verifications)}


async def _autonomous_pr_factory_merge_verification_detail(verification_id: str):
    if not _re.fullmatch(r"pmv-[a-f0-9]{8}", verification_id):
        raise HTTPException(status_code=400, detail="invalid verification_id format")
    _root = os.environ.get("UMH_ROOT", "/opt/OS")
    mv_dir = Path(_root, "data", "umh", "autonomous_lane", "merge_verifications").resolve()
    candidate = Path(mv_dir, f"{verification_id}.json").resolve()
    if not candidate.is_relative_to(mv_dir):
        raise HTTPException(status_code=400, detail="invalid verification_id")
    if not candidate.is_file():
        return {"error": f"verification {verification_id} not found"}
    with open(candidate) as f:
        return json.load(f)


async def _autonomous_pr_factory_cleanup_eligible():
    manager, factory = _get_pr_factory()
    if manager is None:
        return {"error": "organism not running"}
    eligible = []
    for sb in manager.all_sandboxes:
        if sb.status.value in ("merged", "abandoned", "cleaned"):
            eligible.append(sb.to_dict())
    stale = []
    now = _time.time()
    for sb in manager.all_sandboxes:
        age_h = (now - sb.created_at) / 3600
        if age_h > manager._ttl_hours and sb.status.value not in ("merged", "cleaned"):
            stale.append({"sandbox_id": sb.sandbox_id, "age_hours": round(age_h, 1), "status": sb.status.value})
    return {"cleanup_eligible": eligible, "stale": stale, "count": len(eligible) + len(stale)}


# ── Autonomous Cadence handlers ────────────────────────────────────────────────


async def _autonomous_cadence_status():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    cadence = getattr(daemon, "_autonomous_cadence", None)
    if cadence is None:
        return {"error": "cadence not available"}
    return cadence.to_dict()


async def _autonomous_cadence_run_dry_run():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    cadence = getattr(daemon, "_autonomous_cadence", None)
    if cadence is None:
        return {"error": "cadence not available"}
    result = cadence.run_cycle()
    return result.to_dict()


async def _autonomous_cadence_set_mode(payload: dict):
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    cadence = getattr(daemon, "_autonomous_cadence", None)
    if cadence is None:
        return {"error": "cadence not available"}
    from substrate.organism.autonomous_cadence import CadenceMode
    mode_str = payload.get("mode", "off")
    try:
        cadence.mode = CadenceMode(mode_str)
    except ValueError:
        return {"error": f"invalid mode: {mode_str}"}
    return {"ok": True, "mode": cadence.mode.value}


# ── Template Registry handlers ────────────────────────────────────────────────


async def _template_registry_summary():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    registry = getattr(daemon, "_template_registry", None)
    if registry is None:
        return {"error": "template registry not available"}
    return registry.to_safe_dict()


async def _template_registry_promoted():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    registry = getattr(daemon, "_template_registry", None)
    if registry is None:
        return {"error": "template registry not available"}
    promoted = registry.list_promoted()
    return {
        "count": len(promoted),
        "templates": [
            {
                "template_id": t.template_id,
                "template_type": t.template_type.value,
                "confidence": round(t.confidence, 3),
                "observed_success_count": t.observed_success_count,
                "observed_failure_count": t.observed_failure_count,
                "risk_class": t.risk_class,
                "status": t.status.value,
            }
            for t in promoted
        ],
    }


async def _template_registry_candidates():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    registry = getattr(daemon, "_template_registry", None)
    if registry is None:
        return {"error": "template registry not available"}
    candidates = registry.list_candidates()
    return {
        "count": len(candidates),
        "candidates": [
            {
                "template_id": t.template_id,
                "template_type": t.template_type.value,
                "confidence": round(t.confidence, 3),
                "status": t.status.value,
            }
            for t in candidates[-20:]
        ],
    }


# ── Candidate Supply handlers ─────────────────────────────────────────────────


async def _candidate_supply_scan():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    supply = getattr(daemon, "_candidate_supply_engine", None)
    if supply is None:
        return {"error": "candidate supply engine not available"}
    return supply.summary()


async def _candidate_supply_run():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    supply = getattr(daemon, "_candidate_supply_engine", None)
    if supply is None:
        return {"error": "candidate supply engine not available"}
    result = supply.discover()
    return result.to_dict()


# ── Template Governance handlers ───────────────────────────────────────────────


async def _template_governance_evaluate():
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    registry = getattr(daemon, "_template_registry", None)
    if registry is None:
        return {"error": "template registry not available"}
    from substrate.organism.template_governance import TemplateGovernance
    gov = TemplateGovernance()
    promoted = registry.list_promoted()
    scores = gov.evaluate_batch(promoted)
    return {
        "template_count": len(promoted),
        "scores": [s.to_dict() for s in scores],
        "summary": {
            "cadence_eligible": sum(1 for s in scores if s.decision.value == "cadence_eligible"),
            "candidate_only": sum(1 for s in scores if s.decision.value == "candidate_only"),
            "operator_review_required": sum(1 for s in scores if s.decision.value == "operator_review_required"),
            "blocked": sum(1 for s in scores if s.decision.value == "blocked"),
        },
    }


# ── PR Factory Preview handler ─────────────────────────────────────────────────


async def _pr_factory_preview():
    """Generate a preview review packet from the top eligible candidate without creating a PR."""
    daemon = _get_organism()
    if daemon is None:
        return {"error": "organism not running"}
    supply = getattr(daemon, "_candidate_supply_engine", None)
    if supply is None:
        return {"error": "candidate supply engine not available"}
    registry = getattr(daemon, "_template_registry", None)
    if registry is None:
        return {"error": "template registry not available"}

    result = supply.discover()
    if not result.candidates:
        return {
            "preview": None,
            "reason": "no candidates discovered",
            "source_scan_proof": result.source_scan_proof,
        }

    best = result.candidates[0]

    template = None
    if best.matching_templates:
        template = registry.get_template(best.matching_templates[0])

    from substrate.organism.template_governance import TemplateGovernance
    gov_score = None
    if template:
        gov = TemplateGovernance()
        gov_score = gov.evaluate(template)

    return {
        "preview": {
            "candidate": best.to_dict(),
            "template_match": {
                "template_id": template.template_id if template else None,
                "template_type": template.template_type.value if template else None,
                "confidence": round(template.confidence, 3) if template else None,
                "steps": [s.to_dict() for s in template.reusable_steps] if template else [],
                "validation": template.validation.to_dict() if template and template.validation else None,
                "rollback": template.rollback.to_dict() if template and template.rollback else None,
            } if template else None,
            "governance": gov_score.to_dict() if gov_score else None,
            "policy_decision": best.policy_decision,
            "would_create_pr": best.policy_decision == "cadence_eligible",
        },
        "pr_created": False,
        "reason": "preview mode — no actual PR created",
        "source_scan_proof": result.source_scan_proof,
    }

# ── Phase 10.5: Reliability-weighted cadence handlers ────────────────────────


async def _reliability_signals():
    from substrate.organism.reliability_signals import ReliabilitySignalAggregator
    agg = ReliabilitySignalAggregator()
    return agg.aggregate()


async def _cadence_ranked_candidates():
    daemon = _get_organism()
    supply = getattr(daemon, "_candidate_supply_engine", None) if daemon else None
    if supply is None:
        from substrate.organism.candidate_supply_engine import CandidateSupplyEngine
        supply = CandidateSupplyEngine()
    result = supply.discover()
    from substrate.organism.reliability_signals import ReliabilitySignalAggregator
    from substrate.organism.reliability_weighted_ranker import ReliabilityWeightedRanker
    agg = ReliabilitySignalAggregator()
    agg.aggregate()
    ranker = ReliabilityWeightedRanker(aggregator=agg)
    cadence_dicts = [c.to_cadence_dict() for c in result.candidates]
    ranked = ranker.rank_candidates(cadence_dicts)
    return {
        "unranked_count": len(result.candidates),
        "ranked_count": len(ranked),
        "candidates": [rc.to_dict() for rc in ranked],
        "ranker_config": ranker.to_dict(),
    }


async def _promotion_thresholds():
    from substrate.organism.reliability_signals import ReliabilitySignalAggregator
    from substrate.organism.promotion_threshold_policy import PromotionThresholdPolicy
    agg = ReliabilitySignalAggregator()
    agg.aggregate()
    policy = PromotionThresholdPolicy(aggregator=agg)
    return policy.to_dict()


async def _template_reliability():
    from substrate.organism.reliability_signals import ReliabilitySignalAggregator
    agg = ReliabilitySignalAggregator()
    agg.aggregate()
    return {"templates": {tid: sig.to_dict() for tid, sig in agg._template_signals.items()}}


async def _agent_reliability():
    from substrate.organism.reliability_signals import ReliabilitySignalAggregator
    agg = ReliabilitySignalAggregator()
    agg.aggregate()
    return {"agents": {atype: sig.to_dict() for atype, sig in agg._agent_signals.items()}}


async def _candidate_source_reliability():
    from substrate.organism.reliability_signals import ReliabilitySignalAggregator
    agg = ReliabilitySignalAggregator()
    agg.aggregate()
    return {"sources": {src: sig.to_dict() for src, sig in agg._source_signals.items()}}
