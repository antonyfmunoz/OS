"""
WorldModel — two-layer world model for the Meta Harness.

Canonical layer: shared truths across all orgs (slow-changing, seeded).
Instance layer: per-org observations and learnings (fast-changing).

Instance entries can be promoted to canonical when they prove universal.
"""

import os
import sys
import uuid as _uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


@dataclass
class WorldModelEntry:
    id: str
    entry_type: str  # "pattern", "causal", "strategy", "environment", "entity"
    content: str
    confidence: float  # 0.0 to 1.0
    source: str  # "observed", "promoted", "seeded"
    layer: str  # "canonical" or "instance"
    org_id: str | None  # None for canonical
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    promotion_count: int = 0


class CanonicalWorldModel:
    def __init__(self):
        from execution.transport.storage import get_storage
        self._store = get_storage()

    def _key(self, entry_type: str, entry_id: str) -> str:
        return f"worldmodel:canonical:{entry_type}:{entry_id}"

    def add_entry(self, entry: WorldModelEntry) -> None:
        entry.layer = "canonical"
        entry.org_id = None
        self._store.put(self._key(entry.entry_type, entry.id), asdict(entry))

    def get_entries(self, entry_type: str | None = None) -> list[WorldModelEntry]:
        entries = []
        prefix = "worldmodel:canonical:"
        if entry_type:
            prefix += f"{entry_type}:"
        for key in self._store.all_keys():
            if key.startswith(prefix):
                data = self._store.get(key)
                if data and isinstance(data, dict):
                    entries.append(WorldModelEntry(**data))
        return entries

    def promote_from_instance(self, entry: WorldModelEntry) -> WorldModelEntry:
        """Copy an instance entry to canonical, increment promotion_count."""
        canonical = WorldModelEntry(
            id=str(_uuid.uuid4()),
            entry_type=entry.entry_type,
            content=entry.content,
            confidence=min(entry.confidence + 0.1, 1.0),
            source="promoted",
            layer="canonical",
            org_id=None,
            promotion_count=entry.promotion_count + 1,
        )
        self.add_entry(canonical)
        return canonical

    def search(self, query: str, limit: int = 10) -> list[WorldModelEntry]:
        """Simple keyword search across canonical entries."""
        query_lower = query.lower()
        results = []
        for entry in self.get_entries():
            if query_lower in entry.content.lower():
                results.append(entry)
            if len(results) >= limit:
                break
        return results


