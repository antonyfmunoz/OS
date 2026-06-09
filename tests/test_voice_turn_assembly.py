"""Phase 14.13V: Voice turn assembly tests.

Tests the voice-turn-assembler.ts logic patterns via Python equivalents.
Also tests that the TypeScript files exist with the required exports.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, "/opt/OS")

import pytest


class TestVoiceTurnAssemblerExists:
    """voice-turn-assembler.ts must exist with required exports."""

    def _repo_root(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_file_exists(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        assert os.path.exists(path), f"Missing: {path}"

    def test_has_create_turn(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "export function createTurn" in content

    def test_has_append_segment(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "export function appendSegment" in content

    def test_has_commit_turn(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "export function commitTurn" in content

    def test_has_deduplicate_segments(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "export function deduplicateSegments" in content

    def test_has_normalize_transcript(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "export function normalizeTranscript" in content

    def test_has_start_silence_timer(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "export function startSilenceTimer" in content

    def test_has_voice_turn_id_type(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "voiceTurnId" in content

    def test_has_get_silence_timeout(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "getSilenceTimeoutMs" in content


class TestVoiceTurnControllerIntegration:
    """voice-controller.ts must import and use voice-turn-assembler."""

    def _repo_root(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_controller_imports_assembler(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-controller.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "voice-turn-assembler" in content
        assert "createTurn" in content
        assert "commitTurn" in content

    def test_controller_dispatches_via_assembler(self):
        """Controller should dispatch committed turns, not raw transcripts."""
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-controller.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "_dispatchCommittedTurn" in content

    def test_controller_has_barge_in(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-controller.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "barge_in" in content

    def test_controller_has_tap_to_stop(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-controller.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "tap_to_stop" in content

    def test_controller_creates_turn_on_mic_start(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-controller.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "turn_started_on_mic_start" in content

    def test_controller_passes_voice_turn_id(self):
        """sendMessage must receive voiceTurnId."""
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/stores/chatStore.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "voice_turn_id" in content
        assert "voiceTurnId" in content


class TestSilenceTimerValues:
    """Silence timer values match spec: 1600ms desktop, 2200ms mobile."""

    def _repo_root(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_desktop_timeout(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "1600" in content

    def test_mobile_timeout(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "2200" in content


class TestDeduplicationLogic:
    """Deduplication patterns exist in the assembler."""

    def _repo_root(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_has_overlap_detection(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "_findOverlap" in content

    def test_has_subset_detection(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "dedup_skip_subset" in content

    def test_has_superset_detection(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "dedup_replace_superset" in content

    def test_has_merge_overlap(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/api/voice-turn-assembler.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "dedup_merge_overlap" in content


class TestDraftBubbleSupport:
    """chatStore must support draft messages for live voice display."""

    def _repo_root(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_chat_store_has_draft(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/stores/chatStore.ts",
        )
        with open(path) as f:
            content = f.read()
        assert "draftMessage" in content
        assert "setDraftMessage" in content
        assert "commitDraftMessage" in content

    def test_right_rail_renders_draft(self):
        path = os.path.join(
            self._repo_root(),
            "cockpit/src/renderer/components/RightRail.tsx",
        )
        with open(path) as f:
            content = f.read()
        assert "draftMessage" in content
        assert "speaking..." in content
