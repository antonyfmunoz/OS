"""Tests for Reality Recovery Benchmark — C23A Phase 2."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.benchmarks.reality_recovery import (
    Question,
    RealityRecoveryBenchmark,
    RealityRecoveryResult,
    ScoredAnswer,
)


@pytest.fixture
def benchmark():
    return RealityRecoveryBenchmark()


class TestQuestionGeneration:
    def test_generates_questions(self, benchmark):
        questions = benchmark.generate_questions()
        assert len(questions) > 0

    def test_questions_have_required_fields(self, benchmark):
        questions = benchmark.generate_questions()
        for q in questions:
            assert q.question_id, f"Missing question_id: {q.question}"
            assert q.category, f"Missing category: {q.question_id}"
            assert q.question, f"Missing question text: {q.question_id}"
            assert q.source, f"Missing source: {q.question_id}"

    def test_questions_have_unique_ids(self, benchmark):
        questions = benchmark.generate_questions()
        ids = [q.question_id for q in questions]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_ground_truth_is_not_empty(self, benchmark):
        questions = benchmark.generate_questions()
        non_empty = [q for q in questions if q.ground_truth]
        assert len(non_empty) > len(questions) * 0.5, "More than half of questions should have ground truth"

    def test_categories_covered(self, benchmark):
        questions = benchmark.generate_questions()
        categories = {q.category for q in questions}
        assert "containers" in categories or "architecture" in categories
        assert "organism" in categories or "deployment" in categories


class TestScoring:
    def test_exact_match(self, benchmark):
        questions = [
            Question(question_id="q1", category="test", question="What is X?", ground_truth="42"),
        ]
        answers = {"q1": "42"}
        result = benchmark.score_answers(questions, answers)
        assert result.correct == 1
        assert result.accuracy == 1.0

    def test_case_insensitive_match(self, benchmark):
        questions = [
            Question(question_id="q1", category="test", question="What?", ground_truth="Hello"),
        ]
        answers = {"q1": "hello"}
        result = benchmark.score_answers(questions, answers)
        assert result.correct == 1

    def test_incorrect_answer(self, benchmark):
        questions = [
            Question(question_id="q1", category="test", question="What?", ground_truth="42"),
        ]
        answers = {"q1": "99"}
        result = benchmark.score_answers(questions, answers)
        assert result.incorrect == 1
        assert result.accuracy == 0.0

    def test_no_answer_is_unknown(self, benchmark):
        questions = [
            Question(question_id="q1", category="test", question="What?", ground_truth="42"),
        ]
        answers = {}
        result = benchmark.score_answers(questions, answers)
        assert result.unknown == 1

    def test_partial_numeric_match(self, benchmark):
        questions = [
            Question(question_id="q1", category="test", question="Count?", ground_truth="100"),
        ]
        answers = {"q1": "95"}
        result = benchmark.score_answers(questions, answers)
        assert result.partial == 1
        assert result.accuracy == 0.5

    def test_numeric_out_of_range(self, benchmark):
        questions = [
            Question(question_id="q1", category="test", question="Count?", ground_truth="100"),
        ]
        answers = {"q1": "50"}
        result = benchmark.score_answers(questions, answers)
        assert result.incorrect == 1

    def test_multiple_questions(self, benchmark):
        questions = [
            Question(question_id="q1", category="a", question="Q1?", ground_truth="yes"),
            Question(question_id="q2", category="a", question="Q2?", ground_truth="no"),
            Question(question_id="q3", category="b", question="Q3?", ground_truth="42"),
            Question(question_id="q4", category="b", question="Q4?", ground_truth="hello"),
        ]
        answers = {"q1": "yes", "q2": "no", "q3": "40", "q4": "wrong"}
        result = benchmark.score_answers(questions, answers)
        assert result.correct == 2
        assert result.partial == 1  # q3: 40 within 10% of 42
        assert result.incorrect == 1
        assert result.total_questions == 4

    def test_accuracy_by_category(self, benchmark):
        questions = [
            Question(question_id="q1", category="cat_a", question="Q1?", ground_truth="yes"),
            Question(question_id="q2", category="cat_a", question="Q2?", ground_truth="no"),
            Question(question_id="q3", category="cat_b", question="Q3?", ground_truth="x"),
        ]
        answers = {"q1": "yes", "q2": "wrong", "q3": "x"}
        result = benchmark.score_answers(questions, answers)
        assert result.accuracy_by_category["cat_a"] == 0.5  # 1 correct, 1 wrong
        assert result.accuracy_by_category["cat_b"] == 1.0

    def test_empty_questions(self, benchmark):
        result = benchmark.score_answers([], {})
        assert result.total_questions == 0
        assert result.accuracy == 0.0


class TestResultFormat:
    def test_result_to_dict(self):
        result = RealityRecoveryResult(
            total_questions=10,
            correct=7,
            incorrect=2,
            partial=1,
            accuracy=0.75,
            accuracy_by_category={"containers": 0.9},
        )
        d = result.to_dict()
        assert d["total_questions"] == 10
        assert d["accuracy"] == 0.75
        assert "containers" in d["accuracy_by_category"]

    def test_question_to_dict(self):
        q = Question(question_id="q1", category="test", question="What?", ground_truth="42", source="manual")
        d = q.to_dict()
        assert d["question_id"] == "q1"
        assert d["ground_truth"] == "42"

    def test_scored_answer_to_dict(self):
        sa = ScoredAnswer(question_id="q1", score="correct", explanation="Exact match")
        d = sa.to_dict()
        assert d["score"] == "correct"


class TestSubstringMatch:
    def test_truth_contained_in_answer(self, benchmark):
        questions = [
            Question(question_id="q1", category="test", question="Status?", ground_truth="healthy"),
        ]
        answers = {"q1": "container is healthy and running"}
        result = benchmark.score_answers(questions, answers)
        assert result.partial == 1

    def test_answer_contained_in_truth(self, benchmark):
        questions = [
            Question(question_id="q1", category="test", question="Names?",
                     ground_truth="os-discord,os-operator,os-webhook"),
        ]
        answers = {"q1": "os-discord,os-operator"}
        result = benchmark.score_answers(questions, answers)
        assert result.partial == 1


class TestIntegration:
    def test_full_benchmark_generates_and_scores(self, benchmark):
        questions = benchmark.generate_questions()
        if not questions:
            pytest.skip("No questions generated (likely no docker)")

        answerable = [q for q in questions if q.ground_truth]
        perfect_answers = {q.question_id: q.ground_truth for q in answerable}
        result = benchmark.score_answers(answerable, perfect_answers)
        assert result.correct == len(answerable)
        assert result.incorrect == 0
