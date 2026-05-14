"""
UserModel — learns how the founder thinks, communicates, and makes decisions.

Closes the intent-expression gap: the difference between what he says and
what he means. Profiles built from 30-day interaction history in Neon.
Trust level grows with interaction volume — higher trust unlocks aggressive
prompt expansion before generic Haiku enhancement runs.

Wired into CognitiveLoop._enhance_prompt():
  expanded = user_model.get_intent_expansion(prompt)
  if expanded != prompt: return expanded
  # user model expansion takes priority over generic Haiku enhancement

Usage:
    from runtime.context import load_context_from_env
    from runtime.user_model import UserModel

    ctx = load_context_from_env()
    um  = UserModel(ctx)

    trust    = um.get_trust_level()           # 1-5
    profile  = um.build_communication_profile()
    expanded = um.get_intent_expansion("do outreach")
"""

import json
import os
import sys
import datetime
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

load_dotenv(Path(__file__).parent / ".env")

from runtime.context import EOSContext
from control_plane.runtime.cognitive_loop import CognitiveLoop
from execution.runtime.agent_runtime import AgentRuntime, TaskType
from state.storage.db import get_conn


# ─── Trust level thresholds ───────────────────────────────────────────────────
#   interaction_count → trust_level
_TRUST_THRESHOLDS = [
    (200, 5),
    (100, 4),
    (50, 3),
    (10, 2),
    (0, 1),
]


