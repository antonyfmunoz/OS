"""North Star template candidate detection.

Identifies repeatable patterns from workflow results that could become
templates, checklists, scripts, or SOPs. Does not build the Template
System — only identifies candidates.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from typing import Any

from umh.workflows.contracts import WorkflowResult, WorkflowTrack


_BUSINESS_CANDIDATE_TYPES = [
    "content_prompt",
    "dm_script",
    "qualification_checklist",
    "objection_response",
    "daily_review_template",
    "onboarding_source_checklist",
]

_SELF_BUILD_CANDIDATE_TYPES = [
    "phase_prompt_template",
    "test_checklist",
    "safety_checklist",
    "report_template",
    "build_sequence_template",
]


def identify_template_candidates_from_business_result(
    result: WorkflowResult,
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    if len(result.completed_tasks) >= 3:
        candidates.append({
            "type": "daily_review_template",
            "reason": "Enough tasks completed to standardize a daily checklist",
        })
    if result.objections:
        candidates.append({
            "type": "objection_response",
            "reason": f"{len(result.objections)} objections captured — build response scripts",
        })
    if any("content" in t.lower() or "post" in t.lower() for t in result.completed_tasks):
        candidates.append({
            "type": "content_prompt",
            "reason": "Content tasks completed — templatize the content angle selection",
        })
    if any("dm" in t.lower() or "conversation" in t.lower() for t in result.completed_tasks):
        candidates.append({
            "type": "dm_script",
            "reason": "DM/conversation tasks completed — templatize opening scripts",
        })
    if any("qualif" in t.lower() or "lead" in t.lower() for t in result.completed_tasks):
        candidates.append({
            "type": "qualification_checklist",
            "reason": "Qualification tasks completed — templatize qualification criteria",
        })
    if not candidates:
        candidates.append({
            "type": "daily_review_template",
            "reason": "Default candidate — every run should produce a review template",
        })
    return candidates


def identify_template_candidates_from_self_build_result(
    result: WorkflowResult,
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    if len(result.completed_tasks) >= 3:
        candidates.append({
            "type": "build_sequence_template",
            "reason": "Enough steps completed to standardize a build sequence",
        })
    if any("test" in t.lower() for t in result.completed_tasks):
        candidates.append({
            "type": "test_checklist",
            "reason": "Testing tasks completed — templatize test checklist",
        })
    if any("safety" in t.lower() for t in result.completed_tasks):
        candidates.append({
            "type": "safety_checklist",
            "reason": "Safety tasks completed — templatize safety scan process",
        })
    if any("report" in t.lower() for t in result.completed_tasks):
        candidates.append({
            "type": "report_template",
            "reason": "Report tasks completed — templatize phase report structure",
        })
    if any("phase" in t.lower() or "plan" in t.lower() for t in result.completed_tasks):
        candidates.append({
            "type": "phase_prompt_template",
            "reason": "Phase selection completed — templatize phase prompt",
        })
    if not candidates:
        candidates.append({
            "type": "build_sequence_template",
            "reason": "Default candidate — every build cycle should produce a sequence template",
        })
    return candidates


def classify_template_candidate(candidate: dict[str, str]) -> str:
    ctype = candidate.get("type", "unknown")
    if ctype in _BUSINESS_CANDIDATE_TYPES:
        return "business"
    if ctype in _SELF_BUILD_CANDIDATE_TYPES:
        return "self_build"
    return "unknown"


def build_template_candidate_summary(
    candidates: list[dict[str, str]],
) -> dict[str, Any]:
    business = [c for c in candidates if classify_template_candidate(c) == "business"]
    self_build = [c for c in candidates if classify_template_candidate(c) == "self_build"]
    unknown = [c for c in candidates if classify_template_candidate(c) == "unknown"]
    return {
        "total": len(candidates),
        "business_count": len(business),
        "self_build_count": len(self_build),
        "unknown_count": len(unknown),
        "types": list({c.get("type", "unknown") for c in candidates}),
        "candidates": candidates,
    }
