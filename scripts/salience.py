#!/usr/bin/env python3
"""
Salience scoring for conversation summaries.

Deterministic heuristic scoring — no LLM required.
Operates on structured summary data (parsed frontmatter + body sections).

Scoring signals:
    - Decisions made (highest weight — these change how the system works)
    - Architecture/infrastructure entities mentioned
    - Constraints discovered (rules that govern future work)
    - Bug fixes or corrections (user feedback, error resolution)
    - Open loops (unresolved work = future relevance)
    - Wiki candidates identified by LLM (pre-screened durability)
    - Topic density (breadth of session)
    - Cross-session repetition (entities/topics/decisions recurring across summaries)

Used by:
    scripts/summarize_conversations.py
    scripts/nightly_consolidation.py
"""

import re
from dataclasses import dataclass, field

# ─── Score weights ──────────────────────────────────────────────────────────
# Each signal contributes points. Max theoretical ~200+ but typical range 0-100.
# Bands are calibrated against this range.

WEIGHTS = {
    "decision": 10,  # per decision
    "constraint": 10,  # per constraint
    "architecture_entity": 8,  # per architecture-relevant entity
    "wiki_candidate": 12,  # per wiki candidate (LLM already judged durability)
    "open_loop": 4,  # per unresolved item
    "entity": 2,  # per generic entity mentioned
    "topic": 3,  # per topic tag
    "bug_fix_signal": 15,  # if session contains bug fix indicators
    "user_correction": 15,  # if session contains correction signals
    "provider_change": 10,  # routing/model/provider changes
}

# Architecture-relevant keywords that boost entity scores
ARCHITECTURE_KEYWORDS = {
    "cognitive_loop",
    "gateway",
    "agent_runtime",
    "model_router",
    "authority_engine",
    "memory",
    "orchestrator",
    "db",
    "neon",
    "knowledge_graph",
    "primitives",
    "harness",
    "discord_bot",
    "telegram",
    "webhook",
    "docker",
    "deploy",
    "migration",
    "schema",
    "rls",
    "entity_links",
    "events",
    "skill_registry",
    "media_processor",
    "voice_engine",
    "system_health",
}

# Bug fix / correction signals in summary text
BUG_SIGNALS = {
    "fix",
    "fixed",
    "bug",
    "broke",
    "broken",
    "crash",
    "error",
    "regression",
    "hotfix",
    "patch",
    "revert",
}

CORRECTION_SIGNALS = {
    "corrected",
    "correction",
    "wrong",
    "mistake",
    "should have",
    "changed to",
    "was incorrect",
    "user correction",
    "not that",
}

PROVIDER_SIGNALS = {
    "anthropic",
    "gemini",
    "ollama",
    "groq",
    "perplexity",
    "fallback",
    "routing",
    "model_router",
    "provider",
    "call_with_fallback",
    "escalation",
}

# ─── Salience bands ─────────────────────────────────────────────────────────

BANDS = [
    (80, "critical"),
    (50, "high"),
    (25, "medium"),
    (0, "low"),
]


@dataclass
class SalienceResult:
    """Result of salience scoring for a summary."""

    score: int
    label: str  # low, medium, high, critical
    reasons: list[str] = field(default_factory=list)
    promotion_recommendation: str = "skip"  # skip, consider, promote, must_promote
    consolidation_recommendation: str = "index"  # skip, index, summarize, promote

    def to_dict(self) -> dict:
        return {
            "salience_score": self.score,
            "salience_label": self.label,
            "salience_reasons": self.reasons,
            "promotion_recommendation": self.promotion_recommendation,
            "consolidation_recommendation": self.consolidation_recommendation,
        }


def _count_architecture_entities(entities: list) -> int:
    """Count entities that match architecture-relevant keywords."""
    count = 0
    for entity in entities:
        if isinstance(entity, str):
            normalized = entity.lower().replace(" ", "_").replace("-", "_")
            for kw in ARCHITECTURE_KEYWORDS:
                if kw in normalized:
                    count += 1
                    break
    return count


def _has_signal(text: str, signal_set: set[str]) -> bool:
    """Check if any signal keyword appears in text."""
    text_lower = text.lower()
    return any(signal in text_lower for signal in signal_set)


