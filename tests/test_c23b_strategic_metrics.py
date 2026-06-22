"""Campaign 23B — Strategic Metrics test suite.

Covers Category T (Model Correspondence), Category O (Strategic Compression),
and Category S (Human Amplification).
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

import pytest

from substrate.organism.audits.model_correspondence import (
    CORRESPONDENCE_DOMAINS,
    CorrespondenceDimension,
    ModelCorrespondenceAudit,
    ModelCorrespondenceReport,
    PredictionRecord,
    score_match,
)
from substrate.organism.benchmarks.human_amplification import (
    AmplificationRecord,
    AmplificationResult,
    HumanAmplificationBenchmark,
    SkillLevel,
    TaskComplexity,
)
from substrate.organism.benchmarks.strategic_compression import (
    IntentRecord,
    StrategicCompressionBenchmark,
    StrategicCompressionResult,
)


# ===========================================================================
# Category T — Model Correspondence
# ===========================================================================

def test_correspondence_domains_constant():
    assert CORRESPONDENCE_DOMAINS == ["runtime", "project", "capability", "timeline", "risk"]


def test_score_match_exact_case_insensitive():
    assert score_match("Running", "running") == 1.0
    assert score_match("RUNNING", "running") == 1.0


def test_score_match_substring():
    assert score_match("running", "service running ok") == 0.7
    assert score_match("service running ok", "running") == 0.7


def test_score_match_no_match():
    assert score_match("running", "stopped") == 0.0


def test_score_match_empty():
    assert score_match("", "running") == 0.0
    assert score_match("running", "") == 0.0
    assert score_match("", "") == 0.0


def test_prediction_resolved_score_uses_preset():
    rec = PredictionRecord(domain="runtime", predicted_state="x", observed_state="y", match_score=0.42)
    assert rec.resolved_score() == 0.42


def test_prediction_resolved_score_computes_when_unset():
    rec = PredictionRecord(domain="runtime", predicted_state="up", observed_state="up")
    assert rec.resolved_score() == 1.0


def test_prediction_to_dict():
    rec = PredictionRecord(prediction_id="p1", domain="runtime", match_score=0.5)
    d = rec.to_dict()
    assert d["prediction_id"] == "p1"
    assert d["domain"] == "runtime"
    assert d["match_score"] == 0.5
    assert d["metadata"] == {}


def _five_predictions_three_domains() -> list[PredictionRecord]:
    return [
        # runtime: two exact -> accuracy 1.0
        PredictionRecord(prediction_id="r1", domain="runtime", predicted_state="up", observed_state="up"),
        PredictionRecord(prediction_id="r2", domain="runtime", predicted_state="up", observed_state="up"),
        # project: one substring (0.7), one no-match (0.0) -> accuracy 0.35
        PredictionRecord(prediction_id="p1", domain="project", predicted_state="phase23", observed_state="phase23 active"),
        PredictionRecord(prediction_id="p2", domain="project", predicted_state="done", observed_state="blocked"),
        # capability: one exact -> accuracy 1.0
        PredictionRecord(prediction_id="c1", domain="capability", predicted_state="ready", observed_state="ready"),
    ]


def test_correspondence_per_domain_accuracy():
    report = ModelCorrespondenceAudit().run(_five_predictions_three_domains())
    by_domain = {d.domain: d for d in report.dimensions}

    assert by_domain["runtime"].predictions_evaluated == 2
    assert by_domain["runtime"].accuracy == 1.0
    assert by_domain["runtime"].best_hit == 1.0
    assert by_domain["runtime"].worst_miss == 1.0

    assert by_domain["project"].predictions_evaluated == 2
    assert by_domain["project"].accuracy == 0.35
    assert by_domain["project"].best_hit == 0.7
    assert by_domain["project"].worst_miss == 0.0
    assert by_domain["project"].mean_error == round(1.0 - 0.35, 4)

    assert by_domain["capability"].accuracy == 1.0


def test_correspondence_overall_accuracy_weighted():
    report = ModelCorrespondenceAudit().run(_five_predictions_three_domains())
    # scores: 1.0, 1.0, 0.7, 0.0, 1.0 -> 3.7 / 5 = 0.74
    assert report.total_predictions == 5
    assert report.overall_accuracy == 0.74


def test_correspondence_best_worst_domain():
    report = ModelCorrespondenceAudit().run(_five_predictions_three_domains())
    assert report.worst_domain == "project"
    # best is a tie between runtime and capability; either is acceptable at 1.0
    assert report.best_domain in {"runtime", "capability"}


def test_correspondence_drift_detected():
    preds = [
        PredictionRecord(domain="risk", predicted_state="low", observed_state="critical"),
        PredictionRecord(domain="risk", predicted_state="low", observed_state="high"),
    ]
    report = ModelCorrespondenceAudit().run(preds)
    assert report.drift_detected is True


def test_correspondence_no_drift_when_above_threshold():
    preds = [
        PredictionRecord(domain="runtime", predicted_state="up", observed_state="up"),
        PredictionRecord(domain="timeline", predicted_state="ontrack", observed_state="ontrack"),
    ]
    report = ModelCorrespondenceAudit().run(preds)
    assert report.drift_detected is False


def test_correspondence_auto_scoring_mix():
    preds = [
        PredictionRecord(domain="runtime", predicted_state="up", observed_state="up"),  # 1.0 auto
        PredictionRecord(domain="runtime", match_score=0.9),  # preset
    ]
    report = ModelCorrespondenceAudit().run(preds)
    by_domain = {d.domain: d for d in report.dimensions}
    assert by_domain["runtime"].accuracy == round((1.0 + 0.9) / 2, 4)


def test_correspondence_empty():
    report = ModelCorrespondenceAudit().run([])
    assert isinstance(report, ModelCorrespondenceReport)
    assert report.total_predictions == 0
    assert report.overall_accuracy == 0.0
    assert report.dimensions == []
    assert report.drift_detected is False


def test_correspondence_report_to_dict():
    report = ModelCorrespondenceAudit().run(_five_predictions_three_domains())
    d = report.to_dict()
    assert d["total_predictions"] == 5
    assert isinstance(d["dimensions"], list)
    assert all(isinstance(dim, dict) for dim in d["dimensions"])


def test_correspondence_dimension_to_dict():
    dim = CorrespondenceDimension(domain="runtime", predictions_evaluated=3, accuracy=0.8)
    d = dim.to_dict()
    assert d["domain"] == "runtime"
    assert d["accuracy"] == 0.8


def test_correspondence_unknown_domain_label():
    preds = [PredictionRecord(predicted_state="x", observed_state="x")]
    report = ModelCorrespondenceAudit().run(preds)
    assert report.dimensions[0].domain == "unknown"


def test_correspondence_dimensions_sorted():
    report = ModelCorrespondenceAudit().run(_five_predictions_three_domains())
    domains = [d.domain for d in report.dimensions]
    assert domains == sorted(domains)


# ===========================================================================
# Category O — Strategic Compression
# ===========================================================================

def _five_intents() -> list[IntentRecord]:
    return [
        IntentRecord(intent_id="i1", word_count=4, clarification_rounds=0, steps_to_execution=2, output_loc=100, duration_seconds=30.0),
        IntentRecord(intent_id="i2", word_count=6, clarification_rounds=1, steps_to_execution=4, output_loc=200, duration_seconds=60.0),
        IntentRecord(intent_id="i3", word_count=10, clarification_rounds=0, steps_to_execution=3, output_loc=300, duration_seconds=45.0),
        IntentRecord(intent_id="i4", word_count=5, clarification_rounds=2, steps_to_execution=6, output_loc=150, duration_seconds=90.0),
        IntentRecord(intent_id="i5", word_count=5, clarification_rounds=0, steps_to_execution=1, output_loc=250, duration_seconds=15.0),
    ]


def test_compression_basic_counts():
    result = StrategicCompressionBenchmark().evaluate(_five_intents())
    assert result.intents_processed == 5


def test_compression_ratio_math():
    result = StrategicCompressionBenchmark().evaluate(_five_intents())
    # total output = 100+200+300+150+250 = 1000; total words = 4+6+10+5+5 = 30
    assert result.compression_ratio == round(1000 / 30, 4)


def test_compression_direct_execution_rate():
    result = StrategicCompressionBenchmark().evaluate(_five_intents())
    # 3 of 5 have 0 clarifications
    assert result.direct_execution_rate == round(3 / 5, 4)


def test_compression_avg_steps_and_clarifications():
    result = StrategicCompressionBenchmark().evaluate(_five_intents())
    # steps: 2+4+3+6+1 = 16 / 5
    assert result.avg_steps_to_execution == round(16 / 5, 4)
    # clarifications: 0+1+0+2+0 = 3 / 5
    assert result.avg_clarification_rounds == round(3 / 5, 4)


def test_compression_duration_metrics():
    result = StrategicCompressionBenchmark().evaluate(_five_intents())
    # durations: 30+60+45+90+15 = 240 / 5 = 48
    assert result.avg_duration_seconds == 48.0
    assert result.fastest_intent_seconds == 15.0
    assert result.slowest_intent_seconds == 90.0


def test_compression_word_count_auto_from_text():
    rec = IntentRecord(intent_text="build me a full saas product", word_count=0, output_loc=60)
    assert rec.resolved_word_count() == 6
    result = StrategicCompressionBenchmark().evaluate([rec])
    # 60 output / 6 words = 10.0
    assert result.compression_ratio == 10.0


def test_compression_word_count_preset_wins():
    rec = IntentRecord(intent_text="build me a full saas product", word_count=3)
    assert rec.resolved_word_count() == 3


def test_compression_zero_words_no_division_error():
    rec = IntentRecord(intent_text="", word_count=0, output_loc=50)
    result = StrategicCompressionBenchmark().evaluate([rec])
    # max(total_words, 1) guards division
    assert result.compression_ratio == 50.0


def test_compression_empty():
    result = StrategicCompressionBenchmark().evaluate([])
    assert isinstance(result, StrategicCompressionResult)
    assert result.intents_processed == 0
    assert result.compression_ratio == 0.0
    assert result.direct_execution_rate == 0.0


def test_compression_to_dict():
    result = StrategicCompressionBenchmark().evaluate(_five_intents())
    d = result.to_dict()
    assert d["intents_processed"] == 5
    assert "compression_ratio" in d


def test_intent_record_to_dict():
    rec = IntentRecord(intent_id="i1", output_loc=10)
    d = rec.to_dict()
    assert d["intent_id"] == "i1"
    assert d["output_loc"] == 10


# ===========================================================================
# Category S — Human Amplification
# ===========================================================================

def test_skill_level_constants():
    assert SkillLevel.NOVICE == "novice"
    assert SkillLevel.ALL == frozenset({"novice", "intermediate", "expert"})


def test_task_complexity_rank():
    assert TaskComplexity.RANK["low"] == 1
    assert TaskComplexity.RANK["extreme"] == 4
    assert TaskComplexity.ALL == frozenset({"low", "medium", "high", "extreme"})


def _amplification_records() -> list[AmplificationRecord]:
    return [
        # novice completes an extreme specialist task -> strong amplification
        AmplificationRecord(record_id="a1", operator_skill_level=SkillLevel.NOVICE, task_complexity=TaskComplexity.EXTREME, task_completed=True, quality_score=0.9, would_need_specialist_without=True),
        # novice completes a low non-specialist task
        AmplificationRecord(record_id="a2", operator_skill_level=SkillLevel.NOVICE, task_complexity=TaskComplexity.LOW, task_completed=True, quality_score=0.7, would_need_specialist_without=False),
        # intermediate fails a high specialist task
        AmplificationRecord(record_id="a3", operator_skill_level=SkillLevel.INTERMEDIATE, task_complexity=TaskComplexity.HIGH, task_completed=False, quality_score=0.3, would_need_specialist_without=True),
        # expert completes a medium non-specialist task
        AmplificationRecord(record_id="a4", operator_skill_level=SkillLevel.EXPERT, task_complexity=TaskComplexity.MEDIUM, task_completed=True, quality_score=1.0, would_need_specialist_without=False),
    ]


def test_amplification_complexity_rank_helper():
    rec = AmplificationRecord(task_complexity=TaskComplexity.HIGH)
    assert rec.complexity_rank() == 3
    assert AmplificationRecord(task_complexity="bogus").complexity_rank() == 0


def test_amplification_capability_expansion_rate():
    result = HumanAmplificationBenchmark().evaluate(_amplification_records())
    # specialist tasks: a1 (completed), a3 (not) -> 1/2
    assert result.total_specialist_tasks == 2
    assert result.specialist_tasks_completed == 1
    assert result.capability_expansion_rate == 0.5


def test_amplification_quality_by_skill_level():
    result = HumanAmplificationBenchmark().evaluate(_amplification_records())
    # novice quality: (0.9 + 0.7) / 2 = 0.8
    assert result.quality_by_skill_level["novice"] == 0.8
    assert result.quality_by_skill_level["intermediate"] == 0.3
    assert result.quality_by_skill_level["expert"] == 1.0


def test_amplification_completion_by_skill_level():
    result = HumanAmplificationBenchmark().evaluate(_amplification_records())
    # novice: both completed -> 1.0
    assert result.completion_by_skill_level["novice"] == 1.0
    # intermediate: 0/1 -> 0.0
    assert result.completion_by_skill_level["intermediate"] == 0.0
    assert result.completion_by_skill_level["expert"] == 1.0


def test_amplification_complexity_ceilings():
    result = HumanAmplificationBenchmark().evaluate(_amplification_records())
    # with UMH: highest completed rank = extreme (4) from a1
    assert result.complexity_ceiling_with_umh == 4
    # without UMH: highest completed non-specialist = medium (2) from a4
    assert result.complexity_ceiling_without == 2


def test_amplification_ratio():
    result = HumanAmplificationBenchmark().evaluate(_amplification_records())
    # 4 / max(2, 1) = 2.0
    assert result.amplification_ratio == 2.0


def test_amplification_ratio_no_baseline_capability():
    # operator can do nothing without a specialist; ceiling_without falls to 0 -> max(0,1)=1
    records = [
        AmplificationRecord(operator_skill_level=SkillLevel.NOVICE, task_complexity=TaskComplexity.HIGH, task_completed=True, would_need_specialist_without=True),
    ]
    result = HumanAmplificationBenchmark().evaluate(records)
    assert result.complexity_ceiling_with_umh == 3
    assert result.complexity_ceiling_without == 0
    assert result.amplification_ratio == 3.0


def test_amplification_skill_level_absent_omitted():
    records = [
        AmplificationRecord(operator_skill_level=SkillLevel.NOVICE, task_complexity=TaskComplexity.LOW, task_completed=True, quality_score=0.5, would_need_specialist_without=False),
    ]
    result = HumanAmplificationBenchmark().evaluate(records)
    assert "intermediate" not in result.quality_by_skill_level
    assert "expert" not in result.quality_by_skill_level


def test_amplification_no_specialist_tasks():
    records = [
        AmplificationRecord(operator_skill_level=SkillLevel.EXPERT, task_complexity=TaskComplexity.LOW, task_completed=True, would_need_specialist_without=False),
    ]
    result = HumanAmplificationBenchmark().evaluate(records)
    assert result.total_specialist_tasks == 0
    assert result.capability_expansion_rate == 0.0


def test_amplification_empty():
    result = HumanAmplificationBenchmark().evaluate([])
    assert isinstance(result, AmplificationResult)
    assert result.records_evaluated == 0
    assert result.amplification_ratio == 0.0
    assert result.quality_by_skill_level == {}
    assert result.complexity_ceiling_with_umh == 0


def test_amplification_to_dict():
    result = HumanAmplificationBenchmark().evaluate(_amplification_records())
    d = result.to_dict()
    assert d["records_evaluated"] == 4
    assert d["amplification_ratio"] == 2.0
    assert isinstance(d["quality_by_skill_level"], dict)


def test_amplification_record_to_dict():
    rec = AmplificationRecord(record_id="a1", quality_score=0.9)
    d = rec.to_dict()
    assert d["record_id"] == "a1"
    assert d["quality_score"] == 0.9


# ===========================================================================
# Parametrized + extended coverage
# ===========================================================================

@pytest.mark.parametrize("predicted,observed,expected", [
    ("running", "running", 1.0),
    ("Running", "RUNNING", 1.0),
    ("up", "service up now", 0.7),
    ("service up now", "up", 0.7),
    ("up", "down", 0.0),
    ("", "up", 0.0),
    ("up", "", 0.0),
    ("  up  ", "up", 1.0),
])
def test_score_match_parametrized(predicted, observed, expected):
    assert score_match(predicted, observed) == expected


@pytest.mark.parametrize("complexity,rank", [
    ("low", 1),
    ("medium", 2),
    ("high", 3),
    ("extreme", 4),
    ("", 0),
    ("unknown", 0),
])
def test_complexity_rank_parametrized(complexity, rank):
    assert AmplificationRecord(task_complexity=complexity).complexity_rank() == rank


@pytest.mark.parametrize("domain", CORRESPONDENCE_DOMAINS)
def test_correspondence_each_domain_perfect(domain):
    preds = [PredictionRecord(domain=domain, predicted_state="ok", observed_state="ok")]
    report = ModelCorrespondenceAudit().run(preds)
    assert report.dimensions[0].domain == domain
    assert report.dimensions[0].accuracy == 1.0
    assert report.drift_detected is False


@pytest.mark.parametrize("domain", CORRESPONDENCE_DOMAINS)
def test_correspondence_each_domain_drift(domain):
    preds = [PredictionRecord(domain=domain, predicted_state="a", observed_state="b")]
    report = ModelCorrespondenceAudit().run(preds)
    assert report.dimensions[0].accuracy == 0.0
    assert report.drift_detected is True


@pytest.mark.parametrize("clarifications,expected_direct", [
    ([0, 0, 0], 1.0),
    ([1, 1, 1], 0.0),
    ([0, 1, 0, 1], 0.5),
    ([0], 1.0),
    ([3], 0.0),
])
def test_compression_direct_rate_parametrized(clarifications, expected_direct):
    records = [
        IntentRecord(intent_id=f"i{i}", word_count=5, clarification_rounds=c, output_loc=10)
        for i, c in enumerate(clarifications)
    ]
    result = StrategicCompressionBenchmark().evaluate(records)
    assert result.direct_execution_rate == round(expected_direct, 4)


@pytest.mark.parametrize("skill", list(SkillLevel.ALL))
def test_amplification_single_skill_grouping(skill):
    records = [
        AmplificationRecord(operator_skill_level=skill, task_complexity=TaskComplexity.LOW, task_completed=True, quality_score=0.6, would_need_specialist_without=False),
    ]
    result = HumanAmplificationBenchmark().evaluate(records)
    assert result.quality_by_skill_level[skill] == 0.6
    assert result.completion_by_skill_level[skill] == 1.0
    # other levels absent
    for other in SkillLevel.ALL - {skill}:
        assert other not in result.quality_by_skill_level


def test_correspondence_single_prediction():
    report = ModelCorrespondenceAudit().run([
        PredictionRecord(domain="runtime", predicted_state="up", observed_state="up"),
    ])
    assert report.total_predictions == 1
    assert report.overall_accuracy == 1.0
    assert report.best_domain == "runtime"
    assert report.worst_domain == "runtime"


def test_correspondence_all_domains_present():
    preds = [
        PredictionRecord(domain=d, predicted_state="ok", observed_state="ok")
        for d in CORRESPONDENCE_DOMAINS
    ]
    report = ModelCorrespondenceAudit().run(preds)
    assert len(report.dimensions) == len(CORRESPONDENCE_DOMAINS)
    assert report.overall_accuracy == 1.0


def test_correspondence_preset_zero_falls_back_to_compute():
    # match_score == 0 is treated as "unset" -> compute from states
    rec = PredictionRecord(domain="runtime", predicted_state="up", observed_state="up", match_score=0.0)
    assert rec.resolved_score() == 1.0


def test_correspondence_mean_error_is_complement():
    preds = [
        PredictionRecord(domain="risk", predicted_state="a", observed_state="risk a level"),  # 0.7
    ]
    report = ModelCorrespondenceAudit().run(preds)
    dim = report.dimensions[0]
    assert dim.accuracy == 0.7
    assert dim.mean_error == round(1.0 - 0.7, 4)


def test_correspondence_metadata_preserved_in_dict():
    rec = PredictionRecord(domain="runtime", metadata={"source": "tick"})
    assert rec.to_dict()["metadata"] == {"source": "tick"}


def test_compression_single_intent():
    result = StrategicCompressionBenchmark().evaluate([
        IntentRecord(intent_id="solo", word_count=2, clarification_rounds=0, steps_to_execution=1, output_loc=50, duration_seconds=10.0),
    ])
    assert result.intents_processed == 1
    assert result.compression_ratio == 25.0
    assert result.fastest_intent_seconds == 10.0
    assert result.slowest_intent_seconds == 10.0
    assert result.avg_duration_seconds == 10.0


def test_compression_all_clarified():
    records = [IntentRecord(word_count=3, clarification_rounds=2, output_loc=9) for _ in range(3)]
    result = StrategicCompressionBenchmark().evaluate(records)
    assert result.direct_execution_rate == 0.0
    assert result.avg_clarification_rounds == 2.0


def test_compression_zero_output_loc():
    records = [IntentRecord(word_count=10, output_loc=0)]
    result = StrategicCompressionBenchmark().evaluate(records)
    assert result.compression_ratio == 0.0


def test_compression_mixed_word_count_sources():
    records = [
        IntentRecord(intent_text="one two three", word_count=0, output_loc=30),  # 3 words
        IntentRecord(intent_text="ignored", word_count=7, output_loc=70),  # preset 7
    ]
    result = StrategicCompressionBenchmark().evaluate(records)
    # output 100 / words (3+7=10) = 10.0
    assert result.compression_ratio == 10.0


def test_amplification_all_specialist_completed():
    records = [
        AmplificationRecord(operator_skill_level=SkillLevel.NOVICE, task_complexity=TaskComplexity.HIGH, task_completed=True, would_need_specialist_without=True),
        AmplificationRecord(operator_skill_level=SkillLevel.NOVICE, task_complexity=TaskComplexity.EXTREME, task_completed=True, would_need_specialist_without=True),
    ]
    result = HumanAmplificationBenchmark().evaluate(records)
    assert result.capability_expansion_rate == 1.0
    assert result.total_specialist_tasks == 2
    assert result.specialist_tasks_completed == 2


def test_amplification_no_specialist_completed():
    records = [
        AmplificationRecord(operator_skill_level=SkillLevel.NOVICE, task_complexity=TaskComplexity.HIGH, task_completed=False, would_need_specialist_without=True),
    ]
    result = HumanAmplificationBenchmark().evaluate(records)
    assert result.capability_expansion_rate == 0.0
    assert result.complexity_ceiling_with_umh == 0


def test_amplification_incomplete_tasks_excluded_from_ceiling():
    records = [
        AmplificationRecord(operator_skill_level=SkillLevel.EXPERT, task_complexity=TaskComplexity.EXTREME, task_completed=False, would_need_specialist_without=False),
        AmplificationRecord(operator_skill_level=SkillLevel.EXPERT, task_complexity=TaskComplexity.LOW, task_completed=True, would_need_specialist_without=False),
    ]
    result = HumanAmplificationBenchmark().evaluate(records)
    # extreme not completed -> ceiling reflects only the completed low task
    assert result.complexity_ceiling_with_umh == 1
    assert result.complexity_ceiling_without == 1


def test_amplification_ceiling_with_beats_without():
    records = [
        AmplificationRecord(operator_skill_level=SkillLevel.NOVICE, task_complexity=TaskComplexity.EXTREME, task_completed=True, would_need_specialist_without=True),
        AmplificationRecord(operator_skill_level=SkillLevel.NOVICE, task_complexity=TaskComplexity.LOW, task_completed=True, would_need_specialist_without=False),
    ]
    result = HumanAmplificationBenchmark().evaluate(records)
    assert result.complexity_ceiling_with_umh >= result.complexity_ceiling_without


def test_amplification_quality_averaging_multiple():
    records = [
        AmplificationRecord(operator_skill_level=SkillLevel.EXPERT, task_complexity=TaskComplexity.LOW, task_completed=True, quality_score=0.4, would_need_specialist_without=False),
        AmplificationRecord(operator_skill_level=SkillLevel.EXPERT, task_complexity=TaskComplexity.LOW, task_completed=True, quality_score=0.8, would_need_specialist_without=False),
        AmplificationRecord(operator_skill_level=SkillLevel.EXPERT, task_complexity=TaskComplexity.LOW, task_completed=False, quality_score=0.6, would_need_specialist_without=False),
    ]
    result = HumanAmplificationBenchmark().evaluate(records)
    assert result.quality_by_skill_level["expert"] == round((0.4 + 0.8 + 0.6) / 3, 4)
    assert result.completion_by_skill_level["expert"] == round(2 / 3, 4)


def test_all_results_are_json_serializable():
    import json
    corr = ModelCorrespondenceAudit().run(_five_predictions_three_domains())
    comp = StrategicCompressionBenchmark().evaluate(_five_intents())
    amp = HumanAmplificationBenchmark().evaluate(_amplification_records())
    for result in (corr, comp, amp):
        json.dumps(result.to_dict())  # must not raise


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
