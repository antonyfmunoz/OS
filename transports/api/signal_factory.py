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
    organization_id: str = "",
    source: SignalSource = SignalSource.EXTERNAL_API,
    urgency: SignalUrgency = SignalUrgency.NORMAL,
    metadata: dict[str, Any] | None = None,
) -> SignalEnvelope:
    """Convert an HTTP request payload to a SignalEnvelope."""
    # Org id is instance context — resolve from env, never a hardcoded org.
    if not organization_id:
        import os
        organization_id = os.environ.get("UMH_ORG_ID") or os.environ.get("EOS_ORG_ID") or ""
    return SignalEnvelope(
        source=source,
        content=content,
        user_id=user_id,
        organization_id=organization_id,
        modality=Modality.TEXT,
        urgency=urgency,
        metadata=metadata or {},
    )
