#!/usr/bin/env python3
"""Gate 14 — Voice Runtime Divergence (P4S31 Voice Convergence).

The hard law of Phase 0 is *converge, never diverge*: there is exactly ONE
canonical voice runtime with an audio STT pipeline
(``substrate/execution/voice/session.py::VoiceSession``), and every surface is a
thin capture edge on it. This gate makes a SECOND runtime — or a cloud-STT
default, or a divergent status enum, or a TS error taxonomy that drifts from the
Python one — structurally impossible to commit.

It is SHAPE-based, not name-based (modeled on ``check_type_divergence.py``): a
class that literally drives STT off a VoiceEngine is a runtime, whatever it is
called. TTS-only reuse (``VoiceEngine().speak(...)`` for Discord playback) is NOT
a runtime and is allowed.

Four invariants:
  1. SINGLE STT RUNTIME — only the canonical ``VoiceSession`` may call
     ``<engine>.transcribe_fast(...)`` / ``.transcribe(...)``. Any other ClassDef
     in substrate/transports/services/umh/adapters that does so is a rival.
  2. NO CLOUD STT DEFAULT — no ``groq`` / cloud-STT import may sit on a voice
     module that also owns transcription (FREE+LOCAL law).
  3. ONE STATUS ENUM — the record status enum lives once, in voice/store.py.
  4. TS MIRROR IS A SUBSET — every VoiceErrorCode value appears in the codegen'd
     ``voiceErrorCodes.ts`` (client can never invent a server code).

Exit non-zero on any violation. Runs in pre-commit as Gate 14.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The ONE session runtime allowed to drive STT off a VoiceEngine.
CANONICAL_RUNTIME = "substrate/execution/voice/session.py"

# PERMANENT infrastructure exemptions — these are the STT ENGINE and batch
# media transcription, NOT rival session runtimes. The engine is the thing the
# canonical VoiceSession delegates to; exempting it is correct, not debt.
# {"file::Class": "why it is not a rival session runtime"}
ENGINE_INFRASTRUCTURE = {
    "substrate/execution/voice/voice_engine.py::VoiceEngine": (
        "the canonical STT/TTS engine itself (local faster-whisper); VoiceSession "
        "delegates transcription to it — it is the implementation, not a runtime"
    ),
    "substrate/execution/voice/voice_engine.py::IntelligentVoiceProcessor": (
        "engine-internal processor owned by voice_engine.py; not a session loop"
    ),
    "substrate/execution/media/media_processor.py::MediaProcessor": (
        "batch media-file transcription (uploaded files), a distinct concern from "
        "a live governed voice session"
    ),
}

# SHRINK-ONLY legacy debt — real FREE+LOCAL / rival violations that predate the
# convergence and are frozen here so the gate records them visibly and blocks any
# NEW one. Each MUST carry owner + rationale + sunset. This list may only shrink.
# {"file": {"owner", "rationale", "sunset"}}
LEGACY_VOICE_VIOLATIONS = {
    "services/discord_bot.py": {
        "owner": "voice-convergence",
        "rationale": (
            "legacy os-discord entrypoint (services/CLAUDE.md: 'being migrated'); "
            "its Groq STT (transcribe_with_groq) is documented legacy. The "
            "substrate-wired successor transports/discord/bot.py routes through the "
            "canonical runtime. Migrating py-cord's SilenceDetectingSink path off "
            "Groq is a separate slice (has its own 4006 connection bug) tracked "
            "as voice-first Phase 1 Discord regression (field-test step 12)."
        ),
        "sunset": "2026-09-01",
    },
}

# Tree scanned for rival runtimes.
SCAN_DIRS = ("substrate", "transports", "services", "umh", "adapters")

# STT method names that mark "this class owns a transcription session".
STT_METHODS = {"transcribe_fast", "transcribe"}

# Cloud-STT tokens that may not appear in a module that also transcribes.
CLOUD_STT_TOKENS = ("groq", "deepgram", "assemblyai", "whisper_api", "openai_stt")

_EXCLUDE_PARTS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "tests",
    ".claude",
}


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace(os.sep, "/")


def _py_files() -> list[Path]:
    out: list[Path] = []
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            # Exclude by path RELATIVE to ROOT — the repo may itself live under a
            # path segment like `.claude/worktrees/...`, so an absolute-parts check
            # would wrongly exclude the entire tree.
            rel_parts = p.relative_to(ROOT).parts
            if any(part in _EXCLUDE_PARTS for part in rel_parts):
                continue
            out.append(p)
    return out


def _class_calls_stt(node: ast.ClassDef) -> bool:
    """True if the class body calls ``<anything>.transcribe_fast/transcribe(...)``."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr in STT_METHODS:
                return True
    return False


