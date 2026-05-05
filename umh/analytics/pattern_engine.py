"""
PatternEngine — cross-session behavioral pattern detection + success reinforcement.

Two concerns, one domain:

1. **Behavioral detection** (PatternEngine class): analyzes Neon messages/events
   to surface avoidance, building-over-selling, low follow-through, late hours.

2. **Success reinforcement** (extract_success_patterns): reads high-confidence
   good-outcome entries from WorldModel and distills reusable pattern strings
   for prompt injection. No LLM calls — deterministic heuristic extraction.

Usage::

    # Behavioral patterns
    from umh.analytics.pattern_engine import PatternEngine
    pe = PatternEngine(ctx)
    patterns = pe.analyze(days_back=14)

    # Success patterns for prompt reinforcement
    from umh.analytics.pattern_engine import extract_success_patterns
    patterns = extract_success_patterns(world_model, limit=5)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umh.world.model import WorldModel

from umh.environments.system_context import EOSContext


@dataclass
class Pattern:
    pattern_type: str
    description: str
    evidence: list[str]
    frequency: int
    first_seen: datetime
    last_seen: datetime
    urgency: int  # 1–5
    venture_id: str = ""


class PatternEngine:
    def __init__(self, ctx: EOSContext):
        self.ctx = ctx

    def analyze(self, days_back: int = 30) -> list[Pattern]:
        """
        Analyze stored messages and commitment events to detect behavioral patterns.
        Returns a list of Pattern objects sorted by urgency descending.
        """
        patterns: list[Pattern] = []
        try:
            from umh.storage.adapters.neon import get_conn

            cutoff = (datetime.now() - timedelta(days=days_back)).isoformat()

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT content, created_at
                    FROM messages
                    WHERE org_id = %s
                      AND role = 'user'
                      AND created_at > %s
                    ORDER BY created_at ASC
                    """,
                    (self.ctx.org_id, cutoff),
                )
                messages = cur.fetchall()

            if not messages:
                return patterns

            contents = [
                (m["content"].lower(), m["created_at"])
                for m in messages
                if m.get("content")
            ]
            first_ts = messages[0]["created_at"]
            last_ts = messages[-1]["created_at"]

            # ── Pattern 1: Avoidance — content focus when pipeline is empty ──
            content_signals = [
                "content",
                "post",
                "instagram",
                "brand",
                "audience",
                "followers",
            ]
            outreach_signals = [
                "dm",
                "outreach",
                "pipeline",
                "sent dms",
                "replied",
                "closed",
            ]

            content_count = sum(
                1 for c, _ in contents if any(s in c for s in content_signals)
            )
            outreach_count = sum(
                1 for c, _ in contents if any(s in c for s in outreach_signals)
            )

            if content_count > outreach_count * 2:
                patterns.append(
                    Pattern(
                        pattern_type="avoidance",
                        description=(
                            f"Content strategy focus ({content_count}x) vs outreach ({outreach_count}x). "
                            f"Content questions are replacing outreach action."
                        ),
                        evidence=[
                            c
                            for c, _ in contents
                            if any(s in c for s in content_signals)
                        ][:3],
                        frequency=content_count,
                        first_seen=first_ts,
                        last_seen=last_ts,
                        urgency=3,
                    )
                )

            # ── Pattern 2: Building over selling ──────────────────────────────
            building_signals = [
                "build",
                "feature",
                "system",
                "automate",
                "infrastructure",
                "setup",
                "configure",
            ]
            selling_signals = [
                "sale",
                "client",
                "close",
                "follow up",
                "call",
                "revenue",
            ]

            building_count = sum(
                1 for c, _ in contents if any(s in c for s in building_signals)
            )
            selling_count = sum(
                1 for c, _ in contents if any(s in c for s in selling_signals)
            )

            if building_count > selling_count * 3:
                patterns.append(
                    Pattern(
                        pattern_type="building_over_selling",
                        description=(
                            f"Building ({building_count}x) vs selling ({selling_count}x). "
                            f"3x more likely to build than sell. Zero revenue while building."
                        ),
                        evidence=[
                            c
                            for c, _ in contents
                            if any(s in c for s in building_signals)
                        ][:3],
                        frequency=building_count,
                        first_seen=first_ts,
                        last_seen=last_ts,
                        urgency=4,
                    )
                )

            # ── Pattern 3: Low commitment follow-through ─────────────────────
            try:
                with get_conn(self.ctx.org_id) as cur:
                    cur.execute(
                        """
                        SELECT
                            COUNT(*) AS total,
                            COUNT(CASE WHEN payload_json->>'fulfilled' = 'true' THEN 1 END) AS fulfilled
                        FROM events
                        WHERE org_id = %s
                          AND event_type = 'commitment'
                          AND created_at > %s
                        """,
                        (self.ctx.org_id, cutoff),
                    )
                    row = cur.fetchone()
                    if row and (row["total"] or 0) > 3:
                        total = row["total"]
                        fulfilled = row["fulfilled"] or 0
                        rate = (fulfilled / total) * 100
                        if rate < 50:
                            patterns.append(
                                Pattern(
                                    pattern_type="low_follow_through",
                                    description=(
                                        f"Commitment follow-through: {rate:.0f}% "
                                        f"({fulfilled}/{total}). More than half of "
                                        f"stated commitments go unfulfilled."
                                    ),
                                    evidence=[],
                                    frequency=total,
                                    first_seen=first_ts,
                                    last_seen=last_ts,
                                    urgency=4,
                                )
                            )
            except Exception:
                pass

            # ── Pattern 4: Late working hours ─────────────────────────────────
            morning = sum(
                1 for _, ts in contents if hasattr(ts, "hour") and ts.hour < 12
            )
            evening = sum(
                1 for _, ts in contents if hasattr(ts, "hour") and ts.hour >= 18
            )

            if evening > morning * 2:
                patterns.append(
                    Pattern(
                        pattern_type="late_working",
                        description=(
                            f"Activity skewed late — {evening} evening vs {morning} morning. "
                            f"Morning outreach blocks would hit higher energy windows."
                        ),
                        evidence=[],
                        frequency=evening,
                        first_seen=first_ts,
                        last_seen=last_ts,
                        urgency=2,
                    )
                )

        except Exception as e:
            print(f"[PatternEngine] analyze failed: {e}")

        patterns.sort(key=lambda p: p.urgency, reverse=True)
        return patterns

    def format_for_brief(self, patterns: list[Pattern]) -> str:
        """Format top patterns for the morning brief or Telegram message."""
        if not patterns:
            return ""
        _emoji = {4: "🚨", 3: "⚠️", 2: "📍", 1: "💡"}
        lines = ["📊 **Behavioral Patterns:**"]
        for p in patterns[:3]:
            emoji = _emoji.get(p.urgency, "•")
            lines.append(f"{emoji} {p.description}")
        return "\n".join(lines)

    def inject_to_context(self, patterns: list[Pattern]) -> str:
        """Format top patterns for injection into cognitive loop system context."""
        if not patterns:
            return ""
        lines = ["BEHAVIORAL PATTERNS DETECTED:"]
        for p in patterns[:2]:
            lines.append(f"- {p.pattern_type}: {p.description[:120]}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Success Pattern Reinforcement
# ═══════════════════════════════════════════════════════════════════════════════

SUCCESS_CONFIDENCE_THRESHOLD = 0.5
SUCCESS_PATTERN_LIMIT = 5


def extract_success_patterns(
    world_model: "WorldModel",
    limit: int = SUCCESS_PATTERN_LIMIT,
    confidence_threshold: float = SUCCESS_CONFIDENCE_THRESHOLD,
) -> list[str]:
    """Extract short pattern strings from high-confidence successful interactions.

    Queries instance-layer entries for outcome="good" above the confidence
    threshold, extracts structural traits from the response text, and
    returns deduplicated pattern strings.
    """
    try:
        entries = world_model.instance.get_entries()
    except Exception:
        return []

    good_entries = [
        e
        for e in entries
        if e.confidence >= confidence_threshold and "[outcome=good]" in e.content
    ]

    if not good_entries:
        return []

    good_entries.sort(key=lambda e: e.confidence, reverse=True)

    raw_patterns: list[str] = []
    for entry in good_entries:
        extracted = _extract_pattern_from_content(entry.content)
        if extracted:
            raw_patterns.append(extracted)

    return _deduplicate_patterns(raw_patterns, limit)


def _extract_pattern_from_content(content: str) -> str | None:
    """Pull a pattern description from a world model entry's content.

    Content format from WorldModel.update_from_interaction:
        "Interaction: <msg> → Response: <resp> [outcome=good]"
    """
    parts = content.split("→ Response: ")
    if len(parts) < 2:
        return None

    response_text = parts[-1].replace("[outcome=good]", "").strip()
    if len(response_text) < 20:
        return None

    return _distill_pattern(response_text)


def _distill_pattern(response_text: str) -> str | None:
    """Reduce a response snippet to a reusable pattern description.

    Pure heuristics — no LLM. Detects structural traits of the response
    and returns a human-readable pattern string.
    """
    text_lower = response_text.lower()
    traits: list[str] = []

    imperative_verbs = [
        "send ",
        "try ",
        "start ",
        "stop ",
        "focus on",
        "prioritize",
        "reach out",
        "follow up",
        "schedule ",
        "book ",
        "post ",
        "create ",
        "write ",
        "track ",
    ]
    if any(v in text_lower for v in imperative_verbs):
        traits.append("direct actionable guidance")

    if re.search(r"\d+", response_text):
        traits.append("specific measurable targets")

    structure_markers = ["1.", "2.", "- ", "first,", "then,", "finally,"]
    if any(m in text_lower for m in structure_markers):
        traits.append("structured step-by-step format")

    if "because" in text_lower or "reason" in text_lower:
        traits.append("reasoning included")

    if traits:
        return "; ".join(traits)

    if len(response_text) > 150:
        return response_text[:150].rsplit(" ", 1)[0]
    return response_text


def _deduplicate_patterns(patterns: list[str], limit: int) -> list[str]:
    """Remove patterns that are substrings of earlier ones."""
    seen: list[str] = []
    for p in patterns:
        p_lower = p.lower()
        if any(p_lower in s.lower() or s.lower() in p_lower for s in seen):
            continue
        seen.append(p)
        if len(seen) >= limit:
            break
    return seen


def filter_redundant_patterns(
    patterns: list[str],
    base_prompt: str,
) -> list[str]:
    """Remove patterns whose core content already appears in the base prompt."""
    prompt_lower = base_prompt.lower()
    return [p for p in patterns if p.lower() not in prompt_lower]
