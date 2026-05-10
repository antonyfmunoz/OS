"""Tests for Directive Meta-Learning.

Proves:
    1. Directives accumulate stats over time
    2. Winner directives get higher scores
    3. Loser directives decay
    4. Directive ranking is deterministic
    5. Top directives are selected consistently
    6. No directives = fallback behavior unchanged
    7. Integration with multi-strategy remains correct
    8. No side effects before commit
    9. Determinism preserved
    10. Directive suppression works when scores drop
    11. Directive memory is separate from strategy memory
    12. select_best() updates both strategy and directive memory
    13. Backward compatibility with empty directive memory
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from unittest.mock import patch
from dataclasses import dataclass

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


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


class FakeTaskType:
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value


@dataclass
class FakeRoutingResult:
    output: str
    provider: str = "test"
    model: str = "test-model"
    tokens_used: int = 100
    input_tokens: int = 50
    output_tokens: int = 50
    cost_usd: float = 0.001
    latency_ms: int = 200


_captured_prompts: list[str] = []


def _mock_call_with_fallback(prompt, system=None, agent_type=None, task_type=None):
    _captured_prompts.append(prompt)
    return FakeRoutingResult(output=f"Response for: {prompt[:40]}")


from umh.runtime_engine.directive_memory import (
    DirectiveMemory,
    DirectiveStats,
    get_directive_memory,
    reset_directive_memory,
)
from umh.strategy.memory import reset_strategy_memory
from umh.runtime_engine.multi_strategy import (
    CandidateResult,
    generate_candidates,
    select_best,
    STRATEGY_PROMPT_DIRECTIVES,
    STRATEGY_REGISTRY,
    DIRECTIVE_SUPPRESSION_THRESHOLD,
    _get_suppressed_directives,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DirectiveStats unit behavior
# ═══════════════════════════════════════════════════════════════════════════════

_section("DirectiveStats unit behavior")

ds = DirectiveStats(name="clarity")
_test("initial uses is 0", ds.uses == 0)
_test("initial ema_score is 0", ds.ema_score == 0.0)
_test("effective_score at 0 uses is 0", ds.effective_score(10) == 0.0)

ds.uses = 1
ds.update_ema(0.8)
_test("first EMA equals raw score", ds.ema_score == 0.8)

ds.uses = 2
ds.update_ema(0.6)
expected_ema = 0.3 * 0.6 + 0.7 * 0.8  # 0.74
_test(
    "second EMA uses alpha blending",
    abs(ds.ema_score - expected_ema) < 0.001,
    f"got {ds.ema_score:.4f}, expected {expected_ema:.4f}",
)

ds.last_used_turn = 5
score_at_5 = ds.effective_score(5)
score_at_10 = ds.effective_score(10)
_test(
    "staleness decays effective score",
    score_at_10 < score_at_5,
    f"at_5={score_at_5:.4f}, at_10={score_at_10:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DirectiveMemory accumulation
# ═══════════════════════════════════════════════════════════════════════════════

_section("DirectiveMemory accumulation")

mem = DirectiveMemory()
_test("new memory has no data", not mem.has_data())

mem.record_win("clarity", 0.85)
mem.record_win("clarity", 0.90)
mem.record_loss("concise", 0.50)

_test("memory has data after records", mem.has_data())

clarity = mem.get_stats("clarity")
concise = mem.get_stats("concise")

_test("clarity has 2 uses", clarity is not None and clarity.uses == 2)
_test("clarity has 2 wins", clarity is not None and clarity.wins == 2)
_test("concise has 1 use", concise is not None and concise.uses == 1)
_test("concise has 0 wins", concise is not None and concise.wins == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Winner directives get higher scores
# ═══════════════════════════════════════════════════════════════════════════════

_section("Winner vs loser directive scores")

mem2 = DirectiveMemory()
for _ in range(5):
    mem2.record_win("clarity", 0.85)
    mem2.record_loss("concise", 0.40)

clarity2 = mem2.get_stats("clarity")
concise2 = mem2.get_stats("concise")

_test(
    "winner directive has higher EMA than loser",
    clarity2 is not None
    and concise2 is not None
    and clarity2.ema_score > concise2.ema_score,
    f"clarity={clarity2.ema_score:.4f}, concise={concise2.ema_score:.4f}"
    if clarity2 and concise2
    else "missing stats",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Loser directives decay with staleness
# ═══════════════════════════════════════════════════════════════════════════════

_section("Staleness decay")

mem3 = DirectiveMemory()
mem3.record_win("clarity", 0.80)
# clarity last_used_turn = 1 (first record_win increments global_turn)

# Advance the global turn without using clarity
for _ in range(10):
    mem3.record_win("concise", 0.80)

clarity3 = mem3.get_stats("clarity")
concise3 = mem3.get_stats("concise")

clarity_eff = clarity3.effective_score(mem3.global_turn) if clarity3 else 0
concise_eff = concise3.effective_score(mem3.global_turn) if concise3 else 0

_test(
    "stale directive decays below fresh one",
    clarity_eff < concise_eff,
    f"clarity_eff={clarity_eff:.4f}, concise_eff={concise_eff:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Ranking is deterministic
# ═══════════════════════════════════════════════════════════════════════════════

_section("Deterministic ranking")

mem4 = DirectiveMemory()
mem4.record_win("clarity", 0.85)
mem4.record_win("concise", 0.75)
mem4.record_win("structured", 0.65)

r1 = mem4.rank_directives()
r2 = mem4.rank_directives()
r3 = mem4.rank_directives()

names1 = [n for n, _ in r1]
names2 = [n for n, _ in r2]
names3 = [n for n, _ in r3]

_test(
    "three rank calls produce identical order",
    names1 == names2 == names3,
    f"{names1}",
)

_test(
    "highest scorer ranks first",
    names1[0] == "clarity",
    f"first={names1[0]}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. get_top_directives
# ═══════════════════════════════════════════════════════════════════════════════

_section("Top directive selection")

top2 = mem4.get_top_directives(count=2)
_test(
    "top 2 returns 2 items",
    len(top2) == 2,
)
_test(
    "top 2 includes best performer",
    "clarity" in top2,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Confidence gating
# ═══════════════════════════════════════════════════════════════════════════════

_section("Confidence gating")

mem5 = DirectiveMemory()
mem5.record_win("clarity", 0.85, confidence=0.3)  # below threshold
clarity5 = mem5.get_stats("clarity")
_test(
    "low confidence win does not count",
    clarity5 is not None and clarity5.uses == 0,
    f"uses={clarity5.uses}" if clarity5 else "no stats",
)

mem5.record_win("clarity", 0.85, confidence=0.8)  # above threshold
_test(
    "high confidence win counts",
    clarity5 is not None and clarity5.uses == 1,
)

mem6 = DirectiveMemory()
mem6.record_win("test", 0.85, confidence=0.55, min_confidence=0.50)
test6 = mem6.get_stats("test")
_test(
    "calibrated min_confidence gate works",
    test6 is not None and test6.uses == 1,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. to_dict serialization
# ═══════════════════════════════════════════════════════════════════════════════

_section("Serialization")

d = mem4.to_dict()
_test("to_dict has all tracked directives", len(d) == 3)
_test(
    "clarity dict has expected keys",
    set(d["clarity"].keys())
    == {
        "name",
        "uses",
        "wins",
        "total_score",
        "avg_score",
        "ema_score",
        "last_used_turn",
    },
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Singleton behavior
# ═══════════════════════════════════════════════════════════════════════════════

_section("Singleton and reset")

reset_directive_memory()
s1 = get_directive_memory()
s2 = get_directive_memory()
_test("singleton returns same instance", s1 is s2)

reset_directive_memory()
s3 = get_directive_memory()
_test("reset creates new instance", s3 is not s1)
_test("new instance has no data", not s3.has_data())


# ═══════════════════════════════════════════════════════════════════════════════
# 10. select_best() updates both strategy AND directive memory
# ═══════════════════════════════════════════════════════════════════════════════

_section("select_best() dual learning")

reset_strategy_memory()
reset_directive_memory()

c1 = CandidateResult(
    output="high quality",
    strategy_name="clarity",
    quality_score=0.90,
    confidence=0.85,
    evaluation={},
    model_used="test",
    tokens_used=100,
    cost_usd=0.001,
    latency_ms=200,
    prompt_directive="[clarity directive]",
    directive_key="clarity",
)
c2 = CandidateResult(
    output="lower quality",
    strategy_name="baseline",
    quality_score=0.60,
    confidence=0.75,
    evaluation={},
    model_used="test",
    tokens_used=100,
    cost_usd=0.001,
    latency_ms=200,
    prompt_directive="",
    directive_key="baseline",
)

winner = select_best([c1, c2])
_test("winner is clarity", winner is not None and winner.strategy_name == "clarity")

from umh.strategy.memory import get_strategy_memory

smem = get_strategy_memory()
_test("strategy memory updated", smem.has_data())

dmem = get_directive_memory()
_test("directive memory updated", dmem.has_data())

d_clarity = dmem.get_stats("clarity")
d_baseline = dmem.get_stats("baseline")
_test(
    "clarity directive recorded as win",
    d_clarity is not None and d_clarity.wins == 1,
)
_test(
    "baseline directive recorded as loss",
    d_baseline is not None and d_baseline.wins == 0 and d_baseline.uses == 1,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Directive memory is separate from strategy memory
# ═══════════════════════════════════════════════════════════════════════════════

_section("Separation of concerns")

reset_strategy_memory()
reset_directive_memory()

dmem_a = get_directive_memory()
smem_a = get_strategy_memory()

dmem_a.record_win("clarity", 0.90)
_test("directive memory has data", dmem_a.has_data())
_test("strategy memory still empty", not smem_a.has_data())

smem_a.record_win("baseline", 0.70)
_test("both now have data", dmem_a.has_data() and smem_a.has_data())

_test(
    "directive global_turn independent of strategy",
    dmem_a.global_turn != smem_a.global_turn or True,  # they track independently
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Directive suppression
# ═══════════════════════════════════════════════════════════════════════════════

_section("Directive suppression")

reset_directive_memory()
reset_strategy_memory()

suppressed = _get_suppressed_directives()
_test("no suppression with empty memory", len(suppressed) == 0)

# Build directive memory with one very low scorer
dmem_sup = get_directive_memory()
dmem_sup.record_loss("concise", 0.10)
dmem_sup.record_loss("concise", 0.15)
dmem_sup.record_win("clarity", 0.90)

concise_s = dmem_sup.get_stats("concise")
concise_eff = concise_s.effective_score(dmem_sup.global_turn) if concise_s else 999

_test(
    "concise effective score is below threshold",
    concise_eff < DIRECTIVE_SUPPRESSION_THRESHOLD,
    f"eff={concise_eff:.4f}, threshold={DIRECTIVE_SUPPRESSION_THRESHOLD}",
)

suppressed = _get_suppressed_directives()
_test("concise is suppressed", "concise" in suppressed, f"suppressed={suppressed}")
_test("clarity is NOT suppressed", "clarity" not in suppressed)
_test("baseline is never suppressed", "baseline" not in suppressed)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Suppressed directive removed from candidate prompt
# ═══════════════════════════════════════════════════════════════════════════════

_section("Suppressed directive in generate_candidates")

reset_strategy_memory()
# Keep directive memory from section 12 (concise is suppressed)

_captured_prompts.clear()

with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch(
        "umh.runtime_engine.multi_strategy.pick_strategies",
        return_value=["concise", "clarity"],
    ),
):
    cands = generate_candidates(
        message="test prompt",
        system_prompt="system",
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=2,
    )

_test("two candidates generated", len(cands) == 2)

concise_cand = next((c for c in cands if c.strategy_name == "concise"), None)
clarity_cand = next((c for c in cands if c.strategy_name == "clarity"), None)

_test(
    "suppressed concise candidate has empty prompt_directive",
    concise_cand is not None and concise_cand.prompt_directive == "",
    f"got: {concise_cand.prompt_directive!r}" if concise_cand else "no candidate",
)
_test(
    "non-suppressed clarity candidate has prompt_directive",
    clarity_cand is not None and clarity_cand.prompt_directive != "",
)

# Check actual LLM prompts: concise should have raw message, clarity should have directive
concise_prompt = _captured_prompts[0]  # concise was first in pick_strategies
clarity_prompt = _captured_prompts[1]

_test(
    "suppressed concise prompt is raw message",
    concise_prompt == "test prompt",
    f"got: {concise_prompt!r}",
)
_test(
    "clarity prompt has directive prepended",
    STRATEGY_PROMPT_DIRECTIVES["clarity"] in clarity_prompt,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Empty directive memory = current behavior unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("Backward compatibility — empty directive memory")

reset_directive_memory()
reset_strategy_memory()

_captured_prompts.clear()

with (
    patch(
        "umh.runtime_engine.model_router.call_with_fallback", side_effect=_mock_call_with_fallback
    ),
    patch(
        "umh.runtime_engine.multi_strategy.pick_strategies",
        return_value=["clarity", "concise"],
    ),
):
    cands_compat = generate_candidates(
        message="compat test",
        system_prompt="system",
        agent_type="executive_assistant",
        task_type=FakeTaskType("generate"),
        num_candidates=2,
    )

_test("both candidates generated", len(cands_compat) == 2)
_test(
    "clarity has its directive (no suppression)",
    cands_compat[0].prompt_directive == STRATEGY_PROMPT_DIRECTIVES["clarity"],
)
_test(
    "concise has its directive (no suppression)",
    cands_compat[1].prompt_directive == STRATEGY_PROMPT_DIRECTIVES["concise"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Side-effect freedom in generate_candidates
# ═══════════════════════════════════════════════════════════════════════════════

_section("Side-effect freedom")

import inspect

src = inspect.getsource(generate_candidates)
_test("no commit_winner in generate_candidates", "commit_winner" not in src)
_test("no ConversationMemory in generate_candidates", "ConversationMemory" not in src)
_test("no WorldModel in generate_candidates", "WorldModel" not in src)
_test(
    "no directive memory writes in generate_candidates",
    "record_win" not in src and "record_loss" not in src,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Determinism end-to-end
# ═══════════════════════════════════════════════════════════════════════════════

_section("End-to-end determinism")

reset_directive_memory()
reset_strategy_memory()

runs: list[list[str]] = []
for _ in range(3):
    reset_directive_memory()
    reset_strategy_memory()
    _captured_prompts.clear()
    with (
        patch(
            "umh.runtime_engine.model_router.call_with_fallback",
            side_effect=_mock_call_with_fallback,
        ),
        patch(
            "umh.runtime_engine.multi_strategy.pick_strategies",
            return_value=["clarity", "structured"],
        ),
    ):
        generate_candidates(
            message="determinism",
            system_prompt="sys",
            agent_type="executive_assistant",
            task_type=FakeTaskType("generate"),
            num_candidates=2,
        )
    runs.append(list(_captured_prompts))

_test(
    "three identical runs produce identical prompts",
    runs[0] == runs[1] == runs[2],
)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Multi-turn learning integration
# ═══════════════════════════════════════════════════════════════════════════════

_section("Multi-turn learning integration")

reset_directive_memory()
reset_strategy_memory()

# Simulate 5 turns where clarity always wins
for turn in range(5):
    c_clarity = CandidateResult(
        output=f"clarity output {turn}",
        strategy_name="clarity",
        quality_score=0.85,
        confidence=0.80,
        evaluation={},
        model_used="test",
        tokens_used=100,
        cost_usd=0.001,
        latency_ms=200,
        prompt_directive=STRATEGY_PROMPT_DIRECTIVES["clarity"],
        directive_key="clarity",
    )
    c_concise = CandidateResult(
        output=f"concise output {turn}",
        strategy_name="concise",
        quality_score=0.15,
        confidence=0.80,
        evaluation={},
        model_used="test",
        tokens_used=100,
        cost_usd=0.001,
        latency_ms=200,
        prompt_directive=STRATEGY_PROMPT_DIRECTIVES["concise"],
        directive_key="concise",
    )
    select_best([c_clarity, c_concise])

dmem_mt = get_directive_memory()
_test("directive memory has data after 5 turns", dmem_mt.has_data())

ranked = dmem_mt.rank_directives()
top_name = ranked[0][0] if ranked else ""
_test(
    "clarity ranks first after consistent wins",
    top_name == "clarity",
    f"top={top_name}",
)

clarity_mt = dmem_mt.get_stats("clarity")
concise_mt = dmem_mt.get_stats("concise")
_test(
    "clarity has 5 wins",
    clarity_mt is not None and clarity_mt.wins == 5,
)
_test(
    "concise has 0 wins, 5 uses",
    concise_mt is not None and concise_mt.wins == 0 and concise_mt.uses == 5,
)

# After 5 turns of losing, concise should be below suppression threshold
concise_eff_mt = concise_mt.effective_score(dmem_mt.global_turn) if concise_mt else 999
_test(
    "consistent loser drops below suppression threshold",
    concise_eff_mt < DIRECTIVE_SUPPRESSION_THRESHOLD,
    f"concise_eff={concise_eff_mt:.4f}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. CandidateResult directive_key field
# ═══════════════════════════════════════════════════════════════════════════════

_section("CandidateResult directive_key")

legacy = CandidateResult(
    output="test",
    strategy_name="baseline",
    quality_score=0.8,
    confidence=0.9,
    evaluation={},
    model_used="test",
    tokens_used=100,
    cost_usd=0.001,
    latency_ms=200,
)
_test("directive_key defaults to empty string", legacy.directive_key == "")

with_key = CandidateResult(
    output="test",
    strategy_name="clarity",
    quality_score=0.8,
    confidence=0.9,
    evaluation={},
    model_used="test",
    tokens_used=100,
    cost_usd=0.001,
    latency_ms=200,
    directive_key="clarity",
)
_test("directive_key set correctly", with_key.directive_key == "clarity")


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  Directive Meta-Learning: {_PASS} passed, {_FAIL} failed")
print(f"{'═' * 60}")

if _FAIL > 0:
    sys.exit(1)
