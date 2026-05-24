"""Sensing adapter foundation for UMH perception modalities.

Provides the abstract contract (SensingAdapter), type definitions
(AdapterFamily, AdapterHealth), and registry (SensingAdapterRegistry)
that all 12 sensing adapter families implement against.

Usage:
    from adapters.sensing import SensingAdapter, SensingAdapterRegistry
    from adapters.sensing.types import AdapterFamily, SensingSocketType
"""

from adapters.sensing.base import SensingAdapter
from adapters.sensing.registry import SensingAdapterRegistry
from adapters.sensing.types import (
    AdapterFamily,
    AdapterHealth,
    SensingAdapterState,
    SensingSocketType,
)

__all__ = [
    "AdapterFamily",
    "AdapterHealth",
    "SensingAdapter",
    "SensingAdapterRegistry",
    "SensingAdapterState",
    "SensingSocketType",
]
