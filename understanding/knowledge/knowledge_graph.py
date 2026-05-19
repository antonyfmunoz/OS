"""
KnowledgeGraph — entity relationship layer for EOS.

Connects leads, signals, conversations, outcomes, skills, ventures,
agents, and events into a navigable graph. Memory becomes a list only
without this; with it the system can reason about relationships.

Table: entity_links
    (id UUID, org_id UUID, from_type TEXT, from_id TEXT,
     to_type TEXT, to_id TEXT, relationship TEXT,
     metadata_json JSONB, created_at TIMESTAMPTZ)
"""

import json
from datetime import datetime, timezone

from state.context.context import EntrepreneurOSContext
from state.storage.db import get_conn, resolve_venture, ORG_ID


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class KnowledgeGraph:

    def __init__(self, ctx: EntrepreneurOSContext):
        self.ctx = ctx
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_conn(self.ctx.org_id) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS entity_links (
                    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                    org_id        UUID        NOT NULL,
                    from_type     TEXT        NOT NULL,
                    from_id       TEXT        NOT NULL,
                    to_type       TEXT        NOT NULL,
                    to_id         TEXT        NOT NULL,
                    relationship  TEXT        NOT NULL,
                    metadata_json JSONB,
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_entity_links_from
                ON entity_links (org_id, from_type, from_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_entity_links_to
                ON entity_links (org_id, to_type, to_id)
            """)

    # ─── Write ────────────────────────────────────────────────────────────────

    def link_entities(
        self,
        from_type: str,
        from_id: str,
        to_type: str,
        to_id: str,
        relationship: str,
        metadata: dict | None = None,
    ) -> str:
        """
        Write a directed edge from_entity → to_entity.
        Returns the new link id (UUID string).
        """
        from state.stores.entity_link_store import EntityLinkStore
        return EntityLinkStore().insert_link(
            org_id=self.ctx.org_id,
            from_type=from_type,
            from_id=from_id,
            to_type=to_type,
            to_id=to_id,
            relationship=relationship,
            metadata=metadata,
        )

    # ─── Traversal ────────────────────────────────────────────────────────────

    def get_entity_context(
        self,
        entity_type: str,
        entity_id: str,
        depth: int = 1,
    ) -> dict:
        """
        Traverse entity_links from this entity.
        depth=1: direct connections only.
        depth=2: connections of connections.
        Returns: {entity: {type, id}, connections: [{relationship, direction, connected_entity}]}
        """
        visited: set[tuple] = set()
        return self._traverse(entity_type, entity_id, depth, visited)

    def _traverse(
        self,
        entity_type: str,
        entity_id: str,
        remaining_depth: int,
        visited: set,
    ) -> dict:
        visited.add((entity_type, entity_id))
        connections: list[dict] = []

        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                """
                SELECT to_type, to_id, relationship, metadata_json
                FROM entity_links
                WHERE org_id = %s AND from_type = %s AND from_id = %s
                """,
                (self.ctx.org_id, entity_type, entity_id),
            )
            outbound = cur.fetchall()

            cur.execute(
                """
                SELECT from_type, from_id, relationship, metadata_json
                FROM entity_links
                WHERE org_id = %s AND to_type = %s AND to_id = %s
                """,
                (self.ctx.org_id, entity_type, entity_id),
            )
            inbound = cur.fetchall()

        for row in outbound:
            conn_type = row["to_type"]
            conn_id   = row["to_id"]
            entry: dict = {
                "direction":         "outbound",
                "relationship":      row["relationship"],
                "connected_entity":  {"type": conn_type, "id": conn_id},
                "metadata":          row["metadata_json"],
            }
            if remaining_depth > 1 and (conn_type, conn_id) not in visited:
                entry["connected_entity"]["connections"] = (
                    self._traverse(conn_type, conn_id, remaining_depth - 1, visited)
                    .get("connections", [])
                )
            connections.append(entry)

        for row in inbound:
            conn_type = row["from_type"]
            conn_id   = row["from_id"]
            entry = {
                "direction":         "inbound",
                "relationship":      row["relationship"],
                "connected_entity":  {"type": conn_type, "id": conn_id},
                "metadata":          row["metadata_json"],
            }
            if remaining_depth > 1 and (conn_type, conn_id) not in visited:
                entry["connected_entity"]["connections"] = (
                    self._traverse(conn_type, conn_id, remaining_depth - 1, visited)
                    .get("connections", [])
                )
            connections.append(entry)

        return {
            "entity":      {"type": entity_type, "id": entity_id},
            "connections": connections,
        }

    # ─── Lead journey ─────────────────────────────────────────────────────────

    def get_lead_journey(self, username: str) -> dict:
        """
        Complete traversal for a lead. Finds all signals, conversations,
        and outcomes connected to this username.
        """
        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                """
                SELECT i.id, i.agent_label, i.task_type,
                       i.input_summary, i.output_summary,
                       i.created_at, s.name AS skill_used
                FROM interactions i
                LEFT JOIN skills s ON s.id = i.skill_id
                WHERE i.lead_username = %s AND i.org_id = %s
                ORDER BY i.created_at ASC
                """,
                (username, self.ctx.org_id),
            )
            interactions = [dict(r) for r in cur.fetchall()]

            if not interactions:
                return {
                    "username":          username,
                    "first_signal":      None,
                    "signal_source":     None,
                    "icp_score":         None,
                    "conversations":     [],
                    "current_stage":     "unknown",
                    "outcomes":          [],
                    "total_touchpoints": 0,
                }

            # Outcomes for all interactions
            interaction_ids = [str(r["id"]) for r in interactions]
            placeholders    = ",".join(["%s"] * len(interaction_ids))
            cur.execute(
                f"""
                SELECT interaction_id, outcome_label, score, notes, created_at
                FROM outcomes
                WHERE interaction_id IN ({placeholders})
                ORDER BY created_at ASC
                """,
                interaction_ids,
            )
            outcomes = [dict(r) for r in cur.fetchall()]

            # Human profile (icp score)
            cur.execute(
                """
                SELECT profile_json FROM human_profiles
                WHERE username = %s AND org_id = %s
                ORDER BY updated_at DESC LIMIT 1
                """,
                (username, self.ctx.org_id),
            )
            profile_row = cur.fetchone()

        icp_score = None
        if profile_row and profile_row["profile_json"]:
            p = profile_row["profile_json"]
            if isinstance(p, str):
                try:
                    p = json.loads(p)
                except Exception:
                    p = {}
            icp_score = p.get("icp_score") or p.get("score")

        # Classify as signals vs conversations
        signals = [
            i for i in interactions
            if i.get("task_type") in ("score", "analyze")
            or (i.get("agent_label") or "").startswith("research")
            or i.get("agent_label") == "icp_scorer"
        ]
        conversations = [
            i for i in interactions
            if i.get("task_type") == "generate"
            or (i.get("agent_label") or "").startswith("sales")
            or (i.get("agent_label") or "").startswith("dm")
        ]

        # First signal metadata
        first_signal  = None
        signal_source = None
        if signals:
            ts = signals[0]["created_at"]
            first_signal = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            inp = signals[0].get("input_summary", "") or ""
            if "#" in inp:
                tag = inp.split("#")[1].split()[0].rstrip(".,;:").lower()
                signal_source = f"#{tag}" if tag else None
            elif "@" in inp:
                signal_source = "direct_mention"

        # Pipeline stage from outcomes
        outcome_labels = [o["outcome_label"] for o in outcomes]
        if "closed" in outcome_labels:
            stage = "closed"
        elif "booked" in outcome_labels:
            stage = "booked"
        elif "reply" in outcome_labels or conversations:
            stage = "replied"
        elif signals:
            stage = "contacted"
        else:
            stage = "new"

        def _ts(val) -> str | None:
            return val.isoformat() if hasattr(val, "isoformat") else (str(val) if val else None)

        return {
            "username":     username,
            "first_signal": first_signal,
            "signal_source": signal_source,
            "icp_score":    icp_score,
            "conversations": [
                {
                    "id":         str(c["id"]),
                    "agent":      c.get("agent_label"),
                    "summary":    (c.get("output_summary") or "")[:200],
                    "created_at": _ts(c["created_at"]),
                }
                for c in conversations
            ],
            "current_stage": stage,
            "outcomes": [
                {
                    "type":       o["outcome_label"],
                    "score":      o["score"],
                    "notes":      o.get("notes"),
                    "created_at": _ts(o["created_at"]),
                }
                for o in outcomes
            ],
            "total_touchpoints": len(interactions),
        }

    # ─── Pattern detection ────────────────────────────────────────────────────

    def find_patterns(self, venture_id: str) -> list[dict]:
        """
        Look for recurring patterns in interaction + outcome data.
        Returns patterns with confidence scores.
        High-confidence patterns are logged as HIGH intelligence signals.
        """
        patterns: list[dict] = []
        venture_uuid = resolve_venture(venture_id)
        if not venture_uuid:
            return []

        # ── Pattern 1: Close rate by signal source keyword ──
        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                """
                SELECT i.input_summary, o.outcome_label
                FROM interactions i
                LEFT JOIN outcomes o ON o.interaction_id = i.id
                WHERE i.venture_id = %s AND i.org_id = %s
                  AND i.lead_username IS NOT NULL
                ORDER BY i.created_at DESC
                LIMIT 2000
                """,
                (venture_uuid, self.ctx.org_id),
            )
            rows = cur.fetchall()

        source_outcomes: dict[str, dict] = {}
        for row in rows:
            summary = row["input_summary"] or ""
            label   = row["outcome_label"]
            source  = "unknown"
            if "#" in summary:
                parts = summary.split("#")
                if len(parts) > 1:
                    tag = parts[1].split()[0].rstrip(".,;:").lower()
                    if tag:
                        source = f"#{tag}"
            if source not in source_outcomes:
                source_outcomes[source] = {"total": 0, "closed": 0, "booked": 0, "replied": 0}
            source_outcomes[source]["total"]  += 1
            if label == "closed":
                source_outcomes[source]["closed"]  += 1
            elif label == "booked":
                source_outcomes[source]["booked"]  += 1
            elif label == "reply":
                source_outcomes[source]["replied"] += 1

        total_all   = sum(v["total"]  for v in source_outcomes.values())
        closed_all  = sum(v["closed"] + v["booked"] for v in source_outcomes.values())
        baseline    = closed_all / total_all if total_all >= 10 else None

        for source, data in source_outcomes.items():
            if data["total"] < 5:
                continue
            conversion = (data["closed"] + data["booked"]) / data["total"]
            reply_rate = data["replied"] / data["total"]
            lift = (conversion / baseline) if (baseline and baseline > 0) else 1.0

            if lift >= 1.5 and data["total"] >= 5:
                confidence = min(0.95, 0.5 + (data["total"] / 100) * 0.45)
                patterns.append({
                    "type":              "source_conversion_rate",
                    "description":       (
                        f"Leads from {source} convert at "
                        f"{conversion:.1%} ({lift:.1f}x baseline)"
                    ),
                    "venture_id":        venture_id,
                    "source":            source,
                    "sample_size":       data["total"],
                    "conversion_rate":   round(conversion, 3),
                    "reply_rate":        round(reply_rate, 3),
                    "lift_vs_baseline":  round(lift, 2),
                    "confidence":        round(confidence, 2),
                    "signal_tier":       "HIGH" if confidence >= 0.7 else "NORMAL",
                })

        # ── Pattern 2: Keyword patterns in conversations → booking ──
        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                """
                SELECT i.output_summary, o.outcome_label
                FROM interactions i
                LEFT JOIN outcomes o ON o.interaction_id = i.id
                WHERE i.venture_id = %s AND i.org_id = %s
                  AND (i.agent_label LIKE 'sales%%' OR i.task_type = 'generate')
                LIMIT 1000
                """,
                (venture_uuid, self.ctx.org_id),
            )
            conv_rows = cur.fetchall()

        target_keywords = [
            "structure", "accountability", "discipline", "lost",
            "stuck", "frustrated", "direction", "purpose",
            "consistent", "failing", "help", "change",
        ]
        keyword_hits: dict[str, dict] = {}
        for row in conv_rows:
            summary = (row["output_summary"] or "").lower()
            label   = row["outcome_label"]
            for kw in target_keywords:
                if kw in summary:
                    if kw not in keyword_hits:
                        keyword_hits[kw] = {"total": 0, "booked": 0}
                    keyword_hits[kw]["total"] += 1
                    if label in ("booked", "closed"):
                        keyword_hits[kw]["booked"] += 1

        for kw, data in keyword_hits.items():
            if data["total"] < 3:
                continue
            book_rate = data["booked"] / data["total"]
            if book_rate >= 0.3:
                confidence = min(0.9, 0.4 + (data["total"] / 50) * 0.5)
                patterns.append({
                    "type":        "keyword_booking_signal",
                    "description": (
                        f"Conversations mentioning '{kw}' book at {book_rate:.1%}"
                    ),
                    "venture_id":  venture_id,
                    "keyword":     kw,
                    "sample_size": data["total"],
                    "book_rate":   round(book_rate, 3),
                    "confidence":  round(confidence, 2),
                    "signal_tier": "HIGH" if confidence >= 0.6 else "NORMAL",
                })

        patterns.sort(key=lambda p: p["confidence"], reverse=True)

        # Log high-confidence patterns to Neon events
        high_patterns = [p for p in patterns if p.get("signal_tier") == "HIGH"]
        if high_patterns:
            try:
                from state.memory.memory import AgentMemory
                mem = AgentMemory()
                for p in high_patterns[:5]:
                    mem.log_event(
                        org_id=self.ctx.org_id,
                        event_type="high_confidence_pattern",
                        payload=p,
                    )
            except Exception:
                pass

        return patterns

    # ─── Auto-link ────────────────────────────────────────────────────────────

    def auto_link_interaction(self, interaction_id: str) -> None:
        """
        Called after every interaction is logged.
        Creates entity_links: interaction → venture, skill, agent, lead.
        """
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT i.id, i.venture_id, i.skill_id, i.agent_label,
                           i.lead_username, i.task_type,
                           s.name AS skill_name
                    FROM interactions i
                    LEFT JOIN skills   s ON s.id = i.skill_id
                    WHERE i.id = %s AND i.org_id = %s
                    """,
                    (interaction_id, self.ctx.org_id),
                )
                row = cur.fetchone()

            if not row:
                return

            iid = str(row["id"])

            if row["venture_id"]:
                self.link_entities(
                    "interaction", iid,
                    "venture",     str(row["venture_id"]),
                    "belongs_to_venture",
                )
            if row["skill_id"]:
                self.link_entities(
                    "interaction", iid,
                    "skill",       str(row["skill_id"]),
                    "skill_used_in_interaction",
                    metadata={"skill_name": row["skill_name"]},
                )
            if row["agent_label"]:
                self.link_entities(
                    "interaction",  iid,
                    "agent",        row["agent_label"],
                    "agent_handled_interaction",
                )
            if row["lead_username"]:
                self.link_entities(
                    "interaction",  iid,
                    "lead",         row["lead_username"],
                    "interaction_with_lead",
                )
                # Directional lead link based on task type
                task = row["task_type"] or ""
                if task in ("score", "analyze"):
                    rel = "lead_from_signal"
                elif task == "generate":
                    rel = "signal_led_to_conversation"
                else:
                    rel = "lead_interaction"
                self.link_entities(
                    "lead",         row["lead_username"],
                    "interaction",  iid,
                    rel,
                )

        except Exception as e:
            print(f"[KnowledgeGraph] auto_link_interaction failed: {e}")