def check_single_stt_runtime() -> list[str]:
    errors: list[str] = []
    for path in _py_files():
        rel = _rel(path)
        if rel == CANONICAL_RUNTIME:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and _class_calls_stt(node):
                key = f"{rel}::{node.name}"
                if key in ENGINE_INFRASTRUCTURE:
                    continue  # the engine / batch media transcription, not a runtime
                if rel in LEGACY_VOICE_VIOLATIONS:
                    continue  # frozen legacy debt (shrink-only)
                errors.append(
                    f"  RIVAL RUNTIME: {key} drives STT "
                    f"(transcribe/transcribe_fast) outside the canonical "
                    f"{CANONICAL_RUNTIME}. Route through VoiceSession instead."
                )
    return errors


def check_no_cloud_stt_default() -> list[str]:
    errors: list[str] = []
    for path in _py_files():
        rel = _rel(path)
        if rel in LEGACY_VOICE_VIOLATIONS:
            continue  # frozen legacy debt (shrink-only) — recorded, not silent
        text = path.read_text(encoding="utf-8")
        low = text.lower()
        # only care about modules that actually transcribe
        if not any(m in text for m in STT_METHODS):
            continue
        for tok in CLOUD_STT_TOKENS:
            # an import/use of a cloud STT provider on a transcribing module
            if f"import {tok}" in low or f"{tok}." in low or f'"{tok}"' in low:
                errors.append(
                    f"  CLOUD STT: {rel} transcribes AND references '{tok}' — "
                    f"voice STT must be FREE+LOCAL (faster-whisper). No cloud default."
                )
    return errors


def check_one_status_enum() -> list[str]:
    """The record status enum is defined once, in voice/store.py."""
    errors: list[str] = []
    homes: list[str] = []
    for path in _py_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "VoiceSessionRecordStatus":
                homes.append(_rel(path))
    canonical_home = "substrate/execution/voice/store.py"
    for h in homes:
        if h != canonical_home:
            errors.append(
                f"  DUPLICATE STATUS ENUM: VoiceSessionRecordStatus defined in {h}; "
                f"the one home is {canonical_home}."
            )
    return errors


def check_ts_mirror_subset() -> list[str]:
    errors: list[str] = []
    try:
        sys.path.insert(0, str(ROOT))
        from substrate.execution.voice.error_codes import VoiceErrorCode
    except Exception as e:  # pragma: no cover
        return [f"  CANNOT LOAD VoiceErrorCode: {e}"]
    ts = ROOT / "cockpit" / "src" / "renderer" / "api" / "voiceErrorCodes.ts"
    if not ts.exists():
        return [f"  MISSING TS MIRROR: {_rel(ts)} — run gen_voice_error_codes_ts.py"]
    mirror = ts.read_text(encoding="utf-8")
    for code in (c.value for c in VoiceErrorCode):
        if code not in mirror:
            errors.append(
                f"  TS MIRROR DRIFT: canonical code {code} absent from voiceErrorCodes.ts "
                f"— regenerate with gen_voice_error_codes_ts.py."
            )
    return errors


# ── P4S-VOICE-WS-AUTH-PREFLIGHT-001 additions ──────────────────────────────────
# Cockpit production source (renderer) — the client bundle. Excludes tests.
_COCKPIT_SRC = ROOT / "cockpit" / "src" / "renderer"

# Retired legacy voice execution surfaces that must never reappear in production.
LEGACY_VOICE_RUNTIME_TOKENS = (":8096", "VOICE_WS_UPSTREAM", "umh-voice-server")

# The voice WS connect module + the bounded-token accessor it must use.
_VOICE_WS_TS = _COCKPIT_SRC / "api" / "voice-ws.ts"
_CLIENT_TS = _COCKPIT_SRC / "api" / "client.ts"


def _cockpit_src_files() -> list[Path]:
    if not _COCKPIT_SRC.exists():
        return []
    out: list[Path] = []
    for p in _COCKPIT_SRC.rglob("*.ts*"):
        parts = p.relative_to(ROOT).parts
        if any(x in ("__tests__", "node_modules") for x in parts):
            continue
        if p.name.endswith(".test.ts") or p.name.endswith(".test.tsx"):
            continue
        out.append(p)
    return out


def check_no_legacy_voice_runtime_refs() -> list[str]:
    """No production cockpit source may reference a retired voice execution runtime
    (:8096 / VOICE_WS_UPSTREAM / umh-voice-server). Convergence must stay converged."""
    errors: list[str] = []
    for path in _cockpit_src_files():
        text = path.read_text(encoding="utf-8")
        for tok in LEGACY_VOICE_RUNTIME_TOKENS:
            if tok in text:
                errors.append(
                    f"  LEGACY VOICE RUNTIME REF: {_rel(path)} references '{tok}' — "
                    f"the standalone voice server is retired; use /api/umh/voice/ws only."
                )
    return errors


def check_voice_ws_url_canonical() -> list[str]:
    """The voice WS module must target the ONE canonical path and no other."""
    errors: list[str] = []
    if not _VOICE_WS_TS.exists():
        return errors
    text = _VOICE_WS_TS.read_text(encoding="utf-8")
    if "/api/umh/voice/ws" not in text:
        errors.append(
            f"  VOICE URL DRIFT: {_rel(_VOICE_WS_TS)} does not target /api/umh/voice/ws."
        )
    return errors


