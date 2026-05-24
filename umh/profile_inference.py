"""Profile auto-inference from observed behavior — Phase 8.

Analyzes workspace tracking data (window categories, time patterns),
discovery results, and onboarding answers to suggest profile modes.
Entirely deterministic — no LLM needed.

The inference produces suggestions, not forced switches. The interaction
loop surfaces them: "You've been researching for 20 minutes. Switch to
research mode?"
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
INFERENCE_FILE = os.path.join(UMH_ROOT, "data", "sessions", "inferred_profiles.json")

CATEGORY_TO_MODE: dict[str, str] = {
    "development": "developer",
    "research": "research",
    "communication": "command_center",
    "content": "content",
    "writing": "content",
}

MINIMUM_EVENTS_FOR_INFERENCE = 10
DOMINANCE_THRESHOLD = 0.40


@dataclass
class ProfileSuggestion:
    """A suggested profile mode with evidence."""

    mode: str
    confidence: float
    evidence: str
    source: str

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "source": self.source,
        }


@dataclass
class InferredProfile:
    """Complete inference result."""

    primary_mode: str = "developer"
    suggestions: list[ProfileSuggestion] = field(default_factory=list)
    category_distribution: dict[str, float] = field(default_factory=dict)
    inferred_at: str = ""
    event_count: int = 0

    def to_dict(self) -> dict:
        return {
            "primary_mode": self.primary_mode,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "category_distribution": self.category_distribution,
            "inferred_at": self.inferred_at,
            "event_count": self.event_count,
        }


def infer_from_workspace(events: list[dict]) -> InferredProfile:
    """Infer profile modes from workspace tracking events.

    Each event should have at minimum a 'category' field (from
    umh/perception/workspace.py's _CATEGORY_PATTERNS).
    """
    result = InferredProfile(
        inferred_at=datetime.now(datetime.UTC).isoformat(),
        event_count=len(events),
    )

    if len(events) < MINIMUM_EVENTS_FOR_INFERENCE:
        result.suggestions.append(
            ProfileSuggestion(
                mode="developer",
                confidence=0.5,
                evidence=f"Insufficient data ({len(events)} events, need {MINIMUM_EVENTS_FOR_INFERENCE})",
                source="default",
            )
        )
        return result

    category_counts: dict[str, int] = {}
    for event in events:
        cat = event.get("category", "other")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    total = sum(category_counts.values())
    if total == 0:
        return result

    distribution = {cat: count / total for cat, count in category_counts.items()}
    result.category_distribution = distribution

    for category, fraction in sorted(distribution.items(), key=lambda x: -x[1]):
        mode = CATEGORY_TO_MODE.get(category)
        if mode is None:
            continue

        confidence = min(fraction * 2, 1.0)
        evidence = f"{category} activity: {fraction:.0%} of {total} events"

        result.suggestions.append(
            ProfileSuggestion(
                mode=mode,
                confidence=confidence,
                evidence=evidence,
                source="workspace_tracking",
            )
        )

    if result.suggestions:
        top = result.suggestions[0]
        if top.confidence >= DOMINANCE_THRESHOLD:
            result.primary_mode = top.mode

    return result


def infer_from_onboarding(onboarding_path: str | None = None) -> list[ProfileSuggestion]:
    """Infer profile suggestions from onboarding answers."""
    path = onboarding_path or os.path.join(UMH_ROOT, "data", "onboarding", "onboarding_result.json")
    if not os.path.exists(path):
        return []

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        logger.debug("Failed to load onboarding data: %s", exc)
        return []

    suggestions: list[ProfileSuggestion] = []

    role = (data.get("role", "") or "").lower()
    if any(w in role for w in ("developer", "engineer", "cto", "technical")):
        suggestions.append(
            ProfileSuggestion(
                mode="developer",
                confidence=0.8,
                evidence=f"Role: {data.get('role', '')}",
                source="onboarding",
            )
        )

    if any(w in role for w in ("ceo", "founder", "owner")):
        suggestions.append(
            ProfileSuggestion(
                mode="command_center",
                confidence=0.7,
                evidence=f"Role: {data.get('role', '')}",
                source="onboarding",
            )
        )

    channel = (data.get("primary_channel", "") or "").lower()
    if any(w in channel for w in ("content", "youtube", "social", "tiktok", "instagram")):
        suggestions.append(
            ProfileSuggestion(
                mode="content",
                confidence=0.6,
                evidence=f"Channel: {data.get('primary_channel', '')}",
                source="onboarding",
            )
        )

    if any(w in channel for w in ("outbound", "cold", "email", "dm", "outreach")):
        suggestions.append(
            ProfileSuggestion(
                mode="outreach",
                confidence=0.6,
                evidence=f"Channel: {data.get('primary_channel', '')}",
                source="onboarding",
            )
        )

    return suggestions


def infer_from_discovery(discovery_path: str | None = None) -> list[ProfileSuggestion]:
    """Infer profile suggestions from environment discovery results."""
    if discovery_path is None:
        discovery_dir = os.path.join(UMH_ROOT, "data", "environment_maps")
        if not os.path.isdir(discovery_dir):
            return []
        files = sorted(
            (f for f in os.listdir(discovery_dir) if f.startswith("scan_")),
            reverse=True,
        )
        if not files:
            return []
        discovery_path = os.path.join(discovery_dir, files[0])

    try:
        with open(discovery_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        logger.debug("Failed to load discovery data: %s", exc)
        return []

    suggestions: list[ProfileSuggestion] = []

    platforms = data.get("platforms_found", 0)
    if platforms >= 5:
        suggestions.append(
            ProfileSuggestion(
                mode="developer",
                confidence=0.6,
                evidence=f"{platforms} development platforms detected",
                source="discovery",
            )
        )

    return suggestions


def run_full_inference() -> InferredProfile:
    """Run inference from all available sources."""
    workspace_events: list[dict] = []

    try:
        from umh.perception.workspace import WorkspaceTracker

        tracker = WorkspaceTracker()
        workspace_events = [
            {"category": e.category, "title": e.title, "process": e.process_name}
            for e in tracker.state.history
        ]
    except Exception as exc:
        logger.debug("Workspace event collection failed: %s", exc)

    result = infer_from_workspace(workspace_events)

    onboarding_suggestions = infer_from_onboarding()
    discovery_suggestions = infer_from_discovery()

    for suggestion in onboarding_suggestions + discovery_suggestions:
        existing_modes = {s.mode for s in result.suggestions}
        if suggestion.mode not in existing_modes:
            result.suggestions.append(suggestion)
        else:
            for existing in result.suggestions:
                if existing.mode == suggestion.mode:
                    existing.confidence = max(existing.confidence, suggestion.confidence)
                    existing.evidence += f"; {suggestion.evidence}"
                    break

    result.suggestions.sort(key=lambda s: -s.confidence)

    if result.suggestions and result.suggestions[0].confidence >= DOMINANCE_THRESHOLD:
        result.primary_mode = result.suggestions[0].mode

    return result


def save_inference(result: InferredProfile) -> None:
    os.makedirs(os.path.dirname(INFERENCE_FILE), exist_ok=True)
    try:
        with open(INFERENCE_FILE, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2)
    except Exception as exc:
        logger.debug("Failed to save inference: %s", exc)


def load_inference() -> InferredProfile | None:
    if not os.path.exists(INFERENCE_FILE):
        return None
    try:
        with open(INFERENCE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        result = InferredProfile(
            primary_mode=data.get("primary_mode", "developer"),
            inferred_at=data.get("inferred_at", ""),
            event_count=data.get("event_count", 0),
            category_distribution=data.get("category_distribution", {}),
        )
        for s in data.get("suggestions", []):
            result.suggestions.append(
                ProfileSuggestion(
                    mode=s["mode"],
                    confidence=s["confidence"],
                    evidence=s["evidence"],
                    source=s["source"],
                )
            )
        return result
    except Exception as exc:
        logger.debug("Failed to load inference: %s", exc)
        return None


def show_inference() -> int:
    """Display current profile inference."""
    result = load_inference()
    if result is None:
        result = run_full_inference()
        save_inference(result)

    print()
    print("=" * 50)
    print("  UMH Profile Inference")
    print("=" * 50)
    print(f"  Primary mode:    {result.primary_mode}")
    print(f"  Events analyzed: {result.event_count}")
    if result.inferred_at:
        print(f"  Inferred at:     {result.inferred_at[:19]}")
    print()

    if result.suggestions:
        print("  Suggestions:")
        for s in result.suggestions:
            bar = "#" * int(s.confidence * 10)
            print(f"    {s.mode:<20s} {s.confidence:.0%} [{bar:<10s}]")
            print(f"      {s.evidence}")
    else:
        print("  No suggestions yet — need more workspace activity data.")

    if result.category_distribution:
        print()
        print("  Activity distribution:")
        for cat, frac in sorted(result.category_distribution.items(), key=lambda x: -x[1]):
            bar = "#" * int(frac * 20)
            print(f"    {cat:<15s} {frac:.0%} [{bar}]")

    print("=" * 50)
    print()
    return 0
