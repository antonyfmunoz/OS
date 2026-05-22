"""API signal factory — converts HTTP requests to SignalEnvelopes."""
from __future__ import annotations

from typing import Any

from substrate.types import (
    Modality,
    SignalEnvelope,
    SignalSource,
    SignalUrgency,
)


def http_request_to_signal(
    content: str,
    user_id: str = "api",
    organization_id: str = "munoz-holdings",
    source: SignalSource = SignalSource.EXTERNAL_API,
    urgency: SignalUrgency = SignalUrgency.NORMAL,
    metadata: dict[str, Any] | None = None,
) -> SignalEnvelope:
    """Convert an HTTP request payload to a SignalEnvelope."""
    return SignalEnvelope(
        source=source,
        content=content,
        user_id=user_id,
        organization_id=organization_id,
        modality=Modality.TEXT,
        urgency=urgency,
        metadata=metadata or {},
    )
