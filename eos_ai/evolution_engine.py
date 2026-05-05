"""
EvolutionEngine — continuous self-improvement beyond skill rewrites.

Combines two concerns:
  1. Stage-primitive lifecycle — tracks which KnowledgePrimitives are
     active at the venture's current stage, what unlocks next, and
     whether a given primitive applies right now. Wired into
     CognitiveLoop PERCEIVE step.

  2. Weekly system evolution — workflows evolve, new agents get proposed,
     knowledge library reorganizes. Runs Saturdays via orchestrator cron.
     Results sent to Telegram.

Usage:
    from eos_ai.context import load_context_from_env
    from eos_ai.evolution_engine import EvolutionEngine

    ctx = load_context_from_env()
    ee  = EvolutionEngine(ctx)

    # Stage-primitive lifecycle
    stage  = ee.get_current_stage('lyfe_institute')
    active = ee.get_active_primitives('lyfe_institute')
    result = ee.is_primitive_unlocked('hire_salesperson', 'lyfe_institute')
    # {'applies': False, 'warning': '...', 'what_applies_instead': '...'}

    # Weekly cycle
    perf    = ee.analyze_system_performance()
    summary = ee.run_weekly_evolution_cycle()
"""

import json
import os
import sys
import uuid
import datetime
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

load_dotenv(Path(__file__).parent / ".env")

from eos_ai.context import EOSContext
from eos_ai.cognitive_loop import CognitiveLoop
from eos_ai.agent_runtime import AgentRuntime, TaskType
from eos_ai.skill_improvement import SkillImprovementEngine
from eos_ai.research_engine import ResearchEngine
from eos_ai.db import get_conn


# ─── Primitive composition rules ─────────────────────────────────────────────

PRIMITIVE_PREREQUISITES: dict[str, list[str]] = {
    # before you can apply this primitive, these must be true first
    'offer_optimization': [
        'conversation_first',
    ],
    'hire_salesperson': [
        'outreach_before_content',
        'offer_optimization',
    ],
    'paid_advertising': [
        'offer_optimization',
        'unit_economics',
    ],
    'hire_top_down': [
        'hire_bottom_up',
        'unit_economics',
    ],
    'content_strategy': [
        'outreach_before_content',
    ],
    'referral_flywheel': [
        'conversation_first',
    ],
    'retention_over_acquisition': [
        'conversation_first',
    ],
}


# ─── Stage transition map ─────────────────────────────────────────────────────

STAGE_TRANSITIONS: dict[int, dict] = {
    1: {
        'proof_needed': 'first_sale',
        'unlocks': [
            'offer_optimization',
            'hire_bottom_up',
        ],
        'retires': [
            'conversation_first',
        ],
        'signal': (
            'First paying client acquired '
            'from consistent channel'
        ),
    },
    2: {
        'proof_needed': 'ten_consistent_sales',
        'unlocks': [
            'hire_salesperson',
            'paid_advertising',
            'content_strategy',
        ],
        'retires': [
            'outreach_before_content',
        ],
        'signal': (
            '10 sales from same channel '
            'with same message'
        ),
    },
    3: {
        'proof_needed': 'repeatable_revenue',
        'unlocks': [
            'hire_top_down',
            'paid_advertising_scale',
            'systems_building',
        ],
        'retires': [
            'founder_does_sales',
        ],
        'signal': (
            'Consistent monthly revenue '
            'without founder direct involvement'
        ),
    },
}


