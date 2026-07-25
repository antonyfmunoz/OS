"""Wave 2 R1 — evidence finalization is one-way, and hashes describe final bytes.

Pins finding SEC-C1, which had two parts:

1. A bare ``\\b[0-9a-f]{64}\\b`` redaction rule destroyed every legitimate sha256
   in the evidence package — artifact hashes, package_hash, scope_hash, image
   IDs — i.e. exactly the values the manifest's integrity claim rests on.
2. Files were hashed BEFORE a redaction pass rewrote them, so the recorded
   hashes described bytes that no longer existed and could never re-verify.

The tests below plant a real secret alongside legitimate 40-hex and 64-hex
hashes and assert that the secret is removed while every hash survives, then
verify the finalized package byte-for-byte.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from substrate.execution.attempts.evidence_finalization import (
    EvidenceFinalizationError,
    finalize_evidence,
    redact_text,
    scan_for_secrets,
    verify_evidence,
)

_GIT_SHA = "57c266b380cac6ec982d50088f2aa0f95e704f76"  # 40 hex — must survive
_ARTIFACT_SHA = hashlib.sha256(b"evidence").hexdigest()  # 64 hex — must survive
_IMAGE_ID = "sha256:" + hashlib.sha256(b"image").hexdigest()  # must survive
_RUN_SECRET = "a" * 64  # 64 hex — MUST be removed
_API_KEY = "sk-ant-api03-" + "Z" * 40  # typed — MUST be removed


def _write_evidence(root, *, with_secret=True):
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "candidate_sha": _GIT_SHA,
        "artifact_sha256": {"pass1.json": _ARTIFACT_SHA},
        "package_hash": _ARTIFACT_SHA,
        "authorized_scope_hash": _ARTIFACT_SHA,
        "container_image_id": _IMAGE_ID,
    }
    if with_secret:
        payload["leaked_line"] = f"UMH_W2_DISPATCH_SECRET={_RUN_SECRET}"
        payload["api"] = _API_KEY
    (root / "pass1.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (root / "notes.txt").write_text(
        f"commit {_GIT_SHA} artifact {_ARTIFACT_SHA}\n", encoding="utf-8"
    )
    (root / "screenshot.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"binary-body")
    return root


# ── redaction precision ─────────────────────────────────────────────────────


def test_legitimate_hashes_survive_redaction():
    """The regression: a bare 64-hex rule ate these. They must survive."""
    text = (
        f'{{"candidate_sha":"{_GIT_SHA}","package_hash":"{_ARTIFACT_SHA}",'
        f'"container_image_id":"{_IMAGE_ID}"}}'
    )
    out = redact_text(text)
    assert _GIT_SHA in out, "40-hex git SHA must survive"
    assert _ARTIFACT_SHA in out, "64-hex artifact/package hash must survive"
    assert _IMAGE_ID in out, "sha256: image id must survive"
    assert out == text, "no redaction should occur in hash-only text"


def test_known_exact_secret_is_removed():
    text = f"UMH_W2_DISPATCH_SECRET={_RUN_SECRET} and artifact {_ARTIFACT_SHA}"
    out = redact_text(text, exact_values=[_RUN_SECRET])
    assert _RUN_SECRET not in out, "the known secret value must be removed"
    assert _ARTIFACT_SHA in out, "the legitimate hash must survive alongside it"


def test_typed_credentials_are_removed_without_exact_value():
    for secret in (_API_KEY, "ghp_" + "B" * 36, "Bearer " + "C" * 40):
        out = redact_text(f"value: {secret}")
        assert secret not in out, f"typed credential not redacted: {secret[:12]}"


def test_scan_detects_residue_and_clears_when_clean():
    assert scan_for_secrets(f"x {_API_KEY}") != []
    assert scan_for_secrets(f"artifact {_ARTIFACT_SHA} commit {_GIT_SHA}") == []


# ── one-way pipeline ────────────────────────────────────────────────────────


def test_finalize_removes_secret_keeps_hashes_and_verifies(tmp_path):
    root = _write_evidence(tmp_path / "run")
    final = finalize_evidence(root, exact_values=[_RUN_SECRET])

    body = (root / "pass1.json").read_text(encoding="utf-8")
    assert _RUN_SECRET not in body, "run secret survived finalization"
    assert _API_KEY not in body, "api key survived finalization"
    assert _ARTIFACT_SHA in body, "artifact hash was destroyed by redaction"
    assert _GIT_SHA in body, "commit id was destroyed by redaction"
    assert _IMAGE_ID in body, "image id was destroyed by redaction"

    assert final.secret_scan_clean
    assert "pass1.json" in final.redacted_files
    # Binary artifacts are hashed, never rewritten.
    assert "screenshot.png" in final.files
    assert final.manifest_sha256

    result = verify_evidence(root)
    assert result["ok"], result


def test_recorded_hashes_describe_final_bytes(tmp_path):
    """The ordering bug: hashes were taken BEFORE redaction rewrote the files."""
    root = _write_evidence(tmp_path / "run")
    final = finalize_evidence(root, exact_values=[_RUN_SECRET])
    for rel, meta in final.files.items():
        actual = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        assert actual == meta["sha256"], f"{rel}: manifest hash != bytes on disk"


def test_verify_detects_post_finalization_mutation(tmp_path):
    root = _write_evidence(tmp_path / "run")
    finalize_evidence(root, exact_values=[_RUN_SECRET])
    assert verify_evidence(root)["ok"]

    (root / "notes.txt").write_text("tampered\n", encoding="utf-8")
    result = verify_evidence(root)
    assert not result["ok"]
    assert "notes.txt" in result["mismatched"]


def test_verify_detects_added_and_removed_files(tmp_path):
    root = _write_evidence(tmp_path / "run")
    finalize_evidence(root, exact_values=[_RUN_SECRET])

    (root / "smuggled.json").write_text("{}", encoding="utf-8")
    assert "smuggled.json" in verify_evidence(root)["extra"]
    (root / "smuggled.json").unlink()

    (root / "notes.txt").unlink()
    assert "notes.txt" in verify_evidence(root)["missing"]


def test_verification_is_deterministic_across_restarts(tmp_path):
    """Same package, repeated verification — identical result (no in-memory state)."""
    root = _write_evidence(tmp_path / "run")
    finalize_evidence(root, exact_values=[_RUN_SECRET])
    first = verify_evidence(root)
    second = verify_evidence(root)
    assert first == second and first["ok"]


def test_package_reverifies_after_transfer(tmp_path):
    """Copying the package elsewhere (evidence transfer) must still verify."""
    import shutil

    root = _write_evidence(tmp_path / "run")
    finalize_evidence(root, exact_values=[_RUN_SECRET])
    dest = tmp_path / "shipped"
    shutil.copytree(root, dest)
    assert verify_evidence(dest)["ok"], "package failed to re-verify after transfer"


def test_manifest_does_not_self_hash(tmp_path):
    root = _write_evidence(tmp_path / "run")
    final = finalize_evidence(root, exact_values=[_RUN_SECRET])
    assert "manifest.json" not in final.files, "manifest must not hash itself"
    detached = (root / "manifest.sha256").read_text(encoding="utf-8").strip()
    assert detached == final.manifest_sha256
    actual = hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
    assert actual == detached, "detached manifest hash must match the manifest bytes"


def test_finalize_fails_closed_when_a_secret_survives(tmp_path, monkeypatch):
    """If redaction cannot remove a secret, finalization must refuse."""
    root = _write_evidence(tmp_path / "run")
    # Neuter redaction so the planted secret survives into the second scan.
    monkeypatch.setattr(
        "substrate.execution.attempts.evidence_finalization.redact_text",
        lambda text, **kw: text,
    )
    with pytest.raises(EvidenceFinalizationError, match="survived redaction"):
        finalize_evidence(root, exact_values=[_RUN_SECRET])


def test_withdrawn_bare_hex_rule_does_not_eat_hashes_in_live_output():
    """Guard the specific regression BEHAVIOURALLY.

    Asserting on raw source text would also match the comment that documents the
    withdrawal, so this exercises the COMPILED operator-output regex instead:
    legitimate hashes must survive it, while the assignment form that caused the
    launch-log incident must still be redacted.
    """
    import importlib.util
    import os
    import sys

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts",
        "wave2_field_dispatch.py",
    )
    spec = importlib.util.spec_from_file_location("_w2fd_guard", path)
    mod = importlib.util.module_from_spec(spec)
    # Register before exec: a module-level @dataclass (QualificationVerdict) makes
    # dataclasses resolve sys.modules[cls.__module__] during construction; an
    # unregistered synthetic name resolves to None and crashes the import.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # import-time side effects are lazy by design
    rx = mod._SECRET_REDACT_RE

    for keep in (_GIT_SHA, _ARTIFACT_SHA, _IMAGE_ID):
        assert rx.sub("<r>", keep) == keep, f"live-output regex ate a legitimate hash: {keep}"

    leak = f"UMH_W2_DISPATCH_SECRET={_RUN_SECRET}"
    assert rx.sub("<r>", leak) != leak, "the launch-log leak form must still be redacted"
