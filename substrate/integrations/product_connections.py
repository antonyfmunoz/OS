"""SaaS product connection manager — unified API for EOS, CreatorOS, LYFEOS.

Each product is an independent SaaS application with its own database.
UMH connects to them via integration manifests (signals, capabilities, config).
This module provides the single entry point for:
  - Checking connection status per product
  - Loading configuration from environment
  - Querying cross-product data
  - Routing signals between products

The three products share one intelligence substrate (UMH).
Each works standalone; any two compound; all three multiply.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Product(str, Enum):
    EOS = "eos"
    CREATOROS = "creatoros"
    LYFEOS = "lyfeos"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    CONFIGURED = "configured"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ProductConnection:
    product: Product
    status: ConnectionStatus
    database_url: str = ""
    poll_interval: float = 60.0
    capabilities: list[str] = field(default_factory=list)
    signal_types: list[str] = field(default_factory=list)
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ProductConnectionManager:
    """Manages connections to all three SaaS products."""

    def __init__(self) -> None:
        self._connections: dict[Product, ProductConnection] = {}
        self._load_all()

    def _load_all(self) -> None:
        self._connections[Product.EOS] = self._load_eos()
        self._connections[Product.CREATOROS] = self._load_creatoros()
        self._connections[Product.LYFEOS] = self._load_lyfeos()

    def _load_eos(self) -> ProductConnection:
        try:
            from projections.eos.integration.manifest import (
                INTEGRATION_ID,
                SIGNAL_DESCRIPTORS,
                CAPABILITY_DESCRIPTORS,
                load_eos_config,
            )

            config = load_eos_config()
            if not config:
                return ProductConnection(
                    product=Product.EOS,
                    status=ConnectionStatus.DISCONNECTED,
                )
            return ProductConnection(
                product=Product.EOS,
                status=ConnectionStatus.CONFIGURED,
                database_url=config.get("database_url", ""),
                poll_interval=config.get("poll_interval", 60.0),
                capabilities=[c.name for c in CAPABILITY_DESCRIPTORS],
                signal_types=[s.content_type for s in SIGNAL_DESCRIPTORS],
                metadata={"integration_id": INTEGRATION_ID},
            )
        except Exception as e:
            return ProductConnection(
                product=Product.EOS,
                status=ConnectionStatus.DISCONNECTED,
                error=str(e),
            )

    def _load_creatoros(self) -> ProductConnection:
        try:
            from projections.creatoros.integration.manifest import (
                INTEGRATION_ID,
                SIGNAL_DESCRIPTORS,
                CAPABILITY_DESCRIPTORS,
                load_creatoros_config,
            )

            config = load_creatoros_config()
            if not config:
                return ProductConnection(
                    product=Product.CREATOROS,
                    status=ConnectionStatus.DISCONNECTED,
                )
            return ProductConnection(
                product=Product.CREATOROS,
                status=ConnectionStatus.CONFIGURED,
                database_url=config.get("database_url", ""),
                poll_interval=config.get("poll_interval", 60.0),
                capabilities=[c.name for c in CAPABILITY_DESCRIPTORS],
                signal_types=[s.content_type for s in SIGNAL_DESCRIPTORS],
                metadata={"integration_id": INTEGRATION_ID},
            )
        except Exception as e:
            return ProductConnection(
                product=Product.CREATOROS,
                status=ConnectionStatus.DISCONNECTED,
                error=str(e),
            )

    def _load_lyfeos(self) -> ProductConnection:
        try:
            from projections.lyfeos.integration.manifest import (
                INTEGRATION_ID,
                SIGNAL_DESCRIPTORS,
                CAPABILITY_DESCRIPTORS,
                load_lyfeos_config,
            )

            config = load_lyfeos_config()
            if not config:
                return ProductConnection(
                    product=Product.LYFEOS,
                    status=ConnectionStatus.DISCONNECTED,
                )
            return ProductConnection(
                product=Product.LYFEOS,
                status=ConnectionStatus.CONFIGURED,
                database_url=config.get("database_url", ""),
                poll_interval=config.get("poll_interval", 60.0),
                capabilities=[c.name for c in CAPABILITY_DESCRIPTORS],
                signal_types=[s.content_type for s in SIGNAL_DESCRIPTORS],
                metadata={"integration_id": INTEGRATION_ID},
            )
        except Exception as e:
            return ProductConnection(
                product=Product.LYFEOS,
                status=ConnectionStatus.DISCONNECTED,
                error=str(e),
            )

    def get_connection(self, product: Product) -> ProductConnection:
        return self._connections.get(
            product, ProductConnection(product=product, status=ConnectionStatus.DISCONNECTED)
        )

    def all_connections(self) -> list[dict[str, Any]]:
        return [
            {
                "product": conn.product.value,
                "status": conn.status.value,
                "capabilities": conn.capabilities,
                "signal_types": conn.signal_types,
                "poll_interval": conn.poll_interval,
                "error": conn.error,
            }
            for conn in self._connections.values()
        ]

    def connected_products(self) -> list[Product]:
        return [
            p
            for p, conn in self._connections.items()
            if conn.status in (ConnectionStatus.CONNECTED, ConnectionStatus.CONFIGURED)
        ]

    def cross_product_summary(self) -> dict[str, Any]:
        connected = self.connected_products()
        total_capabilities = sum(len(c.capabilities) for c in self._connections.values())
        total_signals = sum(len(c.signal_types) for c in self._connections.values())
        return {
            "total_products": len(self._connections),
            "connected": len(connected),
            "products": [p.value for p in connected],
            "total_capabilities": total_capabilities,
            "total_signal_types": total_signals,
            "compounding": len(connected) >= 2,
        }

    def refresh(self) -> None:
        self._load_all()


_manager: ProductConnectionManager | None = None


def get_product_manager() -> ProductConnectionManager:
    global _manager
    if _manager is None:
        _manager = ProductConnectionManager()
    return _manager
