"""
Tests for Pattern Engine — success pattern extraction and prompt integration.

Validates:
    - High-confidence good-outcome entries are extracted
    - Low-confidence entries are ignored
    - Entries without outcome=good are ignored
    - Patterns are injected into adaptive prompt
    - No patterns → no modification to prompt
    - Deduplication works
    - Redundancy filter against existing prompt text
    - Deterministic output
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


from dataclasses import asdict

from umh.runtime_engine.pattern_engine import (
    extract_success_patterns,
    filter_redundant_patterns,
)
from umh.world.model import WorldModel


_test_run_id = uuid.uuid4().hex[:8]


def _make_world_model(org_id: str = "test_pattern") -> WorldModel:
    return WorldModel(org_id=f"{org_id}_{_test_run_id}")


def _add_good_entry(
    wm: WorldModel,
    message: str,
    response: str,
    confidence: float = 0.6,
) -> None:
    """Add a good-outcome entry and boost its confidence."""
    wm.update_from_interaction(message, response, outcome="good")
    entries = wm.instance.get_entries()
    for e in entries:
        if "[outcome=good]" in e.content and response[:50] in e.content:
            e.confidence = confidence
            key = wm.instance._key(e.entry_type, e.id)
            wm.instance._store.put(key, asdict(e))
            break


def _add_poor_entry(
    wm: WorldModel,
    message: str,
    response: str,
    confidence: float = 0.6,
) -> None:
    """Add a poor-outcome entry and boost its confidence."""
    wm.update_from_interaction(message, response, outcome="poor")
    entries = wm.instance.get_entries()
    for e in entries:
        if "[outcome=poor]" in e.content and response[:50] in e.content:
            e.confidence = confidence
            key = wm.instance._key(e.entry_type, e.id)
            wm.instance._store.put(key, asdict(e))
            break


# ═══════════════════════════════════════════════════════════════════════════════
# 1. High-confidence good entries are extracted
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. High-Confidence Extraction")

wm = _make_world_model("test_pattern_1")
_add_good_entry(
    wm,
    "What should I focus on today?",
    "Send 20 DMs to prospects in your ICP and track reply rates over 3 days",
    confidence=0.7,
)

patterns = extract_success_patterns(wm)
_test("patterns extracted", len(patterns) > 0, f"got {len(patterns)}")
_test(
    "pattern has actionable trait",
    any("actionable" in p.lower() for p in patterns),
    str(patterns),
)
_test(
    "pattern has measurable trait",
    any("measurable" in p.lower() for p in patterns),
    str(patterns),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Low-confidence entries are ignored
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Low-Confidence Ignored")

wm2 = _make_world_model("test_pattern_2")
_add_good_entry(
    wm2,
    "What should I do?",
    "Send 10 emails to warm leads and schedule follow-up calls",
    confidence=0.2,
)

patterns2 = extract_success_patterns(wm2, confidence_threshold=0.5)
_test("low confidence → no patterns", len(patterns2) == 0, f"got {len(patterns2)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Poor-outcome entries are ignored
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Poor-Outcome Ignored")

wm3 = _make_world_model("test_pattern_3")
_add_poor_entry(
    wm3,
    "What should I do?",
    "Just keep doing what you're doing and hope for the best results eventually",
    confidence=0.8,
)

patterns3 = extract_success_patterns(wm3)
_test("poor outcome → no patterns", len(patterns3) == 0, f"got {len(patterns3)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Patterns injected into adaptive prompt
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Prompt Integration")

from umh.runtime_engine.adaptive_prompt import adapt_prompt

wm4 = _make_world_model("test_pattern_4")
_add_good_entry(
    wm4,
    "What's my next step?",
    "Send 15 personalized DMs to fitness coaches and track open rates daily",
    confidence=0.7,
)

base = "You are a helpful business assistant."
result = adapt_prompt(base, world_model=wm4)
_test("prompt modified with patterns", result != base, f"len={len(result)}")
_test(
    "high-performing header present",
    "high-performing response patterns" in result.lower(),
    result[:300],
)
_test("original prompt preserved", base in result)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. No patterns → no modification
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. No Patterns → Unchanged")

wm5 = _make_world_model("test_pattern_5")
result5 = adapt_prompt(base, world_model=wm5)
_test("empty world model → unchanged", result5 == base)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Deduplication
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Deduplication")

wm6 = _make_world_model("test_pattern_6")
_add_good_entry(
    wm6,
    "Focus?",
    "Send 20 DMs to prospects and track reply rates for 5 days",
    confidence=0.8,
)
_add_good_entry(
    wm6,
    "Priority?",
    "Send 25 DMs to leads and track conversion rates for 7 days",
    confidence=0.75,
)

patterns6 = extract_success_patterns(wm6)
_test(
    "similar patterns deduplicated",
    len(patterns6) <= 2,
    f"got {len(patterns6)}: {patterns6}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Redundancy filter
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Redundancy Filter")

test_patterns = ["direct actionable guidance", "specific measurable targets"]
prompt_with_overlap = "always give direct actionable guidance to the user"

filtered = filter_redundant_patterns(test_patterns, prompt_with_overlap)
_test(
    "overlapping pattern removed",
    "direct actionable guidance" not in filtered,
    str(filtered),
)
_test(
    "non-overlapping pattern kept",
    "specific measurable targets" in filtered,
    str(filtered),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Deterministic output
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Determinism")

wm8 = _make_world_model("test_pattern_8")
_add_good_entry(
    wm8,
    "What now?",
    "Focus on sending 30 cold DMs per day and track response rates weekly",
    confidence=0.7,
)

r1 = extract_success_patterns(wm8)
r2 = extract_success_patterns(wm8)
_test("same inputs → same output", r1 == r2, f"{r1} vs {r2}")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Limit parameter respected
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Limit Respected")

wm9 = _make_world_model("test_pattern_9")
for i in range(10):
    _add_good_entry(
        wm9,
        f"Question {i}?",
        f"Unique response {i}: schedule {i + 1} calls and create {i + 2} proposals and write {i + 3} follow-ups daily",
        confidence=0.7 + (i * 0.01),
    )

patterns9 = extract_success_patterns(wm9, limit=3)
_test("limit=3 respected", len(patterns9) <= 3, f"got {len(patterns9)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Mixed entries — only good extracted
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Mixed Entries")

wm10 = _make_world_model("test_pattern_10")
_add_good_entry(
    wm10,
    "Next step?",
    "Book 5 discovery calls this week and prepare tailored pitch decks for each prospect",
    confidence=0.7,
)
_add_poor_entry(
    wm10,
    "What about content?",
    "Just post random stuff on social media whenever you feel like it and see what sticks",
    confidence=0.8,
)
wm10.update_from_interaction(
    "How's the weather?",
    "It's sunny today, perfect for outdoor activities",
)

patterns10 = extract_success_patterns(wm10)
_test(
    "only good patterns extracted",
    len(patterns10) >= 1,
    f"got {len(patterns10)}",
)
_test(
    "no poor-outcome content leaks",
    not any("random" in p.lower() for p in patterns10),
    str(patterns10),
)


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

sys.exit(1 if _FAIL > 0 else 0)