class EvolutionEngine:
    """
    Continuous improvement layer. Analyzes system performance, proposes
    workflow improvements and new agents, and orchestrates the weekly
    evolution cycle.
    """

    def __init__(self, ctx: EOSContext):
        self.ctx              = ctx
        self.loop             = CognitiveLoop(ctx)
        self.skill_improvement = SkillImprovementEngine()
        self.research          = ResearchEngine(ctx)

    # ─── Stage-primitive lifecycle ────────────────────────────────────────────

    def _get_stage(self, venture_id: str) -> int:
        """Read BIS stage for venture. Returns 1 on any failure (safe default)."""
        try:
            from eos_ai.business_instance import BusinessInstanceManager
            bim     = BusinessInstanceManager(self.ctx)
            ctx_str = bim.get_context_for_agents(venture_id)
            for line in ctx_str.split('\n'):
                if line.startswith('STAGE:'):
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        stage_token = parts[1].strip().split()[0]
                        return int(stage_token)
        except Exception:
            pass
        return 1

    def get_current_stage(self, venture_id: str) -> int:
        """Return the current BIS stage integer for a venture."""
        return self._get_stage(venture_id)

    def get_active_primitives(self, venture_id: str) -> list[str]:
        """
        Return list of primitive IDs that are active (applies=True) at the
        venture's current stage.
        """
        from eos_ai.primitives import PRIMITIVE_LIBRARY
        stage  = self._get_stage(venture_id)
        return [
            pid for pid, prim in PRIMITIVE_LIBRARY.items()
            if prim.stage_applicability.get(stage, False)
        ]

    def is_primitive_unlocked(self, primitive_id: str, venture_id: str = 'lyfe_institute') -> dict:
        """
        Check whether a primitive applies at the venture's current stage.

        Returns:
            {
                'applies':              bool,
                'warning':              str,
                'what_applies_instead': str,
            }
        """
        from eos_ai.primitives import PRIMITIVE_LIBRARY, STAGE_PRIMITIVES
        prim  = PRIMITIVE_LIBRARY.get(primitive_id)
        stage = self._get_stage(venture_id)

        if prim is None:
            return {
                'applies': False,
                'warning': f'Unknown primitive: {primitive_id}',
                'what_applies_instead': '',
            }

        applies = prim.stage_applicability.get(stage, False)
        if applies:
            return {'applies': True, 'warning': '', 'what_applies_instead': ''}

        # Pull the richest warning available from validity_conditions
        warning   = ''
        redirect  = ''
        for vc in prim.validity_conditions:
            if not vc.get('applies', True):
                warning  = vc.get('warning', '')
                redirect = vc.get('what_applies_instead', '')
                break

        if not warning:
            stage_info = STAGE_PRIMITIVES.get(stage, {})
            warning = (
                f'Stage {stage} ({stage_info.get("name", "")}) — '
                f'{primitive_id} not applicable yet.'
            )
        if not redirect:
            stage_info = STAGE_PRIMITIVES.get(stage, {})
            redirect   = stage_info.get('what_applies_instead', '')

        return {
            'applies':              False,
            'warning':              warning,
            'what_applies_instead': redirect,
        }

    def check_prerequisites(
        self,
        primitive_id: str,
        venture_id: str = 'lyfe_institute',
    ) -> dict:
        """
        Check whether the prerequisites for a primitive are met.

        Returns:
            {
                'ready':   bool,
                'missing': list[str],
                'message': str,
            }
        """
        prereqs = PRIMITIVE_PREREQUISITES.get(primitive_id, [])
        if not prereqs:
            return {'ready': True, 'missing': [], 'message': 'Ready to apply'}

        missing = []
        for prereq_id in prereqs:
            result = self.is_primitive_unlocked(prereq_id, venture_id)
            if not result.get('applies', True):
                missing.append(prereq_id)

        return {
            'ready':   len(missing) == 0,
            'missing': missing,
            'message': (
                f'Complete these first: {", ".join(missing)}'
                if missing else 'Ready to apply'
            ),
        }

    # ─── analyze_system_performance ──────────────────────────────────────────

    def analyze_system_performance(self) -> dict:
        """
        Query last 30 days of interactions, outcomes, and events from Neon.

        Calculates:
            overall_reply_rate:       float | None   — reply outcomes / total outcomes
            avg_iterations_per_task:  float          — from cognitive_reflection events
            most_used_skills:         list[str]      — top skills by invocation count
            least_used_skills:        list[str]      — bottom skills by invocation count
            tasks_with_no_skill_match: int           — interactions with no skill_id
            approval_queue_backlog:   int            — pending approvals
            total_interactions_30d:   int
            total_outcomes_30d:       int
        """
        cutoff = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=30)
        ).isoformat()

        # ── Reply rate ────────────────────────────────────────────────────────
        overall_reply_rate: float | None = None
        total_interactions_30d  = 0
        total_outcomes_30d      = 0
        tasks_with_no_skill     = 0

        try:
            with get_conn(self.ctx.org_id) as cur:
                # Interaction + outcome join
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT i.id) AS total_i,
                           SUM(CASE WHEN o.outcome_label = 'reply' THEN 1 ELSE 0 END) AS replies,
                           COUNT(o.id) AS total_o
                    FROM interactions i
                    LEFT JOIN outcomes o ON o.interaction_id = i.id
                    WHERE i.org_id = %s AND i.created_at >= %s
                    """,
                    (self.ctx.org_id, cutoff),
                )
                row = cur.fetchone()
                if row:
                    total_interactions_30d = int(row["total_i"] or 0)
                    total_outcomes_30d     = int(row["total_o"] or 0)
                    replies                = int(row["replies"] or 0)
                    if total_outcomes_30d > 0:
                        overall_reply_rate = round(
                            replies / total_outcomes_30d, 3
                        )

                # Tasks with no skill match
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM interactions
                    WHERE org_id = %s
                      AND skill_id IS NULL
                      AND created_at >= %s
                    """,
                    (self.ctx.org_id, cutoff),
                )
                row = cur.fetchone()
                tasks_with_no_skill = int((row["cnt"] if row else 0) or 0)

        except Exception as e:
            print(f"[EvolutionEngine] Interaction query failed: {e}")

        # ── Skill usage ───────────────────────────────────────────────────────
        most_used_skills:  list[str] = []
        least_used_skills: list[str] = []

        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT s.name, COUNT(i.id) AS cnt
                    FROM interactions i
                    JOIN skills s ON s.id = i.skill_id
                    WHERE i.org_id = %s AND i.created_at >= %s
                    GROUP BY s.name
                    ORDER BY cnt DESC
                    """,
                    (self.ctx.org_id, cutoff),
                )
                rows = cur.fetchall()

            skill_rows = [(row["name"], int(row["cnt"])) for row in rows]
            most_used_skills  = [name for name, _ in skill_rows[:5]]
            least_used_skills = [name for name, _ in skill_rows[-5:] if skill_rows]

        except Exception as e:
            print(f"[EvolutionEngine] Skill usage query failed: {e}")

        # ── Avg iterations from cognitive_reflection events ───────────────────
        avg_iterations: float = 0.0

        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json
                    FROM events
                    WHERE org_id = %s
                      AND event_type = 'cognitive_reflection'
                      AND created_at >= %s
                    ORDER BY created_at DESC
                    LIMIT 100
                    """,
                    (self.ctx.org_id, cutoff),
                )
                rows = cur.fetchall()

            iteration_values: list[int] = []
            for row in rows:
                payload = row["payload_json"]
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        continue
                if isinstance(payload, dict) and "iterations" in payload:
                    iteration_values.append(int(payload["iterations"]))

            if iteration_values:
                avg_iterations = round(
                    sum(iteration_values) / len(iteration_values), 2
                )

        except Exception as e:
            print(f"[EvolutionEngine] Reflection events query failed: {e}")

        # ── Approval queue backlog ────────────────────────────────────────────
        approval_backlog = 0

        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM approvals
                    WHERE org_id = %s AND status = 'pending'
                    """,
                    (self.ctx.org_id,),
                )
                row = cur.fetchone()
                approval_backlog = int((row["cnt"] if row else 0) or 0)
        except Exception as e:
            print(f"[EvolutionEngine] Approvals query failed: {e}")

        return {
            "overall_reply_rate":        overall_reply_rate,
            "avg_iterations_per_task":   avg_iterations,
            "most_used_skills":          most_used_skills,
            "least_used_skills":         least_used_skills,
            "tasks_with_no_skill_match": tasks_with_no_skill,
            "approval_queue_backlog":    approval_backlog,
            "total_interactions_30d":    total_interactions_30d,
            "total_outcomes_30d":        total_outcomes_30d,
        }

    # ─── propose_workflow_improvement ────────────────────────────────────────

    def propose_workflow_improvement(self, workflow_id: str) -> dict:
        """
        Load workflow from Neon, analyze execution history, and propose
        an improved version using Musk's Law (question every step, delete
        unnecessary ones, simplify, accelerate).

        Does NOT auto-apply — queues for founder approval.

        Returns:
            status:        'proposed' | 'skipped' | 'error'
            workflow_id:   str
            proposed_steps: dict | None
            approval_id:   str | None
            reason:        str
        """
        # ── Load workflow ─────────────────────────────────────────────────────
        workflow: dict = {}
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT id, name, steps_json, autonomy_stage
                    FROM workflows
                    WHERE id = %s AND org_id = %s
                    """,
                    (workflow_id, self.ctx.org_id),
                )
                row = cur.fetchone()
                if not row:
                    return {
                        "status":         "skipped",
                        "workflow_id":    workflow_id,
                        "proposed_steps": None,
                        "approval_id":    None,
                        "reason":         f"Workflow {workflow_id} not found in Neon.",
                    }
                workflow = {
                    "id":             str(row["id"]),
                    "name":           row["name"] or workflow_id,
                    "steps_json":     row["steps_json"] or {},
                    "autonomy_stage": row["autonomy_stage"] or "manual",
                }
        except Exception as e:
            return {
                "status":         "error",
                "workflow_id":    workflow_id,
                "proposed_steps": None,
                "approval_id":    None,
                "reason":         f"Workflow load failed: {e}",
            }

        # ── Load execution history ────────────────────────────────────────────
        history_summary = ""
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT input_summary, output_summary, agent_label, created_at
                    FROM interactions
                    WHERE org_id = %s
                    ORDER BY created_at DESC
                    LIMIT 30
                    """,
                    (self.ctx.org_id,),
                )
                rows = cur.fetchall()
            history_lines = [
                f"  [{r['agent_label']}] {(r['input_summary'] or '')[:120]}"
                for r in rows
            ]
            history_summary = "\n".join(history_lines[:15]) or "(no execution history)"
        except Exception:
            history_summary = "(execution history unavailable)"

        # ── Identify problems with the workflow ───────────────────────────────
        steps_str = json.dumps(workflow["steps_json"], indent=2)

        prompt = (
            "You are analyzing a workflow to improve it using Musk's Law:\n"
            "1. Question the requirement of every step — most are wrong\n"
            "2. Delete unnecessary steps (at least 20% should be deletable)\n"
            "3. Simplify what remains\n"
            "4. Accelerate — only after simplification\n\n"
            f"WORKFLOW: {workflow['name']}\n"
            f"CURRENT STEPS:\n{steps_str[:2000]}\n\n"
            "RECENT EXECUTION HISTORY (to identify slow steps, failures, re-work):\n"
            f"{history_summary}\n\n"
            "Identify: slow steps, frequent failure points, steps that require "
            "human re-work, and unnecessary steps.\n\n"
            "Produce an improved version of steps_json. Apply Musk's Law: delete "
            "what's unnecessary before you try to optimize.\n\n"
            "Return ONLY valid JSON — the improved steps object — no commentary."
        )

        try:
            result = self.loop.run(
                input=prompt,
                agent="evolution_engine.workflow",
                task_type=TaskType.ANALYZE,
                max_iterations=1,
            )
            raw = (result.output or "").strip()
            if raw.startswith("```"):
                import re as _re
                raw = _re.sub(r"^```[a-z]*\n?", "", raw)
                raw = raw.rstrip("`").strip()
            proposed_steps = json.loads(raw)
        except Exception as e:
            return {
                "status":         "error",
                "workflow_id":    workflow_id,
                "proposed_steps": None,
                "approval_id":    None,
                "reason":         f"AI improvement failed: {e}",
            }

        # ── Queue for approval ────────────────────────────────────────────────
        approval_id = str(uuid.uuid4())
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO approvals (id, org_id, request, status, created_at)
                    VALUES (%s, %s, %s, 'pending', NOW())
                    """,
                    (
                        approval_id,
                        self.ctx.org_id,
                        json.dumps({
                            "action_type":    "workflow_improvement",
                            "workflow_id":    workflow_id,
                            "workflow_name":  workflow["name"],
                            "proposed_steps": proposed_steps,
                            "agent":          "evolution_engine",
                        }),
                    ),
                )
            print(f"[EvolutionEngine] Workflow improvement queued → approval {approval_id}")
        except Exception as e:
            return {
                "status":         "error",
                "workflow_id":    workflow_id,
                "proposed_steps": proposed_steps,
                "approval_id":    None,
                "reason":         f"Approval queue failed: {e}",
            }

        return {
            "status":         "proposed",
            "workflow_id":    workflow_id,
            "proposed_steps": proposed_steps,
            "approval_id":    approval_id,
            "reason":         (
                f"Improvement proposed for '{workflow['name']}'. "
                f"Queued for approval: {approval_id}"
            ),
        }

    # ─── propose_new_agent ───────────────────────────────────────────────────

    def propose_new_agent(self, pattern_description: str) -> dict:
        """
        If a task pattern repeats 10+ times with no matching agent, propose
        a new sub-agent. Queues proposal to approvals table.
        Founder approves → agent row inserted to Neon.

        Returns:
            status:      'proposed' | 'error'
            name:        str
            approval_id: str | None
        """
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
            "You are designing a new AI sub-agent for a founder-operator's "
            f"system ({_v_framing}).\n\n"
            "A recurring task pattern has been detected with no assigned agent:\n\n"
            f"PATTERN: {pattern_description}\n\n"
            "Design a new sub-agent that handles this pattern.\n\n"
            "Return ONLY valid JSON with exactly these keys:\n"
            "{\n"
            '  "name": "snake_case_agent_name",\n'
            '  "department": "sales|content|research|ops|finance",\n'
            '  "soul": "2-3 sentence description of this agent\'s personality and role",\n'
            '  "domain_rules": ["rule1", "rule2", "rule3"],\n'
            '  "suggested_skills": ["skill1", "skill2"]\n'
            "}"
        )

        try:
            result = self.loop.run(
                input=prompt,
                agent="evolution_engine.agent_designer",
                task_type=TaskType.GENERATE,
                max_iterations=1,
            )
            raw = (result.output or "").strip()
            if raw.startswith("```"):
                import re as _re
                raw = _re.sub(r"^```[a-z]*\n?", "", raw)
                raw = raw.rstrip("`").strip()
            agent_spec = json.loads(raw)
        except Exception as e:
            return {
                "status": "error",
                "name":   "unknown",
                "reason": f"Agent design failed: {e}",
            }

        approval_id = str(uuid.uuid4())
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO approvals (id, org_id, request, status, created_at)
                    VALUES (%s, %s, %s, 'pending', NOW())
                    """,
                    (
                        approval_id,
                        self.ctx.org_id,
                        json.dumps({
                            "action_type":       "new_agent_proposal",
                            "pattern":           pattern_description[:300],
                            "proposed_agent":    agent_spec,
                            "agent":             "evolution_engine",
                        }),
                    ),
                )
            print(f"[EvolutionEngine] New agent proposed: {agent_spec.get('name')} → approval {approval_id}")
        except Exception as e:
            return {
                "status": "error",
                "name":   agent_spec.get("name", "unknown"),
                "reason": f"Approval queue failed: {e}",
            }

        return {
            "status":      "proposed",
            "name":        agent_spec.get("name", "unknown"),
            "department":  agent_spec.get("department"),
            "approval_id": approval_id,
        }

    # ─── detect_new_agent_patterns ───────────────────────────────────────────

    def detect_new_agent_patterns(self) -> list[dict]:
        """
        Find task patterns repeated 10+ times in the last 30 days with no
        matched agent (agent_label is null or default).
        Returns list of {task_type, agent, count, description}.
        """
        cutoff = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=30)
        ).isoformat()

        patterns: list[dict] = []
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT task_type, agent_label, COUNT(*) AS cnt
                    FROM interactions
                    WHERE org_id = %s
                      AND created_at >= %s
                      AND skill_id IS NULL
                      AND task_type NOT IN ('unknown')
                      AND (agent_label IS NULL
                           OR agent_label NOT IN ('default', 'orchestrator', 'icp_scorer'))
                    GROUP BY task_type, agent_label
                    HAVING COUNT(*) >= 10
                    ORDER BY cnt DESC
                    """,
                    (self.ctx.org_id, cutoff),
                )
                rows = cur.fetchall()

            for row in rows:
                agent = row["agent_label"] or "unassigned"
                count = int(row["cnt"])
                patterns.append({
                    "task_type":   row["task_type"] or "unknown",
                    "agent":       agent,
                    "count":       count,
                    "description": (
                        f"Agent '{agent}' runs {count} '{row['task_type']}' tasks "
                        f"with no assigned skill in the last 30 days."
                    ),
                })
        except Exception as e:
            print(f"[EvolutionEngine] Pattern detection failed: {e}")

        return patterns

    # ─── run_weekly_evolution_cycle ───────────────────────────────────────────

    def run_weekly_evolution_cycle(self) -> dict:
        """
        Full weekly evolution cycle:
          1. analyze_system_performance()
          2. skill_improvement.run_improvement_cycle()
          3. research.run_gap_fill_cycle()
          4. Propose improvements for workflows with low performance
          5. detect_new_agent_patterns() → propose_new_agent() for each
          6. Return summary dict

        Called every Saturday by orchestrator. Summary sent to Telegram.
        """
        print("[EvolutionEngine] ── Weekly evolution cycle start ──")
        summary: dict = {}

        # 1. Performance snapshot
        perf = self.analyze_system_performance()
        summary["performance"] = perf
        print(
            f"[EvolutionEngine] Performance: reply_rate={perf['overall_reply_rate']}, "
            f"interactions_30d={perf['total_interactions_30d']}, "
            f"no_skill_tasks={perf['tasks_with_no_skill_match']}"
        )

        # 2. Skill improvement cycle
        skill_results: list[dict] = []
        try:
            skill_results = self.skill_improvement.run_improvement_cycle()
            improved = [r for r in skill_results if r["action"] == "improved"]
            summary["skills_improved"] = len(improved)
            summary["skills_checked"]  = len(skill_results)
            print(f"[EvolutionEngine] Skills: {len(improved)} improved of {len(skill_results)} checked")
        except Exception as e:
            summary["skills_error"] = str(e)
            print(f"[EvolutionEngine] Skill improvement error: {e}")

        # 3. Research gap fill
        try:
            gap_result = self.research.run_gap_fill_cycle()
            summary["knowledge_gaps_filled"]   = gap_result.get("gaps_filled", 0)
            summary["knowledge_objects_created"] = gap_result.get("knowledge_objects_created", 0)
            print(
                f"[EvolutionEngine] Research: "
                f"{gap_result.get('gaps_found', 0)} gaps found, "
                f"{gap_result.get('gaps_filled', 0)} filled"
            )
        except Exception as e:
            summary["research_error"] = str(e)
            print(f"[EvolutionEngine] Research error: {e}")

        # 4. Workflow improvements for workflows with low reply rate
        workflow_proposals: list[dict] = []
        if (
            perf["overall_reply_rate"] is not None
            and perf["overall_reply_rate"] < 0.25
        ):
            try:
                with get_conn(self.ctx.org_id) as cur:
                    cur.execute(
                        "SELECT id FROM workflows WHERE org_id = %s LIMIT 5",
                        (self.ctx.org_id,),
                    )
                    wf_rows = cur.fetchall()

                for row in wf_rows:
                    wf_id = str(row["id"])
                    result = self.propose_workflow_improvement(wf_id)
                    workflow_proposals.append(result)
                    print(f"[EvolutionEngine] Workflow {wf_id}: {result['status']}")
            except Exception as e:
                print(f"[EvolutionEngine] Workflow improvement error: {e}")

        summary["workflow_proposals"] = len(workflow_proposals)

        # 5. New agent patterns
        new_agent_proposals: list[dict] = []
        try:
            patterns = self.detect_new_agent_patterns()
            print(f"[EvolutionEngine] New agent patterns detected: {len(patterns)}")
            for pattern in patterns:
                result = self.propose_new_agent(pattern["description"])
                new_agent_proposals.append(result)
                print(f"[EvolutionEngine] Agent proposal: {result.get('name')} — {result['status']}")
        except Exception as e:
            print(f"[EvolutionEngine] New agent detection error: {e}")

        summary["new_agent_proposals"] = len(new_agent_proposals)

        print("[EvolutionEngine] ── Weekly evolution cycle complete ──")
        print(f"[EvolutionEngine] Summary: {summary}")
        return summary

    # ─── Format for Telegram ─────────────────────────────────────────────────

    def format_performance_report(self, perf: dict) -> str:
        """Format analyze_system_performance() result for Telegram."""
        reply_rate = perf.get("overall_reply_rate")
        rr_str = f"{reply_rate:.1%}" if reply_rate is not None else "no data"

        most_skills   = ", ".join(perf.get("most_used_skills", [])[:3]) or "none"
        least_skills  = ", ".join(perf.get("least_used_skills", [])[:3]) or "none"

        return (
            "EOS PERFORMANCE REPORT\n"
            "─────────────────────\n\n"
            f"Reply rate (30d):     {rr_str}\n"
            f"Interactions (30d):   {perf.get('total_interactions_30d', 0)}\n"
            f"Outcomes (30d):       {perf.get('total_outcomes_30d', 0)}\n"
            f"Avg iterations/task:  {perf.get('avg_iterations_per_task', 0)}\n"
            f"No-skill tasks:       {perf.get('tasks_with_no_skill_match', 0)}\n"
            f"Approval backlog:     {perf.get('approval_queue_backlog', 0)}\n\n"
            f"Top skills:           {most_skills}\n"
            f"Least used:           {least_skills}"
        )

    def format_evolution_summary(self, summary: dict) -> str:
        """Format run_weekly_evolution_cycle() result for Telegram."""
        perf = summary.get("performance", {})
        reply_rate = perf.get("overall_reply_rate")
        rr_str = f"{reply_rate:.1%}" if reply_rate is not None else "no data"

        return (
            "EOS WEEKLY EVOLUTION\n"
            "────────────────────\n\n"
            f"Reply rate (30d):    {rr_str}\n"
            f"Skills improved:     {summary.get('skills_improved', 0)} / "
            f"{summary.get('skills_checked', 0)}\n"
            f"Knowledge gaps filled: {summary.get('knowledge_gaps_filled', 0)}\n"
            f"Knowledge objects:   {summary.get('knowledge_objects_created', 0)}\n"
            f"Workflow proposals:  {summary.get('workflow_proposals', 0)}\n"
            f"New agent proposals: {summary.get('new_agent_proposals', 0)}"
            + (f"\n\nErrors: {summary.get('skills_error', '')}" if summary.get("skills_error") else "")
        )
