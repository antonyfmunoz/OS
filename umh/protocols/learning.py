"""UMH Protocol — Learning + Self-Regulation Layer (Layer 10).

Covers internal signaling (§16.2).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from .common import Severity, SignalType


class InternalSignal(BaseModel):
    """Self-regulation signal between modules. Defined in canonical synthesis §16.2."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    source_module: str
    signal_type: SignalType
    severity: Severity
    payload: dict[str, Any] = {}
    timestamp: int
    recommended_action: str | None = None
