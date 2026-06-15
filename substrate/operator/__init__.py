"""UMH Operator — unified intent classification and routing layer.

Converges the two independent operator entry paths:
  Path A (Signal/Conversation): Substrate.execute(signal) -> ExecutionResult
  Path B (Work/Organism): Substrate.execute_work(intent) -> OrganismLoopResult

IntentRouter classifies operator input and routes to the correct path.
IntentReceipt provides a canonical audit trail for every operator interaction.

Phase 18. UMH substrate subsystem. Instance-agnostic.
"""

from substrate.operator.intent_router import IntentRouter, RouteClassification, RouteType
from substrate.operator.intent_receipt import IntentReceipt, IntentReceiptStore, ReceiptStatus

__all__ = [
    "IntentRouter",
    "RouteClassification",
    "RouteType",
    "IntentReceipt",
    "IntentReceiptStore",
    "ReceiptStatus",
]
