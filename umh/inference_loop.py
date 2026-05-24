"""Runtime profile inference — periodic mode suggestions during interaction.

Runs profile inference periodically during the interaction loop and
surfaces suggestions when the inferred mode differs from the current mode.
NOT auto-switching — suggestions only. The operator decides.

Inference interval is configurable (default 5 minutes). Suggestions
are suppressed if the same suggestion was shown recently (debounce).

UMH workstation subsystem.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_INFERENCE_INTERVAL_S = 300
SUGGESTION_DEBOUNCE_S = 600
SUGGESTION_CONFIDENCE_THRESHOLD = 0.6


class InferenceChecker:
    """Periodic inference checker wired into the interaction loop."""

    def __init__(
        self,
        interval_s: float = DEFAULT_INFERENCE_INTERVAL_S,
        debounce_s: float = SUGGESTION_DEBOUNCE_S,
        confidence_threshold: float = SUGGESTION_CONFIDENCE_THRESHOLD,
    ) -> None:
        self._interval_s = interval_s
        self._debounce_s = debounce_s
        self._confidence_threshold = confidence_threshold
        self._last_check_time: float = time.monotonic()
        self._last_suggestion_time: float = 0.0
        self._last_suggested_mode: str = ""

    def check(self, current_mode: str) -> str | None:
        """Check if inference suggests a different mode.

        Called each poll cycle. Returns a suggestion string to display,
        or None if no suggestion is warranted. Respects interval and
        debounce timers to avoid spamming.
        """
        now = time.monotonic()

        if now - self._last_check_time < self._interval_s:
            return None
        self._last_check_time = now

        if now - self._last_suggestion_time < self._debounce_s:
            return None

        try:
            from umh.profile_inference import run_full_inference, save_inference

            result = run_full_inference()
            save_inference(result)
        except Exception as exc:
            logger.debug("Inference check failed: %s", exc)
            return None

        if not result.suggestions:
            return None

        top = result.suggestions[0]
        if top.confidence < self._confidence_threshold:
            return None

        if top.mode == current_mode:
            return None

        if (
            top.mode == self._last_suggested_mode
            and now - self._last_suggestion_time < self._debounce_s
        ):
            return None

        self._last_suggestion_time = now
        self._last_suggested_mode = top.mode

        return (
            f"Activity suggests {top.mode} mode ({top.confidence:.0%} confidence). "
            f"Switch with '{top.mode} mode'."
        )


def create_inference_checker(preferences: Any = None) -> InferenceChecker:
    """Create an InferenceChecker from workstation preferences."""
    if preferences is None:
        try:
            from umh.profile import ProfileManager

            preferences = ProfileManager().get_preferences()
        except Exception:
            pass

    interval = DEFAULT_INFERENCE_INTERVAL_S
    debounce = SUGGESTION_DEBOUNCE_S
    threshold = SUGGESTION_CONFIDENCE_THRESHOLD

    if preferences is not None:
        interval = getattr(preferences, "inference_interval_s", interval)
        debounce = getattr(preferences, "inference_debounce_s", debounce)
        threshold = getattr(preferences, "inference_confidence_threshold", threshold)

    return InferenceChecker(
        interval_s=interval,
        debounce_s=debounce,
        confidence_threshold=threshold,
    )