def score_summary(parsed: dict, body_text: str = "") -> SalienceResult:
    """Score a parsed summary for salience.

    Args:
        parsed: Dict with keys like decisions, constraints, entities,
                open_loops, wiki_candidates, topics, title.
                Can come from LLM extraction or frontmatter.
        body_text: Optional full body text for signal detection.

    Returns:
        SalienceResult with score, label, reasons, and recommendations.
    """
    score = 0
    reasons: list[str] = []

    # Combined text for signal detection
    all_text = body_text + " " + str(parsed.get("title", ""))

    # ── Decisions ──────────────────────────────────────────────────────
    decisions = parsed.get("decisions", [])
    n_decisions = len(decisions) if isinstance(decisions, list) else 0
    if n_decisions > 0:
        pts = n_decisions * WEIGHTS["decision"]
        score += pts
        reasons.append(f"{n_decisions} decision(s) made (+{pts})")

    # ── Constraints ───────────────────────────────────────────────────
    constraints = parsed.get("constraints", [])
    n_constraints = len(constraints) if isinstance(constraints, list) else 0
    if n_constraints > 0:
        pts = n_constraints * WEIGHTS["constraint"]
        score += pts
        reasons.append(f"{n_constraints} constraint(s) established (+{pts})")

    # ── Wiki candidates ───────────────────────────────────────────────
    wiki_candidates = parsed.get("wiki_candidates", [])
    n_wiki = len(wiki_candidates) if isinstance(wiki_candidates, list) else 0
    if n_wiki > 0:
        pts = n_wiki * WEIGHTS["wiki_candidate"]
        score += pts
        reasons.append(f"{n_wiki} wiki candidate(s) identified (+{pts})")

    # ── Entities (split architecture vs generic) ──────────────────────
    entities = parsed.get("entities", [])
    if isinstance(entities, list):
        n_arch = _count_architecture_entities(entities)
        n_generic = len(entities) - n_arch
        if n_arch > 0:
            pts = n_arch * WEIGHTS["architecture_entity"]
            score += pts
            reasons.append(f"{n_arch} architecture entity/ies (+{pts})")
        if n_generic > 0:
            pts = n_generic * WEIGHTS["entity"]
            score += pts
            reasons.append(f"{n_generic} generic entity/ies (+{pts})")

    # ── Open loops ────────────────────────────────────────────────────
    open_loops = parsed.get("open_loops", [])
    n_loops = len(open_loops) if isinstance(open_loops, list) else 0
    if n_loops > 0:
        pts = n_loops * WEIGHTS["open_loop"]
        score += pts
        reasons.append(f"{n_loops} open loop(s) (+{pts})")

    # ── Topics ────────────────────────────────────────────────────────
    topics = parsed.get("topics", [])
    n_topics = len(topics) if isinstance(topics, list) else 0
    if n_topics > 0:
        pts = n_topics * WEIGHTS["topic"]
        score += pts
        reasons.append(f"{n_topics} topic(s) covered (+{pts})")

    # ── Signal detection (body text) ──────────────────────────────────
    if _has_signal(all_text, BUG_SIGNALS):
        score += WEIGHTS["bug_fix_signal"]
        reasons.append(f"Bug fix signals detected (+{WEIGHTS['bug_fix_signal']})")

    if _has_signal(all_text, CORRECTION_SIGNALS):
        score += WEIGHTS["user_correction"]
        reasons.append(f"User correction signals (+{WEIGHTS['user_correction']})")

    if _has_signal(all_text, PROVIDER_SIGNALS):
        score += WEIGHTS["provider_change"]
        reasons.append(
            f"Provider/routing change signals (+{WEIGHTS['provider_change']})"
        )

    # ── Determine band ────────────────────────────────────────────────
    label = "low"
    for threshold, band in BANDS:
        if score >= threshold:
            label = band
            break

    # ── Recommendations ───────────────────────────────────────────────
    promotion_rec = _promotion_recommendation(label, n_wiki)
    consolidation_rec = _consolidation_recommendation(label)

    return SalienceResult(
        score=score,
        label=label,
        reasons=reasons,
        promotion_recommendation=promotion_rec,
        consolidation_recommendation=consolidation_rec,
    )


def _promotion_recommendation(label: str, n_wiki_candidates: int) -> str:
    """Determine promotion recommendation based on salience and wiki candidates."""
    if label == "critical":
        return "must_promote"
    if label == "high":
        return "promote" if n_wiki_candidates > 0 else "consider"
    if label == "medium":
        return "consider" if n_wiki_candidates > 0 else "skip"
    return "skip"


def _consolidation_recommendation(label: str) -> str:
    """Determine consolidation action based on salience band."""
    if label == "critical":
        return "promote"  # summarize + index + promote to wiki
    if label == "high":
        return "promote"  # summarize + index + strongly consider wiki
    if label == "medium":
        return "summarize"  # summarize + index, promote only if clearly durable
    return "index"  # index in Neon only, no summary needed


