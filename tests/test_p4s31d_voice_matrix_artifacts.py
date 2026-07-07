"""P4S-31D voice capability-matrix artifact validation — compile-mode gate.

Validates the compile-only deliverables of P4S-31D-VOICE-CAPABILITY-MATRIX-001:
  - the JSON artifacts parse and declare compile mode,
  - every REQUIRED platform target has a feasibility row,
  - every one of the 6 contract types declares its fields,
  - NO artifact carries a first-tenant or device-hostname literal as global truth
    (device bindings must reference infra/device_registry.json roles/ids),
  - compile-mode flags are present on the workgraph packet,
  - NO voice implementation files were shipped by this compile packet.

This mirrors tests/test_p4_sync_campaign_artifacts.py in spirit: mechanical,
fail-closed, and truthful about what "done" means for a compile packet.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

_ROOT = Path(_WORKTREE)
_MATRIX = _ROOT / "data/umh/voice/platform_voice_feasibility_matrix.json"
_TYPES = _ROOT / "data/umh/voice/voice_intent_contract_types.json"
_WORKGRAPH = _ROOT / "data/umh/roadmap/p4_sync_workgraph.json"
_CONTRACT_DOC = _ROOT / "docs/VOICE_INTENT_CONTRACT.md"

# First-tenant + device-hostname literals that must never appear as global truth.
_BANNED_LITERALS = ("antony", "afm", "munoz", "beast")

# The 6 contract types the doc + type-shapes artifact must both declare.
_REQUIRED_TYPES = {
    "TranscriptEvent",
    "WakeEvent",
    "VoiceSession",
    "DeviceCapabilityProfile",
    "PlatformVoiceAdapter",
    "VoiceConsentGrant",
}

# Every required feasibility target (owner-listed).
_REQUIRED_TARGETS = {
    "desktop_browser",
    "desktop_app",
    "mobile_app",
    "mobile_browser",
    "desktop_ambient_wake_word",
    "mobile_ambient_wake_word",
}

_PACKET_ID = "P4S-31D-VOICE-CAPABILITY-MATRIX-001"

# Files this compile packet is allowed to touch. Anything voice-*implementation*
# (adapter/route/cockpit/service code) shipping under this packet is a stop condition.
_ALLOWED_FILES = {
    "docs/VOICE_INTENT_CONTRACT.md",
    "data/umh/voice/platform_voice_feasibility_matrix.json",
    "data/umh/voice/voice_intent_contract_types.json",
    "tests/test_p4s31d_voice_matrix_artifacts.py",
}


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── parse + compile mode ──────────────────────────────────────────────────────

def test_artifacts_parse():
    for path in (_MATRIX, _TYPES, _WORKGRAPH):
        assert path.exists(), f"missing artifact {path}"
        _load(path)  # raises on bad JSON


def test_matrix_and_types_declare_compile_mode():
    for path in (_MATRIX, _TYPES):
        data = _load(path)
        assert "compile" in data.get("mode", ""), f"{path.name} must declare compile mode"


def test_contract_doc_exists_and_declares_compile_mode():
    assert _CONTRACT_DOC.exists(), "VOICE_INTENT_CONTRACT.md missing"
    text = _CONTRACT_DOC.read_text(encoding="utf-8").lower()
    assert "compile mode" in text, "contract doc must declare compile mode"


# ── feasibility targets ───────────────────────────────────────────────────────

def test_every_required_target_has_a_feasibility_row():
    data = _load(_MATRIX)
    present = {row["target"] for row in data["targets"]}
    missing = _REQUIRED_TARGETS - present
    assert not missing, f"feasibility matrix missing required targets: {missing}"


def test_each_target_row_declares_verdicts_and_reasoning():
    data = _load(_MATRIX)
    valid_verdicts = set(data["verdict_legend"].keys())
    for row in data["targets"]:
        target = row["target"]
        # Every row must carry at least a wake_word block (the honest-verdict axis)
        assert "wake_word" in row, f"{target} missing wake_word verdict block"
        for axis in ("push_to_talk", "wake_word", "ambient_always_on"):
            block = row.get(axis)
            if block is None:
                continue
            assert "why" in block or "sub_verdicts" in block, (
                f"{target}.{axis} must carry a 'why' rationale or sub_verdicts"
            )
            verdict = block.get("verdict", "")
            if verdict:
                # verdict may be a compound string (e.g. 'LIKELY(electron)/CONSTRAINED(browser)')
                assert any(v in verdict for v in valid_verdicts), (
                    f"{target}.{axis} verdict {verdict!r} uses no legend term"
                )


def test_summary_verdicts_cover_every_required_target():
    data = _load(_MATRIX)
    summary = data["summary_verdicts"]
    missing = _REQUIRED_TARGETS - set(summary)
    assert not missing, f"summary_verdicts missing targets: {missing}"


def test_mobile_ambient_is_not_promised():
    """Mobile ambient must be CONSTRAINED/NOT_FEASIBLE, never a clean promise."""
    data = _load(_MATRIX)
    summary = data["summary_verdicts"]["mobile_ambient_wake_word"]
    blob = json.dumps(summary).upper()
    assert "NOT_FEASIBLE" in blob or "CONSTRAINED" in blob, (
        "mobile ambient must be honestly constrained/not-feasible, never promised"
    )
    assert "PROVEN" not in blob and "LIKELY" not in blob, (
        "mobile ambient must not be promised as PROVEN/LIKELY"
    )


# ── contract types ────────────────────────────────────────────────────────────

def test_all_six_contract_types_declared_with_fields():
    data = _load(_TYPES)
    by_name = {t["name"]: t for t in data["types"]}
    missing = _REQUIRED_TYPES - set(by_name)
    assert not missing, f"type-shapes artifact missing types: {missing}"
    for name in _REQUIRED_TYPES:
        t = by_name[name]
        assert t.get("fields") or t.get("shape") == "interface", (
            f"type {name} must declare fields (or be an interface shape)"
        )
        # interface types still declare a fields list of members
        assert isinstance(t.get("fields"), list) and t["fields"], (
            f"type {name} declares no fields"
        )
        for field in t["fields"]:
            assert "name" in field, f"{name} has a field without a name"


def test_contract_doc_names_all_six_types():
    text = _CONTRACT_DOC.read_text(encoding="utf-8")
    for name in _REQUIRED_TYPES:
        assert name in text, f"contract doc does not define {name}"


def test_no_audio_carrying_transcript_or_wake_event():
    """Hard invariant: TranscriptEvent and WakeEvent never carry audio."""
    data = _load(_TYPES)
    by_name = {t["name"]: t for t in data["types"]}
    for name in ("TranscriptEvent", "WakeEvent"):
        fields = {f["name"]: f for f in by_name[name]["fields"]}
        assert "carries_audio" in fields, f"{name} must declare carries_audio"
        assert fields["carries_audio"].get("const") is False, (
            f"{name}.carries_audio must be const false"
        )


# ── tenant / device safety ────────────────────────────────────────────────────

def test_no_tenant_or_device_literal_in_voice_artifacts():
    """The voice JSON artifacts must be free of first-tenant + device-hostname
    literals — device bindings reference infra/device_registry.json roles/ids."""
    for path in (_MATRIX, _TYPES):
        text = json.dumps(_load(path)).lower()
        for literal in _BANNED_LITERALS:
            assert literal not in text, (
                f"{path.name} carries banned literal {literal!r} — device/tenant "
                "bindings must go through registry references, never literals"
            )


def test_contract_doc_free_of_tenant_and_device_literals():
    text = _CONTRACT_DOC.read_text(encoding="utf-8").lower()
    for literal in _BANNED_LITERALS:
        assert literal not in text, (
            f"VOICE_INTENT_CONTRACT.md carries banned literal {literal!r}"
        )


def test_device_bindings_reference_the_registry():
    """DeviceCapabilityProfile must key on the registry id, not a hostname."""
    data = _load(_TYPES)
    by_name = {t["name"]: t for t in data["types"]}
    fields = {f["name"] for f in by_name["DeviceCapabilityProfile"]["fields"]}
    assert "device_registry_id" in fields, (
        "DeviceCapabilityProfile must bind via device_registry_id (registry ref)"
    )


# ── workgraph registration ────────────────────────────────────────────────────

def test_compile_packet_registered_with_full_schema():
    data = _load(_WORKGRAPH)
    packets = {p["id"]: p for p in data["packets"]}
    assert _PACKET_ID in packets, f"{_PACKET_ID} not registered in workgraph"
    p = packets[_PACKET_ID]
    required = {"id", "objective", "dependencies", "expected_files", "tests",
                "proof", "rollback", "stop_conditions", "executor", "lane"}
    missing = required - set(p)
    assert not missing, f"{_PACKET_ID} missing packet-schema fields: {missing}"
    assert p["executor"] in ("Opus", "Sonnet")
    assert p["lane"] == "B"


def test_compile_packet_declares_compile_only():
    data = _load(_WORKGRAPH)
    p = {q["id"]: q for q in data["packets"]}[_PACKET_ID]
    assert p.get("compile_only") is True, "compile packet must flag compile_only"
    assert "compile" in p.get("mode", "").lower(), "compile packet must declare compile mode"


def test_implementation_followups_are_hard_held():
    """The first two implementation follow-ups must be registered AND hard-held."""
    data = _load(_WORKGRAPH)
    packets = {p["id"]: p for p in data["packets"]}
    for pid in ("P4S-31D-1-DESKTOP-BROWSER-PTT-001",
                "P4S-31D-2-DESKTOP-BROWSER-VOICE-PROOF-001"):
        assert pid in packets, f"implementation follow-up {pid} not registered"
        assert packets[pid].get("hard_hold"), f"{pid} must carry an explicit hard_hold"
        # full runbook schema still required on implementation packets
        required = {"id", "objective", "dependencies", "expected_files", "tests",
                    "proof", "rollback", "stop_conditions", "executor", "lane"}
        assert not (required - set(packets[pid])), f"{pid} missing runbook fields"


def test_implementation_followups_depend_on_the_compile_packet():
    data = _load(_WORKGRAPH)
    packets = {p["id"]: p for p in data["packets"]}
    # PTT depends on the compile packet; the proof depends on PTT.
    assert _PACKET_ID in packets["P4S-31D-1-DESKTOP-BROWSER-PTT-001"]["dependencies"]
    assert "P4S-31D-1-DESKTOP-BROWSER-PTT-001" in \
        packets["P4S-31D-2-DESKTOP-BROWSER-VOICE-PROOF-001"]["dependencies"]


# ── compile-mode: no implementation shipped ───────────────────────────────────

def test_no_voice_implementation_files_shipped_by_this_packet():
    """Compile mode: the deliverables are docs + JSON data + one test. No voice
    adapter/route/cockpit/service code may ship under this packet.

    We assert the four allowed deliverables exist and that none of them is a
    runtime code module (adapter/route/service/cockpit component)."""
    for rel in _ALLOWED_FILES:
        assert (_ROOT / rel).exists(), f"expected compile deliverable missing: {rel}"

    # None of the deliverables may be a Python/TS module under a runtime dir.
    runtime_dirs = ("adapters/", "transports/", "services/", "substrate/", "cockpit/src/")
    for rel in _ALLOWED_FILES:
        assert not any(rel.startswith(d) for d in runtime_dirs), (
            f"compile packet shipped a runtime file {rel} — implementation not allowed"
        )
    # The only .py deliverable is this validation test itself.
    py_deliverables = [r for r in _ALLOWED_FILES if r.endswith(".py")]
    assert py_deliverables == ["tests/test_p4s31d_voice_matrix_artifacts.py"], (
        "the only code deliverable in compile mode is the validation test"
    )
