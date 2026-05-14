"""UMH Protocol — Control Plane (Layer 2).

Defined in canonical synthesis §8.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from .common import AuthorityContext


class ControlPlaneEvent(BaseModel):
    """Event flowing through the UMH control plane. Defined in canonical synthesis §8."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    event_id: str
    source: str
    event_type: str
    payload: dict[str, Any]
    schema_version: str
    user_instance_id: str
    session_id: str
    environment_id: str
    timestamp: int
    authority_context: AuthorityContext
    trace_id: str
