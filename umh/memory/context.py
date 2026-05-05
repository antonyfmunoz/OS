"""Context retrieval layer for UMH memory.

Searches persistent memory store by keyword relevance and recency,
returning scored results suitable for injection into planner prompts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from umh.memory.persistent_store import Memory, get_memory_store


def get_relevant_context(objective: str, limit: int = 5) -> list[dict]:
    """Search memory for entries relevant to the given objective.

    Splits objective into keywords (words > 3 chars), searches for each,
    deduplicates by memory ID, and scores by keyword hit count + recency.
    """
    keywords = [w.lower() for w in objective.split() if len(w) > 3]
    if not keywords:
        return []

    store = get_memory_store()
    hits: dict[str, dict] = {}
    hit_counts: dict[str, int] = {}

    for keyword in keywords:
        results = store.search_memories(keyword, limit=50)
        for mem in results:
            if mem.id not in hits:
                hits[mem.id] = _memory_to_dict(mem)
                hit_counts[mem.id] = 0
            hit_counts[mem.id] += 1

    if not hits:
        return []

    now = datetime.now(timezone.utc)
    scored: list[dict] = []
    for memory_id, entry in hits.items():
        keyword_score = hit_counts[memory_id]
        recency_score = _recency_score(entry["created_at"], now)
        entry["relevance_score"] = round(keyword_score + recency_score, 4)
        scored.append(entry)

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:limit]


def format_context_for_planner(memories: list[dict]) -> str:
    """Format scored memory results for injection into planner context.

    Returns empty string if no memories provided.
    """
    if not memories:
        return ""

    lines = ["Relevant context from memory:"]
    for mem in memories:
        tags_str = f" ({', '.join(mem['tags'])})" if mem.get("tags") else ""
        lines.append(f"- [{mem['type']}] {mem['content']}{tags_str}")
    return "\n".join(lines)


def _memory_to_dict(mem: Memory) -> dict:
    return {
        "id": mem.id,
        "type": mem.type,
        "content": mem.content,
        "tags": mem.tags,
        "created_at": mem.created_at,
    }


def _recency_score(created_at: str, now: datetime) -> float:
    """Score from 0.0 to 1.0 based on how recent the memory is.

    Memories less than 1 hour old get ~1.0; older memories decay toward 0.
    Uses exponential decay with a 24-hour half-life.
    """
    try:
        created = datetime.fromisoformat(created_at)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_hours = max((now - created).total_seconds() / 3600, 0)
        half_life = 24.0
        return 2.0 ** (-age_hours / half_life)
    except (ValueError, TypeError):
        return 0.0
