"""Phase 85 deliberation engine — orchestrate a full council deliberation.

Wires together request validation, perspective collection, evidence
assessment, gap detection, disagreement mapping, scoring, aggregation,
ontology bridge, and advisory generation. Deterministic v1.

No execution (aside from internal council logic). No adapter calls. No LLM calls.
"""

from __future__ import annotations

from typing import Any

from umh.council.advisory import CouncilAdvisory, build_council_advisory
from umh.council.aggregation import aggregate_perspectives
from umh.council.contracts import CouncilStatus
from umh.council.disagreement import map_disagreements
from umh.council.evidence import assess_evidence
from umh.council.gaps import detect_gaps
from umh.council.ontology_bridge import OntologyContext, resolve_ontology_context
from umh.council.perspective import PerspectiveReport
from umh.council.request import DeliberationRequest, validate_deliberation_request
from umh.council.roles import CouncilRole, get_default_council_roles
from umh.council.scoring import score_perspectives


def deliberate(
    request: DeliberationRequest,
    perspectives: list[PerspectiveReport],
    *,
    roles: list[CouncilRole] | None = None,
    include_ontology: bool = True,
) -> CouncilAdvisory:
    if roles is None:
        roles = get_default_council_roles()

    req_issues = validate_deliberation_request(request)
    if any("Missing question" in i for i in req_issues):
        return CouncilAdvisory(
            advisory_id="",
            request_id=request.request_id,
            status=CouncilStatus.REJECTED,
            warnings=req_issues,
        )

    request.status = CouncilStatus.CONVENED

    evidence_assessment = assess_evidence(request.request_id, perspectives)
    gap_analysis = detect_gaps(request, roles, perspectives)
    disagreement_map = map_disagreements(request.request_id, perspectives)
    scoring_result = score_perspectives(request.request_id, perspectives, roles)

    ontology_ctx: OntologyContext | None = None
    if include_ontology and (request.relevant_laws or request.relevant_polarities):
        ontology_ctx = resolve_ontology_context(
            request.request_id,
            relevant_laws=request.relevant_laws,
            relevant_polarities=request.relevant_polarities,
        )

    recommendation = aggregate_perspectives(
        request.request_id,
        perspectives,
        scoring_result,
        evidence_assessment,
        gap_analysis,
        disagreement_map,
    )

    advisory = build_council_advisory(
        request.request_id,
        recommendation,
        scoring_result,
        evidence_assessment,
        gap_analysis,
        disagreement_map,
        perspective_count=len(perspectives),
    )

    if ontology_ctx:
        advisory.metadata["ontology_context"] = ontology_ctx.to_dict()

    return advisory
