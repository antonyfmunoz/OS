"""Cockpit reality model routes — canonical patterns, instance observations, simulation.

Mounted under /api/umh/ via include_router in cockpit.py.

Phase 14.7A WP-1.1. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

reality_model_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, reality_model_router
    _configured = True
    reality_model_router = _build_router(require_operator_dep)


def _get_canonical():
    from substrate.reality_model.canonical import CanonicalRealityModel
    return CanonicalRealityModel()


def _get_instance():
    from substrate.reality_model.instance import InstanceRealityModel
    org_id = os.environ.get("UMH_ORG_ID", os.environ.get("EOS_ORG_ID", "default"))
    user_id = os.environ.get("UMH_USER_ID", os.environ.get("EOS_USER_ID", "default"))
    return InstanceRealityModel(user_id=user_id, org_id=org_id)


def _get_simulation():
    from substrate.reality_model.simulation import SimulationReality
    return SimulationReality(
        canonical=_get_canonical(),
        instance=_get_instance(),
    )


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/reality-model/status", _status, methods=["GET"])
    r.add_api_route("/reality-model/canonical/patterns", _canonical_patterns, methods=["GET"])
    r.add_api_route("/reality-model/canonical/pattern/{name}", _canonical_pattern_detail, methods=["GET"])
    r.add_api_route("/reality-model/canonical/search", _canonical_search, methods=["GET"])
    r.add_api_route("/reality-model/canonical/domains", _canonical_domains, methods=["GET"])
    r.add_api_route("/reality-model/canonical/stats", _canonical_stats, methods=["GET"])
    r.add_api_route("/reality-model/canonical/relationships/{name}", _canonical_relationships, methods=["GET"])

    r.add_api_route("/reality-model/instance/observations", _instance_observations, methods=["GET"])
    r.add_api_route("/reality-model/instance/recent", _instance_recent, methods=["GET"])
    r.add_api_route("/reality-model/instance/search", _instance_search, methods=["GET"])
    r.add_api_route("/reality-model/instance/domains", _instance_domains, methods=["GET"])
    r.add_api_route("/reality-model/instance/stats", _instance_stats, methods=["GET"])

    r.add_api_route("/reality-model/timeline", _reality_timeline, methods=["GET"])

    r.add_api_route(
        "/reality-model/canonical/store",
        _canonical_store,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/reality-model/instance/record",
        _instance_record,
        methods=["POST"],
        dependencies=auth,
    )
    r.add_api_route(
        "/reality-model/simulate",
        _simulate,
        methods=["POST"],
        dependencies=auth,
    )

    return r


async def _status():
    canonical = _get_canonical()
    instance = _get_instance()
    return {
        "canonical": canonical.stats(),
        "instance": instance.stats(),
        "layers": ["canonical", "instance", "simulation"],
    }


async def _canonical_patterns(domain: str | None = None, limit: int = 100):
    canonical = _get_canonical()
    if domain:
        patterns = canonical.list_by_domain(domain)
    else:
        patterns = canonical.all()
    result = []
    for p in patterns[:limit]:
        d = {
            "id": str(p.id),
            "name": p.name,
            "domain": p.domain,
            "description": p.description,
            "evidence_count": p.evidence_count,
            "confidence": p.confidence,
            "effective_confidence": p.effective_confidence(),
            "promoted_at": p.promoted_at.isoformat(),
            "last_confirmed": p.last_confirmed.isoformat(),
            "tags": p.tags,
        }
        result.append(d)
    return result


async def _canonical_pattern_detail(name: str):
    canonical = _get_canonical()
    p = canonical.get_by_name(name)
    if not p:
        return {"error": "Pattern not found", "name": name}
    related = canonical.get_related(name)
    return {
        "id": str(p.id),
        "name": p.name,
        "domain": p.domain,
        "description": p.description,
        "evidence_count": p.evidence_count,
        "confidence": p.confidence,
        "effective_confidence": p.effective_confidence(),
        "promoted_at": p.promoted_at.isoformat(),
        "last_confirmed": p.last_confirmed.isoformat(),
        "tags": p.tags,
        "metadata": p.metadata,
        "relationships": [
            {"name": r[0], "type": r[1], "strength": r[2]}
            for r in related
        ],
    }


async def _canonical_search(q: str = "", limit: int = 10):
    if not q:
        return []
    canonical = _get_canonical()
    results = canonical.search(q, limit=limit)
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "domain": p.domain,
            "description": p.description,
            "effective_confidence": p.effective_confidence(),
        }
        for p in results
    ]


async def _canonical_domains():
    canonical = _get_canonical()
    patterns = canonical.all()
    domains: dict[str, int] = {}
    for p in patterns:
        domains[p.domain] = domains.get(p.domain, 0) + 1
    return [{"domain": d, "pattern_count": c} for d, c in sorted(domains.items())]


async def _canonical_stats():
    return _get_canonical().stats()


async def _canonical_relationships(name: str):
    canonical = _get_canonical()
    related = canonical.get_related(name)
    return [
        {"name": r[0], "type": r[1], "strength": r[2]}
        for r in related
    ]


async def _instance_observations(domain: str | None = None, limit: int = 50):
    instance = _get_instance()
    if domain:
        obs_list = instance.list_by_domain(domain)
    else:
        obs_list = instance.all()
    return [
        {
            "id": str(o.id),
            "content": o.content[:500],
            "domain": o.domain,
            "confidence": o.confidence,
            "effective_confidence": o.effective_confidence(),
            "observed_at": o.observed_at.isoformat(),
            "tags": o.tags,
        }
        for o in obs_list[:limit]
    ]


async def _instance_recent(limit: int = 20):
    instance = _get_instance()
    recent = instance.recent(limit=limit)
    return [
        {
            "id": str(o.id),
            "content": o.content[:500],
            "domain": o.domain,
            "confidence": o.confidence,
            "effective_confidence": o.effective_confidence(),
            "observed_at": o.observed_at.isoformat(),
            "tags": o.tags,
        }
        for o in recent
    ]


async def _instance_search(q: str = "", limit: int = 10):
    if not q:
        return []
    instance = _get_instance()
    results = instance.query(q, limit=limit)
    return [
        {
            "id": str(o.id),
            "content": o.content[:500],
            "domain": o.domain,
            "effective_confidence": o.effective_confidence(),
            "observed_at": o.observed_at.isoformat(),
        }
        for o in results
    ]


async def _instance_domains():
    instance = _get_instance()
    obs_list = instance.all()
    domains: dict[str, int] = {}
    for o in obs_list:
        domains[o.domain] = domains.get(o.domain, 0) + 1
    return [{"domain": d, "observation_count": c} for d, c in sorted(domains.items())]


async def _instance_stats():
    return _get_instance().stats()


async def _reality_timeline(
    domain: str | None = None,
    source: str | None = None,
    limit: int = 50,
    min_confidence: float = 0.0,
):
    instance = _get_instance()
    recent = instance.recent(limit=max(limit, 200))

    observations = []
    domains_seen: set[str] = set()
    sources_seen: set[str] = set()

    for o in recent:
        eff_conf = o.effective_confidence()
        if eff_conf < min_confidence:
            continue

        source_system = ""
        for tag in o.tags:
            if tag.startswith("source:"):
                source_system = tag[7:]
                break

        if domain and o.domain != domain:
            continue
        if source and source_system != source:
            continue

        domains_seen.add(o.domain)
        if source_system:
            sources_seen.add(source_system)

        observations.append({
            "id": str(o.id),
            "content": o.content[:500],
            "domain": o.domain,
            "confidence": o.confidence,
            "effective_confidence": eff_conf,
            "source_system": source_system,
            "observed_at": o.observed_at.isoformat(),
            "tags": o.tags,
            "evidence": {
                k: v for k, v in (o.metadata or {}).items()
                if k not in ("mutation_id", "source_system", "source_id")
            },
        })

        if len(observations) >= limit:
            break

    return {
        "observations": observations,
        "filters": {
            "domains": sorted(domains_seen),
            "sources": sorted(sources_seen),
        },
        "total": len(observations),
    }


async def _canonical_store(request: Request):
    body = await request.json()
    name = body.get("name", "")
    domain = body.get("domain", "")
    description = body.get("description", "")
    if not name or not domain or not description:
        return {"success": False, "error": "name, domain, and description are required"}

    governance_approved = body.get("governance_approved", False)
    if not governance_approved:
        return {
            "success": False,
            "error": "Canonical patterns require governance_approved=true",
        }

    from substrate.reality_model.canonical import CanonicalPattern
    canonical = _get_canonical()
    pattern = CanonicalPattern(
        name=name,
        domain=domain,
        description=description,
        evidence_count=body.get("evidence_count", 1),
        confidence=body.get("confidence", 0.5),
        tags=body.get("tags", []),
        metadata=body.get("metadata", {}),
    )
    pattern_id = canonical.store(pattern)
    return {"success": True, "pattern_id": str(pattern_id), "name": name}


async def _instance_record(request: Request):
    body = await request.json()
    content = body.get("content", "")
    if not content:
        return {"success": False, "error": "content is required"}

    from substrate.reality_model.instance import InstanceObservation
    instance = _get_instance()
    obs = InstanceObservation(
        content=content[:2000],
        domain=body.get("domain", "general"),
        confidence=body.get("confidence", 0.5),
        tags=body.get("tags", []),
        metadata=body.get("metadata", {}),
    )
    obs_id = instance.record(obs)
    return {"success": True, "observation_id": str(obs_id)}


async def _simulate(request: Request):
    body = await request.json()
    hypothesis = body.get("hypothesis", "")
    if not hypothesis:
        return {"success": False, "error": "hypothesis is required"}

    actions = body.get("actions")
    simulation = _get_simulation()
    result = simulation.simulate(hypothesis=hypothesis, actions=actions)
    return {"success": True, "result": result.to_dict()}
