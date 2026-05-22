"""Daemon unit tests — verifies config, governance, adapters, and client.

Runs on Linux (VPS). Windows-only features (pywin32, pygetwindow)
are tested conditionally.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/opt/OS/.claude/worktrees/layer3-phase2-slice-d-handoff")


def test_config_defaults():
    from daemon.umh_node.config import NodeConfig, load_node_config

    config = load_node_config(
        config_path=Path("/nonexistent/path.toml"), env_path=Path("/nonexistent/.env")
    )
    assert config.vps_port == 8094
    assert config.reconnect_max_backoff_s == 60
    print("PASS: config defaults")


def test_config_from_env():
    os.environ["UMH_VPS_HOST"] = "100.77.233.50"
    os.environ["UMH_NODE_ID"] = "test-node"
    os.environ["UMH_NODE_TOKEN"] = "test-token"

    from daemon.umh_node.config import load_node_config

    config = load_node_config(
        config_path=Path("/nonexistent/path.toml"), env_path=Path("/nonexistent/.env")
    )
    assert config.vps_host == "100.77.233.50"
    assert config.node_id == "test-node"
    assert config.ws_url == "ws://100.77.233.50:8094/ws?token=test-token"

    del os.environ["UMH_VPS_HOST"]
    del os.environ["UMH_NODE_ID"]
    del os.environ["UMH_NODE_TOKEN"]
    print("PASS: config from env")


def test_config_from_toml():
    toml_content = b"""
[connection]
vps_host = "10.0.0.1"
vps_port = 9999

[identity]
node_id = "toml-node"
hostname = "TomlPC"

[capabilities.shell]
enabled = true
max_risk_class = "REVERSIBLE_WRITE"

[capabilities.desktop]
enabled = false

