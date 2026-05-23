"""OutcomeClassifier — classifies execution results into outcome categories.

Rule-based classifier for MVP. Examines execution_result dict fields
to determine outcome category and detail string.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class OutcomeCategory:
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """The result of classifying an execution outcome."""

    category: str
    detail: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "detail": self.detail,
            "confidence": self.confidence,
        }


class OutcomeClassifier:
    """Rule-based outcome classifier for trace execution results."""

    def classify(
        self,
        execution_result: dict[str, Any],
        status: str = "",
    ) -> ClassificationResult:
        """Classify an execution result into an outcome category.

        Examines known fields: success, error, exit_code, timeout,
        skipped, partial, output.
        """
        if not execution_result and not status:
            return ClassificationResult(
                category=OutcomeCategory.UNKNOWN,
                detail="no execution result provided",
                confidence=0.5,
            )

        if status == "timeout" or execution_result.get("timeout"):
            return ClassificationResult(
                category=OutcomeCategory.TIMEOUT,
                detail=str(execution_result.get("timeout_detail", "execution timed out")),
                confidence=0.95,
            )

        if status == "skipped" or execution_result.get("skipped"):
            return ClassificationResult(
                category=OutcomeCategory.SKIPPED,
                detail=str(execution_result.get("skip_reason", "execution skipped")),
                confidence=0.95,
            )

        error = execution_result.get("error")
        if error:
            return ClassificationResult(
                category=OutcomeCategory.ERROR,
                detail=str(error)[:300],
                confidence=0.9,
            )

        exit_code = execution_result.get("exit_code")
        if exit_code is not None and exit_code != 0:
            return ClassificationResult(
                category=OutcomeCategory.FAILURE,
                detail=f"exit_code={exit_code}",
                confidence=0.85,
            )

        if execution_result.get("partial"):
            return ClassificationResult(
                category=OutcomeCategory.PARTIAL,
                detail=str(execution_result.get("partial_detail", "partial completion")),
                confidence=0.8,
            )

        success = execution_result.get("success")
        if success is True or (exit_code == 0):
            return ClassificationResult(
                category=OutcomeCategory.SUCCESS,
                detail=str(execution_result.get("output", ""))[:200] or "completed successfully",
                confidence=0.9,
            )

        if success is False:
            return ClassificationResult(
                category=OutcomeCategory.FAILURE,
                detail=str(execution_result.get("output", ""))[:200] or "execution failed",
                confidence=0.85,
            )

        if execution_result.get("output"):
            return ClassificationResult(
                category=OutcomeCategory.SUCCESS,
                detail="output present, assumed success",
                confidence=0.6,
            )

        return ClassificationResult(
            category=OutcomeCategory.UNKNOWN,
            detail="unable to determine outcome from execution result",
            confidence=0.3,
        )
