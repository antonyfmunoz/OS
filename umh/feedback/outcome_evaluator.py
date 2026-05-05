"""
OutcomeEvaluator — lightweight, deterministic quality scoring for LLM responses.

Runs after quality verification and stage filtering, before feedback logging.
No LLM calls. Pure heuristics. Produces structured signals that feed into
feedback_loop and world_model for future learning.

Usage::

    from umh.feedback.outcome_evaluator import evaluate_outcome

    evaluation = evaluate_outcome(
        input_text="What should I focus on today?",
        output_text="Focus on sending 20 DMs to ...",
        context={"agent_type": "executive_assistant", "venture_id": "lyfe_institute"},
        metadata={"model_used": "gemini/gemini-2.5-flash", "iterations": 1},
    )
    # evaluation["quality_score"]  -> 0.72
    # evaluation["flags"]          -> {"hallucination_risk": False, ...}
"""

import re


def evaluate_outcome(
    input_text: str,
    output_text: str,
    context: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    """Score a response using cheap deterministic heuristics.

    Returns::

        {
            "quality_score": float,    # 0.0–1.0
            "confidence": float,       # how confident the evaluator is in its score
            "flags": {
                "hallucination_risk": bool,
                "low_information": bool,
                "incomplete": bool,
            },
            "reason": str,
        }
    """
    context = context or {}
    metadata = metadata or {}

    if not output_text or not output_text.strip():
        return {
            "quality_score": 0.0,
            "confidence": 1.0,
            "flags": {
                "hallucination_risk": False,
                "low_information": True,
                "incomplete": True,
            },
            "reason": "empty output",
        }

    scores: list[tuple[float, float, str]] = []  # (score, weight, label)

    # ── 1. Length ratio ──────────────────────────────────────────────────────
    input_len = max(len(input_text.split()), 1)
    output_len = len(output_text.split())
    ratio = output_len / input_len

    if output_len < 5:
        scores.append((0.1, 2.0, "extremely short output"))
    elif ratio < 0.3:
        scores.append((0.3, 1.5, "output much shorter than input"))
    elif ratio > 50:
        scores.append((0.5, 1.0, "output disproportionately long"))
    else:
        scores.append((0.8, 1.0, "reasonable length ratio"))

    # ── 2. Repetition detection ──────────────────────────────────────────────
    sentences = [s.strip() for s in re.split(r"[.!?]+", output_text) if s.strip()]
    if len(sentences) >= 3:
        unique = set(s.lower() for s in sentences)
        repetition_ratio = 1.0 - (len(unique) / len(sentences))
        if repetition_ratio > 0.5:
            scores.append((0.2, 2.0, "high repetition"))
        elif repetition_ratio > 0.25:
            scores.append((0.5, 1.0, "moderate repetition"))
        else:
            scores.append((0.9, 0.8, "low repetition"))

    # ── 3. Error / apology detection ─────────────────────────────────────────
    output_lower = output_text[:500].lower()
    error_signals = [
        "i encountered an error",
        "i'm unable to",
        "i cannot",
        "i don't have access",
        "something went wrong",
        "[executionspine]",
        "system configuration error",
    ]
    has_error = any(sig in output_lower for sig in error_signals)
    if has_error:
        scores.append((0.1, 3.0, "error/inability signal"))

    # ── 4. Keyword overlap (basic relevance) ─────────────────────────────────
    input_words = set(input_text.lower().split()) - _STOP_WORDS
    output_words = set(output_text[:1000].lower().split()) - _STOP_WORDS
    if input_words:
        overlap = len(input_words & output_words) / len(input_words)
        if overlap < 0.1:
            scores.append((0.4, 1.5, "low keyword overlap"))
        elif overlap > 0.3:
            scores.append((0.85, 0.8, "good keyword overlap"))
        else:
            scores.append((0.65, 0.8, "moderate keyword overlap"))

    # ── 5. Completeness heuristic ────────────────────────────────────────────
    truncation_signals = [
        output_text.rstrip().endswith("..."),
        output_text.rstrip().endswith("etc"),
        re.search(r"\b(to be continued|more later|will follow up)\b", output_lower),
    ]
    incomplete = any(truncation_signals)
    if incomplete:
        scores.append((0.5, 1.0, "appears incomplete"))

    # ── Aggregate ────────────────────────────────────────────────────────────
    if not scores:
        return {
            "quality_score": 0.5,
            "confidence": 0.3,
            "flags": _default_flags(),
            "reason": "insufficient signals",
        }

    total_weight = sum(w for _, w, _ in scores)
    weighted_sum = sum(s * w for s, w, _ in scores)
    quality_score = round(weighted_sum / total_weight, 3)

    # Confidence is higher when more signals agree
    signal_variance = _variance([s for s, _, _ in scores])
    confidence = round(max(0.3, 1.0 - signal_variance * 2), 3)

    # ── Build flags ──────────────────────────────────────────────────────────
    flags = {
        "hallucination_risk": _detect_hallucination_risk(
            input_text, output_text, context
        ),
        "low_information": output_len < 10 or quality_score < 0.3,
        "incomplete": incomplete,
    }

    # Primary reason = lowest-scoring signal
    worst = min(scores, key=lambda x: x[0])
    reason = worst[2] if quality_score < 0.7 else "acceptable"

    result = {
        "quality_score": quality_score,
        "confidence": confidence,
        "flags": flags,
        "reason": reason,
    }

    try:
        from umh.signal.router import route_signals

        attributed = route_signals(result)
        result["signals"] = attributed.to_dict()
    except Exception:
        pass

    return result


def _detect_hallucination_risk(
    input_text: str,
    output_text: str,
    context: dict,
) -> bool:
    """Flag responses that claim specific facts without grounding."""
    output_lower = output_text[:1000].lower()

    specificity_signals = [
        re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", output_text),
        re.search(r"\$\d+[\d,]*", output_text),
        re.search(r"\b\d+%\b", output_text),
        re.search(r"(?:according to|research shows|studies show)", output_lower),
    ]
    specificity_count = sum(1 for s in specificity_signals if s)

    grounding_signals = [
        "real-time search result" in input_text.lower(),
        "portfolio data" in input_text.lower(),
        context.get("has_web_search", False),
    ]
    has_grounding = any(grounding_signals)

    return specificity_count >= 2 and not has_grounding


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def _default_flags() -> dict:
    return {
        "hallucination_risk": False,
        "low_information": False,
        "incomplete": False,
    }


_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "it",
        "to",
        "of",
        "in",
        "for",
        "on",
        "and",
        "or",
        "but",
        "not",
        "with",
        "this",
        "that",
        "be",
        "are",
        "was",
        "were",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "can",
        "may",
        "at",
        "by",
        "from",
        "as",
        "i",
        "my",
        "me",
        "we",
        "you",
        "your",
        "he",
        "she",
        "they",
        "what",
        "how",
        "when",
        "where",
        "who",
        "which",
        "if",
        "then",
        "so",
        "no",
        "yes",
    }
)
