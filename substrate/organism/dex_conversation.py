"""Backward-compat shim — canonical module is advisor_conversation.py.

All new code should import from substrate.organism.advisor_conversation.
"""
from substrate.organism.advisor_conversation import (  # noqa: F401
    AdvisorConversation as DexConversation,
    AdvisorResponse as DexResponse,
)