def check_bounded_token_on_connect() -> list[str]:
    """The voice WS connect path must acquire the Clerk token under a BOUNDED budget
    (acquireClerkToken), never a raw unbounded ``await getClerkToken()`` /
    ``getToken()`` that can stall the whole voice-start budget (the mobile-Safari
    deadlock that surfaced a false 'unreachable')."""
    errors: list[str] = []
    if not _VOICE_WS_TS.exists():
        return errors
    text = _VOICE_WS_TS.read_text(encoding="utf-8")
    if "acquireClerkToken" not in text:
        errors.append(
            f"  UNBOUNDED TOKEN: {_rel(_VOICE_WS_TS)} must use acquireClerkToken() "
            f"(bounded+retried) on the connect path, not a raw token fetch."
        )
    # A bare `await getClerkToken()` or `.getToken(` on the connect module is the
    # exact unbounded pattern we removed — block its reintroduction.
    for bad in ("await getClerkToken(", ".getToken("):
        if bad in text:
            errors.append(
                f"  UNBOUNDED TOKEN: {_rel(_VOICE_WS_TS)} contains '{bad}' — the voice "
                f"connect path must go through the bounded acquireClerkToken()."
            )
    return errors


def check_no_bare_unreachable_only() -> list[str]:
    """The generic 'Voice server unreachable' string may not be the client's only
    voice failure signal — a typed taxonomy must exist alongside it. We assert the
    canonical typed codes are present in the renderer so no failure is unclassified."""
    errors: list[str] = []
    store = _COCKPIT_SRC / "stores" / "voiceStore.ts"
    if not store.exists():
        return errors
    text = store.read_text(encoding="utf-8")
    required = (
        "VOICE_WS_AUTH_TOKEN_MISSING",
        "VOICE_WS_AUTH_TOKEN_TIMEOUT",
        "VOICE_WS_AUTH_FAILED",
        "VOICE_WS_UPGRADE_FAILED",
        "VOICE_RUNTIME_TIMEOUT",
    )
    missing = [c for c in required if c not in text]
    if missing:
        errors.append(
            f"  TAXONOMY INCOMPLETE: {_rel(store)} missing typed voice codes "
            f"{missing} — a generic 'unreachable' must never be the only signal."
        )
    return errors


def check_exemption_integrity() -> list[str]:
    """Fail-closed audit of the two allowlists: no dead entries, valid metadata.

    - Every ENGINE_INFRASTRUCTURE key must resolve to a real file::Class.
    - Every LEGACY_VOICE_VIOLATIONS file must exist, carry owner/rationale/sunset,
      and not be past its sunset date (compared against a build-time date passed
      via env; skipped if unset, since scripts can't read the clock here).
    """
    errors: list[str] = []
    for key in ENGINE_INFRASTRUCTURE:
        rel, _, cls = key.partition("::")
        f = ROOT / rel
        if not f.exists():
            errors.append(f"  DEAD ENGINE EXEMPTION: {rel} does not exist")
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        if cls not in names:
            errors.append(f"  DEAD ENGINE EXEMPTION: {rel} has no class {cls}")

    today = os.environ.get("UMH_GATE_TODAY", "")  # YYYY-MM-DD, optional
    for rel, meta in LEGACY_VOICE_VIOLATIONS.items():
        if not (ROOT / rel).exists():
            errors.append(f"  DEAD LEGACY EXEMPTION: {rel} does not exist")
        for field in ("owner", "rationale", "sunset"):
            if not meta.get(field):
                errors.append(f"  LEGACY EXEMPTION MISSING '{field}': {rel}")
        sunset = meta.get("sunset", "")
        if today and sunset and today > sunset:
            errors.append(
                f"  LEGACY EXEMPTION PAST SUNSET: {rel} sunset {sunset} < {today} "
                f"— migrate it off the cloud/rival path or re-justify."
            )
    return errors


def main() -> int:
    all_errors: list[str] = []
    all_errors += check_single_stt_runtime()
    all_errors += check_no_cloud_stt_default()
    all_errors += check_one_status_enum()
    all_errors += check_ts_mirror_subset()
    # P4S-VOICE-WS-AUTH-PREFLIGHT-001: convergence + client-preflight invariants.
    all_errors += check_no_legacy_voice_runtime_refs()
    all_errors += check_voice_ws_url_canonical()
    all_errors += check_bounded_token_on_connect()
    all_errors += check_no_bare_unreachable_only()
    all_errors += check_exemption_integrity()

    if all_errors:
        print("✗ FAIL — voice runtime divergence detected:")
        for e in all_errors:
            print(e)
        print(
            "\nPhase 0 law: ONE canonical voice runtime (VoiceSession), FREE+LOCAL "
            "STT, one status enum, TS mirror ⊆ Python taxonomy."
        )
        return 1

    print("✓ PASS — one voice runtime, local STT, one status enum, TS mirror in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
