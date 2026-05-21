"""SystemSelector — choose the best system template for a context.

Scores candidate templates using a weighted blend of context similarity,
success rate, average credit, and confidence. Outputs a selection result
with full observability for the trace layer.

Pipeline position:
    SystemRegistry.find_candidates() → select_system() → execute or fallback

Pure scoring. No side effects. No I/O. Deterministic.

Usage::

    from umh.execution.system_selector import select_system

    result = select_system(context_sig, candidates)
    if result.selected_template_id:
        # use template
    else:
        # build new system
"""

from __future__ import annotations

from dataclasses import dataclass


# ─��─ Constants ────────────────────────────────────────────────────

MIN_USAGE_FOR_SELECTION = 2
MIN_CONFIDENCE_FOR_SELECTION = 0.15
MIN_COMPOSITE_SCORE = 0.3

W_MATCH = 0.35
W_SUCCESS = 0.25
W_CREDIT = 0.20
W_CONFIDENCE = 0.20


# ─── Data models ──��──────────────────────────────────────────────


@dataclass(frozen=True)
class SystemSelectionResult:
    """Output from select_system()."""

    selected_template_id: str | None
    match_score: float
    composite_score: float
    used_fallback: bool
    reason: str

    def to_dict(self) -> dict:
        return {
            "selected_template_id": self.selected_template_id,
            "match_score": round(self.match_score, 4),
            "composite_score": round(self.composite_score, 4),
            "used_fallback": self.used_fallback,
            "reason": self.reason,
        }


NO_SELECTION = SystemSelectionResult(
    selected_template_id=None,
    match_score=0.0,
    composite_score=0.0,
    used_fallback=True,
    reason="no_candidates",
)


# ─── Scoring ───────────────────���──────────────────────────────────


def _normalize_credit(avg_credit: float) -> float:
    """Normalize avg_credit from [-1, 1] range to [0, 1] for scoring."""
    return max(0.0, min(1.0, (avg_credit + 1.0) / 2.0))


def _score_candidate(
    match_score: float,
    template: object,
) -> float:
    """Compute composite score for a candidate template."""
    success_rate = getattr(template, "success_rate", 0.0)
    avg_credit = getattr(template, "avg_credit", 0.0)
    confidence = getattr(template, "confidence", 0.0)

    normalized_credit = _normalize_credit(avg_credit)

    composite = (
        W_MATCH * match_score
        + W_SUCCESS * success_rate
        + W_CREDIT * normalized_credit
        + W_CONFIDENCE * confidence
    )
    return max(0.0, min(1.0, composite))


# ─── Selection ────────────���───────────────────────────────────────


def select_system(
    context_signature: dict[str, str],
    candidates: list[tuple[float, object]],
) -> SystemSelectionResult:
    """Select the best system template from candidates.

    Candidates are (match_score, SystemTemplate) tuples from
    SystemRegistry.find_candidates().

    Applies minimum usage, confidence, and composite score thresholds.
    Falls back if no candidate meets all criteria.
    """
    if not candidates:
        return NO_SELECTION

    scored: list[tuple[float, float, object]] = []
    for match_score, template in candidates:
        usage = getattr(template, "usage_count", 0)
        confidence = getattr(template, "confidence", 0.0)

        if usage < MIN_USAGE_FOR_SELECTION:
            continue
        if confidence < MIN_CONFIDENCE_FOR_SELECTION:
            continue

        composite = _score_candidate(match_score, template)
        if composite >= MIN_COMPOSITE_SCORE:
            scored.append((composite, match_score, template))

    if not scored:
        best_match = max(candidates, key=lambda x: x[0])
        return SystemSelectionResult(
            selected_template_id=None,
            match_score=best_match[0],
            composite_score=0.0,
            used_fallback=True,
            reason="no_candidate_meets_thresholds",
        )

    scored.sort(key=lambda x: (-x[0], -x[1]))
    best_composite, best_match_score, best_template = scored[0]
    template_id = getattr(best_template, "template_id", "")

    return SystemSelectionResult(
        selected_template_id=template_id,
        match_score=best_match_score,
        composite_score=best_composite,
        used_fallback=False,
        reason=f"selected:{template_id}",
    )


if __name__ == "__main__":
    print("system_selector import OK")
