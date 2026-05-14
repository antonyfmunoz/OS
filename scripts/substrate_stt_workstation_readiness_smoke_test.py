#!/usr/bin/env python3
"""
STT workstation readiness smoke test.

Validates the additive workstation-enablement layer of
``runtime.substrate.stt_producer``:

  * ``stt_workstation_readiness()`` returns a JSON-friendly classification
    that matches the current environment.
  * Env-var overrides coerce push_to_talk down the simulated path cleanly
    (``STT_FORCE_SIMULATED=1`` and ``STT_REAL_CAPTURE_ENABLED=false``).
  * ``STT_MODE`` override is honored by ``capture_once()``.
  * Device enumeration helper is safe on headless envs (returns [] cleanly).
  * Audio quality validator flags all-zero frames as degraded.
  * Existing simulated + manual + empty + push_to_talk paths still degrade
    cleanly.
  * Hot path imports remain clean.

This test is environment-agnostic: it passes on headless VPS (no mic),
CI runners, and real workstations.

Run:
    python3 scripts/substrate_stt_workstation_readiness_smoke_test.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")


def _rule(title: str) -> None:
    print(f"── {title} ".ljust(64, "─"))


def main() -> int:
    from runtime.substrate.stt_producer import (
        SttCaptureStatus,
        SttWorkstationReadiness,
        _detect_environment,
        _enumerate_input_devices,
        _validate_audio_quality,
        get_local_stt_runtime,
        reset_local_stt_runtime_for_tests,
        reset_stt_capture_history_for_tests,
        stt_runtime_status,
        stt_workstation_readiness,
    )

    VALID_CLASSES = {c.value for c in SttWorkstationReadiness}

    _rule("0. Reset state")
    reset_stt_capture_history_for_tests()
    reset_local_stt_runtime_for_tests()
    # Make sure we start with clean env knobs; restore at end.
    saved_env = {
        k: os.environ.get(k)
        for k in (
            "STT_MODE",
            "STT_FORCE_SIMULATED",
            "STT_REAL_CAPTURE_ENABLED",
            "STT_DEFAULT_DURATION_S",
            "STT_MAX_DURATION_S",
        )
    }
    for k in saved_env:
        if k in os.environ:
            del os.environ[k]

    try:
        _rule("1. stt_workstation_readiness() baseline shape")
        readiness = stt_workstation_readiness()
        for key in (
            "classification",
            "reason",
            "next_actions",
            "environment",
            "real_capture_enabled",
            "force_simulated",
            "devices",
            "default_device",
            "capability",
            "generated_at",
        ):
            assert key in readiness, f"missing key {key} in readiness"
        assert readiness["classification"] in VALID_CLASSES
        assert isinstance(readiness["next_actions"], list)
        assert isinstance(readiness["devices"], list)
        assert readiness["real_capture_enabled"] is True
        assert readiness["force_simulated"] is False
        # The classification must correspond to the capability report.
        cap = readiness["capability"]
        print(f"  classification={readiness['classification']}")
        print(f"  environment={readiness['environment']}")
        print(
            f"  mic_available={cap['mic_available']}, providers={cap['providers_available']}"
        )

        _rule("2. classification matches capability")
        if cap["real_stt_available"]:
            assert readiness["classification"] in (
                SttWorkstationReadiness.REAL_READY.value,
                SttWorkstationReadiness.REAL_CAPTURE_READY.value,
            )
        elif cap["providers_available"] and not cap["mic_available"]:
            assert readiness["classification"] == SttWorkstationReadiness.DEGRADED.value
        elif cap["mic_available"] and not cap["providers_available"]:
            assert readiness["classification"] == SttWorkstationReadiness.DEGRADED.value
        else:
            assert (
                readiness["classification"]
                == SttWorkstationReadiness.SIMULATED_ONLY.value
            )
        print("  classification/capability alignment: OK")

        _rule("3. _detect_environment() returns a known token")
        env = _detect_environment()
        assert env in {
            "ci",
            "docker",
            "cloud",
            "workstation_linux",
            "workstation_darwin",
            "workstation_windows",
            "unknown",
        }
        print(f"  environment={env}")

        _rule("4. _enumerate_input_devices() is safe / JSON-friendly")
        devices = _enumerate_input_devices()
        assert isinstance(devices, list)
        json.dumps(devices, default=str)  # must serialize
        print(f"  devices={len(devices)}")

        _rule("5. _validate_audio_quality: all-zeros flagged degraded")
        ok, reason, stats = _validate_audio_quality([0] * 1600)
        assert ok is False, "expected all-zero audio to fail"
        assert reason is not None
        assert "frames" in stats
        print(f"  reason={reason} stats={stats}")

        _rule("6. _validate_audio_quality: empty flagged")
        ok, reason, _ = _validate_audio_quality([])
        assert ok is False
        print(f"  empty reason={reason}")

        _rule("7. STT_FORCE_SIMULATED coerces push_to_talk -> simulated")
        os.environ["STT_FORCE_SIMULATED"] = "1"
        reset_local_stt_runtime_for_tests()
        rt = get_local_stt_runtime()
        event = rt.capture_once(
            "readiness-test-node",
            mode="push_to_talk",
            simulated_text="hello world",
            duration_s=0.1,
        )
        meta = event.metadata or {}
        assert meta.get("coerced_from") == "push_to_talk", meta
        assert "STT_FORCE_SIMULATED" in (meta.get("coerced_reason") or "")
        # Source must be SIMULATED_STT regardless of whether the downstream
        # session could be started (node may not be registered in this env).
        assert event.source.value == "simulated_stt"
        print(
            f"  coerced_from={meta.get('coerced_from')} source={event.source.value} status={event.status.value}"
        )
        del os.environ["STT_FORCE_SIMULATED"]

        _rule("8. STT_REAL_CAPTURE_ENABLED=false also coerces")
        os.environ["STT_REAL_CAPTURE_ENABLED"] = "false"
        reset_local_stt_runtime_for_tests()
        rt = get_local_stt_runtime()
        event = rt.capture_once(
            "readiness-test-node",
            mode="push_to_talk",
            simulated_text="also coerced",
            duration_s=0.1,
        )
        meta = event.metadata or {}
        assert meta.get("coerced_from") == "push_to_talk"
        assert "STT_REAL_CAPTURE_ENABLED" in (meta.get("coerced_reason") or "")
        print(f"  coerced_reason={meta.get('coerced_reason')}")
        del os.environ["STT_REAL_CAPTURE_ENABLED"]

        _rule("9. STT_FORCE_SIMULATED reflected in readiness classification")
        os.environ["STT_FORCE_SIMULATED"] = "1"
        r2 = stt_workstation_readiness()
        assert r2["classification"] == SttWorkstationReadiness.UNSUPPORTED.value, r2[
            "classification"
        ]
        assert r2["force_simulated"] is True
        assert r2["real_capture_enabled"] is False
        print(
            f"  classification={r2['classification']} real_capture_enabled={r2['real_capture_enabled']}"
        )
        del os.environ["STT_FORCE_SIMULATED"]

        _rule("10. STT_MODE=simulated override honored")
        os.environ["STT_MODE"] = "simulated"
        reset_local_stt_runtime_for_tests()
        rt = get_local_stt_runtime()
        # Pass mode="push_to_talk" but expect env override to flip to simulated
        event = rt.capture_once(
            "readiness-test-node",
            mode="push_to_talk",
            simulated_text="env override text",
            duration_s=0.1,
        )
        meta = event.metadata or {}
        assert meta.get("mode_override_env") == "simulated", meta
        assert event.source.value == "simulated_stt"
        print(
            f"  mode_override_env={meta.get('mode_override_env')} source={event.source.value}"
        )
        del os.environ["STT_MODE"]

        _rule("11. stt_runtime_status() now embeds readiness")
        status = stt_runtime_status()
        assert "readiness" in status
        assert status["readiness"]["classification"] in VALID_CLASSES
        print(f"  embedded classification={status['readiness']['classification']}")

        _rule("12. Hot path imports still clean")
        import importlib

        for mod in (
            "runtime.gateway",
            "control_plane.runtime.cognitive_loop",
            "execution.runtime.model_router",
            "execution.runtime.agent_runtime",
            "runtime.primitives",
        ):
            importlib.import_module(mod)
            print(f"  import ok: {mod}")

    finally:
        # Restore env
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    print()
    print("✅ substrate_stt_workstation_readiness_smoke_test: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
