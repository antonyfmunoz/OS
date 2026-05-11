"""
WorkflowEngine — manages multi-step workflow execution and state tracking.

Two layers:

1. Skill-based workflows (WORKFLOWS dict + WorkflowEngine)
   Named sequences of skill references. Steps advance via advance().
   State persisted to disk. Used by agents to run predefined pipelines.

2. Agent-task workflows (AgentWorkflowEngine)
   Dynamic workflows created at runtime via create_workflow().
   Steps execute via TaskExecutor. Human steps pause for approval.
   State persisted to Neon. Used for live business processes.
"""

from __future__ import annotations

import json
import uuid as _uuid_mod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from runtime.context import EOSContext


# ─── Agent-workflow enums and dataclasses ─────────────────────────────────────


class WorkflowStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    PAUSED = "paused"  # waiting for human step or approval
    COMPLETED = "completed"
    FAILED = "failed"
    DEPRECATED = "deprecated"


class StepOwner(Enum):
    HUMAN = "human"
    AGENT = "agent"
    TOOL = "tool"


@dataclass
class AgentWorkflowStep:
    """A single step in an agent-task workflow."""

    id: str
    name: str
    description: str
    owner: StepOwner
    agent_id: str = ""
    task_type: str = ""
    inputs: dict = field(default_factory=dict)
    requires_approval: bool = False
    on_failure: str = "stop"  # 'stop' | 'continue'
    timeout_seconds: int = 300


@dataclass
class AgentWorkflow:
    """A dynamic workflow created at runtime."""

    id: str
    name: str
    venture_id: str
    trigger: str
    steps: list[AgentWorkflowStep]
    status: WorkflowStatus = WorkflowStatus.DRAFT
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class WorkflowRun:
    """Runtime state of an agent-task workflow execution."""

    id: str
    workflow_id: str
    venture_id: str
    status: WorkflowStatus
    current_step: int = 0
    step_results: dict = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: str = ""


# ─── Workflow Step ────────────────────────────────────────────────────────────


@dataclass
class WorkflowStep:
    """A single step in a workflow."""

    name: str
    description: str
    skill_ref: str | None = None  # skill file path this step maps to
    required_inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    failure_action: str = "halt"  # 'halt' | 'skip' | 'retry'
    max_retries: int = 1


@dataclass
class WorkflowState:
    """Runtime state of an in-progress workflow execution."""

    workflow_id: str
    workflow_name: str
    started_at: str
    current_step: int = 0
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    status: str = "running"  # 'running' | 'completed' | 'failed' | 'paused'
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "started_at": self.started_at,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "outputs": self.outputs,
            "status": self.status,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowState":
        return cls(
            workflow_id=d["workflow_id"],
            workflow_name=d["workflow_name"],
            started_at=d["started_at"],
            current_step=d.get("current_step", 0),
            completed_steps=d.get("completed_steps", []),
            failed_steps=d.get("failed_steps", []),
            outputs=d.get("outputs", {}),
            status=d.get("status", "running"),
            error=d.get("error"),
        )


# ─── Workflow Definitions ─────────────────────────────────────────────────────