class UserModel:
    """
    Behavioral model of the founder's communication style, decision patterns,
    and compressed vocabulary.

    Updated every 10 interactions (via maybe_update_profile()).
    Used by CognitiveLoop._enhance_prompt() to expand vague instructions
    before generic Haiku enhancement kicks in.
    """

    def __init__(self, ctx: EOSContext):
        self.ctx = ctx
        self.loop = CognitiveLoop(ctx)
        self._runtime = AgentRuntime(ctx)
        self._ensure_table()

    # ─── Schema migration ─────────────────────────────────────────────────────

    def _ensure_table(self) -> None:
        """
        Create user_profiles table in Neon if it does not exist.
        Non-fatal — update_profile() handles failure gracefully.
        """
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        id           UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
                        user_id      TEXT        NOT NULL,
                        org_id       TEXT        NOT NULL,
                        profile_json JSONB       NOT NULL DEFAULT '{}',
                        updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE (user_id, org_id)
                    )
                    """
                )
        except Exception as e:
            # DDL may fail under certain RLS policies — non-fatal.
            print(f"[UserModel] Table init note: {e}")

    # ─── Trust level ──────────────────────────────────────────────────────────

    def get_trust_level(self) -> int:
        """
        Query total interaction count for this user/org.
        Maps to trust level 1-5:
          0-9    → 1
          10-49  → 2
          50-99  → 3
          100-199 → 4
          200+   → 5
        """
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM interactions WHERE user_id = %s",
                    (self.ctx.user_id,),
                )
                row = cur.fetchone()
                count = int(row["cnt"]) if row else 0
        except Exception as e:
            print(f"[UserModel] Trust level query failed: {e}")
            return 1

        for threshold, level in _TRUST_THRESHOLDS:
            if count >= threshold:
                return level
        return 1

    # ─── Communication profile ────────────────────────────────────────────────

    def build_communication_profile(self) -> dict:
        """
        Query last 30 days of interactions from Neon. Analyze input_summary
        patterns. Synthesize via CognitiveLoop.

        Returns:
            communication_style:   str
            avg_prompt_length:     int  (words)
            common_shorthand:      list[str]
            frequent_ambiguities:  list[str]
            preferred_depth:       'brief' | 'detailed'
            decision_style:        str
            trust_level:           int
        """
        cutoff = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
        ).isoformat()

        # ── Pull interaction history ──────────────────────────────────────────
        interactions: list[dict] = []
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT input_summary, task_type, agent_label, created_at
                    FROM interactions
                    WHERE user_id = %s AND created_at >= %s
                    ORDER BY created_at DESC
                    LIMIT 100
                    """,
                    (self.ctx.user_id, cutoff),
                )
                rows = cur.fetchall()
                interactions = [
                    {
                        "input": (row["input_summary"] or "").strip(),
                        "task_type": row["task_type"] or "unknown",
                        "agent": row["agent_label"] or "unknown",
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[UserModel] Interaction query failed: {e}")

        trust_level = self.get_trust_level()

        # ── No history yet ────────────────────────────────────────────────────
        if not interactions:
            return {
                "communication_style": "No interaction history yet.",
                "avg_prompt_length": 0,
                "common_shorthand": [],
                "frequent_ambiguities": [],
                "preferred_depth": "detailed",
                "decision_style": "unknown",
                "trust_level": trust_level,
            }

        # ── Compute stats ─────────────────────────────────────────────────────
        word_lengths = [len(i["input"].split()) for i in interactions if i["input"]]
        avg_length = int(sum(word_lengths) / len(word_lengths)) if word_lengths else 0

        task_counts: dict[str, int] = {}
        for i in interactions:
            task_counts[i["task_type"]] = task_counts.get(i["task_type"], 0) + 1

        top_tasks = sorted(task_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_tasks_str = ", ".join(f"{k}×{v}" for k, v in top_tasks)

        detailed_count = sum(1 for l in word_lengths if l >= 15)
        preferred_depth = (
            "detailed" if detailed_count > len(word_lengths) * 0.4 else "brief"
        )

        # Sample inputs for AI synthesis
        sample_sorted = sorted(interactions[:40], key=lambda x: len(x["input"]))
        sample_text = "\n".join(
            f"  [{i['task_type']}] {i['input'][:150]}"
            for i in sample_sorted[:20]
            if i["input"]
        )

        # ── Guard: skip LLM call if sample data lacks real content ────────────
        # If all samples are identical or very short channel names, there's
        # nothing behavioral to analyze — return a static profile.
        unique_inputs = set(
            i["input"].strip().lower() for i in interactions if i["input"].strip()
        )
        meaningful_inputs = [
            inp
            for inp in unique_inputs
            if len(inp.split()) >= 3  # at least 3 words to be a real prompt
        ]
        if len(meaningful_inputs) < 5:
            print(
                f"[UserModel] Insufficient prompt diversity for profiling "
                f"({len(meaningful_inputs)} unique meaningful inputs) — skipping LLM call"
            )
            return {
                "communication_style": (
                    "Insufficient interaction data for profiling. "
                    f"Found {len(interactions)} interactions but only "
                    f"{len(meaningful_inputs)} contain real prompt content."
                ),
                "avg_prompt_length": avg_length,
                "common_shorthand": [],
                "frequent_ambiguities": [],
                "preferred_depth": preferred_depth,
                "decision_style": "insufficient data",
                "trust_level": trust_level,
            }

        # ── AI synthesis via CognitiveLoop ────────────────────────────────────
        prompt = (
            "You are building a behavioral communication profile of a founder-operator. "
            "Analyze the following sample of instructions they gave their AI system "
            "over the last 30 days.\n\n"
            f"TOTAL INTERACTIONS: {len(interactions)}\n"
            f"AVG PROMPT LENGTH: {avg_length} words\n"
            f"TOP TASK TYPES: {top_tasks_str}\n"
            f"PREFERRED DEPTH: {preferred_depth}\n\n"
            "SAMPLE INPUTS (ordered short → long):\n"
            f"{sample_text}\n\n"
            "Based on this interaction history, describe how this founder communicates. "
            "What are their recurring patterns? What do they often mean that differs "
            "from what they literally say? What shorthand do they use?\n\n"
            "Return ONLY valid JSON with exactly these keys:\n"
            "{\n"
            '  "communication_style": "2-3 sentence description of how they communicate",\n'
            '  "common_shorthand": ["shorthand1", "shorthand2", "shorthand3"],\n'
            '  "frequent_ambiguities": ["ambiguity1", "ambiguity2"],\n'
            '  "decision_style": "1-2 sentence description of their decision pattern"\n'
            "}"
        )

        ai_profile: dict = {}
        try:
            import re as _re

            result = self.loop.run(
                input=prompt,
                agent="user_model.profiler",
                task_type=TaskType.ANALYZE,
                max_iterations=1,
            )
            raw = (result.output or "").strip()
            # Strip markdown code blocks
            if "```" in raw:
                parts = raw.split("```")
                for part in parts:
                    p = part.strip()
                    if p.startswith("json"):
                        p = p[4:].strip()
                    if p.startswith("{") or p.startswith("["):
                        raw = p
                        break
            elif raw.startswith("```"):
                raw = _re.sub(r"^```[a-z]*\n?", "", raw)
                raw = raw.rstrip("`").strip()
            # Extract first complete JSON object — handles trailing text
            m = _re.search(r"\{.*\}", raw, _re.DOTALL)
            if m:
                raw = m.group(0)
            try:
                # Remove trailing commas before closing braces/brackets
                clean_raw = _re.sub(r",\s*([}\]])", r"\1", raw)
                ai_profile = json.loads(clean_raw, strict=False)
            except (json.JSONDecodeError, ValueError) as je:
                print(f"[UserModel] JSON parse fallback: {je}")
                ai_profile = {}
        except Exception as e:
            print(f"[UserModel] AI synthesis failed: {e}")
            ai_profile = {
                "communication_style": "Could not synthesize — insufficient data or AI error.",
                "common_shorthand": [],
                "frequent_ambiguities": [],
                "decision_style": "unknown",
            }

        return {
            "communication_style": ai_profile.get("communication_style", "unknown"),
            "avg_prompt_length": avg_length,
            "common_shorthand": ai_profile.get("common_shorthand", []),
            "frequent_ambiguities": ai_profile.get("frequent_ambiguities", []),
            "preferred_depth": preferred_depth,
            "decision_style": ai_profile.get("decision_style", "unknown"),
            "trust_level": trust_level,
        }

    # ─── Intent expansion ────────────────────────────────────────────────────

    def get_intent_expansion(self, raw_prompt: str) -> str:
        """
        If a profile exists and trust_level >= 3, use it to expand compressed
        prompts into their full intent. Routes through Haiku (fast, cheap).

        e.g. "do outreach" → "Run the daily Instagram DM outreach sequence for
        Initiate Arena ICP segment using the warm opener template. Focus on
        leads in the Contacted stage."

        Returns original prompt if:
          - no profile built yet
          - trust_level < 3
          - prompt is already >= 15 words
          - expansion fails
        """
        trust = self.get_trust_level()
        threshold = max(5, 15 - (trust * 2))
        if len(raw_prompt.split()) >= threshold:
            return raw_prompt

        profile = self._load_profile()
        if not profile:
            return raw_prompt

        if profile.get("trust_level", 1) < 3:
            return raw_prompt

        comm_style = profile.get("communication_style", "")
        shorthand = ", ".join(profile.get("common_shorthand", []))
        decision_style = profile.get("decision_style", "")

        prompt = (
            "You are a communication bridge for a founder's AI system. "
            "The founder uses compressed, shorthand instructions. "
            "Expand this prompt into its full precise intent.\n\n"
            f"FOUNDER COMMUNICATION STYLE:\n{comm_style}\n\n"
            f"KNOWN SHORTHAND:\n{shorthand or 'none documented yet'}\n\n"
            f"DECISION STYLE:\n{decision_style}\n\n"
            f'COMPRESSED PROMPT: "{raw_prompt}"\n\n'
            "Expand into a precise, expert-grade execution prompt using the profile context. "
            "Return ONLY the expanded prompt — no commentary, no preamble."
        )

        try:
            result = self._runtime.run(
                task_type=TaskType.CLASSIFY,
                prompt=prompt,
                agent="user_model.expander",
            )
            expanded = (result.output or "").strip()
            return expanded if expanded else raw_prompt
        except Exception as e:
            print(f"[UserModel] Intent expansion failed: {e}")
            return raw_prompt

    # ─── Profile persistence ──────────────────────────────────────────────────

    def update_profile(self) -> dict:
        """
        Build communication profile and upsert to Neon user_profiles table.
        Called automatically every 10 interactions via maybe_update_profile().
        Returns the profile dict.
        """
        profile = self.build_communication_profile()

        try:
            from state.stores.profile_store import ProfileStore
            ProfileStore().upsert_user_profile(
                org_id=self.ctx.org_id,
                user_id=self.ctx.user_id,
                profile=profile,
            )
            print(f"[UserModel] Profile updated for user {self.ctx.user_id}")
        except Exception as e:
            print(f"[UserModel] Profile upsert failed: {e}")

        # Sync up to harness-level intelligence profile
        try:
            from runtime.os_trinity import OSTrinity

            trinity = OSTrinity(self.ctx)
            trinity.sync_from_user_model(self.ctx.user_id)
        except Exception as e:
            print(f"[UserModel] OS Trinity sync failed: {e}")

        return profile

    def _load_profile(self) -> dict | None:
        """Load stored profile from Neon. Returns None if not found."""
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT profile_json FROM user_profiles
                    WHERE user_id = %s AND org_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (self.ctx.user_id, self.ctx.org_id),
                )
                row = cur.fetchone()
            if not row:
                return None
            pj = row["profile_json"]
            if isinstance(pj, str):
                return json.loads(pj)
            return dict(pj) if pj else None
        except Exception as e:
            print(f"[UserModel] Profile load failed: {e}")
            return None

    # ─── Auto-trigger ─────────────────────────────────────────────────────────

    def maybe_update_profile(self) -> bool:
        """
        Check if interaction count hit a multiple of 10.
        If so, trigger update_profile(). Returns True if profile was updated.
        Called by CognitiveLoop after each interaction.
        """
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM interactions WHERE user_id = %s",
                    (self.ctx.user_id,),
                )
                row = cur.fetchone()
                count = int(row["cnt"]) if row else 0

            if count > 0 and count % 10 == 0:
                self.update_profile()
                return True
        except Exception as e:
            print(f"[UserModel] maybe_update_profile error: {e}")
        return False
