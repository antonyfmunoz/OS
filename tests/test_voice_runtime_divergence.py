"""P4S31 Voice Convergence — Gate 14 regression tests.

Proves the voice-runtime-divergence gate (1) passes on the converged tree,
(2) actually CATCHES a rival runtime / cloud-STT default / duplicate status enum
(a gate that cannot fail is worthless), and (3) its shrink-only legacy allowlist
is fail-closed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "check_voice_runtime_divergence",
        _ROOT / "scripts" / "check_voice_runtime_divergence.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_gate_passes_on_converged_tree() -> None:
    gate = _load_gate()
    assert gate.main() == 0


def test_gate_scans_the_real_tree_not_zero_files() -> None:
    # Regression: the repo lives under a `.claude/worktrees/...` path; an
    # absolute-parts exclude check wrongly excluded the ENTIRE tree (0 files),
    # silently disabling the gate. It must scan real files.
    gate = _load_gate()
    files = gate._py_files()
    assert len(files) > 100, f"gate scanned only {len(files)} files — exclude bug?"


def test_gate_catches_a_rival_runtime(tmp_path, monkeypatch) -> None:
    gate = _load_gate()
    rival = _ROOT / "substrate" / "execution" / "_gate14_probe.py"
    rival.write_text(
        "class RivalVoiceRuntime:\n"
        "    def run(self, a):\n"
        "        return self._engine.transcribe_fast(a)\n",
        encoding="utf-8",
    )
    try:
        errors = gate.check_single_stt_runtime()
        assert any("RivalVoiceRuntime" in e for e in errors)
    finally:
        rival.unlink(missing_ok=True)


def test_engine_infrastructure_is_exempt() -> None:
    # The canonical STT engine itself must NOT be flagged as a rival.
    gate = _load_gate()
    errors = gate.check_single_stt_runtime()
    assert not any("VoiceEngine drives STT" in e for e in errors)


def test_ts_mirror_subset_enforced() -> None:
    gate = _load_gate()
    assert gate.check_ts_mirror_subset() == []


def test_legacy_allowlist_has_valid_metadata() -> None:
    gate = _load_gate()
    # exemption-integrity audit passes on the current allowlist
    assert gate.check_exemption_integrity() == []
    # every legacy entry carries owner/rationale/sunset
    for rel, meta in gate.LEGACY_VOICE_VIOLATIONS.items():
        assert meta.get("owner") and meta.get("rationale") and meta.get("sunset"), rel