[signals.metrics]
interval_s = 60
"""
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        f.write(toml_content)
        toml_path = Path(f.name)

    try:
        from daemon.umh_node.config import load_node_config

        config = load_node_config(config_path=toml_path, env_path=Path("/nonexistent/.env"))
        assert config.vps_host == "10.0.0.1"
        assert config.vps_port == 9999
        assert config.node_id == "toml-node"
        assert "shell" in config.capabilities
        assert config.capabilities["shell"].max_risk_class == "REVERSIBLE_WRITE"
        assert "desktop" in config.capabilities
        assert config.capabilities["desktop"].enabled is False
        assert config.signals.metrics_interval_s == 60
    finally:
        toml_path.unlink()
    print("PASS: config from TOML")


def test_governance_allow():
    from daemon.umh_node.config import CapabilityConfig
    from daemon.umh_node.governance import validate_request

    cfg = CapabilityConfig(enabled=True, max_risk_class="IRREVERSIBLE_WRITE")
    allowed, reason = validate_request("shell", {"command": "dir"}, "REVERSIBLE_WRITE", cfg)
    assert allowed is True
    print("PASS: governance allow")


def test_governance_risk_exceeded():
    from daemon.umh_node.config import CapabilityConfig
    from daemon.umh_node.governance import validate_request

    cfg = CapabilityConfig(enabled=True, max_risk_class="SAFE_WRITE")
    allowed, reason = validate_request("shell", {}, "IRREVERSIBLE_WRITE", cfg)
    assert allowed is False
    assert "exceeds" in reason
    print("PASS: governance risk exceeded")


def test_governance_disabled():
    from daemon.umh_node.config import CapabilityConfig
    from daemon.umh_node.governance import validate_request

    cfg = CapabilityConfig(enabled=False)
    allowed, reason = validate_request("shell", {}, "READ_ONLY", cfg)
    assert allowed is False
    assert "disabled" in reason
    print("PASS: governance disabled")


def test_governance_not_configured():
    from daemon.umh_node.governance import validate_request

    allowed, reason = validate_request("unknown_cap", {}, "READ_ONLY", None)
    assert allowed is False
    assert "not configured" in reason
    print("PASS: governance not configured")


def test_governance_allowed_commands():
    from daemon.umh_node.config import CapabilityConfig
    from daemon.umh_node.governance import validate_request

    cfg = CapabilityConfig(
        enabled=True, max_risk_class="IRREVERSIBLE_WRITE", allowed_commands=["dir", "echo"]
    )

    allowed, _ = validate_request("shell", {"command": "dir C:\\"}, "REVERSIBLE_WRITE", cfg)
    assert allowed is True

    allowed, reason = validate_request("shell", {"command": "rm -rf /"}, "REVERSIBLE_WRITE", cfg)
    assert allowed is False
    assert "allowed_commands" in reason
    print("PASS: governance allowed_commands")


def test_governance_allowed_paths():
    from daemon.umh_node.config import CapabilityConfig
    from daemon.umh_node.governance import validate_request

    cfg = CapabilityConfig(
        enabled=True, max_risk_class="IRREVERSIBLE_WRITE", allowed_paths=["C:\\Users\\afm"]
    )

    allowed, _ = validate_request(
        "filesystem", {"path": "C:\\Users\\afm\\doc.txt"}, "REVERSIBLE_WRITE", cfg
    )
    assert allowed is True

    allowed, reason = validate_request(
        "filesystem", {"path": "C:\\Windows\\system32"}, "REVERSIBLE_WRITE", cfg
    )
    assert allowed is False
    assert "allowed_paths" in reason
    print("PASS: governance allowed_paths")


def test_shell_adapter():
    from daemon.umh_node.adapters.shell import ShellAdapter

    adapter = ShellAdapter()
    result = adapter.execute("shell.run", {"command": "echo hello"})
    assert result["success"] is True
    assert "hello" in result["stdout"]
    print("PASS: shell adapter")


def test_shell_adapter_timeout():
    from daemon.umh_node.adapters.shell import ShellAdapter

    adapter = ShellAdapter()
    result = adapter.execute("shell.run", {"command": "sleep 10", "timeout": 1})
    assert result["success"] is False
    assert "timed out" in result["error"]
    print("PASS: shell adapter timeout")


def test_filesystem_adapter():
    from daemon.umh_node.adapters.filesystem import FilesystemAdapter

    adapter = FilesystemAdapter()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("test content")
        path = f.name

    try:
        result = adapter.execute("fs.read", {"path": path})
        assert result["success"] is True
        assert result["content"] == "test content"

        result = adapter.execute("fs.list", {"path": str(Path(path).parent)})
        assert result["success"] is True
        assert len(result["entries"]) > 0
    finally:
        Path(path).unlink()

    with tempfile.TemporaryDirectory() as d:
        write_path = str(Path(d) / "test.txt")
        result = adapter.execute("fs.write", {"path": write_path, "content": "written"})
        assert result["success"] is True
        assert Path(write_path).read_text() == "written"

        result = adapter.execute("fs.delete", {"path": write_path})
        assert result["success"] is True
        assert not Path(write_path).exists()

    print("PASS: filesystem adapter")


def test_clipboard_adapter():
    from daemon.umh_node.adapters.clipboard import ClipboardAdapter

    adapter = ClipboardAdapter()
    # Just verify it doesn't crash — clipboard may not be available on VPS
    result = adapter.execute("clipboard.read", {})
    assert "success" in result
    print("PASS: clipboard adapter (no crash)")


def test_metrics_collector():
    from daemon.umh_node.metrics import collect_metrics

    metrics = collect_metrics()
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "disk" in metrics
    assert isinstance(metrics["cpu"], float)
    print("PASS: metrics collector")


def test_client_build_capabilities():
    from daemon.umh_node.client import NodeClient
    from daemon.umh_node.config import CapabilityConfig, NodeConfig

    config = NodeConfig(
        vps_host="127.0.0.1",
        node_id="test",
        capabilities={
            "shell": CapabilityConfig(enabled=True, max_risk_class="IRREVERSIBLE_WRITE"),
            "filesystem": CapabilityConfig(enabled=True),
            "desktop": CapabilityConfig(enabled=False),
        },
    )
    client = NodeClient(config)
    caps = client._build_capabilities()

    names = {c["name"] for c in caps}
    assert "shell" in names
    assert "filesystem" in names
    assert "desktop" not in names  # disabled
    print("PASS: client build_capabilities")


if __name__ == "__main__":
    test_config_defaults()
    test_config_from_env()
    test_config_from_toml()
    test_governance_allow()
    test_governance_risk_exceeded()
    test_governance_disabled()
    test_governance_not_configured()
    test_governance_allowed_commands()
    test_governance_allowed_paths()
    test_shell_adapter()
    test_shell_adapter_timeout()
    test_filesystem_adapter()
    test_clipboard_adapter()
    test_metrics_collector()
    test_client_build_capabilities()
    print("\n=== ALL 15 DAEMON TESTS PASSED ===")
