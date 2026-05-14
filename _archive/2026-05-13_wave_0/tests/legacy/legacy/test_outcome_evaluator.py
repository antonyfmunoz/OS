"""
Tests for the OutcomeEvaluator — deterministic heuristic scoring.

Validates:
    - Empty/missing output → low score
    - Normal output → mid/high score
    - Length ratio extremes
    - Repetition detection
    - Error signal detection
    - Hallucination risk flags
    - Incomplete output flags
    - Keyword overlap scoring
    - Spine integration (evaluate_outcome callable with spine signatures)
    - Feedback loop accepts evaluation
    - World model uses outcome
"""

import sys
import uuid

sys.path.insert(0, "/opt/OS")

_PASS = 0
_FAIL = 0


def _test(name: str, ok: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
    else:
        _FAIL += 1
    status = "PASS" if ok else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")


def _section(name: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {name}")
    print(f"{'─' * 60}")


from umh.runtime_engine.outcome_evaluator import evaluate_outcome


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Empty output
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. Empty Output")

r = evaluate_outcome("What should I focus on?", "")
_test("empty output → score 0.0", r["quality_score"] == 0.0)
_test("empty output → confidence 1.0", r["confidence"] == 1.0)
_test("empty output → low_information flag", r["flags"]["low_information"] is True)
_test("empty output → incomplete flag", r["flags"]["incomplete"] is True)
_test("empty output → reason", r["reason"] == "empty output")

r2 = evaluate_outcome("hello", "   ")
_test("whitespace-only → score 0.0", r2["quality_score"] == 0.0)

r3 = evaluate_outcome("hello", None)
_test("None output → score 0.0", r3["quality_score"] == 0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Normal output
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Normal Output")

r = evaluate_outcome(
    "What should I focus on today?",
    "Focus on sending 20 DMs to prospects in your ICP. "
    "Prioritize Initiate Arena leads from LinkedIn. "
    "Track reply rates and follow up on any warm responses.",
)
_test(
    "normal output → score > 0.5",
    r["quality_score"] > 0.5,
    f"score={r['quality_score']}",
)
_test("normal output → confidence > 0.3", r["confidence"] > 0.3)
_test("normal output → no low_information", r["flags"]["low_information"] is False)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Length ratio extremes
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Length Ratio")

# Very short output relative to input
r_short = evaluate_outcome(
    "Tell me everything about our pipeline status, all ventures, "
    "what leads we have, reply rates, and conversion funnels",
    "OK.",
)
_test(
    "extremely short output → low score",
    r_short["quality_score"] < 0.5,
    f"score={r_short['quality_score']}",
)

# Reasonable ratio
r_balanced = evaluate_outcome(
    "What is the current stage?",
    "You are currently at Stage 1, validation phase. "
    "Monthly revenue target is $10K. "
    "Focus remains on proving the Initiate Arena offer works.",
)
_test(
    "balanced ratio → decent score",
    r_balanced["quality_score"] > 0.5,
    f"score={r_balanced['quality_score']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Repetition detection
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Repetition Detection")

r_repeat = evaluate_outcome(
    "What should I do?",
    "Send DMs to leads. Send DMs to leads. Send DMs to leads. "
    "Send DMs to leads. Send DMs to leads. Send DMs to leads.",
)
_test(
    "repeated sentences → lower score",
    r_repeat["quality_score"] < 0.6,
    f"score={r_repeat['quality_score']}",
)

r_varied = evaluate_outcome(
    "What should I do?",
    "First, send 20 DMs to prospects. "
    "Then, review your pipeline for warm leads. "
    "After that, prepare follow-up messages for yesterday's outreach. "
    "Finally, update the CRM with today's results.",
)
_test(
    "varied sentences → higher score",
    r_varied["quality_score"] > r_repeat["quality_score"],
    f"varied={r_varied['quality_score']} vs repeat={r_repeat['quality_score']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Error signal detection
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Error Signals")

r_error = evaluate_outcome(
    "What is the pipeline status?",
    "I encountered an error processing your request: connection timeout",
)
_test(
    "error response → very low score",
    r_error["quality_score"] < 0.4,
    f"score={r_error['quality_score']}",
)

r_spine_error = evaluate_outcome(
    "Run analysis",
    "[ExecutionSpine] No response from model chain.",
)
_test(
    "spine error string → low score (error signal detected)",
    r_spine_error["quality_score"] < 0.5,
    f"score={r_spine_error['quality_score']} (spine guards skip this in production)",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Hallucination risk flag
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Hallucination Risk")

r_halluc = evaluate_outcome(
    "How is the market doing?",
    "According to research shows the market grew 45% in Q3. "
    "Revenue reached $2.3M with a 67% conversion rate.",
)
_test(
    "ungrounded stats → hallucination_risk True",
    r_halluc["flags"]["hallucination_risk"] is True,
)

r_grounded = evaluate_outcome(
    "REAL-TIME SEARCH RESULT:\nMarket up 10%\n\nHow is the market?",
    "Based on the search, the market is up 10% this quarter.",
)
_test(
    "grounded response → hallucination_risk False",
    r_grounded["flags"]["hallucination_risk"] is False,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Incomplete output flag
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Incomplete Output")

r_trunc = evaluate_outcome(
    "Give me the full analysis",
    "Here is the beginning of the analysis. The key points are "
    "first, we need to consider the market dynamics. Second...",
)
_test(
    "truncated with ... → incomplete flag",
    r_trunc["flags"]["incomplete"] is True,
)

r_complete = evaluate_outcome(
    "Give me the analysis",
    "The analysis shows three key findings. "
    "First, outreach is working. "
    "Second, conversion needs improvement. "
    "Third, pipeline is healthy.",
)
_test(
    "complete response → incomplete False",
    r_complete["flags"]["incomplete"] is False,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Keyword overlap
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Keyword Overlap")

r_relevant = evaluate_outcome(
    "What are the pipeline conversion rates?",
    "Your pipeline conversion rates are currently at 12%. "
    "The conversion funnel shows strong top-of-funnel activity.",
)

r_irrelevant = evaluate_outcome(
    "What are the pipeline conversion rates?",
    "The weather today is sunny with a high of 72 degrees. "
    "Remember to stay hydrated and wear sunscreen outside.",
)

_test(
    "relevant response scores higher than irrelevant",
    r_relevant["quality_score"] > r_irrelevant["quality_score"],
    f"relevant={r_relevant['quality_score']} vs irrelevant={r_irrelevant['quality_score']}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Return structure
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Return Structure")

r = evaluate_outcome("test", "test response", {"agent_type": "ea"}, {"model": "gemini"})
_test("has quality_score", "quality_score" in r)
_test("has confidence", "confidence" in r)
_test("has flags", "flags" in r)
_test("has reason", "reason" in r)
_test("quality_score is float", isinstance(r["quality_score"], float))
_test("confidence is float", isinstance(r["confidence"], float))
_test("flags is dict", isinstance(r["flags"], dict))
_test("flags has hallucination_risk", "hallucination_risk" in r["flags"])
_test("flags has low_information", "low_information" in r["flags"])
_test("flags has incomplete", "incomplete" in r["flags"])
_test("quality_score in [0, 1]", 0.0 <= r["quality_score"] <= 1.0)
_test("confidence in [0, 1]", 0.0 <= r["confidence"] <= 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Spine integration — evaluate_outcome in spine module
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Spine Integration")

try:
    from umh.runtime_engine.execution_spine import log_feedback, update_world_model
    import inspect

    fb_sig = inspect.signature(log_feedback)
    _test(
        "log_feedback accepts evaluation param",
        "evaluation" in fb_sig.parameters,
    )

    wm_sig = inspect.signature(update_world_model)
    _test(
        "update_world_model accepts evaluation param",
        "evaluation" in wm_sig.parameters,
    )
except Exception as e:
    _test("spine integration imports", False, str(e))

# Verify evaluator is called in spine source
try:
    import inspect as _insp
    from umh.runtime_engine.execution_spine import ExecutionSpine

    spine_src = _insp.getsource(ExecutionSpine.run)
    _test(
        "evaluate_outcome called in spine.run",
        "evaluate_outcome" in spine_src,
    )
    _test(
        "evaluation passed to log_feedback",
        "evaluation=_evaluation" in spine_src,
    )
    _test(
        "evaluation passed to update_world_model",
        "evaluation=_evaluation" in spine_src,
    )
except Exception as e:
    _test("spine source inspection", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Feedback loop accepts evaluation
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Feedback Loop Integration")

try:
    from umh.runtime_engine.feedback_loop import FeedbackLoop
    import inspect

    sig = inspect.signature(FeedbackLoop.log_recommendation)
    _test(
        "FeedbackLoop.log_recommendation has evaluation param",
        "evaluation" in sig.parameters,
    )
except Exception as e:
    _test("feedback_loop integration", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 12. World model uses outcome
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. World Model Integration")

try:
    from umh.world.model import WorldModel

    wm = WorldModel(org_id="test_org")

    wm.update_from_interaction("test good", "great response", outcome="good")
    entries = wm.instance.get_entries()
    good_entry = [e for e in entries if "test good" in e.content]
    _test(
        "good outcome → confidence 0.5",
        good_entry and good_entry[0].confidence == 0.5,
        f"confidence={good_entry[0].confidence if good_entry else 'N/A'}",
    )
    _test(
        "good outcome → tagged in content",
        good_entry and "[outcome=good]" in good_entry[0].content,
    )

    wm.update_from_interaction("test poor", "bad response", outcome="poor")
    entries = wm.instance.get_entries()
    poor_entry = [e for e in entries if "test poor" in e.content]
    _test(
        "poor outcome → confidence 0.15",
        poor_entry and poor_entry[0].confidence == 0.15,
        f"confidence={poor_entry[0].confidence if poor_entry else 'N/A'}",
    )

    wm.update_from_interaction("test default", "default response")
    entries = wm.instance.get_entries()
    default_entry = [e for e in entries if "test default" in e.content]
    _test(
        "no outcome → confidence 0.3",
        default_entry and default_entry[0].confidence == 0.3,
        f"confidence={default_entry[0].confidence if default_entry else 'N/A'}",
    )
except Exception as e:
    _test("world model integration", False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
