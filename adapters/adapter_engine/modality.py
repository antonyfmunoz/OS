"""Communication modality types for UMH adapters.

Modality describes HOW an adapter communicates with its external target.
An adapter may use multiple modalities (composition, not inheritance).

Layer 3 Unified Architecture §2.1.
UMH substrate subsystem.
"""

from __future__ import annotations

from enum import Enum


class ModalityType(str, Enum):
    """How an adapter communicates with its external target."""

    API = "api"
    COMPUTER_USE = "computer_use"
    FILESYSTEM = "filesystem"
    DIRECT_DB = "direct_db"
