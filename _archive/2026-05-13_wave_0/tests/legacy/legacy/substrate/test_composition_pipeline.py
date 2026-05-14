"""
Tests for the composition pipeline system.

Covers:
  - Pipeline creation and structure
  - Step execution with mock handlers
  - Failure handling and propagation
  - Structured output format
  - CompositionEngine pattern matching
  - End-to-end pipeline execution
"""

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.substrate.pipeline import (
    Pipeline,
    PipelineRunStatus,
    PipelineStep,
    StepResult,
    StepStatus,
    register_handler,
    get_handler,
)
from umh.substrate.composition_engine import CompositionEngine


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _mock_succeed(step: PipelineStep, context: dict) -> StepResult:
    """Mock handler that always succeeds."""
    return StepResult(
        status="succeeded",
        result={"mock": True, "step_name": step.name},
    )


def _mock_fail(step: PipelineStep, context: dict) -> StepResult:
    """Mock handler that always fails."""
    return StepResult(
        status="failed",
        error="mock failure",
    )


def _mock_raise(step: PipelineStep, context: dict) -> StepResult:
    """Mock handler that raises an exception."""
    raise RuntimeError("handler exploded")


def _mock_context_reader(step: PipelineStep, context: dict) -> StepResult:
    """Mock handler that reads from pipeline context."""
    step_results = context.get("step_results", {})
    return StepResult(
        status="succeeded",
        result={"saw_context": dict(step_results)},
    )


# Register mock handlers
register_handler("mock_succeed", _mock_succeed)
register_handler("mock_fail", _mock_fail)
register_handler("mock_raise", _mock_raise)
register_handler("mock_context_reader", _mock_context_reader)


# ─── Pipeline Creation ────────────────────────────────────────────────────────


class TestPipelineCreation:
    def test_create_pipeline_with_steps(self) -> None:
        steps = [
            PipelineStep.new("step_one", "mock_succeed"),
            PipelineStep.new("step_two", "mock_succeed"),
        ]
        pipe = Pipeline.new("test_pipeline", steps)

        assert pipe.id.startswith("pipe_")
        assert pipe.name == "test_pipeline"
        assert len(pipe.steps) == 2
        assert pipe.status == PipelineRunStatus.PENDING

    def test_create_empty_pipeline(self) -> None:
        pipe = Pipeline.new("empty", [])
        assert len(pipe.steps) == 0
        assert pipe.status == PipelineRunStatus.PENDING

    def test_step_ids_are_unique(self) -> None:
        s1 = PipelineStep.new("a", "mock_succeed")
        s2 = PipelineStep.new("b", "mock_succeed")
        assert s1.id != s2.id

    def test_step_default_status(self) -> None:
        step = PipelineStep.new("s", "mock_succeed")
        assert step.status == StepStatus.PENDING
        assert step.result is None
        assert step.error is None

    def test_pipeline_context_passthrough(self) -> None:
        pipe = Pipeline.new("ctx", [], context={"key": "value"})
        assert pipe.context["key"] == "value"


# ─── Step Execution ──────────────────────────────────────────────────────────


class TestStepExecution:
    def test_successful_step(self) -> None:
        step = PipelineStep.new("s", "mock_succeed")
        pipe = Pipeline.new("test", [step])
        result = pipe.run_step(step)

        assert result.status == "succeeded"
        assert result.result["mock"] is True
        assert step.status == StepStatus.SUCCEEDED
        assert step.started_at is not None
        assert step.finished_at is not None

    def test_failed_step(self) -> None:
        step = PipelineStep.new("s", "mock_fail")
        pipe = Pipeline.new("test", [step])
        result = pipe.run_step(step)

        assert result.status == "failed"
        assert result.error == "mock failure"
        assert step.status == StepStatus.FAILED
        assert step.error == "mock failure"

    def test_exception_in_handler(self) -> None:
        step = PipelineStep.new("s", "mock_raise")
        pipe = Pipeline.new("test", [step])
        result = pipe.run_step(step)

        assert result.status == "failed"
        assert "handler exception" in result.error
        assert step.status == StepStatus.FAILED

    def test_missing_handler(self) -> None:
        step = PipelineStep.new("s", "nonexistent_handler")
        pipe = Pipeline.new("test", [step])
        result = pipe.run_step(step)

        assert result.status == "failed"
        assert "no handler registered" in result.error


