"""
Query Brain — deterministic query interpreter for EOS substrate.

Pure string matching and data retrieval.  NO LLM calls.
Classifies inbound text as a query (vs task), resolves the intent,
retrieves matching records from the task system, interaction archive,
and event store, and returns a structured QueryResult with a
human-readable summary.

Design rules:
  - Deterministic.  No LLM calls, no probabilistic matching.
  - Best-effort.  Never crash — return empty/fallback on errors.
  - Conservative detection.  If ambiguous, treat as task (not query).
  - Bounded retrieval.  All queries cap results by default.
  - Composable.  Sits on top of existing stores, never modifies them.
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

# ─── Config ──────────────────────────────────────────────────────────────────

_LOG_PREFIX = "[substrate.query_brain]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ─── Query Intent ────────────────────────────────────────────────────────────


class QueryIntent(str, Enum):
    """Deterministic intent classification for retrieval queries."""

    QUERY_RECENT_TASKS = "query_recent_tasks"
    QUERY_TIME_WINDOW = "query_time_window"
    QUERY_KEYWORD = "query_keyword"
    QUERY_WORKFLOW = "query_workflow"
    QUERY_GENERAL = "query_general"


# ─── Intent classification ───────────────────────────────────────────────────

# Patterns checked in priority order
_RECENT_TASKS_RE = re.compile(
    r"\b(last\s+task|recent\s+task|previous\s+task|last\s+\d+\s+tasks)\b",
    re.IGNORECASE,
)
_TIME_WINDOW_RE = re.compile(
    r"\b(yesterday|today|this\s+week|last\s+week|this\s+morning|\d+\s+days?\s+ago)\b",
    re.IGNORECASE,
)
_KEYWORD_RE = re.compile(
    r"\b(what\s+did\s+I\s+say\s+about|what\s+did\s+we\s+discuss|find\b|search\s+for)\b",
    re.IGNORECASE,
)
_WORKFLOW_RE = re.compile(
    r"\b(workflow|pipeline|correlation|this\s+session)\b",
    re.IGNORECASE,
)


def classify_query(text: str) -> QueryIntent:
    """Classify a query string into a retrieval intent.

    Rules are checked in priority order:
    1. Recent tasks ("last task", "recent task", "last N tasks")
    2. Time window ("yesterday", "today", "N days ago", etc)
    3. Keyword search ("what did I say about", "find", "search for")
    4. Workflow ("pipeline", "correlation", "this session")
    5. General (fallback)
    """
    if _RECENT_TASKS_RE.search(text):
        return QueryIntent.QUERY_RECENT_TASKS
    if _TIME_WINDOW_RE.search(text):
        return QueryIntent.QUERY_TIME_WINDOW
    if _KEYWORD_RE.search(text):
        return QueryIntent.QUERY_KEYWORD
    if _WORKFLOW_RE.search(text):
        return QueryIntent.QUERY_WORKFLOW
    return QueryIntent.QUERY_GENERAL


# ─── Time parsing ────────────────────────────────────────────────────────────


def parse_time_reference(text: str) -> tuple[str, Optional[str]]:
    """Parse natural-language time references into ISO window boundaries.

    Returns (start_iso, end_iso).  end_iso may be None (meaning "now").
    All timestamps are UTC and formatted to match _now_iso().

    Handles:
      - "yesterday" -> (yesterday 00:00, yesterday 23:59)
      - "today" -> (today 00:00, now)
      - "N days ago" -> (that_day 00:00, that_day 23:59)
      - "this week" -> (monday 00:00, now)
      - "last week" -> (prev monday 00:00, prev sunday 23:59)
      - "this morning" -> (today 06:00, today 12:00)
      - fallback -> (24 hours ago, now)
    """
    now = _now_utc()
    lower = text.lower()

    # "N days ago"
    days_ago_match = re.search(r"(\d+)\s+days?\s+ago", lower)
    if days_ago_match:
        n = int(days_ago_match.group(1))
        target = now - timedelta(days=n)
        start = target.replace(hour=0, minute=0, second=0, microsecond=0)
        end = target.replace(hour=23, minute=59, second=59, microsecond=0)
        return _fmt(start), _fmt(end)

    if "yesterday" in lower:
        target = now - timedelta(days=1)
        start = target.replace(hour=0, minute=0, second=0, microsecond=0)
        end = target.replace(hour=23, minute=59, second=59, microsecond=0)
        return _fmt(start), _fmt(end)

    if "this morning" in lower:
        start = now.replace(hour=6, minute=0, second=0, microsecond=0)
        end = now.replace(hour=12, minute=0, second=0, microsecond=0)
        return _fmt(start), _fmt(end)

    if "today" in lower:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return _fmt(start), None

    if "last week" in lower:
        # Monday of last week
        days_since_monday = now.weekday()
        this_monday = now - timedelta(days=days_since_monday)
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(days=1)
        start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = last_sunday.replace(hour=23, minute=59, second=59, microsecond=0)
        return _fmt(start), _fmt(end)

    if "this week" in lower:
        days_since_monday = now.weekday()
        monday = now - timedelta(days=days_since_monday)
        start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        return _fmt(start), None

    # Fallback: last 24 hours
    start = now - timedelta(hours=24)
    return _fmt(start), None


def _fmt(dt: datetime) -> str:
    """Format a datetime to ISO string matching _now_iso() output."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z") or dt.isoformat()


