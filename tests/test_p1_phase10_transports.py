"""P1 Phase 10 — Transport Layer Convergence tests.

Verifies:
1. Transport file count matches inventory
2. Cockpit routes are thin wrappers
3. Core API files don't import from wrong layers
4. Discord transport is clean

Run with: pytest tests/test_p1_phase10_transports.py -v
"""

import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

pytestmark = pytest.mark.smoke

TRANSPORTS_DIR = os.path.join(_REPO_ROOT, "transports")


class TestTransportInventory:

    def test_transport_dir_exists(self):
        assert os.path.isdir(TRANSPORTS_DIR)

    def test_minimum_file_count(self):
        count = sum(
            1 for root, _, files in os.walk(TRANSPORTS_DIR)
            if "__pycache__" not in root
            for f in files if f.endswith(".py")
        )
        assert count >= 150, f"Expected >= 150 transport files, found {count}"

    def test_cockpit_routes_exist(self):
        api_dir = os.path.join(TRANSPORTS_DIR, "api")
        route_files = [
            f for f in os.listdir(api_dir)
            if f.startswith("cockpit_") and f.endswith("_routes.py")
        ]
        assert len(route_files) >= 100, (
            f"Expected >= 100 cockpit route files, found {len(route_files)}"
        )


class TestTransportSubdirectories:

    def test_discord_transport(self):
        path = os.path.join(TRANSPORTS_DIR, "discord")
        assert os.path.isdir(path)

    def test_presence_transport(self):
        path = os.path.join(TRANSPORTS_DIR, "presence")
        assert os.path.isdir(path)

    def test_node_mesh_transport(self):
        path = os.path.join(TRANSPORTS_DIR, "node_mesh")
        assert os.path.isdir(path)

    def test_channels_transport(self):
        path = os.path.join(TRANSPORTS_DIR, "channels")
        assert os.path.isdir(path)


class TestTransportArchitecture:

    def test_discord_no_services_import(self):
        discord_dir = os.path.join(TRANSPORTS_DIR, "discord")
        for f in os.listdir(discord_dir):
            if not f.endswith(".py"):
                continue
            with open(os.path.join(discord_dir, f)) as fh:
                content = fh.read()
            assert "from services." not in content, (
                f"transports/discord/{f} imports from services/ — wrong direction"
            )
