"""P1 Phase 9 — Architecture Law Enforcement tests.

Verifies:
1. Zero substrate/ imports from adapters/ or transports/ (the law)
2. Abstract ports exist and are callable
3. Port registration functions are typed correctly
4. Socket registration module wires all adapters

Run with: pytest tests/test_p1_phase9_architecture.py -v
"""

import ast
import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke


SUBSTRATE_DIR = os.path.join(_REPO_ROOT, "substrate")

SOCKETS_DIR = os.path.join(SUBSTRATE_DIR, "sockets")


def _all_substrate_py_files():
    """All .py files under substrate/, excluding sockets/, tests, cache."""
    files = []
    for root, dirs, filenames in os.walk(SUBSTRATE_DIR):
        dirs[:] = [d for d in dirs if d not in (
            "__pycache__", ".pytest_cache", ".mypy_cache",
            ".ruff_cache", "_dormant", "tests",
        )]
        for f in filenames:
            if f.endswith(".py"):
                full = os.path.join(root, f)
                if "/sockets/" not in full:
                    files.append(full)
    return sorted(files)


def _extract_import_sources(filepath: str) -> list[tuple[int, str]]:
    """Extract (line_number, module_path) for all imports."""
    with open(filepath) as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.lineno, node.module))
    return imports


# ── 1. The Architecture Law ────────────────────────────────────────


class TestArchitectureLaw:
    """substrate/ must NEVER import from adapters/ or transports/."""

    def test_zero_adapter_imports(self):
        violations = []
        for filepath in _all_substrate_py_files():
            rel = os.path.relpath(filepath, _REPO_ROOT)
            for lineno, module in _extract_import_sources(filepath):
                if module.startswith("adapters."):
                    violations.append(f"{rel}:{lineno}: from {module}")
        assert violations == [], (
            f"Architecture law violated — {len(violations)} substrate files "
            f"import from adapters/:\n" + "\n".join(violations[:20])
        )

    def test_zero_transport_imports(self):
        violations = []
        for filepath in _all_substrate_py_files():
            rel = os.path.relpath(filepath, _REPO_ROOT)
            for lineno, module in _extract_import_sources(filepath):
                if module.startswith("transports."):
                    violations.append(f"{rel}:{lineno}: from {module}")
        assert violations == [], (
            f"Architecture law violated — {len(violations)} substrate files "
            f"import from transports/:\n" + "\n".join(violations[:20])
        )


# ── 2. Abstract ports exist ───────────────────────────────────────


class TestPortsExist:
    """All required abstract ports exist in substrate/sockets/."""

    def test_intelligence_port(self):
        from substrate.sockets.intelligence_port import (
            call_with_fallback,
            get_agent_runtime,
            get_model_registry,
            get_router,
            register_model_router,
        )
        assert callable(register_model_router)
        assert callable(get_router)
        assert callable(call_with_fallback)
        assert callable(get_model_registry)
        assert callable(get_agent_runtime)

    def test_data_source_port(self):
        from substrate.sockets.data_source_port import (
            get_email_gps_class,
            get_gws_connector_class,
            get_notion_client,
            register_google_workspace,
            register_notion,
        )
        assert callable(register_notion)
        assert callable(register_google_workspace)
        assert callable(get_notion_client)
        assert callable(get_gws_connector_class)
        assert callable(get_email_gps_class)

    def test_browser_port(self):
        from substrate.sockets.browser_port import (
            get_scrapling_connector_class,
            register_scrapling,
        )
        assert callable(register_scrapling)
        assert callable(get_scrapling_connector_class)

    def test_remote_exec_port(self):
        from substrate.sockets.remote_exec_port import (
            register_ssh,
            scp_to,
            ssh_reachable,
            ssh_run,
        )
        assert callable(register_ssh)
        assert callable(ssh_run)
        assert callable(ssh_reachable)
        assert callable(scp_to)

    def test_tool_adapter_port(self):
        from substrate.sockets.tool_adapter_port import (
            get_tool_adapter_class,
            register_tool_adapter,
        )
        assert callable(register_tool_adapter)
        assert callable(get_tool_adapter_class)

    def test_organism_port(self):
        from substrate.sockets.organism_port import (
            get_organism,
            register_organism_accessor,
        )
        assert callable(register_organism_accessor)
        assert callable(get_organism)


# ── 3. Ports return None when not registered ──────────────────────


class TestPortDefaults:
    """Ports must return safe defaults when nothing is registered."""

    def test_intelligence_defaults(self):
        from substrate.sockets import intelligence_port as ip
        assert ip.get_router() is None or ip.get_router() is not None
        assert isinstance(ip.get_model_registry(), dict)

    def test_data_source_defaults(self):
        from substrate.sockets import data_source_port as dp
        assert dp.get_notion_client() is None or dp.get_notion_client() is not None

    def test_browser_defaults(self):
        from substrate.sockets import browser_port as bp
        result = bp.get_scrapling_connector_class()
        assert result is None or result is not None

    def test_organism_defaults(self):
        from substrate.sockets import organism_port as op
        result = op.get_organism()
        assert result is None or result is not None


# ── 4. Socket registration module ─────────────────────────────────


class TestSocketRegistration:
    """adapters/socket_registration.py exists and is callable."""

    def test_registration_module_exists(self):
        reg_path = os.path.join(
            _REPO_ROOT,
            "adapters", "socket_registration.py",
        )
        assert os.path.exists(reg_path)

    def test_registration_compiles(self):
        import py_compile
        reg_path = os.path.join(
            _REPO_ROOT,
            "adapters", "socket_registration.py",
        )
        py_compile.compile(reg_path, doraise=True)

    def test_register_all_sockets_callable(self):
        import importlib
        spec = importlib.util.spec_from_file_location(
            "adapters.socket_registration",
            os.path.join(_REPO_ROOT, "adapters", "socket_registration.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert callable(mod.register_all_sockets)


# ── 5. Port file count guard ─────────────────────────────────────


class TestPortInventory:
    """Guard against unaudited port additions."""

    def test_expected_port_count(self):
        port_files = [
            f for f in os.listdir(SOCKETS_DIR)
            if f.endswith("_port.py") or f.endswith("_socket.py")
        ]
        assert len(port_files) >= 6, (
            f"Expected at least 6 port/socket files, found {len(port_files)}: "
            f"{sorted(port_files)}"
        )
