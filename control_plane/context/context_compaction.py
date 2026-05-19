"""
ContextCompactor — seamless context window management for long conversations.

When a conversation approaches 80% of the 200k token window, this module
compresses message history into a structured brief, persists it to Neon,
and seeds the next context window. The user sees one continuous conversation;
internally there are multiple context segments.

Table: context_compactions
    (id UUID, org_id UUID, session_id UUID, generation INT,
     brief_json JSONB, messages_compressed INT,
     tokens_before INT, created_at TIMESTAMPTZ)
"""

import json
import uuid
from datetime import datetime, timezone

from state.context.context import EntrepreneurOSContext
from state.storage.db import get_conn


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContextCompactor:

    # 80% of 200k token window (4 chars ≈ 1 token → 160k tokens ≈ 640k chars)
    COMPACTION_THRESHOLD = 160_000

    def __init__(self, ctx: EntrepreneurOSContext):
        self.ctx = ctx
        self._ensure_table()

    def _ensure_table(self) -> None:
        with get_conn(self.ctx.org_id) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS context_compactions (
                    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                    org_id              UUID        NOT NULL,
                    session_id          UUID        NOT NULL,
                    generation          INT         NOT NULL DEFAULT 1,
                    brief_json          JSONB,
                    messages_compressed INT         NOT NULL DEFAULT 0,
                    tokens_before       INT         NOT NULL DEFAULT 0,
                    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_compactions_session
                ON context_compactions (org_id, session_id)
            """)

    # ─── Token estimation ─────────────────────────────────────────────────────

    def estimate_tokens(self, messages: list[dict]) -> int:
        """Rough estimate: 4 chars per token."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return total_chars // 4

    def should_compact(self, messages: list[dict]) -> bool:
        return self.estimate_tokens(messages) >= self.COMPACTION_THRESHOLD

    # ─── Compact ──────────────────────────────────────────────────────────────

    def compact(self, messages: list[dict], session_id: str) -> dict:
        """
        Compress a message list into a structured brief.
        Stores brief to Neon. Returns the brief dict.
        """
        from control_plane.runtime.cognitive_loop import CognitiveLoop
        from execution.runtime.agent_runtime import TaskType

        tokens_before = self.estimate_tokens(messages)

        # Get generation number
        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS cnt FROM context_compactions
                WHERE org_id = %s AND session_id = %s
                """,
                (self.ctx.org_id, session_id),
            )
            row        = cur.fetchone()
            generation = (row["cnt"] or 0) + 1

        # Build compaction prompt from last 100 messages
        conversation_text = "\n\n".join(
            f"[{str(m.get('role', 'user')).upper()}]: "
            f"{str(m.get('content', ''))[:500]}"
            for m in messages[-100:]
        )

        prompt = (
            "You are compacting a long conversation for context preservation.\n\n"
            "CONVERSATION:\n" + conversation_text[:8000] + "\n\n"
            "Generate a structured JSON brief with EXACTLY these keys:\n"
            '{\n'
            '  "who_user_is": "key facts about the founder/user (1-2 sentences)",\n'
            '  "decisions_made": ["list of concrete decisions"],\n'
            '  "open_loops": ["unresolved items or questions"],\n'
            '  "critical_facts": ["must-not-forget information"],\n'
            '  "last_action": "what was just done",\n'
            '  "next_intent": "what they were about to do"\n'
            '}\n\n'
            "Return ONLY valid JSON. No markdown, no explanation."
        )

        loop   = CognitiveLoop(self.ctx)
        result = loop.run(
            input=prompt,
            agent="context_compactor",
            task_type=TaskType.SUMMARIZE,
        )

        brief: dict = {
            "who_user_is":    "",
            "decisions_made": [],
            "open_loops":     [],
            "critical_facts": [],
            "last_action":    "",
            "next_intent":    "",
        }

        if result.output:
            try:
                raw = result.output.strip()
                # Strip markdown code fences if present
                if raw.startswith("```"):
                    parts = raw.split("```")
                    raw   = parts[1] if len(parts) > 1 else raw
                    if raw.startswith("json"):
                        raw = raw[4:]
                brief = json.loads(raw.strip(), strict=False)
            except (json.JSONDecodeError, Exception):
                brief["last_action"] = result.output[:500]

        # Persist to Neon
        from state.stores.context_compaction_store import ContextCompactionStore
        ContextCompactionStore().insert_compaction(
            org_id=self.ctx.org_id,
            session_id=session_id,
            generation=generation,
            brief=brief,
            messages_compressed=len(messages),
            tokens_before=tokens_before,
        )

        print(
            f"[ContextCompactor] Session {str(session_id)[:8]}... "
            f"compacted gen {generation} — "
            f"{len(messages)} messages, ~{tokens_before:,} tokens"
        )
        return brief

    # ─── Context seeding ──────────────────────────────────────────────────────

    def build_seeded_context(self, brief: dict) -> str:
        """
        Format a compaction brief as a system prompt prefix.
        Seeds the next context window with essential facts.
        """
        decisions = "\n".join(f"  - {d}" for d in brief.get("decisions_made", []))
        open_loops = "\n".join(f"  - {o}" for o in brief.get("open_loops", []))
        critical   = "\n".join(f"  - {c}" for c in brief.get("critical_facts", []))

        return (
            "CONTEXT FROM PRIOR CONVERSATION:\n\n"
            f"WHO: {brief.get('who_user_is', '')}\n\n"
            f"DECISIONS MADE:\n{decisions or '  (none)'}\n\n"
            f"OPEN LOOPS:\n{open_loops or '  (none)'}\n\n"
            f"CRITICAL FACTS:\n{critical or '  (none)'}\n\n"
            f"LAST ACTION: {brief.get('last_action', '')}\n\n"
            f"NEXT INTENT: {brief.get('next_intent', '')}\n\n"
            "---\n"
        )

    # ─── Lineage ──────────────────────────────────────────────────────────────

    def get_lineage(self, session_id: str) -> list[dict]:
        """
        Return all compaction records for a session in chronological order.
        Allows inspection of the full conversation lineage.
        """
        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                """
                SELECT id, session_id, generation, brief_json,
                       messages_compressed, tokens_before, created_at
                FROM context_compactions
                WHERE org_id = %s AND session_id = %s
                ORDER BY generation ASC
                """,
                (self.ctx.org_id, session_id),
            )
            rows = cur.fetchall()

        return [
            {
                "id":                  str(r["id"]),
                "session_id":          str(r["session_id"]),
                "generation":          r["generation"],
                "brief":               r["brief_json"],
                "messages_compressed": r["messages_compressed"],
                "tokens_before":       r["tokens_before"],
                "created_at":          (
                    r["created_at"].isoformat()
                    if r["created_at"] else None
                ),
            }
            for r in rows
        ]
