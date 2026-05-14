"""
SkillImprovementEngine — RLHF-driven skill rewriting + self-organization.

Monitors outcome data in memory.db and automatically rewrites underperforming
skill files using examples of what worked vs what didn't.

Also detects recurring unassigned task patterns and proposes new skill files
for them (self-organization cycle — runs weekly on Mondays).

Minimum 5 scored outcomes required per skill before any rewrite is attempted.
Threshold: reply_rate < 0.30 triggers a rewrite.
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from execution.runtime.agent_runtime import AgentRuntime, TaskType
from runtime.skill_registry import SkillRegistry, get_skill_registry, reset_skill_registry

MIN_OUTCOMES          = 5      # minimum scored outcomes before improvement runs
REPLY_THRESHOLD       = 0.30   # reply_rate below this → rewrite
MIN_PATTERN_OCCURRENCES = 5    # minimum unassigned occurrences before a new skill is proposed
GENERATED_SKILLS_DIR  = Path(_REPO_ROOT) / "skills" / "Generated"


class SkillImprovementEngine:

    def __init__(self) -> None:
        self._registry = get_skill_registry()
        self._runtime  = AgentRuntime()

    # ─── Internal: fetch outcome data for a skill ────────────────────────────

    def _fetch_skill_outcomes(self, skill_id: str) -> list[dict]:
        """
        Return all interactions + outcomes for skill_id from Neon.
        Each row: {input_summary, output_summary, outcome_type, score}
        Uses outcome_label (Python label) as outcome_type for compatibility.
        """
        try:
            from state.storage.db import get_conn, ORG_ID, resolve_skill
            with get_conn(ORG_ID) as cur:
                skill_uuid = resolve_skill(skill_id)
                if not skill_uuid:
                    return []
                cur.execute(
                    """
                    SELECT i.input_summary,
                           i.output_summary,
                           COALESCE(o.outcome_label, o.outcome_type::text) AS outcome_type,
                           o.score
                    FROM interactions i
                    JOIN outcomes o ON o.interaction_id = i.id
                    WHERE i.skill_id = %s
                      AND o.score IS NOT NULL
                    ORDER BY o.score DESC, i.created_at DESC
                    """,
                    (skill_uuid,),
                )
                rows = cur.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"[SkillImprovement] _fetch_skill_outcomes Neon failed: {e}")
            return []

    # ─── Internal: build improvement prompt ──────────────────────────────────

    def _build_prompt(
        self,
        skill: object,
        winners: list[dict],
        losers: list[dict],
        reply_rate: float,
    ) -> str:
        def _fmt_example(row: dict, idx: int) -> str:
            return (
                f"Example {idx + 1}:\n"
                f"  Input:  {row['input_summary']}\n"
                f"  Output: {row['output_summary']}\n"
                f"  Score:  {row['score']}"
            )

        winners_block = "\n\n".join(_fmt_example(r, i) for i, r in enumerate(winners)) or "None available."
        losers_block  = "\n\n".join(_fmt_example(r, i) for i, r in enumerate(losers))  or "None available."

        return (
            f"You are improving an AI skill file based on real-world outcome data.\n\n"
            f"SKILL ID: {skill.skill_id}\n"
            f"SKILL NAME: {skill.name}\n"
            f"CURRENT REPLY RATE: {reply_rate:.1%} (target: ≥ 30%)\n\n"
            f"CURRENT SKILL CONTENT:\n"
            f"{'─' * 60}\n"
            f"{skill.content}\n"
            f"{'─' * 60}\n\n"
            f"TOP 3 PERFORMING OUTPUTS (score = 1.0 — leads replied):\n"
            f"{'─' * 60}\n"
            f"{winners_block}\n"
            f"{'─' * 60}\n\n"
            f"TOP 3 FAILING OUTPUTS (score = 0.0 — no reply):\n"
            f"{'─' * 60}\n"
            f"{losers_block}\n"
            f"{'─' * 60}\n\n"
            f"TASK:\n"
            f"Rewrite the skill to produce more outputs like the winners and "
            f"fewer like the losers. Preserve the overall structure and intent. "
            f"Return ONLY the full rewritten skill content — no commentary, no "
            f"preamble, no markdown code fences. Start directly with the skill "
            f"content as it would appear in the .md file."
        )

    # ─── Public: check and improve a single skill ────────────────────────────

    def check_and_improve(self, skill_id: str) -> dict:
        """
        Evaluate a skill's outcome data and rewrite it if underperforming.

        Returns a result dict:
          action:     "improved" | "skipped_insufficient_data" | "skipped_above_threshold" | "error"
          skill_id:   the skill_id checked
          reply_rate: float or None
          outcomes:   total scored outcomes found
          reason:     human-readable explanation
        """
        skill = self._registry.get_skill(skill_id)
        if not skill:
            return {
                "action":     "error",
                "skill_id":   skill_id,
                "reply_rate": None,
                "outcomes":   0,
                "reason":     f"Skill '{skill_id}' not found in registry.",
            }

        outcomes = self._fetch_skill_outcomes(skill_id)
        total    = len(outcomes)

        if total < MIN_OUTCOMES:
            return {
                "action":     "skipped_insufficient_data",
                "skill_id":   skill_id,
                "reply_rate": None,
                "outcomes":   total,
                "reason":     f"Only {total}/{MIN_OUTCOMES} scored outcomes — need more data.",
            }

        replies    = sum(1 for r in outcomes if r["outcome_type"] == "reply" and r["score"] == 1.0)
        reply_rate = replies / total

        if reply_rate >= REPLY_THRESHOLD:
            return {
                "action":     "skipped_above_threshold",
                "skill_id":   skill_id,
                "reply_rate": reply_rate,
                "outcomes":   total,
                "reason":     f"Reply rate {reply_rate:.1%} ≥ threshold {REPLY_THRESHOLD:.0%} — no improvement needed.",
            }

        # Sort: winners = score 1.0 replies, losers = score 0.0
        winners = [r for r in outcomes if r["score"] == 1.0][:3]
        losers  = [r for r in outcomes if r["score"] == 0.0][:3]

        print(f"[SkillImprovement] Improving '{skill_id}' "
              f"(reply_rate={reply_rate:.1%}, outcomes={total})")

        prompt = self._build_prompt(skill, winners, losers, reply_rate)

        try:
            result = self._runtime.run(
                task_type=TaskType.GENERATE,
                prompt=prompt,
                max_tokens=2000,
                agent="skill_improvement",
            )
            improved_content = result.output.strip()
        except Exception as e:
            return {
                "action":     "error",
                "skill_id":   skill_id,
                "reply_rate": reply_rate,
                "outcomes":   total,
                "reason":     f"AgentRuntime call failed: {e}",
            }

        # Back up current skill file
        skill_path = Path(skill.file_path)
        backup_path = skill_path.with_suffix(".md.bak")
        shutil.copy2(skill_path, backup_path)
        print(f"[SkillImprovement] Backed up → {backup_path}")

        # Write improved version
        skill_path.write_text(improved_content, encoding="utf-8")
        print(f"[SkillImprovement] Wrote improved skill → {skill_path}")

        # Sync improved content to Neon skills table so DB overrides
        # the old file-based version on next SkillRegistry load.
        try:
            from state.storage.db import ORG_ID
            from state.stores.skill_store import SkillStore
            SkillStore().update_skill_content_by_name(
                org_id=ORG_ID,
                name=skill.name,
                content=improved_content,
            )
            print(f"[SkillImprovement] Neon skills table synced for '{skill_id}'")
        except Exception as e:
            print(f"[SkillImprovement] Neon sync skipped (not in DB): {e}")

        # Signal SkillRegistry to reload on next access
        reset_skill_registry()

        return {
            "action":     "improved",
            "skill_id":   skill_id,
            "reply_rate": reply_rate,
            "outcomes":   total,
            "reason":     (
                f"Rewritten. Was: {reply_rate:.1%} reply rate "
                f"across {total} outcomes. Backup at {backup_path.name}."
            ),
        }

    # ─── Public: full cycle ──────────────────────────────────────────────────

    def run_improvement_cycle(self) -> list[dict]:
        """
        Run check_and_improve() on every loaded skill.
        Returns list of result dicts — one per skill.
        """
        skill_ids = self._registry.list_skills()
        print(f"[SkillImprovement] Checking {len(skill_ids)} skills...")

        results = []
        for skill_id in skill_ids:
            result = self.check_and_improve(skill_id)
            results.append(result)
            action = result["action"]
            reason = result["reason"]
            print(f"  [{action}] {skill_id} — {reason}")

        improved = [r for r in results if r["action"] == "improved"]
        skipped  = [r for r in results if r["action"] != "improved"]
        print(
            f"[SkillImprovement] Cycle complete — "
            f"{len(improved)} improved, {len(skipped)} skipped."
        )
        return results

    # ─── Self-organization: detect patterns ──────────────────────────────────

    def detect_patterns(self) -> list[dict]:
        """
        Query Neon interactions from the last 30 days.
        Find recurring task types with no skill_id — these are candidates
        for a new auto-generated skill.

        Returns list of dicts:
            {task_type, agent, count, example_inputs, pattern_description}
        """
        from state.storage.db import get_conn, ORG_ID
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        try:
            with get_conn(ORG_ID) as cur:
                cur.execute(
                    """
                    SELECT task_type, agent_label AS agent, COUNT(*) AS cnt
                    FROM interactions
                    WHERE org_id = %s
                      AND skill_id IS NULL
                      AND created_at >= %s
                      AND task_type NOT IN ('unknown')
                      AND agent_label NOT IN ('default', 'orchestrator', 'icp_scorer')
                    GROUP BY task_type, agent_label
                    HAVING COUNT(*) >= %s
                    ORDER BY cnt DESC
                    """,
                    (ORG_ID, cutoff, MIN_PATTERN_OCCURRENCES),
                )
                rows = cur.fetchall()
        except Exception as e:
            print(f"[SkillImprovement] detect_patterns query failed: {e}")
            return []

        patterns = []
        for row in rows:
            try:
                with get_conn(ORG_ID) as cur:
                    cur.execute(
                        """
                        SELECT input_summary FROM interactions
                        WHERE org_id = %s
                          AND skill_id IS NULL
                          AND task_type = %s AND agent_label = %s
                          AND created_at >= %s
                        ORDER BY created_at DESC LIMIT 5
                        """,
                        (ORG_ID, row["task_type"], row["agent"], cutoff),
                    )
                    examples = cur.fetchall()
            except Exception:
                examples = []

            example_inputs = [e["input_summary"] for e in examples if e["input_summary"]]
            first_ex = example_inputs[0][:100] if example_inputs else "n/a"
            patterns.append({
                "task_type":           row["task_type"],
                "agent":               row["agent"],
                "count":               row["cnt"],
                "example_inputs":      example_inputs,
                "pattern_description": (
                    f"Agent '{row['agent']}' runs {row['cnt']} '{row['task_type']}' tasks "
                    f"with no assigned skill in the last 30 days. "
                    f"Example input: {first_ex}"
                ),
            })

        return patterns

    # ─── Self-organization: propose new skill ────────────────────────────────

    def _log_skill_created(self, skill_id: str, file_path: str, pattern: dict) -> None:
        from state.storage.db import ORG_ID
        from state.memory.memory import AgentMemory
        try:
            AgentMemory().log_event(
                org_id=ORG_ID,
                event_type="skill_created",
                payload={
                    "skill_id":      skill_id,
                    "file_path":     file_path,
                    "pattern_count": pattern["count"],
                    "agent":         pattern["agent"],
                    "task_type":     pattern["task_type"],
                },
                handled_by=json.dumps(["SkillImprovementEngine.propose_new_skill"]),
            )
        except Exception as e:
            print(f"[SkillImprovement] _log_skill_created failed: {e}")

    def propose_new_skill(self, pattern: dict) -> dict:
        """
        Use AgentRuntime to write a new skill file from a detected pattern.
        Writes to skills/Generated/<skill_id>.md.
        Logs a skill_created event to memory.db.

        Returns {action, skill_id, file_path, pattern}.
        """
        GENERATED_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

        # Substrate-neutral venture framing from ctx.
        _ctx = getattr(self, 'ctx', None)
        _active = (
            getattr(_ctx, 'active_venture', None)
            or (getattr(_ctx, 'ventures', []) or [{}])[0]
            or {}
        )
        _v_name = _active.get('name', 'the active venture') if isinstance(_active, dict) else 'the active venture'
        _v_offer = _active.get('offer', '') if isinstance(_active, dict) else ''
        _v_framing = f"{_v_name}{' — ' + _v_offer if _v_offer else ''}"

        prompt = (
            "You are designing a new AI skill file for a founder-operator's "
            f"sales and outreach intelligence system ({_v_framing}).\n\n"
            "A recurring task pattern has been detected with no skill assigned:\n\n"
            f"Pattern      : {pattern['pattern_description']}\n"
            f"Task type    : {pattern['task_type']}\n"
            f"Agent        : {pattern['agent']}\n"
            f"Occurrences  : {pattern['count']} (last 30 days)\n\n"
            "Example inputs this agent receives:\n"
            + "\n".join(f"  - {ex}" for ex in pattern["example_inputs"][:3])
            + "\n\n"
            "Write a complete, production-ready skill file that:\n"
            "1. Defines the role and purpose of this agent clearly\n"
            "2. Specifies the input format to expect\n"
            "3. Provides a step-by-step reasoning process\n"
            "4. Defines a structured, actionable output format\n"
            "5. Lists 3-5 quality constraints (what NOT to do)\n\n"
            "Return ONLY the skill file content — no commentary, no code fences.\n"
            "Start with a # heading that is the skill name."
        )

        result = self._runtime.run(
            task_type=TaskType.GENERATE,
            prompt=prompt,
            max_tokens=1500,
            agent="skill_improvement.propose",
        )

        agent_slug = pattern["agent"].replace(".", "_").replace("/", "_")
        skill_id   = f"{agent_slug}_{pattern['task_type']}_auto"
        skill_path = GENERATED_SKILLS_DIR / f"{skill_id}.md"

        skill_path.write_text(result.output.strip(), encoding="utf-8")
        print(f"[SkillImprovement] New skill written → {skill_path}")

        self._log_skill_created(skill_id, str(skill_path), pattern)

        return {
            "action":    "created",
            "skill_id":  skill_id,
            "file_path": str(skill_path),
            "pattern":   pattern["pattern_description"],
        }

    # ─── Self-organization: full cycle ───────────────────────────────────────

    def run_self_organization_cycle(self) -> list[dict]:
        """
        Detect recurring unassigned patterns → propose a new skill for each.
        Called weekly (Mondays) by the orchestrator morning cycle.
        Returns list of created skill dicts.
        """
        print("[SkillImprovement] ── Self-organization cycle start ──")
        patterns = self.detect_patterns()
        print(f"[SkillImprovement] {len(patterns)} unassigned recurring pattern(s) found")

        created = []
        for pattern in patterns:
            label = pattern["pattern_description"][:80]
            print(f"  Proposing skill for: {label} (×{pattern['count']})")
            try:
                result = self.propose_new_skill(pattern)
                created.append(result)
                print(f"  → {result['skill_id']} written")
            except Exception as exc:
                print(f"  [ERROR] propose_new_skill failed: {exc}")

        print(
            f"[SkillImprovement] Self-organization complete — "
            f"{len(created)}/{len(patterns)} skills created"
        )
        return created
