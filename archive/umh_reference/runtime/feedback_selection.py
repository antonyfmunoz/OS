"""Controlled feedback selection integration — bounded, opt-in ranking adjustment.

Applies feedback-informed ranking to candidates without destabilizing
base scoring. Opt-in only — disabled by default. Returns original ranking
unless explicitly enabled with sufficient confidence.

Correlation-based, not causal. Observational feedback only.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FeedbackSelectionPolicy:
    """Policy controlling feedback-to-selection integration."""

    enabled: bool = False
    min_confidence: float = 0.6
    max_adjustment: float = 0.12
    preserve_top_margin: float = 0.15
    require_valid_candidate: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_confidence", max(0.0, min(1.0, self.min_confidence)))
        object.__setattr__(self, "max_adjustment", max(0.0, min(0.30, self.max_adjustment)))
        object.__setattr__(
            self, "preserve_top_margin", max(0.0, min(1.0, self.preserve_top_margin))
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "min_confidence": round(self.min_confidence, 4),
            "max_adjustment": round(self.max_adjustment, 4),
            "preserve_top_margin": round(self.preserve_top_margin, 4),
            "require_valid_candidate": self.require_valid_candidate,
        }


@dataclass(frozen=True)
class FeedbackAdjustedCandidate:
    """A candidate with base and feedback-adjusted scores."""

    candidate_id: str = ""
    base_score: float = 0.0
    feedback_factor: float = 1.0
    adjusted_score: float = 0.0
    confidence: float = 0.0
    valid: bool = True
    reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_score", max(0.0, min(2.0, self.base_score)))
        object.__setattr__(self, "feedback_factor", max(0.0, min(2.0, self.feedback_factor)))
        object.__setattr__(self, "adjusted_score", max(0.0, min(2.0, self.adjusted_score)))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "base_score": round(self.base_score, 4),
            "feedback_factor": round(self.feedback_factor, 4),
            "adjusted_score": round(self.adjusted_score, 4),
            "confidence": round(self.confidence, 4),
            "valid": self.valid,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class FeedbackSelectionResult:
    """Result of feedback-integrated selection."""

    selected_candidate: str = ""
    adjusted_candidates: tuple[FeedbackAdjustedCandidate, ...] = ()
    policy_enabled: bool = False
    explanation: str = ""
    changed_selection: bool = False
    original_best: str = ""
    adjusted_best: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_candidate": self.selected_candidate,
            "adjusted_candidates": [c.to_dict() for c in self.adjusted_candidates],
            "policy_enabled": self.policy_enabled,
            "explanation": self.explanation,
            "changed_selection": self.changed_selection,
            "original_best": self.original_best,
            "adjusted_best": self.adjusted_best,
        }


def _clamp_factor(
    factor: float,
    max_adjustment: float,
) -> float:
    lo = 1.0 - max_adjustment
    hi = 1.0 + max_adjustment
    return max(lo, min(hi, factor))


def _find_base_best(
    candidates: list[str],
    base_scores: list[float],
    valid_mask: list[bool],
) -> int:
    best_idx = -1
    best_score = -1.0
    for i, cid in enumerate(candidates):
        if not valid_mask[i]:
            continue
        if base_scores[i] > best_score or (
            base_scores[i] == best_score and (best_idx == -1 or cid < candidates[best_idx])
        ):
            best_score = base_scores[i]
            best_idx = i
    return best_idx


def _find_adjusted_best(
    adjusted: list[FeedbackAdjustedCandidate],
    valid_mask: list[bool],
) -> int:
    best_idx = -1
    best_score = -1.0
    for i, ac in enumerate(adjusted):
        if not valid_mask[i]:
            continue
        if ac.adjusted_score > best_score or (
            ac.adjusted_score == best_score
            and (best_idx == -1 or ac.candidate_id < adjusted[best_idx].candidate_id)
        ):
            best_score = ac.adjusted_score
            best_idx = i
    return best_idx


def select_with_feedback(
    candidates: list[str],
    base_scores: list[float],
    feedback_factors: list[float] | None = None,
    confidences: list[float] | None = None,
    policy: FeedbackSelectionPolicy | None = None,
    valid_flags: list[bool] | None = None,
    safe_flags: list[bool] | None = None,
) -> FeedbackSelectionResult:
    """Select best candidate with optional feedback adjustment.

    When policy is disabled or missing, returns the base-score winner.
    When enabled, applies bounded feedback factors gated by confidence,
    then checks preserve_top_margin before allowing reordering.
    """
    p = policy or FeedbackSelectionPolicy()

    if not candidates:
        return FeedbackSelectionResult(
            selected_candidate="",
            adjusted_candidates=(),
            policy_enabled=p.enabled,
            explanation="no candidates provided",
            changed_selection=False,
            original_best="",
            adjusted_best="",
        )

    n = len(candidates)

    if len(base_scores) < n:
        base_scores = list(base_scores) + [0.0] * (n - len(base_scores))
    elif len(base_scores) > n:
        base_scores = base_scores[:n]

    if feedback_factors is None:
        feedback_factors = [1.0] * n
    elif len(feedback_factors) < n:
        feedback_factors = list(feedback_factors) + [1.0] * (n - len(feedback_factors))
    elif len(feedback_factors) > n:
        feedback_factors = feedback_factors[:n]

    if confidences is None:
        confidences = [0.0] * n
    elif len(confidences) < n:
        confidences = list(confidences) + [0.0] * (n - len(confidences))
    elif len(confidences) > n:
        confidences = confidences[:n]

    if valid_flags is None:
        valid_flags = [True] * n
    elif len(valid_flags) < n:
        valid_flags = list(valid_flags) + [True] * (n - len(valid_flags))
    elif len(valid_flags) > n:
        valid_flags = valid_flags[:n]

    if safe_flags is None:
        safe_flags = [True] * n
    elif len(safe_flags) < n:
        safe_flags = list(safe_flags) + [True] * (n - len(safe_flags))
    elif len(safe_flags) > n:
        safe_flags = safe_flags[:n]

    effective_valid = [(valid_flags[i] and safe_flags[i]) for i in range(n)]

    if p.require_valid_candidate and not any(effective_valid):
        return FeedbackSelectionResult(
            selected_candidate="",
            adjusted_candidates=(),
            policy_enabled=p.enabled,
            explanation="all candidates invalid or unsafe",
            changed_selection=False,
            original_best="",
            adjusted_best="",
        )

    base_best_idx = _find_base_best(candidates, base_scores, effective_valid)

    if base_best_idx == -1:
        return FeedbackSelectionResult(
            selected_candidate="",
            adjusted_candidates=(),
            policy_enabled=p.enabled,
            explanation="no valid candidates found",
            changed_selection=False,
            original_best="",
            adjusted_best="",
        )

    adjusted_candidates: list[FeedbackAdjustedCandidate] = []
    for i in range(n):
        cid = candidates[i]
        bs = base_scores[i]
        ff = feedback_factors[i]
        conf = confidences[i]
        v = effective_valid[i]

        if not p.enabled:
            adj_score = bs
            reason = "feedback selection disabled"
            eff_factor = 1.0
        elif conf < p.min_confidence:
            adj_score = bs
            reason = f"confidence {conf:.2f} below threshold {p.min_confidence:.2f}"
            eff_factor = 1.0
        else:
            eff_factor = _clamp_factor(ff, p.max_adjustment)
            adj_score = bs * eff_factor
            if eff_factor > 1.0:
                reason = f"boosted: factor={eff_factor:.4f}, confidence={conf:.2f}"
            elif eff_factor < 1.0:
                reason = f"penalized: factor={eff_factor:.4f}, confidence={conf:.2f}"
            else:
                reason = f"neutral: factor={eff_factor:.4f}, confidence={conf:.2f}"

        adjusted_candidates.append(
            FeedbackAdjustedCandidate(
                candidate_id=cid,
                base_score=bs,
                feedback_factor=eff_factor,
                adjusted_score=adj_score,
                confidence=conf,
                valid=v,
                reason=reason,
            )
        )

    adj_best_idx = _find_adjusted_best(adjusted_candidates, effective_valid)

    if adj_best_idx == -1:
        adj_best_idx = base_best_idx

    original_best = candidates[base_best_idx]
    adjusted_best = candidates[adj_best_idx]

    if not p.enabled:
        selected = original_best
        changed = False
        explanation = (
            f"feedback selection disabled; "
            f"selected '{original_best}' (base_score={base_scores[base_best_idx]:.4f})"
        )
    elif adj_best_idx == base_best_idx:
        selected = original_best
        changed = False
        explanation = (
            f"feedback applied but selection unchanged; "
            f"'{original_best}' remains best "
            f"(base={base_scores[base_best_idx]:.4f}, "
            f"adjusted={adjusted_candidates[adj_best_idx].adjusted_score:.4f})"
        )
    else:
        base_top_score = base_scores[base_best_idx]
        adj_challenger_score = adjusted_candidates[adj_best_idx].adjusted_score

        margin = base_top_score - adj_challenger_score
        if margin >= p.preserve_top_margin:
            selected = original_best
            changed = False
            explanation = (
                f"feedback adjusted '{adjusted_best}' as best "
                f"(adj={adj_challenger_score:.4f}), but base leader "
                f"'{original_best}' (base={base_top_score:.4f}) "
                f"exceeds by margin {margin:.4f} >= "
                f"preserve_top_margin {p.preserve_top_margin:.4f}; "
                f"keeping base leader"
            )
        else:
            selected = adjusted_best
            changed = True
            explanation = (
                f"feedback changed selection from '{original_best}' "
                f"(base={base_top_score:.4f}) to '{adjusted_best}' "
                f"(adjusted={adj_challenger_score:.4f}); "
                f"margin {margin:.4f} < "
                f"preserve_top_margin {p.preserve_top_margin:.4f}"
            )

    return FeedbackSelectionResult(
        selected_candidate=selected,
        adjusted_candidates=tuple(adjusted_candidates),
        policy_enabled=p.enabled,
        explanation=explanation,
        changed_selection=changed,
        original_best=original_best,
        adjusted_best=adjusted_best,
    )
