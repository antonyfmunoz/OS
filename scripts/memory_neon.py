#!/usr/bin/env python3
"""
Neon integration helpers for the memory pipeline.

Thin wrappers around AgentMemory.log_event() and KnowledgeGraph.link_entities().
All calls are try/except guarded — Neon is enhancement, never blocking.

Used by:
    scripts/summarize_conversations.py
    scripts/promote_to_wiki.py
"""

import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import logging

from eos_ai.db import get_conn, ORG_ID

logger = logging.getLogger(__name__)


def record_summary_created(
    session_id: str,
    summary_path: str,
    title: str,
    topics: list[str],
    model_used: str = "unknown",
    provider: str = "unknown",
    salience_score: int | None = None,
    salience_label: str | None = None,
    salience_reasons: list[str] | None = None,
) -> None:
    """Record a summary creation event and link it to its source conversation.

    1. events: event_type='memory_summary_created'
    2. entity_links: summary → conversation (summarizes)
    """
    try:
        payload = {
            "file_path": summary_path,
            "session_id": session_id,
            "title": title,
            "topics": topics,
            "model_used": model_used,
            "provider": provider,
            "salience_score": salience_score,
            "salience_label": salience_label,
            "salience_reasons": salience_reasons,
        }
        with get_conn() as cur:
            cur.execute(
                """
                INSERT INTO events (org_id, event_type, payload_json, handled_by)
                VALUES (%s, 'memory_summary_created', %s, 'memory_pipeline')
                """,
                (ORG_ID, __import__("json").dumps(payload)),
            )
        logger.info("[memory_neon] recorded summary event for %s", session_id[:8])
    except Exception as e:
        logger.warning("[memory_neon] event write failed: %s", e)

    # Link summary → conversation
    _link(
        from_type="summary",
        from_id=_path_to_slug(summary_path),
        to_type="conversation",
        to_id=session_id,
        relationship="summarizes",
    )


def record_wiki_promoted(
    wiki_path: str,
    wiki_slug: str,
    page_type: str,
    source_summary_path: str,
    source_session_id: str | None = None,
    salience_score: int | None = None,
    salience_label: str | None = None,
) -> None:
    """Record a wiki promotion event and link wiki page to its sources.

    1. events: event_type='memory_wiki_promoted'
    2. entity_links: wiki_page → summary (promoted_from)
    3. entity_links: wiki_page → conversation (sourced_from) if session_id available
    """
    try:
        payload = {
            "wiki_path": wiki_path,
            "wiki_slug": wiki_slug,
            "page_type": page_type,
            "source_summary": source_summary_path,
            "source_session": source_session_id,
            "salience_score": salience_score,
            "salience_label": salience_label,
        }
        with get_conn() as cur:
            cur.execute(
                """
                INSERT INTO events (org_id, event_type, payload_json, handled_by)
                VALUES (%s, 'memory_wiki_promoted', %s, 'memory_pipeline')
                """,
                (ORG_ID, __import__("json").dumps(payload)),
            )
        logger.info("[memory_neon] recorded wiki promotion for %s", wiki_slug)
    except Exception as e:
        logger.warning("[memory_neon] event write failed: %s", e)

    # Link wiki_page → summary
    _link(
        from_type="wiki_page",
        from_id=wiki_slug,
        to_type="summary",
        to_id=_path_to_slug(source_summary_path),
        relationship="promoted_from",
    )

    # Link wiki_page → conversation (if session known)
    if source_session_id:
        _link(
            from_type="wiki_page",
            from_id=wiki_slug,
            to_type="conversation",
            to_id=source_session_id,
            relationship="sourced_from",
        )


