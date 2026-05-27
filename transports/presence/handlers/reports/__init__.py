"""Report handler package — re-exports all handler functions."""

from .adapter import _handle_adapter_report
from .capability import _handle_capability_report
from .orchestration import _handle_orchestration_report
from .continuity import _handle_continuity_report
from .governance_intelligence import _handle_governance_intelligence_report
from .constitution import _handle_constitution_report
from .federation import _handle_federation_report
from .economics import _handle_economics_report
from .strategy import _handle_strategy_report
from .epistemic import _handle_epistemic_report
from .identity import _handle_identity_report
from .telos import _handle_telos_report
from .resilience import _handle_resilience_report

__all__ = [
    "_handle_adapter_report",
    "_handle_capability_report",
    "_handle_orchestration_report",
    "_handle_continuity_report",
    "_handle_governance_intelligence_report",
    "_handle_constitution_report",
    "_handle_federation_report",
    "_handle_economics_report",
    "_handle_strategy_report",
    "_handle_epistemic_report",
    "_handle_identity_report",
    "_handle_telos_report",
    "_handle_resilience_report",
]
