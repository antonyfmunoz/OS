from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

_WORKTREE = Path(__file__).resolve().parent.parent


def _load_collector():
    spec = importlib.util.spec_from_file_location(
        "wave2_field_collector",
        str(_WORKTREE / "scripts" / "wave2_field_collector.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wave2_field_collector"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _load_dispatch():
    spec = importlib.util.spec_from_file_location(
        "wave2_field_dispatch",
        str(_WORKTREE / "scripts" / "wave2_field_dispatch.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wave2_field_dispatch"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _collector(tmp_path: Path):
    mod = _load_collector()
    c = mod.FieldCollector(
        url="https://candidate.example",
        run_id="run-1",
        pass_num=1,
        evidence_dir=tmp_path,
        candidate_commit="abc123",
        scenario="full",
        ship_to="/proof/raw",
    )
    c.stages.append({"stage": "w01_session", "ok": True, "ms": 1, "detail": ""})
    c.session_proof = {"ok": True}
    return mod, c


def test_execution_complete_is_not_terminal_before_evidence_receipt(tmp_path, monkeypatch):
    _mod, c = _collector(tmp_path)
    observed_states: list[str] = []

    def fake_publish(_execution_passed: bool):
        status = json.loads((c.pass_dir / "status.json").read_text(encoding="utf-8"))
        observed_states.append(status["state"])
        return {"ok": True, "receipt": {"receipt_id": "r1"}}

    monkeypatch.setattr(c, "_publish_evidence", fake_publish)

    result = c._finalize(SimpleNamespace())

    assert result["pass"] is True
    assert observed_states == ["evidence_shipping"]
    final_status = json.loads((c.pass_dir / "status.json").read_text(encoding="utf-8"))
    assert final_status["state"] == "passed"
    assert final_status["evidence_receipt"]["receipt_id"] == "r1"


def test_publication_failure_is_distinct_from_execution_failure(tmp_path, monkeypatch):
    _mod, c = _collector(tmp_path)

    def fail_publish(_execution_passed: bool):
        return {"ok": False, "error": "manifest mismatch"}

    monkeypatch.setattr(c, "_publish_evidence", fail_publish)

    result = c._finalize(SimpleNamespace())

    assert result["pass"] is False
    assert result["execution_passed"] is True
    assert result["evidence_publication"]["ok"] is False
    status = json.loads((c.pass_dir / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == "evidence_preservation_failed"
    assert status["preservation_error"] == "manifest mismatch"
    saved = json.loads((c.pass_dir / "result.json").read_text(encoding="utf-8"))
    assert saved["pass"] is False
    assert saved["evidence_publication"]["error"] == "manifest mismatch"


def test_poll_status_waits_for_committed_receipt_before_terminal(monkeypatch):
    dispatch = _load_dispatch()
    runner = dispatch.Runner(dry_run=False)
    states = iter(
        [
            {"ok": True, "stdout": json.dumps({"state": "execution_complete"})},
            {"ok": True, "stdout": json.dumps({"state": "evidence_shipping"})},
            {
                "ok": True,
                "stdout": json.dumps(
                    {
                        "state": "passed",
                        "evidence_receipt": {"receipt_id": "receipt-1"},
                    }
                ),
            },
        ]
    )
    monkeypatch.setattr(dispatch, "_mesh_read", lambda *_a, **_kw: next(states))
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)

    out = dispatch._poll_status(runner, "run-1", 1, timeout_min=1)

    assert out["state"] == "passed"
    assert out["evidence_receipt"]["receipt_id"] == "receipt-1"


def test_poll_status_rejects_passed_without_receipt(monkeypatch):
    dispatch = _load_dispatch()
    runner = dispatch.Runner(dry_run=False)
    states = iter(
        [
            {"ok": True, "stdout": json.dumps({"state": "passed"})},
            {
                "ok": True,
                "stdout": json.dumps(
                    {
                        "state": "evidence_preservation_failed",
                        "preservation_error": "no committed receipt",
                    }
                ),
            },
        ]
    )
    monkeypatch.setattr(dispatch, "_mesh_read", lambda *_a, **_kw: next(states))
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)

    out = dispatch._poll_status(runner, "run-1", 1, timeout_min=1)

    assert out["state"] == "evidence_preservation_failed"
    assert out["preservation_error"] == "no committed receipt"


def test_reconcile_ignores_staging_directories(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging = root / "raw" / "run-1" / ".staging-pass1-attempt" / "pass1"
    staging.mkdir(parents=True)
    (staging / "result.json").write_text(
        json.dumps(
            {
                "candidate_commit": "abc123",
                "scenario": "full",
                "run_tag": "tag",
                "stages": [],
                "pass_num": 1,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), "abc123")

    assert out["passes"] == []
    assert out["all_passed"] is False


def test_reconcile_requires_committed_receipt(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    (pass_dir / "result.json").write_text(
        json.dumps(
            {
                "candidate_commit": "abc123",
                "scenario": "full",
                "run_tag": "tag",
                "stages": [],
                "pass_num": 1,
            }
        ),
        encoding="utf-8",
    )
    (pass_dir / "network.jsonl").write_text("", encoding="utf-8")
    (pass_dir / "console.jsonl").write_text("", encoding="utf-8")

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), "abc123")

    assert out["passes"] == []
    assert out["all_passed"] is False


def test_reconcile_accepts_only_verified_manifest_receipt(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    result = {
        "candidate_commit": "abc123",
        "scenario": "full",
        "run_tag": "tag",
        "stages": [],
        "pass_num": 1,
    }
    (pass_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
    (pass_dir / "network.jsonl").write_text("", encoding="utf-8")
    (pass_dir / "console.jsonl").write_text("", encoding="utf-8")
    files = []
    for name in ("result.json", "network.jsonl", "console.jsonl"):
        data = (pass_dir / name).read_bytes()
        files.append(
            {
                "path": name,
                "size": len(data),
                "sha256": dispatch.hashlib.sha256(data).hexdigest(),
            }
        )
    manifest = {
        "schema_version": 1,
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": "abc123",
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
    }
    (pass_dir / "evidence_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True),
        encoding="utf-8",
    )
    digest = dispatch.hashlib.sha256((pass_dir / "evidence_manifest.json").read_bytes()).hexdigest()
    (pass_dir / "evidence_manifest.sha256").write_text(
        f"{digest}  evidence_manifest.json\n",
        encoding="utf-8",
    )
    (pass_dir / "evidence_receipt.json").write_text(
        json.dumps(
            {
                "ok": True,
                "receipt_id": "receipt-1",
                "run_id": "run-1",
                "pass_id": "pass1",
                "pass_num": 1,
                "candidate_sha": "abc123",
                "manifest_sha256": digest,
                "canonical_path": str(pass_dir),
                "verified_at": "2026-08-21T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), "abc123")

    assert len(out["passes"]) == 1
    assert out["passes"][0]["evidence_receipt"]["receipt_id"] == "receipt-1"


def test_reconcile_preserves_receipt_verified_failed_execution_as_failed_pass(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    result = {
        "pass": False,
        "execution_passed": False,
        "candidate_commit": "abc123",
        "scenario": "full",
        "run_tag": "tag",
        "stages": [],
        "pass_num": 1,
    }
    (pass_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
    (pass_dir / "network.jsonl").write_text("", encoding="utf-8")
    (pass_dir / "console.jsonl").write_text("", encoding="utf-8")
    files = []
    for name in ("result.json", "network.jsonl", "console.jsonl"):
        data = (pass_dir / name).read_bytes()
        files.append(
            {
                "path": name,
                "size": len(data),
                "sha256": dispatch.hashlib.sha256(data).hexdigest(),
            }
        )
    manifest = {
        "schema_version": 1,
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": "abc123",
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
    }
    (pass_dir / "evidence_manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    digest = dispatch.hashlib.sha256((pass_dir / "evidence_manifest.json").read_bytes()).hexdigest()
    (pass_dir / "evidence_receipt.json").write_text(
        json.dumps(
            {
                "ok": True,
                "receipt_id": "receipt-1",
                "run_id": "run-1",
                "pass_num": 1,
                "candidate_sha": "abc123",
                "manifest_sha256": digest,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), "abc123")

    assert len(out["passes"]) == 1
    assert out["passes"][0]["execution_passed"] is False
    assert out["passes"][0]["passed"] is False
    assert out["all_passed"] is False


def test_reconcile_rejects_self_authored_manifest_missing_required_artifact(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    (pass_dir / "result.json").write_text(
        json.dumps(
            {
                "candidate_commit": "abc123",
                "scenario": "full",
                "run_tag": "tag",
                "stages": [],
                "pass_num": 1,
            }
        ),
        encoding="utf-8",
    )
    files = []
    data = (pass_dir / "result.json").read_bytes()
    files.append(
        {
            "path": "result.json",
            "size": len(data),
            "sha256": dispatch.hashlib.sha256(data).hexdigest(),
        }
    )
    manifest = {
        "schema_version": 1,
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": "abc123",
        "required_artifacts": ["result.json"],
        "files": files,
    }
    (pass_dir / "evidence_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True),
        encoding="utf-8",
    )
    digest = dispatch.hashlib.sha256((pass_dir / "evidence_manifest.json").read_bytes()).hexdigest()
    (pass_dir / "evidence_receipt.json").write_text(
        json.dumps(
            {
                "ok": True,
                "receipt_id": "receipt-1",
                "run_id": "run-1",
                "pass_num": 1,
                "candidate_sha": "abc123",
                "manifest_sha256": digest,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), "abc123")

    assert out["passes"] == []


def test_reconcile_rejects_unsafe_manifest_path(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    for name, payload in {
        "result.json": json.dumps(
            {
                "candidate_commit": "abc123",
                "scenario": "full",
                "run_tag": "tag",
                "stages": [],
                "pass_num": 1,
            }
        ),
        "network.jsonl": "",
        "console.jsonl": "",
    }.items():
        (pass_dir / name).write_text(payload, encoding="utf-8")
    files = []
    for name in ("result.json", "network.jsonl", "console.jsonl"):
        data = (pass_dir / name).read_bytes()
        files.append(
            {
                "path": name,
                "size": len(data),
                "sha256": dispatch.hashlib.sha256(data).hexdigest(),
            }
        )
    files.append({"path": "../outside", "size": 0, "sha256": dispatch.hashlib.sha256(b"").hexdigest()})
    manifest = {
        "schema_version": 1,
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": "abc123",
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
    }
    (pass_dir / "evidence_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True),
        encoding="utf-8",
    )
    digest = dispatch.hashlib.sha256((pass_dir / "evidence_manifest.json").read_bytes()).hexdigest()
    (pass_dir / "evidence_receipt.json").write_text(
        json.dumps(
            {
                "ok": True,
                "receipt_id": "receipt-1",
                "run_id": "run-1",
                "pass_num": 1,
                "candidate_sha": "abc123",
                "manifest_sha256": digest,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), "abc123")

    assert out["passes"] == []


def test_reconcile_rejects_required_artifact_missing_from_hash_inventory(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    for name, payload in {
        "result.json": json.dumps(
            {
                "candidate_commit": "abc123",
                "scenario": "full",
                "run_tag": "tag",
                "stages": [],
                "pass_num": 1,
            }
        ),
        "network.jsonl": "",
        "console.jsonl": "",
    }.items():
        (pass_dir / name).write_text(payload, encoding="utf-8")
    data = (pass_dir / "result.json").read_bytes()
    manifest = {
        "schema_version": 1,
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": "abc123",
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": [
            {
                "path": "result.json",
                "size": len(data),
                "sha256": dispatch.hashlib.sha256(data).hexdigest(),
            }
        ],
    }
    (pass_dir / "evidence_manifest.json").write_text(
        json.dumps(manifest, sort_keys=True),
        encoding="utf-8",
    )
    digest = dispatch.hashlib.sha256((pass_dir / "evidence_manifest.json").read_bytes()).hexdigest()
    (pass_dir / "evidence_receipt.json").write_text(
        json.dumps(
            {
                "ok": True,
                "receipt_id": "receipt-1",
                "run_id": "run-1",
                "pass_num": 1,
                "candidate_sha": "abc123",
                "manifest_sha256": digest,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), "abc123")

    assert out["passes"] == []


def test_manifest_rewrite_is_idempotent_after_sidecars(tmp_path):
    _mod, c = _collector(tmp_path)
    (c.pass_dir / "result.json").write_text("{}", encoding="utf-8")
    (c.pass_dir / "network.jsonl").write_text("", encoding="utf-8")
    (c.pass_dir / "console.jsonl").write_text("", encoding="utf-8")

    first = c._write_artifact_manifest()
    (c.pass_dir / "status.json").write_text('{"state":"passed"}', encoding="utf-8")
    (c.pass_dir / "evidence_receipt.json").write_text('{"ok":true}', encoding="utf-8")
    second = c._write_artifact_manifest()

    assert second["created_at"] == first["created_at"]
    assert second["manifest_sha256"] == first["manifest_sha256"]
    assert {item["path"] for item in second["files"]} == {
        "result.json",
        "network.jsonl",
        "console.jsonl",
    }


def test_remote_replay_requires_same_manifest_digest(tmp_path, monkeypatch):
    mod, c = _collector(tmp_path)
    captured: dict[str, str] = {}

    def fake_run(cmd, **_kwargs):
        captured["script"] = cmd[2]
        return SimpleNamespace(returncode=0, stdout='{"ok":false}', stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    c._verify_and_promote(
        "vps",
        staging="/tmp/staging",
        canonical="/tmp/canonical",
        manifest={},
    )

    script = captured["script"]
    assert "canonical_digest == staging_manifest_digest" in script
    assert "canonical destination already exists with divergent evidence" in script


def test_teardown_refuses_collector_stop_during_active_publication(monkeypatch):
    dispatch = _load_dispatch()
    stop_called = False

    def fail_if_stop(*_args, **_kwargs):
        nonlocal stop_called
        stop_called = True
        raise AssertionError("collector stop must not run while evidence ships")

    monkeypatch.setattr(
        dispatch,
        "_wait_for_evidence_transaction_clear",
        lambda *_a, **_kw: {
            "ok": False,
            "reason": "evidence publication still active",
            "terminal": {"state": "evidence_shipping"},
        },
    )
    monkeypatch.setattr(dispatch, "_stop_remote_collector_tree", fail_if_stop)
    monkeypatch.setattr(dispatch, "stop_runner", lambda *_a, **_kw: {"stopped": True})
    monkeypatch.setattr(dispatch, "_wait_for_runner_exit", lambda *_a, **_kw: None)
    monkeypatch.setattr(dispatch, "_remove_container_and_wait", lambda *_a, **_kw: None)
    monkeypatch.setattr(dispatch, "_sweep_run_homes", lambda *_a, **_kw: {"ok": True})
    monkeypatch.setattr(dispatch, "_shred_run_secret", lambda *_a, **_kw: True)
    monkeypatch.setattr(dispatch, "_restore_tailscale_serve", lambda *_a, **_kw: None)

    out = dispatch.teardown(dispatch.Runner(dry_run=False), sha="abc123", run_id="run-1")

    assert stop_called is False
    assert out["collector"]["stopped"] is False
    assert out["collector"]["reason"] == "evidence publication active; teardown refused"
    assert out["runner"] == {}
    assert out["serve_restored"] is False


def test_teardown_guard_unknown_status_fails_closed(monkeypatch):
    dispatch = _load_dispatch()
    observations = [
        {"state": "unknown", "read_ok": False},
        {"state": "unknown", "read_ok": True, "raw": "{"},
    ]
    monkeypatch.setattr(
        dispatch,
        "_read_collector_status",
        lambda *_a, **_kw: observations.pop(0) if observations else {"state": "unknown"},
    )
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)
    times = iter([0.0, 0.0, 2.0, 2.0])
    monkeypatch.setattr(dispatch.time, "time", lambda: next(times, 2.0))

    out = dispatch._wait_for_evidence_transaction_clear(
        dispatch.Runner(dry_run=False),
        run_id="run-1",
        timeout_s=1,
        poll_s=0,
    )

    assert out["ok"] is False
    assert out["reason"] == "collector status unavailable during teardown guard"