# ─── Pipeline Execution ──────────────────────────────────────────────────────


class TestPipelineExecution:
    def test_all_steps_succeed(self) -> None:
        steps = [
            PipelineStep.new("one", "mock_succeed"),
            PipelineStep.new("two", "mock_succeed"),
            PipelineStep.new("three", "mock_succeed"),
        ]
        pipe = Pipeline.new("success_pipeline", steps)
        result = pipe.run()

        assert result["status"] == "succeeded"
        assert len(result["steps"]) == 3
        assert all(s["status"] == "succeeded" for s in result["steps"])
        assert pipe.status == PipelineRunStatus.SUCCEEDED
        assert pipe.finished_at is not None

    def test_failure_stops_pipeline(self) -> None:
        steps = [
            PipelineStep.new("one", "mock_succeed"),
            PipelineStep.new("two", "mock_fail"),
            PipelineStep.new("three", "mock_succeed"),
        ]
        pipe = Pipeline.new("fail_pipeline", steps)
        result = pipe.run()

        assert result["status"] == "failed"
        # Step 1 succeeded, step 2 failed, step 3 never ran
        assert result["steps"][0]["status"] == "succeeded"
        assert result["steps"][1]["status"] == "failed"
        assert result["steps"][2]["status"] == "pending"

    def test_empty_pipeline_succeeds(self) -> None:
        pipe = Pipeline.new("empty", [])
        result = pipe.run()
        assert result["status"] == "succeeded"

    def test_context_flows_between_steps(self) -> None:
        steps = [
            PipelineStep.new("producer", "mock_succeed"),
            PipelineStep.new("consumer", "mock_context_reader"),
        ]
        pipe = Pipeline.new("context_flow", steps)
        result = pipe.run()

        assert result["status"] == "succeeded"
        # Consumer should see producer's output in step_results
        consumer_result = result["step_results"]["consumer"]
        assert "producer" in consumer_result["saw_context"]


# ─── Structured Output ───────────────────────────────────────────────────────


class TestStructuredOutput:
    def test_step_result_format(self) -> None:
        sr = StepResult(status="succeeded", result={"key": "val"})
        d = sr.to_dict()
        assert d == {"status": "succeeded", "result": {"key": "val"}, "error": None}

    def test_step_result_with_error(self) -> None:
        sr = StepResult(status="failed", error="broke")
        d = sr.to_dict()
        assert d["status"] == "failed"
        assert d["error"] == "broke"
        assert d["result"] == {}

    def test_pipeline_to_dict(self) -> None:
        steps = [PipelineStep.new("s", "mock_succeed")]
        pipe = Pipeline.new("test", steps, context={"extra": 1})
        d = pipe.to_dict()

        assert d["name"] == "test"
        assert d["status"] == "pending"
        assert d["context"]["extra"] == 1
        assert len(d["steps"]) == 1
        assert d["steps"][0]["handler"] == "mock_succeed"

    def test_step_to_dict(self) -> None:
        step = PipelineStep.new(
            "s",
            "mock_succeed",
            requirements=["url_open"],
            input_data={"url": "https://example.com"},
        )
        d = step.to_dict()

        assert d["name"] == "s"
        assert d["handler"] == "mock_succeed"
        assert d["requirements"] == ["url_open"]
        assert d["input_data"]["url"] == "https://example.com"
        assert d["status"] == "pending"


# ─── Composition Engine ──────────────────────────────────────────────────────


