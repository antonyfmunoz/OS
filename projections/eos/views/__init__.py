"""EOS views — project substrate data into entrepreneur-facing dashboards."""

from projections.eos.views.pipeline import PipelineView
from projections.eos.views.kpis import KPIView
from projections.eos.views.activity import ActivityView

__all__ = ["PipelineView", "KPIView", "ActivityView"]