WORKFLOWS: dict[str, list[WorkflowStep]] = {
    "signal_to_intelligence": [
        WorkflowStep(
            name="scan_inbox",
            description="Scan raw_signals folder for unprocessed signals",
            skill_ref="skills/Research/process_signal_queue.md",
            required_inputs=["inbox_path"],
            outputs=["raw_signals_list"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="analyze_signals",
            description="Run ICP analysis on each raw signal",
            skill_ref="skills/Research/analyze_icp_signal.md",
            required_inputs=["raw_signals_list"],
            outputs=["icp_insights"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="detect_patterns",
            description="Identify recurring patterns across all insights",
            skill_ref="skills/Research/detect_icp_patterns.md",
            required_inputs=["icp_insights"],
            outputs=["pattern_report"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="generate_market_report",
            description="Synthesize patterns into actionable market intelligence",
            skill_ref="skills/Research/generate_market_report.md",
            required_inputs=["pattern_report", "icp_insights"],
            outputs=["market_report_path"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="archive_signals",
            description="Move processed signals to processed_signals folder",
            skill_ref=None,
            required_inputs=["raw_signals_list"],
            outputs=["archived_count"],
            failure_action="skip",
        ),
    ],
    "intelligence_to_outreach": [
        WorkflowStep(
            name="load_market_report",
            description="Load latest market intelligence report",
            skill_ref="skills/Research/generate_market_report.md",
            required_inputs=["market_reports_path"],
            outputs=["market_report"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="generate_outreach_messages",
            description="Generate openers, follow-ups, reframes, and call invitations",
            skill_ref="skills/Sales/generate_outreach_from_intel.md",
            required_inputs=["market_report"],
            outputs=["outreach_messages"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="generate_content_ideas",
            description="Generate content hooks and topics from same intelligence",
            skill_ref="skills/Marketing/Content/generate_content_from_intel.md",
            required_inputs=["market_report"],
            outputs=["content_ideas"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="save_outputs",
            description="Save outreach and content to CRM and content folders",
            skill_ref=None,
            required_inputs=["outreach_messages", "content_ideas"],
            outputs=["saved_files"],
            failure_action="halt",
        ),
    ],
    "lead_qualification": [
        WorkflowStep(
            name="load_lead",
            description="Load lead signal file from CRM or inbox",
            skill_ref=None,
            required_inputs=["lead_path"],
            outputs=["lead_data"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="qualify_lead",
            description="Score lead against ICP criteria",
            skill_ref="skills/Sales/Qualify Lead.md",
            required_inputs=["lead_data"],
            outputs=["qualification_score", "qualification_reason"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="extract_icp_insight",
            description="Extract reusable ICP insight from this lead",
            skill_ref="skills/Sales/Extract ICP Insight.md",
            required_inputs=["lead_data"],
            outputs=["icp_insight"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="update_lead_file",
            description="Append qualification score and insight to lead file",
            skill_ref=None,
            required_inputs=[
                "lead_data",
                "qualification_score",
                "qualification_reason",
            ],
            outputs=["updated_lead_path"],
            failure_action="halt",
        ),
    ],
    "dm_conversation_handling": [
        WorkflowStep(
            name="load_conversation",
            description="Load DM conversation from CRM",
            skill_ref=None,
            required_inputs=["conversation_path"],
            outputs=["conversation_data"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="analyze_conversation",
            description="Determine stage, signals, momentum",
            skill_ref="skills/Sales/Analyze DM Conversation.md",
            required_inputs=["conversation_data"],
            outputs=["stage", "signals", "momentum", "recommended_move"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="generate_response",
            description="Generate the next DM based on analysis",
            skill_ref="skills/Sales/analyze_conversation.md",
            required_inputs=["stage", "signals", "momentum"],
            outputs=["draft_response"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="log_interaction",
            description="Log analysis and draft to conversation file",
            skill_ref=None,
            required_inputs=["draft_response", "stage"],
            outputs=["logged"],
            failure_action="skip",
        ),
    ],
    "morning_cycle": [
        WorkflowStep(
            name="portfolio_advisory",
            description="Get portfolio board view",
            skill_ref=None,
            required_inputs=["ctx"],
            outputs=["board_view"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="ceo_reports",
            description="Per-company health snapshot",
            skill_ref=None,
            required_inputs=["ctx", "orgs"],
            outputs=["company_reports"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="strategy_pulse",
            description="Identify binding constraint",
            skill_ref=None,
            required_inputs=["ctx"],
            outputs=["binding_constraint"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="reality_signals",
            description="Process overnight signal queue",
            skill_ref=None,
            required_inputs=["ctx"],
            outputs=["critical_signals"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="send_brief",
            description="Compile and send Telegram morning brief",
            skill_ref=None,
            required_inputs=["board_view", "company_reports", "binding_constraint"],
            outputs=["message_sent"],
            failure_action="halt",
        ),
    ],
}


# ─── Workflow Templates ──────────────────────────────────────────────────────
# Templates generate workflow steps from venture data (VENTURES_JSON).
# Called by register_venture_workflows() to populate WORKFLOWS dynamically.


def _get_venture(venture_id: str) -> dict:
    """Load a venture dict from VENTURES_JSON by ID."""
    import os as _os

    ventures = json.loads(_os.getenv("VENTURES_JSON", "[]"))
    v = next((x for x in ventures if x.get("id") == venture_id), {})
    return v


def dm_to_close_template(venture_id: str) -> tuple[str, list[WorkflowStep]]:
    """DM-to-close sales workflow for any venture."""
    v = _get_venture(venture_id)
    name = v.get("name", venture_id)
    icp = v.get("icp", "the venture ICP")
    channel = v.get("primary_channel", "DM")
    return f"{venture_id}_dm_to_close", [
        WorkflowStep(
            name="qualify_lead",
            description=f"Score lead against {name} ICP — {icp}, {channel}",
            skill_ref="skills/Sales/Qualify Lead.md",
            required_inputs=["lead_data"],
            outputs=["qualification_score", "icp_fit"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="analyze_dm",
            description="Read DM thread — determine stage, signals, momentum, next move",
            skill_ref="skills/Sales/Analyze DM Conversation.md",
            required_inputs=["conversation_data", "qualification_score"],
            outputs=["stage", "signals", "recommended_move"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="generate_follow_up",
            description="Write the next DM message — opener, follow-up, or call invite",
            skill_ref="skills/Sales/Generate Follow-Up Message.md",
            required_inputs=["stage", "signals", "recommended_move"],
            outputs=["draft_message"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="handle_objections",
            description="Identify likely objection and generate reframe if needed",
            skill_ref="skills/Sales/objection_handling.md",
            required_inputs=["draft_message", "stage"],
            outputs=["final_message", "objection_handled"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="call_to_close",
            description="Run close sequence — anchor, trial close, handle objections, confirm",
            skill_ref="skills/Sales/call_to_close.md",
            required_inputs=["final_message"],
            outputs=["close_outcome"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="summarize_and_log",
            description="Summarize call outcome and log to CRM",
            skill_ref="skills/Sales/Summarize Sales Call.md",
            required_inputs=["close_outcome"],
            outputs=["call_summary", "next_action"],
            failure_action="skip",
        ),
    ]


def weekly_rhythm_template(venture_id: str) -> tuple[str, list[WorkflowStep]]:
    """Weekly operating rhythm workflow for any venture."""
    return f"{venture_id}_weekly_rhythm", [
        WorkflowStep(
            name="pipeline_review",
            description="Pull all active leads from CRM — stage, score, last contact",
            skill_ref=None,
            required_inputs=["crm_path"],
            outputs=["pipeline_snapshot"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="war_room_prep",
            description="Build war room agenda — wins, constraints, priorities",
            skill_ref="skills/Ops/Prepare War Room Agenda.md",
            required_inputs=["pipeline_snapshot"],
            outputs=["war_room_agenda"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="market_intelligence",
            description="Run ICP pattern scan across recent signals",
            skill_ref="skills/Research/generate_market_report.md",
            required_inputs=["signals_path"],
            outputs=["market_report"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="content_plan",
            description="Generate next-week content calendar from market intelligence",
            skill_ref="skills/Marketing/content_calendar.md",
            required_inputs=["market_report"],
            outputs=["content_calendar"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="outreach_queue",
            description="Generate outreach messages for top 10 leads",
            skill_ref="skills/Sales/generate_outreach_from_intel.md",
            required_inputs=["pipeline_snapshot", "market_report"],
            outputs=["outreach_queue"],
            failure_action="skip",
        ),
    ]


def b2b_to_retainer_template(venture_id: str) -> tuple[str, list[WorkflowStep]]:
    """B2B outreach-to-retainer workflow for any venture."""
    v = _get_venture(venture_id)
    name = v.get("name", venture_id)
    icp = v.get("icp", "the venture ICP")
    return f"{venture_id}_b2b_to_retainer", [
        WorkflowStep(
            name="qualify_prospect",
            description=f"Score B2B prospect against {name} ICP — {icp}",
            skill_ref="skills/Sales/Qualify Lead.md",
            required_inputs=["prospect_data"],
            outputs=["qualification_score", "icp_fit"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="generate_outreach",
            description="Write personalized outreach based on prospect signals",
            skill_ref="skills/Sales/generate_outreach_from_intel.md",
            required_inputs=["prospect_data", "qualification_score"],
            outputs=["outreach_message"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="analyze_response",
            description="Analyze prospect's reply — interest level, objections, next move",
            skill_ref="skills/Sales/analyze_conversation.md",
            required_inputs=["conversation_data"],
            outputs=["interest_level", "objections", "recommended_move"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="close_retainer",
            description="Run retainer close — scope, price anchor, objection handling",
            skill_ref="skills/Sales/call_to_close.md",
            required_inputs=["interest_level", "recommended_move"],
            outputs=["close_outcome"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="nurture_sequence",
            description="If not closed — generate 30-day nurture sequence",
            skill_ref="skills/Sales/lead_nurture.md",
            required_inputs=["close_outcome", "prospect_data"],
            outputs=["nurture_plan"],
            failure_action="skip",
        ),
    ]


def content_system_template(venture_id: str) -> tuple[str, list[WorkflowStep]]:
    """Content creation workflow for any venture."""
    v = _get_venture(venture_id)
    offer = v.get("offer", "the active offer")
    return f"{venture_id}_content_system", [
        WorkflowStep(
            name="market_scan",
            description="Scan market signals and ICP patterns for content angles",
            skill_ref="skills/Research/generate_market_report.md",
            required_inputs=["signals_path"],
            outputs=["market_report"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="generate_content_ideas",
            description="Generate hooks, angles, and formats from market intelligence",
            skill_ref="skills/Marketing/Content/generate_content_from_intel.md",
            required_inputs=["market_report"],
            outputs=["content_ideas"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="draft_offer_post",
            description=f"Draft {offer} content post with hook + body + CTA",
            skill_ref="skills/Marketing/Content/Draft Arena Content Post.md",
            required_inputs=["content_ideas"],
            outputs=["draft_post"],
            failure_action="halt",
        ),
        WorkflowStep(
            name="campaign_diagnosis",
            description="Diagnose what's working in current content campaign",
            skill_ref="skills/Marketing/campaign_diagnosis.md",
            required_inputs=["draft_post"],
            outputs=["diagnosis", "optimization_notes"],
            failure_action="skip",
        ),
        WorkflowStep(
            name="update_calendar",
            description="Update content calendar with new post and schedule",
            skill_ref="skills/Marketing/content_calendar.md",
            required_inputs=["draft_post", "diagnosis"],
            outputs=["calendar_updated"],
            failure_action="skip",
        ),
    ]


# ─── Workflow template registry ──────────────────────────────────────────────

WORKFLOW_TEMPLATES = {
    "dm_to_close": dm_to_close_template,
    "weekly_rhythm": weekly_rhythm_template,
    "b2b_to_retainer": b2b_to_retainer_template,
    "content_system": content_system_template,
}


def register_venture_workflows(venture_id: str) -> list[str]:
    """
    Generate and register all workflow templates for a venture.
    Returns list of registered workflow names.
    """
    registered = []
    for template_name, template_fn in WORKFLOW_TEMPLATES.items():
        wf_name, steps = template_fn(venture_id)
        WORKFLOWS[wf_name] = steps
        registered.append(wf_name)
    return registered


def register_all_venture_workflows() -> list[str]:
    """
    Register workflows for all ventures in VENTURES_JSON.
    Called at module load or engine init.
    """
    import os as _os

    ventures = json.loads(_os.getenv("VENTURES_JSON", "[]"))
    all_registered = []
    for v in ventures:
        vid = v.get("id", "")
        if vid:
            all_registered.extend(register_venture_workflows(vid))
    return all_registered


# Auto-register venture workflows on module load
try:
    _registered = register_all_venture_workflows()
    if _registered:
        print(
            f"[WorkflowEngine] Registered {len(_registered)} venture workflows: {_registered}"
        )
except Exception as _e:
    print(f"[WorkflowEngine] Venture workflow registration skipped: {_e}")


# ─── WorkflowEngine ───────────────────────────────────────────────────────────

_STATE_DIR = Path(__file__).parent.parent / "orchestrator" / "workflow_states"


class WorkflowEngine:
    """
    Manages workflow execution, state persistence, and step routing.

    Usage:
        we = WorkflowEngine(ctx)
        state = we.start_workflow('lead_qualification', inputs={'lead_path': '...'})
        we.advance(state, outputs={'lead_data': {...}})
    """

    def __init__(self, ctx: EOSContext) -> None:
        self.ctx = ctx
        _STATE_DIR.mkdir(parents=True, exist_ok=True)

    # ─── start_workflow ──────────────────────────────────────────────────────

    def start_workflow(
        self,
        workflow_name: str,
        inputs: dict[str, Any] | None = None,
    ) -> WorkflowState:
        """
        Initialize and persist a new workflow execution state.
        """
        if workflow_name not in WORKFLOWS:
            raise ValueError(
                f"Unknown workflow: '{workflow_name}'. "
                f"Available: {list(WORKFLOWS.keys())}"
            )
        import uuid

        state = WorkflowState(
            workflow_id=str(uuid.uuid4())[:8],
            workflow_name=workflow_name,
            started_at=datetime.now(timezone.utc).isoformat(),
            outputs=inputs or {},
        )
        self._save_state(state)
        return state

    # ─── get_current_step ────────────────────────────────────────────────────

    def get_current_step(self, state: WorkflowState) -> WorkflowStep | None:
        """Return the current step definition, or None if workflow is complete."""
        steps = WORKFLOWS.get(state.workflow_name, [])
        if state.current_step >= len(steps):
            return None
        return steps[state.current_step]

    # ─── advance ─────────────────────────────────────────────────────────────

    def advance(
        self,
        state: WorkflowState,
        outputs: dict[str, Any],
        success: bool = True,
    ) -> WorkflowStep | None:
        """
        Record step completion and advance to next step.

        Args:
            state:   Current workflow state (mutated in place).
            outputs: Outputs produced by the completed step.
            success: Whether the step succeeded.

        Returns:
            Next WorkflowStep, or None if workflow is complete.
        """
        steps = WORKFLOWS.get(state.workflow_name, [])
        if state.current_step >= len(steps):
            state.status = "completed"
            self._save_state(state)
            return None

        current = steps[state.current_step]
        state.outputs.update(outputs)

        if success:
            state.completed_steps.append(current.name)
        else:
            state.failed_steps.append(current.name)
            if current.failure_action == "halt":
                state.status = "failed"
                state.error = f"Step '{current.name}' failed and failure_action=halt"
                self._save_state(state)
                return None

        state.current_step += 1
        if state.current_step >= len(steps):
            state.status = "completed"
            self._save_state(state)
            return None

        self._save_state(state)
        return steps[state.current_step]

    # ─── get_step_prompt ─────────────────────────────────────────────────────

    def get_step_prompt(self, state: WorkflowState) -> str:
        """
        Return a prompt string for the current step, including available outputs.
        """
        step = self.get_current_step(state)
        if not step:
            return "Workflow complete."

        available = {k: v for k, v in state.outputs.items() if v is not None}
        lines = [
            f"WORKFLOW: {state.workflow_name} (step {state.current_step + 1})",
            f"CURRENT STEP: {step.name}",
            f"DESCRIPTION: {step.description}",
            f"REQUIRED INPUTS: {step.required_inputs}",
            f"EXPECTED OUTPUTS: {step.outputs}",
        ]
        if step.skill_ref:
            lines.append(f"SKILL: {step.skill_ref}")
        if available:
            lines.append(f"AVAILABLE DATA: {list(available.keys())}")
        return "\n".join(lines)

    # ─── list_workflows ──────────────────────────────────────────────────────

    @staticmethod
    def list_workflows() -> list[str]:
        """Return all available workflow names."""
        return list(WORKFLOWS.keys())

    # ─── get_workflow_steps ──────────────────────────────────────────────────

    @staticmethod
    def get_workflow_steps(workflow_name: str) -> list[WorkflowStep]:
        """Return all steps for a given workflow."""
        return WORKFLOWS.get(workflow_name, [])

    # ─── _save_state ─────────────────────────────────────────────────────────

    def _save_state(self, state: WorkflowState) -> None:
        """Persist workflow state to disk."""
        path = _STATE_DIR / f"{state.workflow_id}.json"
        with open(path, "w") as f:
            json.dump(state.to_dict(), f, indent=2)

    # ─── load_state ──────────────────────────────────────────────────────────

    def load_state(self, workflow_id: str) -> WorkflowState | None:
        """Load a workflow state from disk by ID."""
        path = _STATE_DIR / f"{workflow_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return WorkflowState.from_dict(json.load(f))


# ─── AgentWorkflowEngine ─────────────────────────────────────────────────────


class AgentWorkflowEngine:
    """
    Dynamic workflow engine — creates and runs agent-task workflows at runtime.
    Human steps pause execution. Agent steps run via TaskExecutor.
    All state persisted to Neon events table.

    Usage:
        we = AgentWorkflowEngine(ctx)
        wf = we.create_workflow(
            name='DM Outreach',
            venture_id='lyfe_institute',
            trigger='new_outreach_target',
            steps=[
                {'name': 'Score lead', 'owner': 'agent',
                 'agent_id': 'outreach_agent', 'task_type': 'analyze'},
                {'name': 'Founder review', 'owner': 'human'},
            ]
        )
        run = we.run(wf, context={'prospect': 'jake_smith'})
    """

    def __init__(self, ctx: EOSContext) -> None:
        self.ctx = ctx

    # ─── create_workflow ──────────────────────────────────────────────────────

    def create_workflow(
        self,
        name: str,
        venture_id: str,
        trigger: str,
        steps: list[dict],
    ) -> AgentWorkflow:
        workflow = AgentWorkflow(
            id=str(_uuid_mod.uuid4())[:8],
            name=name,
            venture_id=venture_id,
            trigger=trigger,
            steps=[
                AgentWorkflowStep(
                    id=str(_uuid_mod.uuid4())[:8],
                    name=s.get("name", ""),
                    description=s.get("description", ""),
                    owner=StepOwner(s.get("owner", "agent")),
                    agent_id=s.get("agent_id", ""),
                    task_type=s.get("task_type", ""),
                    inputs=s.get("inputs", {}),
                    requires_approval=s.get("requires_approval", False),
                    on_failure=s.get("on_failure", "stop"),
                )
                for s in steps
            ],
        )
        self._save_workflow(workflow)
        print(f"[AgentWorkflowEngine] Created: {workflow.name} ({workflow.id})")
        return workflow

    # ─── run ──────────────────────────────────────────────────────────────────

    def run(
        self,
        workflow: AgentWorkflow,
        context: Optional[dict] = None,
    ) -> WorkflowRun:
        from runtime.task_executor import TaskExecutor, AgentTask, TaskStatus

        run = WorkflowRun(
            id=str(_uuid_mod.uuid4())[:8],
            workflow_id=workflow.id,
            venture_id=workflow.venture_id,
            status=WorkflowStatus.RUNNING,
        )
        self._save_run(run)

        executor = TaskExecutor(self.ctx)

        for i, step in enumerate(workflow.steps):
            run.current_step = i
            print(
                f"[AgentWorkflowEngine] Step {i + 1}/{len(workflow.steps)}: {step.name}"
            )

            # Human step — pause and wait for founder action
            if step.owner == StepOwner.HUMAN:
                run.status = WorkflowStatus.PAUSED
                run.step_results[step.id] = {
                    "status": "waiting_human",
                    "step": step.name,
                }
                self._save_run(run)
                print(f"[AgentWorkflowEngine] Paused — waiting for human: {step.name}")
                return run

            # Agent step — build task and execute
            task = AgentTask(
                id=str(_uuid_mod.uuid4())[:8],
                agent_id=step.agent_id,
                venture_id=workflow.venture_id,
                task_type=step.task_type,
                description=step.description,
                inputs={**step.inputs, **(context or {})},
            )

            completed = executor.execute(task)

            run.step_results[step.id] = {
                "status": completed.status.value,
                "outputs": completed.outputs,
                "error": completed.error,
            }

            if completed.status == TaskStatus.FAILED:
                if step.on_failure == "stop":
                    run.status = WorkflowStatus.FAILED
                    run.error = completed.error
                    self._save_run(run)
                    print(
                        f"[AgentWorkflowEngine] Failed at step: "
                        f"{step.name} — {completed.error}"
                    )
                    return run
                # on_failure='continue' — log and proceed

            if completed.status == TaskStatus.BLOCKED:
                run.status = WorkflowStatus.PAUSED
                self._save_run(run)
                print(
                    f"[AgentWorkflowEngine] Blocked at step: "
                    f"{step.name} (approval required)"
                )
                return run

        run.status = WorkflowStatus.COMPLETED
        run.completed_at = datetime.now()
        self._save_run(run)
        print(f"[AgentWorkflowEngine] Completed: {workflow.name}")
        return run

    # ─── get_workflow_for_trigger ─────────────────────────────────────────────

    def get_workflow_for_trigger(
        self,
        trigger: str,
        venture_id: str,
    ) -> Optional[dict]:
        """Return the most recent active workflow matching this trigger."""
        try:
            from runtime.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json
                    FROM events
                    WHERE org_id      = %s
                      AND event_type  = 'workflow_created'
                      AND payload_json->>'trigger'    = %s
                      AND payload_json->>'venture_id' = %s
                      AND payload_json->>'status'     = 'active'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (self.ctx.org_id, trigger, venture_id),
                )
                row = cur.fetchone()
                if row:
                    data = row["payload_json"] if isinstance(row, dict) else row[0]
                    if isinstance(data, str):
                        try:
                            return json.loads(data)
                        except Exception:
                            return None
                    return data
        except Exception as e:
            print(f"[AgentWorkflowEngine] Find: {e}")
        return None

    # ─── Persistence ──────────────────────────────────────────────────────────

    def _save_workflow(self, workflow: AgentWorkflow) -> None:
        try:
            from runtime.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO events (
                        id, org_id, event_type,
                        payload_json, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (
                        str(_uuid_mod.uuid4()),
                        self.ctx.org_id,
                        "workflow_created",
                        json.dumps(
                            {
                                "workflow_id": workflow.id,
                                "name": workflow.name,
                                "venture_id": workflow.venture_id,
                                "trigger": workflow.trigger,
                                "steps": len(workflow.steps),
                                "status": workflow.status.value,
                            }
                        ),
                    ),
                )
        except Exception as e:
            print(f"[AgentWorkflowEngine] Save: {e}")

    def _save_run(self, run: WorkflowRun) -> None:
        try:
            from runtime.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO events (
                        id, org_id, event_type,
                        payload_json, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (
                        str(_uuid_mod.uuid4()),
                        self.ctx.org_id,
                        "workflow_run",
                        json.dumps(
                            {
                                "run_id": run.id,
                                "workflow_id": run.workflow_id,
                                "status": run.status.value,
                                "current_step": run.current_step,
                                "step_results": run.step_results,
                                "error": run.error,
                            }
                        ),
                    ),
                )
        except Exception as e:
            print(f"[AgentWorkflowEngine] Run save: {e}")
