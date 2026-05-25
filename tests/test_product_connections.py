"""Tests for substrate.integrations.product_connections."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate.integrations.product_connections import (
    ConnectionStatus,
    Product,
    ProductConnection,
    ProductConnectionManager,
    get_product_manager,
)


def test_product_enum_values():
    assert Product.EOS.value == "eos"
    assert Product.CREATOROS.value == "creatoros"
    assert Product.LYFEOS.value == "lyfeos"


def test_connection_status_values():
    assert ConnectionStatus.CONNECTED.value == "connected"
    assert ConnectionStatus.CONFIGURED.value == "configured"
    assert ConnectionStatus.DISCONNECTED.value == "disconnected"
    assert ConnectionStatus.ERROR.value == "error"


def test_product_connection_defaults():
    conn = ProductConnection(product=Product.EOS, status=ConnectionStatus.DISCONNECTED)
    assert conn.database_url == ""
    assert conn.poll_interval == 60.0
    assert conn.capabilities == []
    assert conn.signal_types == []
    assert conn.error == ""
    assert conn.metadata == {}


def test_manager_creates_all_products():
    mgr = ProductConnectionManager()
    conns = mgr.all_connections()
    assert len(conns) == 3
    products = {c["product"] for c in conns}
    assert products == {"eos", "creatoros", "lyfeos"}


def test_manager_get_connection():
    mgr = ProductConnectionManager()
    conn = mgr.get_connection(Product.EOS)
    assert conn.product == Product.EOS


def test_manager_get_missing_product():
    mgr = ProductConnectionManager()
    mgr._connections.clear()
    conn = mgr.get_connection(Product.EOS)
    assert conn.status == ConnectionStatus.DISCONNECTED


def test_all_connections_format():
    mgr = ProductConnectionManager()
    for conn in mgr.all_connections():
        assert "product" in conn
        assert "status" in conn
        assert "capabilities" in conn
        assert "signal_types" in conn
        assert "error" in conn


def test_cross_product_summary_structure():
    mgr = ProductConnectionManager()
    summary = mgr.cross_product_summary()
    assert "total_products" in summary
    assert "connected" in summary
    assert "products" in summary
    assert "total_capabilities" in summary
    assert "total_signal_types" in summary
    assert "compounding" in summary
    assert summary["total_products"] == 3


def test_connected_products_returns_configured():
    mgr = ProductConnectionManager()
    mgr._connections[Product.EOS] = ProductConnection(
        product=Product.EOS, status=ConnectionStatus.CONFIGURED
    )
    connected = mgr.connected_products()
    assert Product.EOS in connected


def test_connected_products_excludes_disconnected():
    mgr = ProductConnectionManager()
    mgr._connections[Product.EOS] = ProductConnection(
        product=Product.EOS, status=ConnectionStatus.DISCONNECTED
    )
    connected = mgr.connected_products()
    assert Product.EOS not in connected


def test_compounding_requires_two():
    mgr = ProductConnectionManager()
    for p in Product:
        mgr._connections[p] = ProductConnection(product=p, status=ConnectionStatus.DISCONNECTED)
    summary = mgr.cross_product_summary()
    assert summary["compounding"] is False

    mgr._connections[Product.EOS] = ProductConnection(
        product=Product.EOS, status=ConnectionStatus.CONFIGURED
    )
    mgr._connections[Product.CREATOROS] = ProductConnection(
        product=Product.CREATOROS, status=ConnectionStatus.CONFIGURED
    )
    summary = mgr.cross_product_summary()
    assert summary["compounding"] is True


def test_refresh_reloads():
    mgr = ProductConnectionManager()
    before = mgr.all_connections()
    mgr.refresh()
    after = mgr.all_connections()
    assert len(before) == len(after)


def test_singleton():
    m1 = get_product_manager()
    m2 = get_product_manager()
    assert m1 is m2
