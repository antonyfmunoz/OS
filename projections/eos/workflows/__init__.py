"""EOS workflows — automated sequences triggered by signals."""

from projections.eos.workflows.outreach import OutreachWorkflow
from projections.eos.workflows.followup import FollowUpWorkflow
from projections.eos.workflows.content import ContentCalendarWorkflow

__all__ = ["OutreachWorkflow", "FollowUpWorkflow", "ContentCalendarWorkflow"]
