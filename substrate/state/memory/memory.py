"""
Persistent memory for OS agents — backed by Neon (PostgreSQL).

Unified data layer: Python AI layer and TypeScript SaaS backend write to the
same Postgres instance through the same RLS firewall. SQLite is gone.

Tables used:
  interactions    — every agent call logged with org/venture/skill/agent context
  outcomes        — RLHF signal: reply/no_reply/booked/closed/ignored
  events          — orphaned replies (no matching interaction) stored here
  human_profiles  — per-lead psychological/behavioral profile JSON
  embeddings      — vector(384), written by EmbeddingEngine.embed_interaction()
                    using fastembed BAAI/bge-small-en-v1.5 (384-dim). Read path
                    is EmbeddingEngine.semantic_search(). See embedding_engine.py.

Public interface is unchanged — callers (agent_runtime, icp_scorer, dm_monitor,
calendly_webhook) do not need modification.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from execution.runtime.agent_runtime import AgentResult

from substrate.state.storage.db import get_conn, resolve_venture, resolve_skill, ORG_ID, USER_ID

# SQLite path — still used by event_bus, gateway, and human_intelligence
# for local-first event persistence and human profiles.
DB_PATH = Path(__file__).parent / "memory.db"


_OUTCOME_TYPES = {
    "reply", "no_reply", "booked", "closed", "ignored",
    "showed", "noshow", "lost", "opened",
}

# Map Python outcome types → Neon outcome_type enum values
# outcome_type enum: positive | negative | neutral | skipped
_OUTCOME_MAP: dict[str, str] = {
    "reply":    "positive",
    "booked":   "positive",
    "closed":   "positive",
    "showed":   "positive",
    "opened":   "neutral",
    "no_reply": "neutral",
    "ignored":  "skipped",
    "noshow":   "negative",
    "lost":     "negative",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens_to_neon(tokens_json: str | dict) -> dict:
    """
    Convert Python token dict {input, output, total} to Neon schema
    {prompt, completion, total, cost_usd}.
    """
    if isinstance(tokens_json, str):
        try:
            t = json.loads(tokens_json)
        except (json.JSONDecodeError, TypeError):
            t = {}
    else:
        t = tokens_json or {}
    return {
        "prompt":     t.get("input",  t.get("prompt",     0)),
        "completion": t.get("output", t.get("completion", 0)),
        "total":      t.get("total",  0),
        "cost_usd":   t.get("cost_usd", 0.0),
    }


class AgentMemory:
    """
    Persistent memory backed by Neon PostgreSQL.

    All writes are RLS-scoped to EOS_ORG_ID via the db.get_conn() context
    manager. interaction_id is now a UUID string instead of an integer.
    """

    # ─── Write: AgentRuntime path ─────────────────────────────────────────────

    def log(
        self,
        agent_result: "AgentResult",
        venture_id: str | None,
        input_summary: str,
        agent: str = "default",
        task_type: str = "unknown",
        lead_username: str | None = None,
    ) -> str:
        """
        Called automatically by AgentRuntime.run(). Returns interaction_id (UUID).
        """
        output_summary = agent_result.output[:300].replace("\n", " ")
        tokens_neon    = _tokens_to_neon(agent_result.tokens_used)

        with get_conn() as cur:
            # Resolve inside the connection — caches are loaded by get_conn()
            venture_uuid = resolve_venture(venture_id)
            skill_uuid   = resolve_skill(agent_result.skill_used)
            cur.execute(
                """
                INSERT INTO interactions
                    (org_id, user_id, venture_id, agent_id, skill_id,
                     task_type, model_used, input_summary, output_summary,
                     tokens_json, agent_label, lead_username)
                VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    ORG_ID, USER_ID, venture_uuid, skill_uuid,
                    task_type, agent_result.model_used,
                    input_summary, output_summary,
                    json.dumps(tokens_neon),
                    agent, lead_username,
                ),
            )
            interaction_id = str(cur.fetchone()["id"])

        # Async embed — never blocks the main log() call
        content_to_embed = (
            f"{input_summary or ''} {output_summary or ''}"
        ).strip()
        if content_to_embed:
            import threading
            from substrate.understanding.embedding.embedding_engine import EmbeddingEngine

            def _embed_async(iid: str, content: str, oid: str) -> None:
                EmbeddingEngine().embed_interaction(iid, content, oid)

            threading.Thread(
                target=_embed_async,
                args=(interaction_id, content_to_embed, ORG_ID),
                daemon=True,
            ).start()

        # Auto-link interaction into knowledge graph
        try:
            from substrate.state.context.context import load_context_from_env
            from substrate.understanding.knowledge.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph(load_context_from_env())
            kg.auto_link_interaction(interaction_id)
        except Exception:
            pass  # knowledge graph is enhancement — never block log()

        # Auto-refresh user profile every 10 interactions
        try:
            with get_conn() as _cur:
                _cur.execute(
                    "SELECT COUNT(*) AS cnt FROM interactions WHERE org_id = %s",
                    (ORG_ID,),
                )
                _total = int((_cur.fetchone() or {}).get("cnt", 0))
            if _total > 0 and _total % 10 == 0:
                import threading as _threading

                def _refresh_user_profile() -> None:
                    try:
                        from substrate.state.context.context import load_context_from_env as _lctx
                        from substrate.state.profiles.user_model import UserModel as _UM
                        _UM(_lctx()).update_profile()
                    except Exception:
                        pass

                _threading.Thread(target=_refresh_user_profile, daemon=True).start()
        except Exception:
            pass  # never block log()

        return interaction_id

    # ─── Write: icp_scorer path ───────────────────────────────────────────────

    def log_lead_scored(
        self,
        username: str,
        venture_id: str,
        comment_text: str,
        score: int,
        archetype: str,
        model_used: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> str:
        """
        Called by icp_scorer when a lead is qualified and a lead file is created.
        Returns the new interaction_id (UUID) — store it in the lead file if needed.
        """
        tokens_neon    = _tokens_to_neon({
            "input":  input_tokens,
            "output": output_tokens,
            "total":  input_tokens + output_tokens,
        })
        input_summary  = comment_text[:200].replace("\n", " ")
        output_summary = f"score={score}, archetype={archetype}"

        with get_conn() as cur:
            venture_uuid = resolve_venture(venture_id)
            skill_uuid   = resolve_skill("analyze_icp_signal")
            cur.execute(
                """
                INSERT INTO interactions
                    (org_id, user_id, venture_id, agent_id, skill_id,
                     task_type, model_used, input_summary, output_summary,
                     tokens_json, agent_label, lead_username)
                VALUES (%s, %s, %s, NULL, %s, 'score', %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    ORG_ID, USER_ID, venture_uuid, skill_uuid,
                    model_used, input_summary, output_summary,
                    json.dumps(tokens_neon),
                    "icp_scorer", username,
                ),
            )
            return str(cur.fetchone()["id"])

    # ─── Proactive milestone alert ────────────────────────────────────────────

    @staticmethod
    def _fire_milestone_alert(outcome_count: int) -> None:
        """Fire a Telegram alert when outcome count hits a milestone (background)."""
        if outcome_count not in (10, 25, 50, 100):
            return
        import threading

        def _alert() -> None:
            try:
                from control_plane.orchestrator.orchestrator import check_outcome_milestone
                from substrate.state.context.context import load_context_from_env
                check_outcome_milestone(load_context_from_env(), outcome_count)
            except Exception:
                pass

        threading.Thread(target=_alert, daemon=True).start()

    # ─── Write: outcome logging ───────────────────────────────────────────────

    def log_outcome(
        self,
        interaction_id: str,
        outcome_type: str,
        score: float | None = None,
        notes: str | None = None,
    ) -> str:
        """
        Log an outcome against a prior interaction.
        outcome_type: reply | no_reply | booked | closed | ignored
        score: 1.0 = positive signal, 0.0 = negative
        Returns outcome_id (UUID).
        """
        if outcome_type not in _OUTCOME_TYPES:
            raise ValueError(
                f"Invalid outcome_type '{outcome_type}'. "
                f"Must be one of: {sorted(_OUTCOME_TYPES)}"
            )
        neon_type = _OUTCOME_MAP[outcome_type]

        with get_conn() as cur:
            # Verify the interaction exists and belongs to this org (RLS enforces)
            cur.execute(
                "SELECT id FROM interactions WHERE id = %s",
                (interaction_id,),
            )
            if cur.fetchone() is None:
                raise ValueError(
                    f"interaction_id {interaction_id} not found in Neon "
                    f"(or does not belong to org {ORG_ID})"
                )
            cur.execute(
                """
                INSERT INTO outcomes
                    (interaction_id, org_id, outcome_type, outcome_label, score, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (interaction_id, ORG_ID, neon_type, outcome_type, score, notes),
            )
            outcome_id = str(cur.fetchone()["id"])
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM outcomes WHERE org_id = %s",
                (ORG_ID,),
            )
            self._fire_milestone_alert(cur.fetchone()["cnt"] or 0)
            return outcome_id

    def log_standalone_outcome(
        self,
        outcome_type: str,
        score: float | None = None,
        notes: str | None = None,
        source: str = "manual",
    ) -> str:
        """
        Log an outcome with no linked interaction_id.
        Used for manual /outcome Telegram commands and any event where
        the originating interaction is unknown.
        Returns outcome_id (UUID).
        """
        if outcome_type not in _OUTCOME_TYPES:
            raise ValueError(
                f"Invalid outcome_type '{outcome_type}'. "
                f"Must be one of: {sorted(_OUTCOME_TYPES)}"
            )
        neon_type = _OUTCOME_MAP[outcome_type]
        notes_with_source = f"[{source}] {notes}" if notes else f"[{source}]"

        with get_conn() as cur:
            cur.execute(
                """
                INSERT INTO outcomes
                    (org_id, outcome_type, outcome_label, score, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (ORG_ID, neon_type, outcome_type, score, notes_with_source),
            )
            outcome_id = str(cur.fetchone()["id"])

        # Chain 1b: milestone alert
        with get_conn() as cur:
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM outcomes WHERE org_id = %s",
                (ORG_ID,),
            )
            self._fire_milestone_alert(cur.fetchone()["cnt"] or 0)

        # Chain 2: if notes contains @username, refresh their profile async
        if notes and notes.lstrip().startswith("@"):
            username = notes.lstrip().split()[0].lstrip("@")
            if username:
                import threading
                def _refresh_profile(uname: str) -> None:
                    try:
                        from substrate.understanding.intelligence.human_intelligence import HumanIntelligenceEngine
                        from substrate.state.context.context import load_context_from_env
                        ctx = load_context_from_env()
                        hie = HumanIntelligenceEngine(ctx)
                        hie.build_profile(uname)
                    except Exception:
                        pass
                threading.Thread(
                    target=_refresh_profile,
                    args=(username,),
                    daemon=True,
                ).start()

        return outcome_id

    def log_orphaned_reply(
        self,
        username: str,
        outcome_type: str = "reply",
        score: float | None = 1.0,
        notes: str | None = None,
    ) -> str:
        """
        Log an outcome with no matching interaction_id.
        Stored in the events table for manual reconciliation.
        Returns event_id (UUID).
        """
        payload = {
            "lead_username": username,
            "outcome_type":  outcome_type,
            "score":         score,
            "notes":         notes,
        }
        with get_conn() as cur:
            cur.execute(
                """
                INSERT INTO events (org_id, event_type, payload_json, handled_by)
                VALUES (%s, 'orphaned_reply', %s, 'python_layer')
                RETURNING id
                """,
                (ORG_ID, json.dumps(payload)),
            )
            event_id = str(cur.fetchone()["id"])

        # Chain 2: refresh this lead's behavioral profile async
        import threading
        def _refresh_orphaned_profile(uname: str) -> None:
            try:
                from substrate.understanding.intelligence.human_intelligence import HumanIntelligenceEngine
                from substrate.state.context.context import load_context_from_env
                ctx = load_context_from_env()
                hie = HumanIntelligenceEngine(ctx)
                hie.build_profile(uname)
            except Exception:
                pass
        threading.Thread(
            target=_refresh_orphaned_profile,
            args=(username,),
            daemon=True,
        ).start()

        return event_id

    def log_event(
        self,
        org_id: str,
        event_type: str,
        payload: dict,
        handled_by: str = "cognitive_loop",
    ) -> str:
        """
        Write a structured event to the Neon events table.
        Returns event_id (UUID).
        """
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO events (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (org_id, event_type, json.dumps(payload), handled_by),
            )
            return str(cur.fetchone()["id"])

    def merge_event_payload(
        self,
        org_id: str,
        event_id: str,
        updates: dict,
    ) -> bool:
        """
        Atomically merge key-value pairs into an event's payload_json.
        Uses JSONB || for server-side merge — no read step, no race condition.
        Returns True on success.
        """
        with get_conn(org_id) as cur:
            cur.execute(
                """
                UPDATE events
                SET payload_json = payload_json || %s::jsonb
                WHERE id = %s AND org_id = %s
                """,
                (json.dumps(updates), event_id, org_id),
            )
            return cur.rowcount > 0

    # ─── Read ──────────────────────────────────────────────────────────────────

    def get_interaction_for_lead(
        self,
        username: str,
        venture_id: str | None = None,
    ) -> dict | None:
        """
        Look up the most recent interaction for a lead by username.
        Used by dm_monitor and calendly_webhook to resolve interaction_id.
        Returns a plain dict or None if not found.
        """
        with get_conn() as cur:
            if venture_id:
                cur.execute(
                    """
                    SELECT * FROM interactions
                    WHERE lead_username = %s AND venture_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (username, resolve_venture(venture_id)),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM interactions
                    WHERE lead_username = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (username,),
                )
            row = cur.fetchone()
        if row is None:
            return None
        d = dict(row)
        d["id"] = str(d["id"])
        d["tokens_used"] = d.pop("tokens_json", {})
        return d

    def get_recent(
        self,
        venture_id: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Return recent interactions, optionally filtered by venture."""
        with get_conn() as cur:
            if venture_id:
                cur.execute(
                    """
                    SELECT * FROM interactions
                    WHERE venture_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (resolve_venture(venture_id), limit),
                )
            else:
                cur.execute(
                    "SELECT * FROM interactions ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
            rows = cur.fetchall()

        result = []
        for row in rows:
            d = dict(row)
            d["id"] = str(d["id"])
            d["tokens_used"] = d.pop("tokens_json", {})
            result.append(d)
        return result

    def get_outcomes_for(self, interaction_id: str) -> list[dict]:
        """Return all outcomes logged against a specific interaction."""
        with get_conn() as cur:
            cur.execute(
                """
                SELECT * FROM outcomes
                WHERE interaction_id = %s
                ORDER BY created_at
                """,
                (interaction_id,),
            )
            rows = cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["id"] = str(d["id"])
            d["interaction_id"] = str(d["interaction_id"])
            # Surface Python outcome type (outcome_label) as outcome_type for callers
            if d.get("outcome_label"):
                d["outcome_type"] = d["outcome_label"]
            result.append(d)
        return result

    def get_orphaned_replies(self, limit: int = 50) -> list[dict]:
        """Return unreconciled orphaned replies for manual review."""
        with get_conn() as cur:
            cur.execute(
                """
                SELECT id, payload_json, created_at
                FROM events
                WHERE event_type = 'orphaned_reply'
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        result = []
        for row in rows:
            d = dict(row["payload_json"])
            d["id"] = str(row["id"])
            d["timestamp"] = row["created_at"].isoformat() if row["created_at"] else None
            result.append(d)
        return result

    # ─── Semantic retrieval ───────────────────────────────────────────────────

    def embed_and_store(self, interaction_id: str, text: str) -> bool:
        """
        Embed text and persist the vector for interaction_id.

        Delegates to EmbeddingEngine.embed_interaction() — the canonical
        write path. Schema is vector(384); fastembed BAAI/bge-small-en-v1.5
        produces matching 384-dim vectors. Returns True on success.
        """
        from substrate.understanding.embedding.embedding_engine import EmbeddingEngine
        return EmbeddingEngine().embed_interaction(interaction_id, text, ORG_ID)

    def semantic_search(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.55,
        venture_id: str = None,
    ) -> list[dict]:
        """
        Search past interactions by semantic similarity.
        Uses cosine distance on 384-dim fastembed vectors.
        Returns ranked results — most similar first.
        """
        try:
            from substrate.understanding.embedding.embedding_engine import EmbeddingEngine
            engine = EmbeddingEngine()
            query_vec = engine.embed(query)
            if not query_vec:
                return []

            vec_literal = "[" + ",".join(str(round(v, 8)) for v in query_vec) + "]"

            with get_conn() as cur:
                # Build SQL inside get_conn — cache is guaranteed loaded here
                params: list = [vec_literal, vec_literal, min_similarity]
                venture_filter = ""
                if venture_id:
                    resolved_venture_id = resolve_venture(venture_id)
                    if resolved_venture_id:
                        try:
                            import uuid as _uuid_lib
                            _uuid_lib.UUID(resolved_venture_id)
                            venture_filter = " AND i.venture_id = %s"
                            params.append(resolved_venture_id)
                        except ValueError:
                            pass  # Not a valid UUID — skip filter silently
                params.append(limit)
                sql = f"""
                    SELECT
                        e.interaction_id,
                        i.input_summary,
                        i.output_summary,
                        i.agent_label,
                        i.skill_id,
                        i.venture_id,
                        i.created_at,
                        1 - (e.embedding <=> %s::vector) AS similarity
                    FROM embeddings e
                    JOIN interactions i ON i.id = e.interaction_id
                    WHERE 1 - (e.embedding <=> %s::vector) >= %s
                    {venture_filter}
                    ORDER BY similarity DESC LIMIT %s
                """
                cur.execute(sql, params)
                rows = cur.fetchall()

            return [
                {
                    "interaction_id": str(row["interaction_id"]),
                    "input_summary": row["input_summary"],
                    "output_summary": row["output_summary"],
                    "agent_label": row["agent_label"],
                    "skill_id": str(row["skill_id"]) if row["skill_id"] else None,
                    "venture_id": str(row["venture_id"]) if row["venture_id"] else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "similarity": round(float(row["similarity"]), 4),
                }
                for row in rows
            ]

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"semantic_search failed: {e}")
            return []

    # ─── RLHF analytics ───────────────────────────────────────────────────────

    def reply_rate_by_skill(self) -> list[dict]:
        """RLHF aggregate: reply rate per skill, sorted by reply_rate desc."""
        with get_conn() as cur:
            cur.execute(
                """
                SELECT
                    s.name                                              AS skill_used,
                    COUNT(DISTINCT i.id)                               AS total_interactions,
                    SUM(CASE WHEN o.outcome_label = 'reply' THEN 1 ELSE 0 END) AS replies,
                    ROUND(
                        100.0
                        * SUM(CASE WHEN o.outcome_label = 'reply' THEN 1 ELSE 0 END)
                        / NULLIF(COUNT(DISTINCT i.id), 0),
                        1
                    )                                                  AS reply_rate_pct
                FROM interactions i
                LEFT JOIN outcomes o ON o.interaction_id = i.id
                LEFT JOIN skills   s ON s.id = i.skill_id
                WHERE i.skill_id IS NOT NULL
                GROUP BY s.name
                ORDER BY reply_rate_pct DESC NULLS LAST
                """
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]


# ─── ConversationMemory ───────────────────────────────────────────────────────
# Word-for-word storage of every message. Never summaries.
# Always retrievable. Always searchable. Foundation for compounding intelligence.

import uuid as _uuid
from dataclasses import dataclass as _dataclass
from typing import Optional as _Optional


@_dataclass
class Message:
    id: str
    org_id: str
    session_id: str
    sequence_num: int
    role: str          # 'user' | 'assistant'
    content: str       # word for word, always
    channel: str       # discord, telegram, voice
    agent: str
    created_at: object
    metadata: dict


class ConversationMemory:
    """
    Persistent word-for-word conversation store backed by Neon.

    Every message stored. Not summaries. Not truncated.
    The complete record — always retrievable, always searchable.
    """

    def __init__(self, ctx: object) -> None:
        self.ctx = ctx

    def store(
        self,
        session_id: str,
        role: str,
        content: str,
        channel: str = 'unknown',
        agent: str = 'executive_assistant',
        metadata: dict | None = None,
    ) -> str:
        """Store a message word for word. Returns message id."""
        try:
            meta = metadata or {}
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    '''
                    SELECT COALESCE(MAX(sequence_num), 0) + 1 AS next_seq
                    FROM messages
                    WHERE org_id = %s AND session_id = %s
                    ''',
                    (self.ctx.org_id, session_id),
                )
                seq = cur.fetchone()['next_seq']
                message_id = str(_uuid.uuid4())
                cur.execute(
                    '''
                    INSERT INTO messages (
                        id, org_id, session_id, sequence_num,
                        role, content, channel, agent, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    (
                        message_id, self.ctx.org_id, session_id, seq,
                        role, content, channel, agent,
                        json.dumps(meta),
                    ),
                )
                # Embed and store
                try:
                    from substrate.understanding.embedding.embedder import embed
                    vec = embed(content)
                    cur.execute(
                        'UPDATE messages SET embedding = %s WHERE id = %s',
                        (vec.tolist(), message_id),
                    )
                except Exception as e:
                    print(f'[ConversationMemory] embed failed: {e}')
                return message_id
        except Exception as e:
            print(f'[ConversationMemory] store failed: {e}')
            return ''

    def get_session(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[Message]:
        """Return all messages in session order."""
        try:
            with get_conn(self.ctx.org_id) as cur:
                q = '''
                    SELECT id, org_id, session_id, sequence_num,
                           role, content, channel, agent, created_at, metadata
                    FROM messages
                    WHERE org_id = %s AND session_id = %s
                    ORDER BY sequence_num ASC
                '''
                params: list = [self.ctx.org_id, session_id]
                if limit:
                    q += ' LIMIT %s'
                    params.append(limit)
                cur.execute(q, params)
                return [self._row(r) for r in cur.fetchall()]
        except Exception as e:
            print(f'[ConversationMemory] get_session failed: {e}')
            return []

    def get_recent(
        self,
        limit: int = 10,
        channel: str | None = None,
    ) -> list[Message]:
        """Return most recent messages across sessions."""
        try:
            with get_conn(self.ctx.org_id) as cur:
                if channel:
                    cur.execute(
                        '''
                        SELECT id, org_id, session_id, sequence_num,
                               role, content, channel, agent, created_at, metadata
                        FROM messages
                        WHERE org_id = %s AND channel = %s
                        ORDER BY created_at DESC LIMIT %s
                        ''',
                        (self.ctx.org_id, channel, limit),
                    )
                else:
                    cur.execute(
                        '''
                        SELECT id, org_id, session_id, sequence_num,
                               role, content, channel, agent, created_at, metadata
                        FROM messages
                        WHERE org_id = %s
                        ORDER BY created_at DESC LIMIT %s
                        ''',
                        (self.ctx.org_id, limit),
                    )
                return [self._row(r) for r in cur.fetchall()]
        except Exception as e:
            print(f'[ConversationMemory] get_recent failed: {e}')
            return []

    def get_by_position(
        self,
        session_id: str,
        position: int,
    ) -> _Optional[Message]:
        """
        Get message by position in session.
        position 1 = first message, -1 = last, -2 = two back.
        """
        try:
            with get_conn(self.ctx.org_id) as cur:
                if position > 0:
                    cur.execute(
                        '''
                        SELECT id, org_id, session_id, sequence_num,
                               role, content, channel, agent, created_at, metadata
                        FROM messages
                        WHERE org_id = %s AND session_id = %s
                        ORDER BY sequence_num ASC
                        LIMIT 1 OFFSET %s
                        ''',
                        (self.ctx.org_id, session_id, position - 1),
                    )
                else:
                    cur.execute(
                        '''
                        SELECT id, org_id, session_id, sequence_num,
                               role, content, channel, agent, created_at, metadata
                        FROM messages
                        WHERE org_id = %s AND session_id = %s
                        ORDER BY sequence_num DESC
                        LIMIT 1 OFFSET %s
                        ''',
                        (self.ctx.org_id, session_id, abs(position) - 1),
                    )
                row = cur.fetchone()
                return self._row(row) if row else None
        except Exception as e:
            print(f'[ConversationMemory] get_by_position failed: {e}')
            return None

    def search(
        self,
        query: str,
        limit: int = 10,
        session_id: str | None = None,
    ) -> list[Message]:
        """Full-text search across all stored messages."""
        try:
            with get_conn(self.ctx.org_id) as cur:
                if session_id:
                    cur.execute(
                        '''
                        SELECT id, org_id, session_id, sequence_num,
                               role, content, channel, agent, created_at, metadata
                        FROM messages
                        WHERE org_id = %s AND session_id = %s
                          AND to_tsvector('english', content)
                              @@ plainto_tsquery('english', %s)
                        ORDER BY created_at DESC LIMIT %s
                        ''',
                        (self.ctx.org_id, session_id, query, limit),
                    )
                else:
                    cur.execute(
                        '''
                        SELECT id, org_id, session_id, sequence_num,
                               role, content, channel, agent, created_at, metadata
                        FROM messages
                        WHERE org_id = %s
                          AND to_tsvector('english', content)
                              @@ plainto_tsquery('english', %s)
                        ORDER BY created_at DESC LIMIT %s
                        ''',
                        (self.ctx.org_id, query, limit),
                    )
                return [self._row(r) for r in cur.fetchall()]
        except Exception as e:
            print(f'[ConversationMemory] search failed: {e}')
            return []

    def get_session_summary(self, session_id: str) -> dict:
        """Return metadata about a session."""
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    '''
                    SELECT COUNT(*) AS total,
                           MIN(created_at) AS started,
                           MAX(created_at) AS last_active
                    FROM messages
                    WHERE org_id = %s AND session_id = %s
                    ''',
                    (self.ctx.org_id, session_id),
                )
                row = cur.fetchone()
                return {
                    'session_id':     session_id,
                    'total_messages': row['total'],
                    'started_at':     str(row['started']),
                    'last_active':    str(row['last_active']),
                }
        except Exception as e:
            print(f'[ConversationMemory] get_session_summary failed: {e}')
            return {}

    def format_session_for_prompt(
        self,
        session_id: str,
        limit: int = 20,
    ) -> str:
        """Format recent session history for injection into cognitive loop."""
        messages = self.get_session(session_id, limit=limit)
        if not messages:
            return ''
        lines = ['CONVERSATION HISTORY:']
        for msg in messages:
            prefix = 'Founder' if msg.role == 'user' else 'AI'
            lines.append(f'{prefix}: {msg.content}')
        return '\n'.join(lines)

    def format_channel_history_for_prompt(
        self,
        channel: str,
        limit: int = 40,
        query: str = '',
    ) -> str:
        """Format message history for a channel.

        When query is provided: fetches top 20 by semantic similarity + last 10
        by recency, merges and deduplicates by id, sorts chronologically.
        When query is empty: last 40 by recency, reversed to chronological.
        """
        try:
            with get_conn(self.ctx.org_id) as cur:
                if query:
                    try:
                        from substrate.understanding.embedding.embedder import embed
                        vec = embed(query)
                        cur.execute(
                            '''
                            SELECT id, role, content, created_at
                            FROM messages
                            WHERE org_id = %s AND channel = %s
                              AND embedding IS NOT NULL
                            ORDER BY embedding <=> %s::vector
                            LIMIT 20
                            ''',
                            (self.ctx.org_id, channel, vec.tolist()),
                        )
                        semantic_rows = cur.fetchall()
                    except Exception as e:
                        print(f'[ConversationMemory] semantic fetch failed: {e}')
                        semantic_rows = []

                    cur.execute(
                        '''
                        SELECT id, role, content, created_at
                        FROM messages
                        WHERE org_id = %s AND channel = %s
                        ORDER BY created_at DESC
                        LIMIT 10
                        ''',
                        (self.ctx.org_id, channel),
                    )
                    recency_rows = cur.fetchall()

                    # Merge, deduplicate by id, sort chronologically
                    seen: set = set()
                    merged = []
                    for row in list(semantic_rows) + list(recency_rows):
                        rid = str(row['id'])
                        if rid not in seen:
                            seen.add(rid)
                            merged.append(row)
                    rows = sorted(merged, key=lambda r: r['created_at'])
                else:
                    cur.execute(
                        '''
                        SELECT id, role, content, created_at
                        FROM messages
                        WHERE org_id = %s AND channel = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        ''',
                        (self.ctx.org_id, channel, limit),
                    )
                    rows = list(reversed(cur.fetchall()))

            if not rows:
                return ''
            lines = ['CONVERSATION HISTORY:']
            for row in rows:
                prefix = 'Founder' if row['role'] == 'user' else 'AI'
                lines.append(f"{prefix}: {row['content']}")
            return '\n'.join(lines)
        except Exception as e:
            print(f'[ConversationMemory] format_channel_history_for_prompt failed: {e}')
            return ''

    def _row(self, row: dict) -> Message:
        return Message(
            id=str(row['id']),
            org_id=str(row['org_id']),
            session_id=str(row['session_id']),
            sequence_num=int(row['sequence_num']),
            role=str(row['role']),
            content=str(row['content']),
            channel=str(row['channel']),
            agent=str(row['agent']),
            created_at=row['created_at'],
            metadata=row['metadata'] if isinstance(row['metadata'], dict) else json.loads(row['metadata']) if row['metadata'] else {},
        )
