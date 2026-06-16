"""Voice/Intent Action Contract — interface between intent sources and ActionBridge.

Defines the data contract that any intent source (voice, text, cockpit button)
must satisfy to trigger a governed action. This is NOT voice recognition — just
the translation layer.

UMH substrate subsystem. Domain-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class IntentActionRequest:
    """What any intent source must provide to trigger an action."""

    raw_text: str
    intent_source: str = "text"
    action_id: str | None = None
    parameters: dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    session_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "intent_source": self.intent_source,
            "action_id": self.action_id,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
        }


class IntentActionContract:
    """Stateless translator: IntentActionRequest → ActionRequest.

    Button clicks provide action_id directly.
    Text/voice provides raw_text for catalog resolution.
    """

    def __init__(self, catalog: Any | None = None) -> None:
        self._catalog = catalog

    def translate(self, intent: IntentActionRequest) -> Any | None:
        """Translate intent to ActionRequest.

        Returns None if no matching action found.
        """
        from substrate.organism.action_bridge import ActionRequest

        if not self._catalog:
            from substrate.organism.action_catalog import ActionCatalog

            self._catalog = ActionCatalog()

        if intent.action_id:
            action = self._catalog.resolve_by_id(intent.action_id)
        else:
            action = self._catalog.resolve(intent.raw_text)

        if not action:
            logger.debug("No action matched for: %s", intent.raw_text[:80])
            return None

        return ActionRequest(
            action_id=action.action_id,
            parameters=intent.parameters,
            source=intent.intent_source,
        )