# ─── Query Result ────────────────────────────────────────────────────────────


@dataclass
class QueryResult:
    """Structured result of a query execution."""

    intent: str  # QueryIntent value
    query_text: str  # original query
    tasks: list[dict[str, Any]] = field(default_factory=list)
    interactions: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    total_results: int = 0
    response_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe dict representation."""
        return asdict(self)


# ─── Store access helpers ────────────────────────────────────────────────────


def _get_task_store():  # type: ignore[return]
    """Best-effort access to the TaskStore singleton."""
    try:
        from umh.substrate.task_system import TaskStore

        return TaskStore.default()
    except Exception as exc:
        _log(f"task store unavailable: {exc}")
        return None


def _get_task_record_store():  # type: ignore[return]
    """Best-effort access to the TaskRecordStore singleton."""
    try:
        from umh.substrate.task_record import get_task_record_store

        return get_task_record_store()
    except Exception as exc:
        _log(f"task record store unavailable: {exc}")
        return None


def _get_interaction_archive():  # type: ignore[return]
    """Best-effort access to the InteractionArchive singleton."""
    try:
        from umh.substrate.interaction_archive import get_interaction_archive

        return get_interaction_archive()
    except Exception as exc:
        _log(f"interaction archive unavailable: {exc}")
        return None


def _get_event_store():  # type: ignore[return]
    """Best-effort access to the EventStore singleton."""
    try:
        from umh.substrate.event_store import get_event_store

        return get_event_store()
    except Exception as exc:
        _log(f"event store unavailable: {exc}")
        return None


# ─── Task query helpers (built on TaskStore.all()) ───────────────────────────


def _tasks_recent(limit: int = 5) -> list[dict[str, Any]]:
    """Return the N most recent tasks as summary dicts."""
    store = _get_task_store()
    if store is None:
        return []
    try:
        all_tasks = store.all()  # sorted by created_at ascending
        recent = all_tasks[-limit:] if len(all_tasks) > limit else all_tasks
        return [_task_summary(t) for t in reversed(recent)]
    except Exception as exc:
        _log(f"tasks_recent failed: {exc}")
        return []


def _tasks_by_time_window(
    start_iso: str, end_iso: Optional[str] = None
) -> list[dict[str, Any]]:
    """Return tasks whose created_at falls within [start, end]."""
    store = _get_task_store()
    if store is None:
        return []
    end = end_iso or _now_iso()
    try:
        results: list[dict[str, Any]] = []
        for task in store.all():
            if task.created_at >= start_iso and task.created_at <= end:
                results.append(_task_summary(task))
        return results
    except Exception as exc:
        _log(f"tasks_by_time_window failed: {exc}")
        return []


def _tasks_search_text(term: str) -> list[dict[str, Any]]:
    """Return tasks whose title or description contains the search term."""
    store = _get_task_store()
    if store is None:
        return []
    lower_term = term.lower()
    try:
        results: list[dict[str, Any]] = []
        for task in store.all():
            haystack = (task.title or "").lower()
            if task.description:
                haystack += " " + task.description.lower()
            if task.execution_result:
                haystack += " " + task.execution_result.lower()
            if lower_term in haystack:
                results.append(_task_summary(task))
        return results
    except Exception as exc:
        _log(f"tasks_search_text failed: {exc}")
        return []


def _task_summary(task: Any) -> dict[str, Any]:
    """Build a concise summary dict from a Task object."""
    report_snippet = ""
    if getattr(task, "execution_result", None):
        report_snippet = task.execution_result[:200]
    elif getattr(task, "result", None):
        report_snippet = task.result[:200]

    return {
        "task_id": task.task_id,
        "title": task.title,
        "status": task.status.value
        if hasattr(task.status, "value")
        else str(task.status),
        "created_at": task.created_at,
        "final_report_snippet": report_snippet,
        "source": "task_system",
    }


# ─── TaskRecord query helpers ───────────────────────────────────────────────


def _records_recent(limit: int = 5) -> list[dict[str, Any]]:
    """Return the N most recent TaskRecords as summary dicts."""
    store = _get_task_record_store()
    if store is None:
        return []
    try:
        records = store.recent(limit=limit)
        return [_record_summary(r) for r in reversed(records)]
    except Exception as exc:
        _log(f"records_recent failed: {exc}")
        return []


def _records_by_time_window(
    start_iso: str, end_iso: Optional[str] = None
) -> list[dict[str, Any]]:
    """Return TaskRecords within a time window."""
    store = _get_task_record_store()
    if store is None:
        return []
    try:
        records = store.by_time_window(start_iso, end_iso)
        return [_record_summary(r) for r in records]
    except Exception as exc:
        _log(f"records_by_time_window failed: {exc}")
        return []


def _records_search_text(term: str) -> list[dict[str, Any]]:
    """Search TaskRecords by substring in input_summary/final_report."""
    store = _get_task_record_store()
    if store is None:
        return []
    try:
        records = store.search_text(term)
        return [_record_summary(r) for r in records]
    except Exception as exc:
        _log(f"records_search_text failed: {exc}")
        return []


def _record_summary(record: Any) -> dict[str, Any]:
    """Build a concise summary dict from a TaskRecord."""
    report_snippet = (getattr(record, "final_report", None) or "")[:200]
    return {
        "task_id": record.task_id,
        "title": record.input_summary,
        "status": record.status,
        "created_at": record.created_at,
        "final_report_snippet": report_snippet,
        "source": "task_record",
    }


# ─── Interaction query helpers ───────────────────────────────────────────────


def _interactions_recent(limit: int = 10) -> list[dict[str, Any]]:
    """Return recent interactions as summary dicts."""
    archive = _get_interaction_archive()
    if archive is None:
        return []
    try:
        items = archive.recent(limit=limit)
        return [_interaction_summary(i) for i in items]
    except Exception as exc:
        _log(f"interactions_recent failed: {exc}")
        return []


def _interactions_by_time_window(
    start_iso: str, end_iso: Optional[str] = None, limit: int = 50
) -> list[dict[str, Any]]:
    """Return interactions within a time window."""
    archive = _get_interaction_archive()
    if archive is None:
        return []
    try:
        items = archive.by_time_window(start_iso, end_iso, limit=limit)
        return [_interaction_summary(i) for i in items]
    except Exception as exc:
        _log(f"interactions_by_time_window failed: {exc}")
        return []


def _interactions_search_text(term: str, scan_limit: int = 200) -> list[dict[str, Any]]:
    """Scan recent interactions for a substring match on raw_text."""
    archive = _get_interaction_archive()
    if archive is None:
        return []
    lower_term = term.lower()
    try:
        items = archive.recent(limit=scan_limit)
        results: list[dict[str, Any]] = []
        for item in items:
            if lower_term in (item.raw_text or "").lower():
                results.append(_interaction_summary(item))
        return results
    except Exception as exc:
        _log(f"interactions_search_text failed: {exc}")
        return []


def _interaction_summary(interaction: Any) -> dict[str, Any]:
    """Build a concise summary dict from an ArchivedInteraction."""
    snippet = (interaction.raw_text or "")[:150]
    return {
        "archive_id": interaction.archive_id,
        "direction": interaction.direction,
        "raw_text_snippet": snippet,
        "created_at": interaction.created_at,
    }


# ─── Event query helpers ────────────────────────────────────────────────────


def _events_recent(limit: int = 10) -> list[dict[str, Any]]:
    """Return recent events as summary dicts (light usage)."""
    store = _get_event_store()
    if store is None:
        return []
    try:
        items = store.read_recent(limit=limit)
        return [_event_summary(e) for e in items]
    except Exception as exc:
        _log(f"events_recent failed: {exc}")
        return []


def _events_by_correlation(correlation_id: str) -> list[dict[str, Any]]:
    """Return events matching a correlation ID."""
    store = _get_event_store()
    if store is None:
        return []
    try:
        items = store.get_by_correlation(correlation_id)
        return [_event_summary(e) for e in items]
    except Exception as exc:
        _log(f"events_by_correlation failed: {exc}")
        return []


def _event_summary(event: Any) -> dict[str, Any]:
    """Build a concise summary dict from an Event."""
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value
        if hasattr(event.event_type, "value")
        else str(event.event_type),
        "source": getattr(event, "source", ""),
        "created_at": getattr(event, "created_at", ""),
    }


# ─── Keyword extraction ─────────────────────────────────────────────────────

_KEYWORD_EXTRACT_RE = re.compile(
    r"\b(?:about|for|discuss|discussed|discussing|search\s+for)\s+(.+)",
    re.IGNORECASE,
)

_TASK_COUNT_RE = re.compile(r"last\s+(\d+)\s+tasks?", re.IGNORECASE)


def _extract_search_term(text: str) -> str:
    """Extract the search keyword/phrase from a query string."""
    m = _KEYWORD_EXTRACT_RE.search(text)
    if m:
        # Strip trailing punctuation and whitespace
        return m.group(1).strip().rstrip("?!.")
    # Fallback: use the whole query minus common prefixes
    cleaned = (
        re.sub(
            r"^(what\s+did\s+\w+\s+|show\s+me\s+|find\s+|list\s+)",
            "",
            text,
            flags=re.IGNORECASE,
        )
        .strip()
        .rstrip("?!.")
    )
    return cleaned


def _extract_task_count(text: str) -> int:
    """Extract task count from 'last N tasks' pattern. Default 5."""
    m = _TASK_COUNT_RE.search(text)
    if m:
        try:
            return max(1, min(int(m.group(1)), 50))
        except ValueError:
            pass
    return 5


# ─── Correlation ID extraction ───────────────────────────────────────────────

_CORRELATION_RE = re.compile(r"\b([a-f0-9]{24,32})\b", re.IGNORECASE)


def _extract_correlation_id(text: str) -> Optional[str]:
    """Try to extract a hex correlation/pipeline ID from text."""
    m = _CORRELATION_RE.search(text)
    return m.group(1) if m else None


# ─── Core query execution ────────────────────────────────────────────────────


def execute_query(text: str) -> QueryResult:
    """Execute a deterministic query against substrate stores.

    Steps:
    1. Classify intent.
    2. Retrieve matching records from task system, interaction archive,
       and event store based on intent.
    3. Merge results into a QueryResult.
    4. Build a human-readable response_text.

    Never crashes — returns an empty result on any error.
    """
    try:
        return _execute_query_inner(text)
    except Exception as exc:
        _log(f"execute_query failed: {exc}")
        return QueryResult(
            intent=QueryIntent.QUERY_GENERAL.value,
            query_text=text,
            response_text="Query failed — no results available.",
        )


def _execute_query_inner(text: str) -> QueryResult:
    """Internal query execution — may raise."""
    intent = classify_query(text)

    tasks: list[dict[str, Any]] = []
    interactions: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {"intent": intent.value}

    if intent == QueryIntent.QUERY_RECENT_TASKS:
        count = _extract_task_count(text)
        tasks = _tasks_recent(limit=count) + _records_recent(limit=count)
        interactions = _interactions_recent(limit=5)
        metadata["requested_count"] = count

    elif intent == QueryIntent.QUERY_TIME_WINDOW:
        start_iso, end_iso = parse_time_reference(text)
        tasks = _tasks_by_time_window(start_iso, end_iso) + _records_by_time_window(
            start_iso, end_iso
        )
        interactions = _interactions_by_time_window(start_iso, end_iso, limit=50)
        metadata["time_window"] = {"start": start_iso, "end": end_iso}

    elif intent == QueryIntent.QUERY_KEYWORD:
        term = _extract_search_term(text)
        tasks = _tasks_search_text(term) + _records_search_text(term)
        interactions = _interactions_search_text(term)
        metadata["search_term"] = term

    elif intent == QueryIntent.QUERY_WORKFLOW:
        corr_id = _extract_correlation_id(text)
        if corr_id:
            events = _events_by_correlation(corr_id)
            metadata["correlation_id"] = corr_id
        else:
            tasks = _tasks_recent(limit=5) + _records_recent(limit=5)
            events = _events_recent(limit=10)

    else:  # QUERY_GENERAL
        tasks = _tasks_recent(limit=5) + _records_recent(limit=5)
        interactions = _interactions_recent(limit=10)

    # Deduplicate tasks by task_id (prefer task_record source)
    seen_ids: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for t in tasks:
        tid = t.get("task_id", "")
        if tid not in seen_ids:
            seen_ids.add(tid)
            deduped.append(t)
    tasks = deduped

    total = len(tasks) + len(interactions) + len(events)

    result = QueryResult(
        intent=intent.value,
        query_text=text,
        tasks=tasks,
        interactions=interactions,
        events=events,
        total_results=total,
        metadata=metadata,
    )

    result.response_text = _build_response(result)
    return result


# ─── Response builder ────────────────────────────────────────────────────────


def _build_response(result: QueryResult) -> str:
    """Build a concise human-readable summary from a QueryResult.

    Keeps output under 1500 chars.  Lists task summaries (1-line each),
    shows relevant interaction quotes, and handles the empty case.
    """
    parts: list[str] = []

    # Tasks
    if result.tasks:
        parts.append(f"**Tasks ({len(result.tasks)}):**")
        for t in result.tasks[:10]:  # cap display
            status = t.get("status", "?")
            title = t.get("title", "untitled")[:80]
            date = (t.get("created_at") or "")[:10]
            parts.append(f"  - [{status}] {title} ({date})")

    # Interactions
    if result.interactions:
        parts.append(f"\n**Interactions ({len(result.interactions)}):**")
        for i in result.interactions[:5]:  # cap display
            direction = i.get("direction", "?")
            snippet = (i.get("raw_text_snippet") or "")[:100]
            date = (i.get("created_at") or "")[:10]
            parts.append(f'  - [{direction}] "{snippet}" ({date})')

    # Events (light)
    if result.events:
        parts.append(f"\n**Events ({len(result.events)}):**")
        for e in result.events[:5]:
            etype = e.get("event_type", "?")
            source = e.get("source", "?")
            date = (e.get("created_at") or "")[:10]
            parts.append(f"  - {etype} from {source} ({date})")

    if not parts:
        return "No matching records found."

    response = "\n".join(parts)

    # Truncate to ~1500 chars
    if len(response) > 1500:
        response = response[:1497] + "..."

    return response


# ─── Query detection (routing) ───────────────────────────────────────────────

# Patterns that strongly indicate a retrieval query
_QUERY_START_RE = re.compile(
    r"^\s*(what\s+did|what\s+was|what\s+were|what\s+happened|show\s+me|show\s+the|list)\b",
    re.IGNORECASE,
)
_QUERY_RECENT_RE = re.compile(
    r"\b(last\s+task|recent\s+task|last\s+\d+\s+tasks)\b",
    re.IGNORECASE,
)
_QUERY_DISCUSS_RE = re.compile(
    r"\b(what\s+did\s+I\s+say|what\s+did\s+we)\b",
    re.IGNORECASE,
)
_QUERY_DAYS_AGO_RE = re.compile(
    r"\b\d+\s+days?\s+ago\b",
    re.IGNORECASE,
)
_QUERY_YESTERDAY_RE = re.compile(
    r"\byesterday\b",
    re.IGNORECASE,
)
_QUERY_CONTEXT_RE = re.compile(
    r"\b(what|show|happened|find|list)\b",
    re.IGNORECASE,
)


def is_query(text: str) -> bool:
    """Return True if the message looks like a retrieval query rather than a task.

    Conservative — if ambiguous, returns False (let it be a task).

    Detection patterns:
      - Starts with: "what did", "what was", "show me", "show the", "list"
      - Contains: "last task", "recent task", "last N tasks"
      - Contains: "what did I say", "what did we"
      - Contains "N days ago"
      - Contains "yesterday" + query context word
    """
    if not text or len(text.strip()) < 3:
        return False

    stripped = text.strip()

    # Strong starters
    if _QUERY_START_RE.match(stripped):
        return True

    # Recent task patterns
    if _QUERY_RECENT_RE.search(stripped):
        return True

    # Discussion recall
    if _QUERY_DISCUSS_RE.search(stripped):
        return True

    # "N days ago" — strong temporal indicator
    if _QUERY_DAYS_AGO_RE.search(stripped):
        return True

    # "yesterday" needs context — must also have a query-like word
    if _QUERY_YESTERDAY_RE.search(stripped) and _QUERY_CONTEXT_RE.search(stripped):
        return True

    return False


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "QueryIntent",
    "QueryResult",
    "classify_query",
    "execute_query",
    "is_query",
    "parse_time_reference",
]
