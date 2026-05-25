"""Training data extraction from UMH execution traces.

Reads traces from the JSONL trace store and converts them into
supervised training pairs (input, output) suitable for fine-tuning.

Extraction strategies:
  1. Signal → Outcome pairs (what input produced what result)
  2. Governance decisions (what was approved/denied and why)
  3. Agent interactions (what tasks were delegated and how they resolved)

Output format: JSONL with {"instruction": ..., "input": ..., "output": ...}
compatible with Alpaca/Llama fine-tuning format.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TRACE_PATH = Path("data/umh/traces/traces.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/umh/training/training_data.jsonl")

MIN_INPUT_LENGTH = 10
MIN_OUTPUT_LENGTH = 5
MAX_INPUT_LENGTH = 2000
MAX_OUTPUT_LENGTH = 2000


@dataclass
class TrainingExample:
    """A single training example in Alpaca format."""

    instruction: str
    input: str
    output: str
    source_trace_id: str = ""
    extraction_type: str = ""
    quality_score: float = 0.5


@dataclass
class ExtractionReport:
    """Summary of a training data extraction run."""

    traces_read: int = 0
    examples_extracted: int = 0
    examples_filtered: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    output_path: str = ""
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


class TrainingExtractor:
    """Extracts training data from UMH execution traces."""

    def __init__(
        self,
        trace_path: Path | None = None,
        output_path: Path | None = None,
        min_quality: float = 0.5,
    ) -> None:
        self._trace_path = trace_path or DEFAULT_TRACE_PATH
        self._output_path = output_path or DEFAULT_OUTPUT_PATH
        self._min_quality = min_quality

    def extract(self, limit: int = 10000) -> ExtractionReport:
        """Extract training examples from traces."""
        t0 = time.monotonic()
        report = ExtractionReport(output_path=str(self._output_path))

        traces = self._load_traces(limit)
        report.traces_read = len(traces)

        examples: list[TrainingExample] = []

        for trace in traces:
            trace_id = trace.get("trace_id", "")

            signal_examples = self._extract_signal_outcome(trace)
            for ex in signal_examples:
                ex.source_trace_id = trace_id
            examples.extend(signal_examples)

            gov_examples = self._extract_governance(trace)
            for ex in gov_examples:
                ex.source_trace_id = trace_id
            examples.extend(gov_examples)

        filtered = [ex for ex in examples if ex.quality_score >= self._min_quality]
        report.examples_extracted = len(filtered)
        report.examples_filtered = len(examples) - len(filtered)

        for ex in filtered:
            report.by_type[ex.extraction_type] = report.by_type.get(ex.extraction_type, 0) + 1

        self._write_output(filtered)

        report.duration_ms = (time.monotonic() - t0) * 1000
        return report

    def _load_traces(self, limit: int) -> list[dict[str, Any]]:
        """Load traces from JSONL, merging updates."""
        if not self._trace_path.exists():
            return []

        traces: dict[str, dict[str, Any]] = {}
        try:
            with open(self._trace_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    trace_id = record.get("trace_id", "")
                    if not trace_id:
                        continue

                    if record.get("_type") == "trace_update":
                        if trace_id in traces:
                            traces[trace_id].update(record)
                    else:
                        traces[trace_id] = record

        except OSError as e:
            logger.warning("Failed to read trace file: %s", e)

        result = list(traces.values())[-limit:]
        return result

    def _extract_signal_outcome(self, trace: dict[str, Any]) -> list[TrainingExample]:
        """Extract signal → outcome training pairs."""
        examples: list[TrainingExample] = []

        input_signal = trace.get("input_signal", "")
        outcome = trace.get("outcome", "")
        outcome_detail = trace.get("outcome_detail", "")
        status = trace.get("status", "")

        if not input_signal or len(input_signal) < MIN_INPUT_LENGTH:
            return examples
        if status != "completed":
            return examples

        exec_result = trace.get("execution_result", {})
        if isinstance(exec_result, dict):
            output_text = exec_result.get("output", {})
            if isinstance(output_text, dict):
                stdout = output_text.get("stdout", "")
                success = output_text.get("success", False)
            else:
                stdout = str(output_text)[:MAX_OUTPUT_LENGTH]
                success = exec_result.get("success", False)
        else:
            stdout = ""
            success = False

        if not stdout or len(stdout.strip()) < MIN_OUTPUT_LENGTH:
            response = outcome_detail[:MAX_OUTPUT_LENGTH] if outcome_detail else outcome
        else:
            response = stdout[:MAX_OUTPUT_LENGTH]

        if not response or len(response.strip()) < MIN_OUTPUT_LENGTH:
            return examples

        quality = 0.7 if success else 0.3

        examples.append(
            TrainingExample(
                instruction="Process this UMH signal and produce the appropriate response.",
                input=input_signal[:MAX_INPUT_LENGTH],
                output=response.strip(),
                extraction_type="signal_outcome",
                quality_score=quality,
            )
        )

        return examples

    def _extract_governance(self, trace: dict[str, Any]) -> list[TrainingExample]:
        """Extract governance decision training pairs."""
        examples: list[TrainingExample] = []

        input_signal = trace.get("input_signal", "")
        gov_decision = trace.get("governance_decision", "")

        if not input_signal or not gov_decision:
            return examples
        if len(input_signal) < MIN_INPUT_LENGTH:
            return examples

        adapter = trace.get("adapter_used", "unknown")
        env = trace.get("environment", "unknown")

        gov_output = f"Decision: {gov_decision}\nAdapter: {adapter}\nEnvironment: {env}"

        quality = 0.6

        examples.append(
            TrainingExample(
                instruction=(
                    "Given this signal, determine the governance decision "
                    "(approve/deny/escalate) with the adapter and environment."
                ),
                input=input_signal[:MAX_INPUT_LENGTH],
                output=gov_output,
                extraction_type="governance",
                quality_score=quality,
            )
        )

        return examples

    def _write_output(self, examples: list[TrainingExample]) -> None:
        """Write training examples to JSONL."""
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._output_path, "w") as f:
            for ex in examples:
                f.write(
                    json.dumps(
                        {
                            "instruction": ex.instruction,
                            "input": ex.input,
                            "output": ex.output,
                            "source_trace_id": ex.source_trace_id,
                            "extraction_type": ex.extraction_type,
                            "quality_score": ex.quality_score,
                        },
                        separators=(",", ":"),
                    )
                    + "\n"
                )
