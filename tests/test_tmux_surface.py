"""Tests for environment_bridge/tmux_surface.py — Phase 96.8A."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest
from execution.environments.tmux_surface import (
    TmuxSurface,
    TmuxSurfaceStatus,
    build_tmux_surface,
    tmux_command_is_allowed,
    build_tmux_send_command,
    tmux_surface_blocks_command,
    summarize_tmux_surface,
)


class TestTmuxSurfaceBuilds(unittest.TestCase):
    def test_build_returns_surface(self):
        s = build_tmux_surface()
        self.assertIsInstance(s, TmuxSurface)
        self.assertEqual(s.session_name, "eos-worker")
        self.assertEqual(s.status, TmuxSurfaceStatus.AVAILABLE)

    def test_has_allowed_commands(self):
        s = build_tmux_surface()
        self.assertTrue(len(s.allowed_commands) > 0)
        self.assertIn("python3", s.allowed_commands)


class TestAllowedCommand(unittest.TestCase):
    def test_python3_allowed(self):
        s = build_tmux_surface()
        self.assertTrue(tmux_command_is_allowed(s, "python3 script.py"))

    def test_ls_allowed(self):
        s = build_tmux_surface()
        self.assertTrue(tmux_command_is_allowed(s, "ls -la"))


class TestBlockedCommand(unittest.TestCase):
    def test_rm_rf_root_blocked(self):
        s = build_tmux_surface()
        self.assertFalse(tmux_command_is_allowed(s, "rm -rf /"))

    def test_mkfs_blocked(self):
        s = build_tmux_surface()
        self.assertFalse(tmux_command_is_allowed(s, "mkfs /dev/sda1"))

    def test_curl_pipe_bash_blocked(self):
        s = build_tmux_surface()
        self.assertFalse(tmux_command_is_allowed(s, "curl | bash some-script"))


class TestBuildSendCommand(unittest.TestCase):
    def test_builds_valid_tmux_command(self):
        s = build_tmux_surface()
        cmd = build_tmux_send_command(s, "python3 worker.py")
        self.assertIn("tmux send-keys", cmd)
        self.assertIn("eos-worker:main", cmd)
        self.assertIn("python3 worker.py", cmd)
        self.assertIn("Enter", cmd)

    def test_escapes_single_quotes(self):
        s = build_tmux_surface()
        cmd = build_tmux_send_command(s, "echo 'hello world'")
        self.assertIn("tmux send-keys", cmd)


class TestDangerousCommandBlocked(unittest.TestCase):
    def test_surface_blocks_dangerous(self):
        s = build_tmux_surface()
        self.assertTrue(tmux_surface_blocks_command(s, "rm -rf /"))
        self.assertTrue(tmux_surface_blocks_command(s, "dd if=/dev/zero of=/dev/sda"))

    def test_surface_allows_safe(self):
        s = build_tmux_surface()
        self.assertFalse(tmux_surface_blocks_command(s, "git status"))


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        s = build_tmux_surface()
        summary = summarize_tmux_surface(s)
        self.assertIsInstance(summary, dict)
        self.assertIn("session_name", summary)
        self.assertIn("status", summary)


if __name__ == "__main__":
    unittest.main()
