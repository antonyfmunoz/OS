"""Report handler functions — backward-compat re-export.

All handler implementations now live in the reports/ package.
This module re-exports them so existing imports continue to work.
"""

from transports.presence.handlers.reports import (  # noqa: F401
    _handle_adapter_report,
    _handle_capability_report,
    _handle_orchestration_report,
    _handle_continuity_report,
    _handle_governance_intelligence_report,
    _handle_constitution_report,
    _handle_federation_report,
    _handle_economics_report,
    _handle_strategy_report,
    _handle_epistemic_report,
    _handle_identity_report,
    _handle_telos_report,
    _handle_resilience_report,
)