def score_from_frontmatter(fm: dict, body: str = "") -> SalienceResult:
    """Score a summary from its frontmatter fields.

    Convenience wrapper that maps frontmatter keys to the parsed dict
    format expected by score_summary().
    """
    # Frontmatter may already have these at top level
    parsed = {
        "title": fm.get("title", ""),
        "topics": fm.get("topics", []),
        "decisions": [],
        "constraints": [],
        "entities": [],
        "open_loops": [],
        "wiki_candidates": fm.get("wiki_candidates", []),
    }

    # If body contains structured sections, extract counts from them
    for section, key in [
        ("## Decisions", "decisions"),
        ("## Constraints", "constraints"),
        ("## Entities", "entities"),
        ("## Open Loops", "open_loops"),
    ]:
        items = _extract_list_items(body, section)
        if items:
            parsed[key] = items

    return score_summary(parsed, body)


def _extract_list_items(body: str, section_header: str) -> list[str]:
    """Extract bullet list items from a markdown section."""
    pattern = re.escape(section_header) + r"\s*\n((?:- .+\n?)+)"
    match = re.search(pattern, body)
    if not match:
        return []
    items = []
    for line in match.group(1).strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return items


# ─── Cross-session salience ────────────────────────────────────────────────────
# Detects repeated themes across summaries to compound importance.
# Keeps per-session and cross-session scores distinct.


CROSS_SESSION_WEIGHTS = {
    "repeated_entity": 5,       # per entity seen in 2+ summaries
    "repeated_topic": 4,        # per topic seen in 2+ summaries
    "repeated_decision_area": 8, # same decision area revisited
    "repeated_open_loop": 6,    # unresolved item persisting
    "repeated_architecture": 10, # same arch concern recurring
    "repeated_provider_issue": 8, # same provider failure recurring
}

# Time window in days — only count repetitions within this window
CROSS_SESSION_WINDOW_DAYS = 30


@dataclass
class CrossSessionResult:
    """Result of cross-session salience analysis."""

    score: int
    reasons: list[str] = field(default_factory=list)
    repeated_entities: list[str] = field(default_factory=list)
    repeated_topics: list[str] = field(default_factory=list)
    repeated_open_loops: list[str] = field(default_factory=list)
    compounded_recommendation: str = "none"  # none, boost, escalate

    def to_dict(self) -> dict:
        return {
            "cross_session_salience_score": self.score,
            "cross_session_salience_reasons": self.reasons,
            "repeated_entities": self.repeated_entities,
            "repeated_topics": self.repeated_topics,
            "repeated_open_loops": self.repeated_open_loops,
            "compounded_recommendation": self.compounded_recommendation,
        }


def _load_recent_summaries(
    summaries_dir: str,
    exclude_session: str = "",
    window_days: int = CROSS_SESSION_WINDOW_DAYS,
) -> list[dict]:
    """Load frontmatter from recent summary files for cross-session comparison.

    Returns list of dicts with keys: session_id, topics, entities,
    decisions, open_loops, created, body.
    """
    import os
    import glob
    import yaml
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    summaries = []

    for path in glob.glob(os.path.join(summaries_dir, "*.md")):
        try:
            with open(path) as f:
                content = f.read()
            if not content.startswith("---"):
                continue
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()

            session_id = fm.get("source_session", "")
            if session_id == exclude_session:
                continue

            # Parse created date
            created_str = fm.get("created", "")
            try:
                created = datetime.fromisoformat(str(created_str)).replace(
                    tzinfo=timezone.utc
                )
            except Exception:
                continue  # skip if can't parse date

            if created < cutoff:
                continue

            # Extract structured data from body sections
            entities = fm.get("entities", []) or _extract_list_items(
                body, "## Entities"
            )
            decisions = fm.get("decisions", []) or _extract_list_items(
                body, "## Decisions"
            )
            open_loops = fm.get("open_loops", []) or _extract_list_items(
                body, "## Open Loops"
            )

            summaries.append(
                {
                    "session_id": session_id,
                    "topics": fm.get("topics", []),
                    "entities": entities,
                    "decisions": decisions,
                    "open_loops": open_loops,
                    "created": created,
                    "body": body,
                }
            )
        except Exception:
            continue

    return summaries


