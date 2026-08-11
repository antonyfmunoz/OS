"""P4S-VOICE-MODEL-BENCH-001 compile-artifact validation — compile-mode gate.

Validates the compile-only benchmark PLAN + candidate matrix:
  - the JSON artifact parses and declares compile_only mode,
  - all FOUR model categories are present (stt / tts / wake_word / vad),
  - every candidate carries license + node-binding + metric (estimate) fields,
  - node assignment respects Node Role Discipline: NO heavy model is bound to
    the orchestrator role (only network-bound API baselines + trivial VAD),
  - every quantitative candidate value is flagged as an ESTIMATE,
  - any voice-clone-capable TTS candidate carries the outbound-voice governance
    flag (never recommended silently),
  - the benchmark method declares datasets + metrics + a CPU-gated executor-only
    execution environment,
  - NO benchmark-EXECUTION intent leaks in (no "run the benchmark" authorization,
    no results file written, no dependency added),
  - no first-tenant or device-hostname literal appears as global truth.

Mirrors tests/test_p4s31d_ambient_compile_artifacts.py: mechanical, fail-closed,
and truthful about what "done" means for a compile packet.
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
_ARTIFACT = _ROOT / "data/umh/voice/voice_model_bench_compile.json"
_DOC = _ROOT / "docs/VOICE_MODEL_BENCH_COMPILE.md"
_RESULTS = _ROOT / "data/umh/voice/voice_model_bench_results.jsonl"

# First-tenant + device-hostname literals that must never appear as global truth.
# Node bindings must reference infra/device_registry.json ROLES, never hostnames.
_BANNED_LITERALS = (
    "antony",
    "afm",
    "munoz",
    "beast",
    "srv1500858",
    "desktop-lvguiq9",
    "100.74.199.102",
    "100.77.233.50",
)

# Phrases that would authorize benchmark EXECUTION. This is a PLAN packet: it
# must never authorize running the benchmark (checked lowercase).
_EXECUTION_PHRASES = (
    "benchmark approved to run",
    "authorized to run",
    "cleared to run",
    "run the benchmark now",
    "begin the benchmark",
    "execute the benchmark",
    "start downloading",
    "download the models now",
    "results are attached",
    "measured on this host",
    "greenlit",
    "go-live",
)

# The FOUR model categories that must all be present.
_REQUIRED_CATEGORIES = {"stt", "tts", "wake_word", "vad"}

# Required top-level sections.
_REQUIRED_KEYS = {
    "record",
    "compiled",
    "mode",
    "compile_only",
    "packet",
    "activation_gate",
    "doctrine",
    "grounding",
    "node_role_discipline",
    "estimate_disclaimer",
    "categories",
    "benchmark_method",
    "forbidden_in_this_packet",
}

# Roles that must NEVER host a heavy (local model) candidate.
_HEAVY_FORBIDDEN_ROLE = "orchestrator"


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _all_candidates(data: dict) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for cat_name, cat in data["categories"].items():
        for cand in cat.get("candidates", []):
            out.append((cat_name, cand))
    return out


# ── parse + compile mode ──────────────────────────────────────────────────────


def test_artifact_parses():
    assert _ARTIFACT.exists(), f"missing artifact {_ARTIFACT}"
    _load(_ARTIFACT)  # raises on bad JSON


def test_artifact_declares_compile_only():
    data = _load(_ARTIFACT)
    assert data.get("compile_only") is True, "artifact must flag compile_only=true"
    assert "compile_only" in data.get("mode", ""), "artifact mode must declare compile_only"
    mode = data.get("mode", "").lower()
    assert "no benchmarks are run" in mode or "no benchmark" in mode, (
        "artifact mode must state that no benchmarks are run"
    )


def test_activation_gate_is_closed():
    data = _load(_ARTIFACT)
    gate = data["activation_gate"]
    assert gate.get("activation_authorized") is False, (
        "activation_gate.activation_authorized must be false"
    )


def test_doc_exists_and_declares_compile_mode():
    assert _DOC.exists(), "VOICE_MODEL_BENCH_COMPILE.md missing"
    text = _DOC.read_text(encoding="utf-8").lower()
    assert "compile mode" in text, "doc must declare compile mode"
    assert "no activation authorized" in text, "doc must state no activation is authorized"


# ── required sections + all four categories ───────────────────────────────────


def test_all_required_top_level_keys_present():
    data = _load(_ARTIFACT)
    missing = _REQUIRED_KEYS - set(data)
    assert not missing, f"artifact missing required top-level keys: {missing}"


def test_all_four_model_categories_present():
    data = _load(_ARTIFACT)
    cats = set(data["categories"])
    missing = _REQUIRED_CATEGORIES - cats
    assert not missing, f"benchmark must cover all four categories; missing: {missing}"


def test_every_category_has_candidates_and_a_primary_metric():
    data = _load(_ARTIFACT)
    for name in _REQUIRED_CATEGORIES:
        cat = data["categories"][name]
        assert cat.get("candidates"), f"category {name} must list candidates"
        has_metric = "primary_metric" in cat or "primary_metrics" in cat
        assert has_metric, f"category {name} must declare a primary metric"


# ── every candidate carries license + node + metric fields ────────────────────


def test_every_candidate_has_license_node_and_metric_fields():
    data = _load(_ARTIFACT)
    for cat_name, cand in _all_candidates(data):
        who = f"{cat_name}:{cand.get('name', '?')}"
        assert cand.get("license"), f"{who} missing license"
        assert cand.get("on_device_vs_api") in {"on_device", "api"}, (
            f"{who} must declare on_device_vs_api"
        )
        nb = cand.get("node_binding", {})
        assert nb.get("runtime_host_role"), f"{who} missing node_binding.runtime_host_role"
        # at least one metric/estimate field must be present
        metric_keys = {
            "est_latency_ms",
            "est_footprint_mb",
            "est_accuracy",
            "est_rtf",
            "est_cpu_pct_single_core",
        }
        assert metric_keys & set(cand), f"{who} must carry at least one estimated metric field"
        assert cand.get("quality_dimension"), f"{who} missing quality_dimension"


# ── every quantitative value is flagged ESTIMATE ──────────────────────────────


def test_every_candidate_is_flagged_estimate():
    data = _load(_ARTIFACT)
    for cat_name, cand in _all_candidates(data):
        who = f"{cat_name}:{cand.get('name', '?')}"
        assert cand.get("is_estimate") is True, (
            f"{who} must carry is_estimate=true — no value in a compile artifact is measured"
        )


def test_estimate_disclaimer_present_and_honest():
    data = _load(_ARTIFACT)
    disc = data.get("estimate_disclaimer", "").lower()
    assert "estimate" in disc, "artifact must carry an estimate disclaimer"
    assert "not a measurement" in disc or "none is a measurement" in disc, (
        "estimate disclaimer must state the numbers are not measurements"
    )


# ── Node Role Discipline: no heavy model on the orchestrator ──────────────────


def test_no_heavy_model_bound_to_orchestrator():
    """A heavy (local model) candidate must NEVER be hostable on the orchestrator
    role. Only API baselines and the trivial energy/WebRTC VAD may name it."""
    data = _load(_ARTIFACT)
    # Candidates whose runtime_host_role MAY include orchestrator: only api
    # clients OR non-model (no local weights) engines. espeak is a trivial
    # CPU-gated subprocess fallback with no model weights (the existing
    # voice_server.py fallback), in the same non-heavy class as the energy VAD.
    non_heavy_ok = {"energy_threshold_baseline", "webrtc_vad", "espeak"}
    for cat_name, cand in _all_candidates(data):
        who = f"{cat_name}:{cand.get('name', '?')}"
        roles = cand["node_binding"]["runtime_host_role"]
        names_orchestrator = _HEAVY_FORBIDDEN_ROLE in roles
        if not names_orchestrator:
            continue
        is_api = cand.get("on_device_vs_api") == "api"
        is_trivial = cand.get("name") in non_heavy_ok
        assert is_api or is_trivial, (
            f"{who} binds runtime_host_role to the orchestrator but is a heavy "
            "on-device model — Node Role Discipline forbids heavy models on the "
            "orchestrator (only API baselines + energy/WebRTC VAD may run there)"
        )


def test_node_role_discipline_section_forbids_orchestrator_heavy():
    data = _load(_ARTIFACT)
    nrd = data["node_role_discipline"]
    orch = nrd["orchestrator_role"]
    assert orch.get("runs_heavy_model") is False, (
        "node_role_discipline.orchestrator_role.runs_heavy_model must be false"
    )
    exec_role = nrd["executor_role"]
    assert exec_role.get("runs_heavy_model") is True, (
        "the executor role is the GPU workhorse and must host heavy models"
    )
    assert "executor" in nrd.get("benchmark_host_rule", "").lower(), (
        "the benchmark host rule must bind execution to the executor role"
    )


# ── voice-clone governance ────────────────────────────────────────────────────


def test_clone_capable_tts_is_governance_flagged():
    data = _load(_ARTIFACT)
    tts = data["categories"]["tts"]
    # the category must declare the outbound-voice governance block
    gov = tts.get("outbound_voice_governance", {})
    assert gov, "tts category must declare outbound_voice_governance"
    assert "voice-clone" in json.dumps(gov).lower() or "voice clone" in json.dumps(gov).lower()
    # every clone-capable candidate must carry a governance flag mentioning clone
    for cand in tts["candidates"]:
        if cand.get("clone_capable") is True:
            flags = " ".join(cand.get("governance_flags", [])).lower()
            assert "clone" in flags, (
                f"clone-capable TTS {cand['name']} must carry a voice-clone governance flag"
            )
            assert "not recommended" in flags, (
                f"clone-capable TTS {cand['name']} must state it is NOT recommended without sign-off"
            )


def test_no_clone_model_is_recommended():
    """The artifact must not RECOMMEND a clone-capable engine — it lists + flags."""
    data = _load(_ARTIFACT)
    gov = data["categories"]["tts"]["outbound_voice_governance"]
    req = json.dumps(gov).lower()
    assert (
        "no clone-capable engine is recommended" in req
        or "recommends none" in req
        or "not recommended" in req
    ), "governance must state no clone-capable engine is recommended by this benchmark"


# ── benchmark method ──────────────────────────────────────────────────────────


def test_benchmark_method_declares_datasets_and_metrics():
    data = _load(_ARTIFACT)
    method = data["benchmark_method"]
    ds = method.get("datasets_and_utterances", {})
    for cat in _REQUIRED_CATEGORIES:
        assert cat in ds, f"benchmark method must declare a dataset for {cat}"
    metrics = method.get("metrics", {})
    for cat in _REQUIRED_CATEGORIES:
        assert metrics.get(cat), f"benchmark method must declare metrics for {cat}"
    # the canonical metrics must be named
    blob = json.dumps(metrics).lower()
    assert "wer" in blob, "STT metric WER must be named"
    assert "mos" in blob, "TTS metric MOS must be named"
    assert "false_accept" in blob or "false accept" in blob, "wake FA metric must be named"
    assert "precision" in blob and "recall" in blob, "VAD precision/recall must be named"


def test_execution_environment_is_executor_only_and_cpu_gated():
    data = _load(_ARTIFACT)
    env = data["benchmark_method"]["execution_environment"]
    assert "executor" in env.get("host_role", "").lower(), (
        "benchmark execution host_role must be executor"
    )
    assert _HEAVY_FORBIDDEN_ROLE in env.get("host_role", "").lower(), (
        "execution environment must explicitly exclude the orchestrator"
    )
    blob = json.dumps(env).lower()
    assert "cpu_gate" in blob or "cpu gate" in blob or "cpu_gate_check" in blob, (
        "execution environment must be CPU-gated (CPU Gate Law)"
    )
    assert (
        "never the orchestrator" in blob
        or "no_orchestrator_load" in env
        or "never on the orchestrator" in blob
    ), "execution environment must forbid heavy load on the orchestrator"


def test_results_file_is_declared_but_not_created_here():
    """The results file belongs to the execution packet. This compile packet
    must NOT create it."""
    data = _load(_ARTIFACT)
    loc = data["benchmark_method"]["results_location"]
    assert "voice_model_bench_results" in loc.get("path", ""), (
        "results_location must name the results file"
    )
    assert "execution packet" in json.dumps(loc).lower(), (
        "results_location must state the execution packet (not this artifact) writes it"
    )
    assert not _RESULTS.exists(), (
        "the results file must NOT exist — a compile packet never writes benchmark results"
    )


# ── no benchmark-EXECUTION authorization / no dependency ──────────────────────


def test_no_execution_authorizing_language():
    text = json.dumps(_load(_ARTIFACT)).lower()
    for phrase in _EXECUTION_PHRASES:
        assert phrase not in text, (
            f"artifact carries execution-authorizing phrase {phrase!r} — "
            "compile mode must never authorize running the benchmark"
        )


def test_doc_free_of_execution_authorizing_language():
    text = _DOC.read_text(encoding="utf-8").lower()
    for phrase in _EXECUTION_PHRASES:
        assert phrase not in text, f"doc carries execution-authorizing phrase {phrase!r}"


def test_no_voice_model_dependency_added_by_this_packet():
    """Compile mode: this packet adds NO dependency. The invariant is that the
    dependency manifests are byte-identical to their committed version — NOT
    that voice libs are absent (faster-whisper / webrtcvad / silero-vad already
    ship as pre-existing runtime deps in requirements.txt, used by
    umh/voice_server.py; this compile artifact must not touch them).

    We assert the manifests are unmodified in the working tree. If git is
    unavailable the test is skipped rather than giving a false pass.
    """
    import subprocess

    manifests = ["requirements.txt", "cockpit/package.json"]
    try:
        result = subprocess.run(
            ["git", "-C", str(_ROOT), "status", "--porcelain", "--", *manifests],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        import pytest

        pytest.skip("git unavailable — cannot assert manifest immutability")
        return
    changed = [line for line in result.stdout.splitlines() if line.strip()]
    assert not changed, (
        f"this compile packet must not modify any dependency manifest — changed: {changed}"
    )


def test_forbidden_list_bans_execution_and_orchestrator_load():
    data = _load(_ARTIFACT)
    forbidden = " ".join(data["forbidden_in_this_packet"]).lower()
    assert "running any benchmark" in forbidden or "run any benchmark" in forbidden
    assert "download" in forbidden, "forbidden list must ban downloading models"
    assert "orchestrator" in forbidden, "forbidden list must ban heavy load on the orchestrator"
    assert "voice-clone" in forbidden or "voice clone" in forbidden, (
        "forbidden list must ban recommending a clone model without the flag"
    )


# ── tenant / device safety ────────────────────────────────────────────────────


def test_no_tenant_or_device_literal_in_artifact():
    text = json.dumps(_load(_ARTIFACT)).lower()
    for literal in _BANNED_LITERALS:
        assert literal not in text, (
            f"artifact carries banned literal {literal!r} — device/tenant "
            "bindings must go through registry role references, never literals"
        )


def test_doc_free_of_tenant_and_device_literals():
    text = _DOC.read_text(encoding="utf-8").lower()
    for literal in _BANNED_LITERALS:
        assert literal not in text, (
            f"VOICE_MODEL_BENCH_COMPILE.md carries banned literal {literal!r}"
        )