class InstanceWorldModel:
    def __init__(self, org_id: str):
        self.org_id = org_id
        from execution.transport.storage import get_storage
        self._store = get_storage()

    def _key(self, entry_type: str, entry_id: str) -> str:
        return f"worldmodel:instance:{self.org_id}:{entry_type}:{entry_id}"

    def add_entry(self, entry: WorldModelEntry) -> None:
        entry.layer = "instance"
        entry.org_id = self.org_id
        self._store.put(self._key(entry.entry_type, entry.id), asdict(entry))

    def get_entries(self, entry_type: str | None = None) -> list[WorldModelEntry]:
        entries = []
        prefix = f"worldmodel:instance:{self.org_id}:"
        if entry_type:
            prefix += f"{entry_type}:"
        for key in self._store.all_keys():
            if key.startswith(prefix):
                data = self._store.get(key)
                if data and isinstance(data, dict):
                    entries.append(WorldModelEntry(**data))
        return entries

    def propose_promotion(self, entry_id: str) -> bool:
        """Mark an instance entry as promotion-candidate. Returns True if found."""
        for key in self._store.all_keys():
            if key.startswith(f"worldmodel:instance:{self.org_id}:") and key.endswith(f":{entry_id}"):
                data = self._store.get(key)
                if data:
                    data["promotion_count"] = data.get("promotion_count", 0) + 1
                    data["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._store.put(key, data)
                    return True
        return False

    def get_user_model(self, user_id: str) -> dict:
        """Get all entity entries related to a specific user."""
        entities = self.get_entries(entry_type="entity")
        return {
            "user_id": user_id,
            "entries": [e for e in entities if user_id in e.content],
        }


class WorldModel:
    """Unified access to both canonical and instance world models."""

    def __init__(self, org_id: str):
        self.org_id = org_id
        self.canonical = CanonicalWorldModel()
        self.instance = InstanceWorldModel(org_id)
        self._ensure_seeded()

    def _ensure_seeded(self) -> None:
        """Seed canonical model if empty."""
        existing = self.canonical.get_entries()
        if existing:
            return
        seeds = [
            WorldModelEntry(
                id="seed_stage_progression",
                entry_type="pattern",
                content="Business stages progress linearly: validation \u2192 repeatability \u2192 scale \u2192 optimization \u2192 expansion. Skipping stages leads to structural failure.",
                confidence=0.95,
                source="seeded",
                layer="canonical",
                org_id=None,
            ),
            WorldModelEntry(
                id="seed_founder_bottleneck",
                entry_type="causal",
                content="At pre-revenue stage, the founder is always the binding constraint. Removing the founder from direct sales before proving the sale works guarantees failure.",
                confidence=0.90,
                source="seeded",
                layer="canonical",
                org_id=None,
            ),
            WorldModelEntry(
                id="seed_outreach_before_content",
                entry_type="strategy",
                content="Direct outreach closes faster than content marketing at stage 1. Content is a compounding asset that pays off at stage 2+. The ratio should be 80% outreach / 20% content until first 10 sales.",
                confidence=0.85,
                source="seeded",
                layer="canonical",
                org_id=None,
            ),
            WorldModelEntry(
                id="seed_unit_economics",
                entry_type="pattern",
                content="Every transaction must be individually profitable before scaling. CAC must be known and below LTV/3 before any paid acquisition. Bootstrapped businesses cannot run negative unit economics.",
                confidence=0.95,
                source="seeded",
                layer="canonical",
                org_id=None,
            ),
            WorldModelEntry(
                id="seed_feedback_loop",
                entry_type="causal",
                content="Systems without feedback loops cannot self-correct. Every action should produce observable outcomes that feed back into the next decision. Delayed feedback distorts causality attribution.",
                confidence=0.90,
                source="seeded",
                layer="canonical",
                org_id=None,
            ),
        ]
        for seed in seeds:
            self.canonical.add_entry(seed)

    def update_from_interaction(self, message: str, response: str, outcome: str | None = None) -> None:
        """Extract learnings from an interaction and store in instance model."""
        # Simple heuristic: if message mentions a pattern or strategy, create an entry
        entry_type = "pattern"
        if any(w in message.lower() for w in ["because", "causes", "leads to", "results in"]):
            entry_type = "causal"
        elif any(w in message.lower() for w in ["should", "strategy", "approach", "plan"]):
            entry_type = "strategy"

        entry = WorldModelEntry(
            id=str(_uuid.uuid4()),
            entry_type=entry_type,
            content=f"Interaction: {message[:200]} \u2192 Response: {response[:200]}",
            confidence=0.3,  # low confidence for raw observations
            source="observed",
            layer="instance",
            org_id=self.org_id,
        )
        self.instance.add_entry(entry)

    def get_context_for_prompt(self, query: str) -> str:
        """Build a world model context string for injection into the system prompt."""
        parts = []

        # Canonical entries (high confidence, universal)
        canonical = self.canonical.search(query, limit=3)
        if canonical:
            lines = ["## World Model (canonical)"]
            for entry in canonical:
                lines.append(f"[{entry.entry_type}|{entry.confidence:.0%}] {entry.content[:200]}")
            parts.append("\n".join(lines))

        # Instance entries (per-org observations)
        instance = self.instance.get_entries()
        # Filter for recent and relevant
        relevant = [e for e in instance if query.lower().split()[0] in e.content.lower()] if query.strip() else []
        if relevant:
            lines = ["## World Model (instance)"]
            for entry in relevant[:3]:
                lines.append(f"[{entry.entry_type}|{entry.confidence:.0%}] {entry.content[:200]}")
            parts.append("\n".join(lines))

        return "\n\n".join(parts) if parts else ""


if __name__ == "__main__":
    wm = WorldModel(org_id="lyfe_institute")
    wm.update_from_interaction("test message about strategy", "test response about approach")
    entries = wm.canonical.get_entries()
    print(f"Canonical entries: {len(entries)}")
    for e in entries:
        print(f"  [{e.entry_type}] {e.content[:80]}...")
    entries = wm.instance.get_entries()
    print(f"Instance entries: {len(entries)}")
    ctx = wm.get_context_for_prompt("stage progression")
    print(f"\nPrompt context length: {len(ctx)} chars")
    if ctx:
        print(ctx[:300])
    print("\nWorldModel OK")
