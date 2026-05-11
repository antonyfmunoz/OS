import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest
from runtime.substrate.adapter_engine_contracts import (
    InterfaceType,
    AccessPathType,
    ExecutionEnvironmentType,
    CapabilityType,
    AdapterPackage,
    AdapterProfile,
    AdapterType,
)


class TestInterfaceType(unittest.TestCase):
    def test_includes_cli(self):
        assert InterfaceType.CLI.value == "cli"

    def test_includes_discord(self):
        assert InterfaceType.DISCORD.value == "discord"

    def test_has_9_values(self):
        assert len(InterfaceType) == 9


class TestAccessPathType(unittest.TestCase):
    def test_includes_api(self):
        assert AccessPathType.API.value == "api"

    def test_includes_sdk(self):
        assert AccessPathType.SDK.value == "sdk"

    def test_includes_mcp_api_connector(self):
        assert AccessPathType.MCP_API_CONNECTOR.value == "mcp_api_connector"

    def test_includes_computer_use(self):
        assert AccessPathType.COMPUTER_USE.value == "computer_use"

    def test_includes_local_export_archive(self):
        assert AccessPathType.LOCAL_EXPORT_ARCHIVE.value == "local_export_archive"

    def test_has_20_values(self):
        assert len(AccessPathType) == 20

    def test_oauth_not_in_access_path(self):
        values = [e.value for e in AccessPathType]
        assert "oauth" not in values
        assert "oauth_user_consent" not in values

    def test_browser_session_not_in_access_path(self):
        values = [e.value for e in AccessPathType]
        assert "browser_session_profile" not in values


class TestExecutionEnvironmentType(unittest.TestCase):
    def test_includes_vps(self):
        assert ExecutionEnvironmentType.VPS.value == "vps"

    def test_includes_wsl(self):
        assert ExecutionEnvironmentType.WSL.value == "wsl"

    def test_includes_tmux(self):
        assert ExecutionEnvironmentType.TMUX.value == "tmux"

    def test_includes_local_desktop(self):
        assert ExecutionEnvironmentType.LOCAL_DESKTOP_SESSION.value == "local_desktop_session"

    def test_has_10_values(self):
        assert len(ExecutionEnvironmentType) == 10


class TestCapabilityType(unittest.TestCase):
    def test_includes_tab_aware_extraction(self):
        assert CapabilityType.TAB_AWARE_DOCUMENT_EXTRACTION.value == "tab_aware_document_extraction"

    def test_has_11_values(self):
        assert len(CapabilityType) == 11


class TestAdapterPackage(unittest.TestCase):
    def test_serializes(self):
        profile = AdapterProfile(adapter_id="test", adapter_type=AdapterType.API)
        pkg = AdapterPackage(adapter_profile=profile, access_paths=[AccessPathType.API])
        d = pkg.to_dict()
        assert d["access_paths"] == ["api"]
        assert d["adapter_profile"]["adapter_id"] == "test"


if __name__ == "__main__":
    unittest.main()