def _link(
    from_type: str,
    from_id: str,
    to_type: str,
    to_id: str,
    relationship: str,
) -> None:
    """Insert an entity_link edge. Skips duplicates via conflict check."""
    try:
        with get_conn() as cur:
            # Check for existing link to avoid duplicates
            cur.execute(
                """
                SELECT id FROM entity_links
                WHERE org_id = %s
                  AND from_type = %s AND from_id = %s
                  AND to_type = %s AND to_id = %s
                  AND relationship = %s
                LIMIT 1
                """,
                (ORG_ID, from_type, from_id, to_type, to_id, relationship),
            )
            if cur.fetchone():
                return  # already linked
            cur.execute(
                """
                INSERT INTO entity_links
                    (org_id, from_type, from_id, to_type, to_id, relationship)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (ORG_ID, from_type, from_id, to_type, to_id, relationship),
            )
            logger.info(
                "[memory_neon] linked %s:%s -> %s:%s (%s)",
                from_type,
                from_id[:20],
                to_type,
                to_id[:20],
                relationship,
            )
    except Exception as e:
        logger.warning("[memory_neon] entity_link write failed: %s", e)


def _path_to_slug(path: str) -> str:
    """Convert a file path to a slug for entity_links from_id/to_id."""
    # vault/memory/summaries/summary_ce52f933_2026-04-06_topic.md -> summary_ce52f933_2026-04-06_topic
    import os

    return os.path.splitext(os.path.basename(path))[0]


# ─── Retrieval functions ──────────────────────────────────────────────────────
# Query the memory pipeline data in Neon: events, entity_links.
# All calls are try/except guarded — Neon is enhancement, never blocking.


def search_memory_events(
    query: str | None = None,
    event_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    salience_label: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search memory pipeline events with optional filters.

    Args:
        query: Free-text search against payload_json (uses JSONB containment
               or text match on title/topics).
        event_type: Filter by event_type (e.g. 'memory_summary_created').
        date_from: ISO date string for lower bound (inclusive).
        date_to: ISO date string for upper bound (inclusive).
        salience_label: Filter by salience_label in payload ('low', 'medium',
                        'high', 'critical').
        limit: Max results (default 20).

    Returns:
        List of event dicts with id, event_type, payload_json, created_at.
    """
    import json

    try:
        conditions = ["event_type LIKE 'memory_%%'"]
        params: list = []

        if event_type:
            conditions.append("event_type = %s")
            params.append(event_type)

        if date_from:
            conditions.append("created_at >= %s::timestamptz")
            params.append(date_from)

        if date_to:
            conditions.append("created_at <= %s::timestamptz")
            params.append(date_to + "T23:59:59Z")

        if salience_label:
            conditions.append("payload_json->>'salience_label' = %s")
            params.append(salience_label)

        if query:
            # Search across title and topics in payload
            conditions.append(
                "(payload_json->>'title' ILIKE %s "
                "OR payload_json::text ILIKE %s)"
            )
            like_pattern = f"%{query}%"
            params.extend([like_pattern, like_pattern])

        params.append(limit)
        where_clause = " AND ".join(conditions)

        with get_conn() as cur:
            cur.execute(
                f"""
                SELECT id, event_type, payload_json, created_at
                FROM events
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                params,
            )
            rows = cur.fetchall()

        return [
            {
                "id": str(row["id"]),
                "event_type": row["event_type"],
                "payload": row["payload_json"],
                "created_at": row["created_at"].isoformat()
                if row["created_at"]
                else None,
            }
            for row in rows
        ]
    except Exception as e:
        logger.warning("[memory_neon] search_memory_events failed: %s", e)
        return []


def search_summaries(
    query: str | None = None,
    topic: str | None = None,
    salience_label: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    promoted: bool | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search summary events in Neon with salience-aware ranking.

    Results are ordered by salience_score descending, then recency.

    Args:
        query: Free-text search on title.
        topic: Filter by topic (checks if topic appears in topics array).
        salience_label: Filter to specific salience band.
        date_from: ISO date lower bound.
        date_to: ISO date upper bound.
        promoted: If True, only promoted summaries. If False, only non-promoted.
        limit: Max results.

    Returns:
        List of summary dicts ranked by salience then recency.
    """
    import json

    try:
        conditions = ["event_type = 'memory_summary_created'"]
        params: list = []

        if query:
            conditions.append("payload_json->>'title' ILIKE %s")
            params.append(f"%{query}%")

        if topic:
            # Check if topic appears in the topics JSON array
            conditions.append("payload_json->'topics' @> %s::jsonb")
            params.append(json.dumps([topic]))

        if salience_label:
            conditions.append("payload_json->>'salience_label' = %s")
            params.append(salience_label)

        if date_from:
            conditions.append("created_at >= %s::timestamptz")
            params.append(date_from)

        if date_to:
            conditions.append("created_at <= %s::timestamptz")
            params.append(date_to + "T23:59:59Z")

        params.append(limit)
        where_clause = " AND ".join(conditions)

        with get_conn() as cur:
            cur.execute(
                f"""
                SELECT id, payload_json, created_at
                FROM events
                WHERE {where_clause}
                ORDER BY
                    COALESCE((payload_json->>'salience_score')::int, 0) DESC,
                    created_at DESC
                LIMIT %s
                """,
                params,
            )
            rows = cur.fetchall()

        results = []
        for row in rows:
            p = row["payload_json"] if isinstance(row["payload_json"], dict) else {}
            results.append(
                {
                    "id": str(row["id"]),
                    "session_id": p.get("session_id"),
                    "title": p.get("title"),
                    "topics": p.get("topics", []),
                    "salience_score": p.get("salience_score"),
                    "salience_label": p.get("salience_label"),
                    "file_path": p.get("file_path"),
                    "created_at": row["created_at"].isoformat()
                    if row["created_at"]
                    else None,
                }
            )

        # Post-filter promoted status via entity_links
        if promoted is not None:
            promoted_summaries = _get_promoted_summary_slugs()
            if promoted:
                results = [
                    r
                    for r in results
                    if _path_to_slug(r.get("file_path", "")) in promoted_summaries
                ]
            else:
                results = [
                    r
                    for r in results
                    if _path_to_slug(r.get("file_path", "")) not in promoted_summaries
                ]

        return results
    except Exception as e:
        logger.warning("[memory_neon] search_summaries failed: %s", e)
        return []


def get_related_sessions(
    entity_id: str,
    entity_type: str = "summary",
    relationship: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Traverse entity_links to find related nodes.

    Given an entity (e.g. a summary slug), find all connected entities
    via entity_links. Works in both directions (from→to and to→from).

    Args:
        entity_id: The entity ID to search from.
        entity_type: The entity type (summary, wiki_page, conversation).
        relationship: Optional filter on relationship type.
        limit: Max results.

    Returns:
        List of related entity dicts.
    """
    try:
        results = []
        params_fwd: list = [entity_type, entity_id]
        params_rev: list = [entity_type, entity_id]
        rel_filter = ""

        if relationship:
            rel_filter = " AND relationship = %s"
            params_fwd.append(relationship)
            params_rev.append(relationship)

        params_fwd.append(limit)
        params_rev.append(limit)

        # Forward traversal: this entity → related
        with get_conn() as cur:
            cur.execute(
                f"""
                SELECT to_type, to_id, relationship, metadata_json, created_at
                FROM entity_links
                WHERE from_type = %s AND from_id = %s
                {rel_filter}
                ORDER BY created_at DESC LIMIT %s
                """,
                params_fwd,
            )
            for row in cur.fetchall():
                results.append(
                    {
                        "direction": "outgoing",
                        "type": row["to_type"],
                        "id": row["to_id"],
                        "relationship": row["relationship"],
                        "metadata": row["metadata_json"],
                        "created_at": row["created_at"].isoformat()
                        if row["created_at"]
                        else None,
                    }
                )

        # Reverse traversal: related → this entity
        with get_conn() as cur:
            cur.execute(
                f"""
                SELECT from_type, from_id, relationship, metadata_json, created_at
                FROM entity_links
                WHERE to_type = %s AND to_id = %s
                {rel_filter}
                ORDER BY created_at DESC LIMIT %s
                """,
                params_rev,
            )
            for row in cur.fetchall():
                results.append(
                    {
                        "direction": "incoming",
                        "type": row["from_type"],
                        "id": row["from_id"],
                        "relationship": row["relationship"],
                        "metadata": row["metadata_json"],
                        "created_at": row["created_at"].isoformat()
                        if row["created_at"]
                        else None,
                    }
                )

        return results[:limit]
    except Exception as e:
        logger.warning("[memory_neon] get_related_sessions failed: %s", e)
        return []


def get_recurring_themes(
    window_days: int = 30,
    min_occurrences: int = 2,
    limit: int = 20,
) -> list[dict]:
    """Find topics/entities that recur across multiple memory events.

    Queries memory_summary_created events and aggregates topics
    to find the most frequently recurring themes.

    Args:
        window_days: Look back this many days.
        min_occurrences: Minimum number of appearances to include.
        limit: Max themes to return.

    Returns:
        List of dicts with theme name and occurrence count.
    """
    import json

    try:
        with get_conn() as cur:
            cur.execute(
                """
                SELECT payload_json->'topics' as topics
                FROM events
                WHERE event_type = 'memory_summary_created'
                  AND created_at >= NOW() - INTERVAL '%s days'
                """,
                (window_days,),
            )
            rows = cur.fetchall()

        # Count topic occurrences
        from collections import Counter

        topic_counts: Counter = Counter()
        for row in rows:
            topics = row["topics"]
            if isinstance(topics, list):
                for t in topics:
                    if isinstance(t, str):
                        topic_counts[t] += 1

        # Filter and sort
        recurring = [
            {"theme": theme, "occurrences": count}
            for theme, count in topic_counts.most_common()
            if count >= min_occurrences
        ]
        return recurring[:limit]
    except Exception as e:
        logger.warning("[memory_neon] get_recurring_themes failed: %s", e)
        return []


def _get_promoted_summary_slugs() -> set[str]:
    """Return set of summary slugs that have been promoted to wiki."""
    try:
        with get_conn() as cur:
            cur.execute(
                """
                SELECT to_id FROM entity_links
                WHERE to_type = 'summary'
                  AND relationship = 'promoted_from'
                """
            )
            return {row["to_id"] for row in cur.fetchall()}
    except Exception:
        return set()


def ensure_indexes() -> None:
    """Create GIN index on events.payload_json if not exists.

    Safe to call multiple times (idempotent via IF NOT EXISTS).
    Run once during setup or migration.
    """
    try:
        with get_conn() as cur:
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_payload_gin
                ON events USING gin (payload_json)
                """
            )
        logger.info("[memory_neon] GIN index on events.payload_json ensured")
    except Exception as e:
        logger.warning("[memory_neon] index creation failed: %s", e)
