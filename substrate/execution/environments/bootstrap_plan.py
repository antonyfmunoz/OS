"""Bootstrap plan for the Environment Bridge.

Generates step-by-step bootstrap plans for one-time local worker
setup. After initial bootstrap, the worker runs autonomously.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BootstrapStepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    COMPLETE = "complete"
    BLOCKED = "blocked"


@dataclass
class BootstrapStep:
    step_id: str = ""
    title: str = ""
    command: str = ""
    environment: str = ""
    required: bool = True
    status: BootstrapStepStatus = BootstrapStepStatus.PENDING
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "command": self.command,
            "environment": self.environment,
            "required": self.required,
            "status": self.status.value,
            "notes": self.notes,
        }


@dataclass
class BootstrapPlan:
    plan_id: str = ""
    target_environment: str = ""
    steps: list[BootstrapStep] = field(default_factory=list)
    manual_once_required: bool = True
    can_be_automated_after_bootstrap: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "target_environment": self.target_environment,
            "steps": [s.to_dict() for s in self.steps],
            "manual_once_required": self.manual_once_required,
            "can_be_automated_after_bootstrap": self.can_be_automated_after_bootstrap,
            "notes": self.notes,
        }


def build_local_worker_bootstrap_plan() -> BootstrapPlan:
    return BootstrapPlan(
        plan_id="bootstrap-local-worker-001",
        target_environment="local_wsl",
        manual_once_required=True,
        can_be_automated_after_bootstrap=True,
        steps=[
            BootstrapStep(
                step_id="create-queue-dirs",
                title="Create local queue directories",
                command=(
                    "mkdir -p ~/eos_advisor_messages/{inbox,outbox,archive,heartbeats,results}"
                ),
                environment="local_wsl",
                required=True,
            ),
            BootstrapStep(
                step_id="start-tmux-session",
                title="Start persistent tmux session",
                command="tmux new-session -d -s eos-worker -n main",
                environment="local_wsl",
                required=True,
            ),
            BootstrapStep(
                step_id="run-local-worker",
                title="Start local worker auto-loop in tmux",
                command=(
                    "tmux send-keys -t eos-worker:main "
                    "'python3 /opt/OS/runtime/substrate/local_worker_auto_loop.py "
                    "~/eos_advisor_messages/inbox/w0_001_cu_rerun_while_present.json' Enter"
                ),
                environment="local_wsl",
                required=True,
            ),
            BootstrapStep(
                step_id="verify-heartbeat",
                title="Verify worker heartbeat file exists",
                command="cat ~/eos_advisor_messages/heartbeats/local-windows-worker.json",
                environment="local_wsl",
                required=True,
            ),
            BootstrapStep(
                step_id="optional-task-scheduler",
                title="Create Windows Task Scheduler job for auto-start",
                command=(
                    'schtasks /create /tn "EOS Local Worker" '
                    "/tr \"wsl bash -c 'tmux new-session -d -s eos-worker'\" "
                    "/sc onlogon /rl highest"
                ),
                environment="local_windows_gui",
                required=False,
                notes=["Optional: auto-starts worker on Windows login"],
            ),
            BootstrapStep(
                step_id="optional-wsl-startup",
                title="Add worker start to .bashrc or .profile",
                command=(
                    "echo '# EOS worker auto-start\\n"
                    "if ! tmux has-session -t eos-worker 2>/dev/null; then\\n"
                    "  tmux new-session -d -s eos-worker -n main\\n"
                    "fi' >> ~/.bashrc"
                ),
                environment="local_wsl",
                required=False,
                notes=["Optional: auto-starts tmux session on WSL login"],
            ),
            BootstrapStep(
                step_id="optional-rsync-pull",
                title="Configure rsync pull from VPS",
                command=(
                    f"rsync -avz root@{os.getenv('EOS_VPS_TAILSCALE_IP', '100.77.233.50')}:/opt/OS/data/work_queue/outbox/ "
                    "~/eos_advisor_messages/inbox/"
                ),
                environment="local_wsl",
                required=False,
                notes=["Optional: pull packets from VPS via rsync instead of manual copy"],
            ),
        ],
        notes=[
            "Steps 1-4 are required for initial bootstrap.",
            "Steps 5-7 are optional convenience automation.",
            "After bootstrap, the worker runs autonomously in tmux.",
            "The worker polls inbox for packets and writes results to outbox.",
        ],
    )


def build_windows_task_scheduler_bootstrap_plan() -> BootstrapPlan:
    return BootstrapPlan(
        plan_id="bootstrap-task-scheduler-001",
        target_environment="local_windows_gui",
        manual_once_required=True,
        can_be_automated_after_bootstrap=True,
        steps=[
            BootstrapStep(
                step_id="create-scheduled-task",
                title="Create Windows Task Scheduler job",
                command=(
                    'schtasks /create /tn "EOS Local Worker" '
                    "/tr \"wsl bash -c 'cd /opt/OS && "
                    "tmux new-session -d -s eos-worker -n main'\" "
                    "/sc onlogon /rl highest"
                ),
                environment="local_windows_gui",
                required=True,
            ),
            BootstrapStep(
                step_id="verify-scheduled-task",
                title="Verify Task Scheduler job exists",
                command='schtasks /query /tn "EOS Local Worker"',
                environment="local_windows_gui",
                required=True,
            ),
        ],
    )


def build_tmux_local_worker_bootstrap_plan() -> BootstrapPlan:
    return BootstrapPlan(
        plan_id="bootstrap-tmux-worker-001",
        target_environment="local_wsl",
        manual_once_required=True,
        can_be_automated_after_bootstrap=True,
        steps=[
            BootstrapStep(
                step_id="install-tmux",
                title="Ensure tmux is installed",
                command="sudo apt-get install -y tmux",
                environment="local_wsl",
                required=True,
            ),
            BootstrapStep(
                step_id="create-session",
                title="Create persistent tmux session",
                command="tmux new-session -d -s eos-worker -n main",
                environment="local_wsl",
                required=True,
            ),
            BootstrapStep(
                step_id="verify-session",
                title="Verify tmux session exists",
                command="tmux has-session -t eos-worker",
                environment="local_wsl",
                required=True,
            ),
        ],
    )


def bootstrap_plan_requires_manual_once(plan: BootstrapPlan) -> bool:
    return plan.manual_once_required


def summarize_bootstrap_plan(plan: BootstrapPlan) -> dict[str, Any]:
    required_steps = [s for s in plan.steps if s.required]
    optional_steps = [s for s in plan.steps if not s.required]
    return {
        "plan_id": plan.plan_id,
        "target_environment": plan.target_environment,
        "total_steps": len(plan.steps),
        "required_steps": len(required_steps),
        "optional_steps": len(optional_steps),
        "manual_once_required": plan.manual_once_required,
        "can_automate_after": plan.can_be_automated_after_bootstrap,
        "step_ids": [s.step_id for s in plan.steps],
    }
