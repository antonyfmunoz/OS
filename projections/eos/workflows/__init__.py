"""EOS workflows — automated sequences triggered by signals."""

from projections.eos.workflows.outreach import OutreachWorkflow
from projections.eos.workflows.followup import FollowUpWorkflow
from projections.eos.workflows.content import ContentCalendarWorkflow
from projections.eos.workflows.research import ResearchWorkflow
from projections.eos.workflows.planning import PlanningWorkflow
from projections.eos.workflows.review import ReviewWorkflow
from projections.eos.workflows.execution import ExecutionWorkflow
from projections.eos.workflows.daily import DailyRhythmWorkflow
from projections.eos.workflows.github import GitHubWorkflow
from projections.eos.workflows.document import DocumentWorkflow
from projections.eos.workflows.browser import BrowserWorkflow
from projections.eos.workflows.slack import SlackWorkflow
from projections.eos.workflows.design import DesignWorkflow
from projections.eos.workflows.runner import WorkflowRunner
from projections.eos.workflows.types import WorkflowStep, WorkflowResult, StepResult

__all__ = [
    "OutreachWorkflow",
    "FollowUpWorkflow",
    "ContentCalendarWorkflow",
    "ResearchWorkflow",
    "PlanningWorkflow",
    "ReviewWorkflow",
    "ExecutionWorkflow",
    "DailyRhythmWorkflow",
    "GitHubWorkflow",
    "DocumentWorkflow",
    "BrowserWorkflow",
    "SlackWorkflow",
    "DesignWorkflow",
    "WorkflowRunner",
    "WorkflowStep",
    "WorkflowResult",
    "StepResult",
]
