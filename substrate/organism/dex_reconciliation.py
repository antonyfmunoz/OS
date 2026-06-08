"""Backward-compat shim — canonical module is advisor_reconciliation.py."""
from substrate.organism.advisor_reconciliation import (  # noqa: F401
    AdvisorReconciliation as DexReconciliation,
)
