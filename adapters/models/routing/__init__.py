"""Model routing — symbolic capability classes and routing config."""

from adapters.models.routing.capabilities import (
    CapabilityClass,
    CapabilityEntry,
    CAPABILITY_REGISTRY,
)
from adapters.models.routing.config import RoutingConfig, load_routing_config

__all__ = [
    "CapabilityClass",
    "CapabilityEntry",
    "CAPABILITY_REGISTRY",
    "RoutingConfig",
    "load_routing_config",
]