def _normalize(text: str) -> str:
    """Normalize text for comparison — lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _find_repeated(
    current_items: list[str], past_summaries: list[dict], field: str
) -> list[str]:
    """Find items from current that appear in at least one past summary."""
    past_items: set[str] = set()
    for s in past_summaries:
        for item in s.get(field, []):
            if isinstance(item, str):
                past_items.add(_normalize(item))
            elif isinstance(item, dict):
                past_items.add(_normalize(str(item)))

    repeated = []
    for item in current_items:
        normalized = _normalize(item if isinstance(item, str) else str(item))
        # Check for substring match (not exact) to catch variations
        for past in past_items:
            if normalized in past or past in normalized:
                repeated.append(item if isinstance(item, str) else str(item))
                break
            # Also check word overlap for entities
            current_words = set(normalized.split())
            past_words = set(past.split())
            # 2+ word overlap signals same concept
            if len(current_words & past_words) >= 2:
                repeated.append(item if isinstance(item, str) else str(item))
                break

    return repeated


def score_cross_session(
    parsed: dict,
    body_text: str = "",
    summaries_dir: str = "/opt/OS/vault/memory/summaries",
    exclude_session: str = "",
) -> CrossSessionResult:
    """Score cross-session salience by detecting repeated themes.

    Args:
        parsed: Current summary's extracted data (entities, topics, etc.)
        body_text: Full body text of current summary.
        summaries_dir: Path to summaries directory.
        exclude_session: Session ID to exclude (the current one).

    Returns:
        CrossSessionResult with score and detailed reasons.
    """
    past = _load_recent_summaries(summaries_dir, exclude_session)
    if not past:
        return CrossSessionResult(score=0, reasons=["No prior summaries for comparison"])

    score = 0
    reasons: list[str] = []

    # ── Repeated entities ─────────────────────────────────────────────
    current_entities = parsed.get("entities", [])
    repeated_entities = _find_repeated(current_entities, past, "entities")
    if repeated_entities:
        # Check if any are architecture entities (higher weight)
        arch_repeated = []
        generic_repeated = []
        for e in repeated_entities:
            normalized = _normalize(e)
            is_arch = any(kw in normalized for kw in ARCHITECTURE_KEYWORDS)
            if is_arch:
                arch_repeated.append(e)
            else:
                generic_repeated.append(e)

        if arch_repeated:
            pts = len(arch_repeated) * CROSS_SESSION_WEIGHTS["repeated_architecture"]
            score += pts
            reasons.append(
                f"{len(arch_repeated)} architecture entity/ies recurring (+{pts})"
            )
        if generic_repeated:
            pts = len(generic_repeated) * CROSS_SESSION_WEIGHTS["repeated_entity"]
            score += pts
            reasons.append(
                f"{len(generic_repeated)} entity/ies recurring (+{pts})"
            )

    # ── Repeated topics ───────────────────────────────────────────────
    current_topics = parsed.get("topics", [])
    repeated_topics = _find_repeated(current_topics, past, "topics")
    if repeated_topics:
        pts = len(repeated_topics) * CROSS_SESSION_WEIGHTS["repeated_topic"]
        score += pts
        reasons.append(f"{len(repeated_topics)} topic(s) recurring (+{pts})")

    # ── Repeated open loops (persistent unresolved items) ─────────────
    current_loops = parsed.get("open_loops", [])
    repeated_loops = _find_repeated(current_loops, past, "open_loops")
    if repeated_loops:
        pts = len(repeated_loops) * CROSS_SESSION_WEIGHTS["repeated_open_loop"]
        score += pts
        reasons.append(
            f"{len(repeated_loops)} open loop(s) persisting across sessions (+{pts})"
        )

    # ── Provider issue recurrence ─────────────────────────────────────
    if _has_signal(body_text, PROVIDER_SIGNALS):
        past_provider_count = sum(
            1 for s in past if _has_signal(s.get("body", ""), PROVIDER_SIGNALS)
        )
        if past_provider_count > 0:
            pts = CROSS_SESSION_WEIGHTS["repeated_provider_issue"]
            score += pts
            reasons.append(
                f"Provider/routing issue recurring ({past_provider_count} prior sessions) (+{pts})"
            )

    # ── Decision area revisited ───────────────────────────────────────
    current_decisions = parsed.get("decisions", [])
    repeated_decisions = _find_repeated(current_decisions, past, "decisions")
    if repeated_decisions:
        pts = len(repeated_decisions) * CROSS_SESSION_WEIGHTS["repeated_decision_area"]
        score += pts
        reasons.append(
            f"{len(repeated_decisions)} decision area(s) revisited (+{pts})"
        )

    # ── Compounded recommendation ─────────────────────────────────────
    if score >= 30:
        compounded = "escalate"
    elif score >= 10:
        compounded = "boost"
    else:
        compounded = "none"

    return CrossSessionResult(
        score=score,
        reasons=reasons,
        repeated_entities=repeated_entities,
        repeated_topics=repeated_topics,
        repeated_open_loops=repeated_loops,
        compounded_recommendation=compounded,
    )