class TestCompositionEngine:
    def setup_method(self) -> None:
        self.engine = CompositionEngine()

    def test_simple_open_url(self) -> None:
        pipe = self.engine.compose("open browser and go to https://www.google.com")
        assert pipe.name == "simple_local_action"
        assert len(pipe.steps) == 1
        assert pipe.steps[0].handler == "open_url"
        assert "google.com" in pipe.steps[0].input_data["url"]

    def test_open_and_extract(self) -> None:
        pipe = self.engine.compose(
            "open https://example.com and extract the main content"
        )
        assert pipe.name == "open_and_extract_url"
        assert len(pipe.steps) == 2
        assert pipe.steps[0].handler == "open_url"
        assert pipe.steps[1].handler == "extract_content"

    def test_research_and_summarize(self) -> None:
        pipe = self.engine.compose("research AI automation trends and summarize them")
        assert pipe.name == "research_and_summarize"
        assert len(pipe.steps) == 4
        handlers = [s.handler for s in pipe.steps]
        assert handlers == [
            "search_web",
            "open_url",
            "extract_content",
            "summarize_content",
        ]

    def test_url_extracted_into_context(self) -> None:
        pipe = self.engine.compose("visit https://docs.python.org and get content")
        assert pipe.context.get("url") == "https://docs.python.org"

    def test_research_topic_extraction(self) -> None:
        pipe = self.engine.compose("research quantum computing trends and summarize")
        assert "quantum computing" in pipe.context.get("topic", "").lower()

    def test_fallback_to_research(self) -> None:
        """Unrecognised intents fall back to research_and_summarize."""
        pipe = self.engine.compose("tell me about the latest in AI")
        assert pipe.name == "research_and_summarize"

    def test_simple_domain_without_protocol(self) -> None:
        pipe = self.engine.compose("open google.com")
        assert pipe.name == "simple_local_action"
        assert pipe.steps[0].input_data["url"].startswith("https://")

    def test_context_passthrough(self) -> None:
        pipe = self.engine.compose(
            "open https://example.com",
            context={"user_id": "test"},
        )
        assert pipe.context["user_id"] == "test"


# ─── Handler Registration ────────────────────────────────────────────────────


class TestHandlerRegistration:
    def test_mock_handlers_registered(self) -> None:
        assert get_handler("mock_succeed") is not None
        assert get_handler("mock_fail") is not None

    def test_real_handlers_registered(self) -> None:
        # Import step_handlers to trigger registration
        import umh.substrate.step_handlers  # noqa: F401

        assert get_handler("open_url") is not None
        assert get_handler("extract_content") is not None
        assert get_handler("summarize_content") is not None
        assert get_handler("search_web") is not None

    def test_unknown_handler_returns_none(self) -> None:
        assert get_handler("totally_fake") is None


# ─── End-to-End ───────────────────────────────────────────────────────────────


class TestEndToEnd:
    """End-to-end test with mock handlers replacing real ones."""

    def test_compose_and_run_with_mocks(self) -> None:
        """Compose a pipeline, swap handlers to mocks, and run it."""
        engine = CompositionEngine()
        pipe = engine.compose("open browser and go to https://www.google.com")

        # Replace the real handler with mock for testing
        original = get_handler("open_url")
        register_handler("open_url", _mock_succeed)
        try:
            result = pipe.run()
            assert result["status"] == "succeeded"
            assert len(result["steps"]) == 1
            assert result["steps"][0]["status"] == "succeeded"
        finally:
            if original:
                register_handler("open_url", original)

    def test_compose_research_and_run_with_mocks(self) -> None:
        """Full research pipeline with mock handlers."""
        engine = CompositionEngine()
        pipe = engine.compose("research Python web frameworks and summarize them")

        # Replace all handlers with mocks
        originals = {}
        for name in ["search_web", "open_url", "extract_content", "summarize_content"]:
            originals[name] = get_handler(name)
            register_handler(name, _mock_succeed)

        try:
            result = pipe.run()
            assert result["status"] == "succeeded"
            assert len(result["steps"]) == 4
            assert all(s["status"] == "succeeded" for s in result["steps"])
        finally:
            for name, fn in originals.items():
                if fn:
                    register_handler(name, fn)

    def test_compose_and_run_failure_mid_pipeline(self) -> None:
        """Research pipeline where extract_content fails."""
        engine = CompositionEngine()
        pipe = engine.compose("research AI trends and summarize")

        originals = {}
        for name in ["search_web", "open_url", "summarize_content"]:
            originals[name] = get_handler(name)
            register_handler(name, _mock_succeed)

        originals["extract_content"] = get_handler("extract_content")
        register_handler("extract_content", _mock_fail)

        try:
            result = pipe.run()
            assert result["status"] == "failed"
            # First two steps succeed, third fails, fourth never runs
            assert result["steps"][0]["status"] == "succeeded"
            assert result["steps"][1]["status"] == "succeeded"
            assert result["steps"][2]["status"] == "failed"
            assert result["steps"][3]["status"] == "pending"
        finally:
            for name, fn in originals.items():
                if fn:
                    register_handler(name, fn)
