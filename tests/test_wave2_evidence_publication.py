from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_WORKTREE = Path(__file__).resolve().parent.parent
FULL_SHA = "a" * 40


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
        candidate_commit=FULL_SHA,
        scenario="full",
        ship_to="/proof/raw",
    )
    c.stages.append({"stage": "w01_session", "ok": True, "ms": 1, "detail": ""})
    c.session_proof = {"ok": True}
    return mod, c


def _write_valid_staging_bundle(
    dispatch,
    root: Path,
    *,
    run_id: str = "run-1",
    pass_num: int = 1,
    candidate_sha: str = FULL_SHA,
    transaction_id: str = "tx-1",
) -> tuple[Path, str]:
    staging = root / "raw" / ".incoming" / "campaign" / run_id / f"pass{pass_num}" / transaction_id
    staging.mkdir(parents=True)
    for name, payload in {
        "result.json": json.dumps(
            {
                "execution_passed": True,
                "candidate_commit": candidate_sha,
                "scenario": "full",
                "run_tag": "tag",
                "stages": [],
                "pass_num": pass_num,
            }
        ),
        "network.jsonl": "",
        "console.jsonl": "",
    }.items():
        (staging / name).write_text(payload, encoding="utf-8")
    files = []
    for name in ("result.json", "network.jsonl", "console.jsonl"):
        data = (staging / name).read_bytes()
        files.append(
            {
                "path": name,
                "size": len(data),
                "sha256": dispatch.hashlib.sha256(data).hexdigest(),
            }
        )
    manifest = {
        "schema_version": 1,
        "campaign_id": "campaign",
        "run_id": run_id,
        "pass_id": f"pass{pass_num}",
        "pass_num": pass_num,
        "candidate_sha": candidate_sha,
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
        "inventory_sha256": dispatch.hashlib.sha256(
            json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    manifest_path = staging / "evidence_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest_digest = dispatch.hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    (staging / "evidence_manifest.sha256").write_text(
        f"{manifest_digest}  evidence_manifest.json\n",
        encoding="utf-8",
    )
    (staging / "upload_complete.json").write_text(
        json.dumps(
            {
                "transaction_id": transaction_id,
                "campaign_id": "campaign",
                "manifest_sha256": manifest_digest,
                "run_id": run_id,
                "pass_id": f"pass{pass_num}",
                "pass_num": pass_num,
                "candidate_sha": candidate_sha,
                "inventory_sha256": manifest["inventory_sha256"],
                "staging_path": str(staging),
                "canonical_path": str(root / "raw" / run_id / f"pass{pass_num}"),
            }
        ),
        encoding="utf-8",
    )
    return staging, manifest_digest


def _rewrite_staging_manifest(dispatch, staging: Path, mutate) -> str:
    manifest_path = staging / "evidence_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    digest = dispatch.hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    (staging / "evidence_manifest.sha256").write_text(
        f"{digest}  evidence_manifest.json\n",
        encoding="utf-8",
    )
    marker_path = staging / "upload_complete.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["manifest_sha256"] = digest
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    return digest


def _write_upload_marker(
    root: Path,
    pass_dir: Path,
    *,
    run_id: str = "run-1",
    pass_num: int = 1,
    candidate_sha: str = FULL_SHA,
    transaction_id: str = "tx-1",
    manifest_digest: str,
    inventory_digest: str,
) -> None:
    (pass_dir / "upload_complete.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "transaction_id": transaction_id,
                "campaign_id": "campaign",
                "run_id": run_id,
                "pass_id": f"pass{pass_num}",
                "pass_num": pass_num,
                "candidate_sha": candidate_sha,
                "manifest_sha256": manifest_digest,
                "inventory_sha256": inventory_digest,
                "staging_path": str(root / "raw" / ".incoming" / "campaign" / run_id / f"pass{pass_num}" / transaction_id),
                "canonical_path": str(root / "raw" / run_id / f"pass{pass_num}"),
            }
        ),
        encoding="utf-8",
    )


def test_execution_complete_is_not_terminal_before_evidence_receipt(tmp_path, monkeypatch):
    _mod, c = _collector(tmp_path)
    observed_states: list[str] = []

    def fake_publish(_execution_passed: bool):
        status = json.loads((c.pass_dir / "status.json").read_text(encoding="utf-8"))
        observed_states.append(status["state"])
        return {
            "ok": True,
            "state": "evidence_uploaded",
            "upload": {"transaction_id": "tx-1", "manifest_sha256": "m1"},
        }

    monkeypatch.setattr(c, "_publish_evidence", fake_publish)

    result = c._finalize(SimpleNamespace())

    assert result["execution_passed"] is True
    assert "pass" not in result
    saved = json.loads((c.pass_dir / "result.json").read_text(encoding="utf-8"))
    assert saved["execution_passed"] is True
    assert "pass" not in saved
    assert observed_states == ["evidence_shipping"]
    final_status = json.loads((c.pass_dir / "status.json").read_text(encoding="utf-8"))
    assert final_status["state"] == "evidence_uploaded"
    assert final_status["evidence_upload"]["transaction_id"] == "tx-1"


def test_publication_failure_is_distinct_from_execution_failure(tmp_path, monkeypatch):
    _mod, c = _collector(tmp_path)

    def fail_publish(_execution_passed: bool):
        return {"ok": False, "error": "manifest mismatch"}

    monkeypatch.setattr(c, "_publish_evidence", fail_publish)

    result = c._finalize(SimpleNamespace())

    assert result["collector_terminal_state"] == "evidence_preservation_failed"
    assert result["execution_passed"] is True
    assert "pass" not in result
    assert result["evidence_publication"]["ok"] is False
    status = json.loads((c.pass_dir / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == "evidence_preservation_failed"
    assert status["preservation_error"] == "manifest mismatch"
    saved = json.loads((c.pass_dir / "result.json").read_text(encoding="utf-8"))
    assert "pass" not in saved
    assert saved["evidence_publication"]["error"] == "manifest mismatch"


def test_collector_creates_transaction_staging_dir_before_flat_upload(tmp_path, monkeypatch):
    mod, c = _collector(tmp_path)
    (c.pass_dir / "result.json").write_text(
        json.dumps({"candidate_commit": FULL_SHA, "execution_passed": True}),
        encoding="utf-8",
    )
    (c.pass_dir / "network.jsonl").write_text("", encoding="utf-8")
    (c.pass_dir / "console.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("UMH_VPS_SSH", "vps.example")
    monkeypatch.setenv("UMH_WAVE2_CAMPAIGN_ID", "campaign")
    monkeypatch.setattr(mod, "uuid4", lambda: SimpleNamespace(hex="tx1deadbeef00"))
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):
        calls.append(list(argv))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    out = c._publish_evidence(execution_passed=True)

    assert out["ok"] is True
    staging = "/proof/raw/.incoming/campaign/run-1/pass1/tx1deadbeef0"
    assert calls[0] == ["ssh", "vps.example", f"mkdir -p {staging} /proof/raw/run-1"]
    first_scp = next(call for call in calls if call[0] == "scp")
    assert first_scp[2] == f"vps.example:{staging}/evidence_manifest.json"


def test_collector_uses_consistent_default_campaign_id(tmp_path, monkeypatch):
    mod, c = _collector(tmp_path)
    (c.pass_dir / "result.json").write_text(
        json.dumps({"candidate_commit": FULL_SHA, "execution_passed": True}),
        encoding="utf-8",
    )
    (c.pass_dir / "network.jsonl").write_text("", encoding="utf-8")
    (c.pass_dir / "console.jsonl").write_text("", encoding="utf-8")
    monkeypatch.delenv("UMH_WAVE2_CAMPAIGN_ID", raising=False)
    monkeypatch.setenv("UMH_VPS_SSH", "vps.example")
    monkeypatch.setattr(mod, "uuid4", lambda: SimpleNamespace(hex="tx1deadbeef00"))
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *_a, **_kw: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    out = c._publish_evidence(execution_passed=True)

    assert out["ok"] is True
    assert out["manifest"]["campaign_id"] == "uncampaigned"
    assert out["upload"]["campaign_id"] == "uncampaigned"
    assert "/.incoming/uncampaigned/run-1/pass1/tx1deadbeef0" in out["upload"]["staging_path"]


def test_collector_excludes_stale_control_tmp_sidecars_from_upload_manifest(tmp_path, monkeypatch):
    mod, c = _collector(tmp_path)
    (c.pass_dir / "result.json").write_text(
        json.dumps({"candidate_commit": FULL_SHA, "execution_passed": True}),
        encoding="utf-8",
    )
    (c.pass_dir / "network.jsonl").write_text("", encoding="utf-8")
    (c.pass_dir / "console.jsonl").write_text("", encoding="utf-8")
    for name in (
        "evidence_manifest.json.tmp",
        "evidence_manifest.sha256.tmp",
        "evidence_commit.json.tmp",
        "evidence_receipt.json.tmp",
        "upload_complete.json.tmp",
    ):
        (c.pass_dir / name).write_text("stale", encoding="utf-8")
    monkeypatch.setenv("UMH_VPS_SSH", "vps.example")
    monkeypatch.setenv("UMH_WAVE2_CAMPAIGN_ID", "campaign")
    monkeypatch.setattr(mod, "uuid4", lambda: SimpleNamespace(hex="tx1deadbeef00"))
    scp_sources: list[str] = []

    def fake_run(argv, **_kwargs):
        if argv[0] == "scp":
            scp_sources.append(Path(argv[1]).name)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    out = c._publish_evidence(execution_passed=True)

    assert out["ok"] is True
    uploaded_tmp = [name for name in scp_sources if name.endswith(".tmp")]
    assert uploaded_tmp == []
    manifest_paths = [item["path"] for item in out["manifest"]["files"]]
    assert not any(path.endswith(".tmp") for path in manifest_paths)


def test_poll_status_rejects_collector_terminal_receipt(monkeypatch):
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
    monkeypatch.setattr(
        dispatch,
        "_commit_uploaded_evidence_transaction",
        lambda *_args, **_kwargs: {"ok": False, "error": "not uploaded yet"},
    )

    out = dispatch._poll_status(runner, "run-1", 1, timeout_min=1)

    assert out["state"] == "evidence_preservation_failed"
    assert out["preservation_error"] == "collector terminal receipt is not destination-owned authority"


def test_poll_status_commits_destination_uploaded_evidence(monkeypatch):
    dispatch = _load_dispatch()
    runner = dispatch.Runner(dry_run=False)
    upload = {
        "transaction_id": "tx-1",
        "staging_path": "/proof/raw/.incoming/c/run-1/pass1/tx-1",
        "canonical_path": "/proof/raw/run-1/pass1",
        "manifest_sha256": "m1",
    }
    monkeypatch.setattr(
        dispatch,
        "_mesh_read",
        lambda *_a, **_kw: {
            "ok": True,
            "stdout": json.dumps(
                {
                    "state": "evidence_uploaded",
                    "execution_passed": True,
                    "evidence_upload": upload,
                }
            ),
        },
    )
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        dispatch,
        "_commit_uploaded_evidence_transaction",
        lambda got, sha, *, run_id, pass_num: {
            "ok": True,
            "receipt": {
                "receipt_id": "receipt-1",
                "run_id": run_id,
                "pass_id": "pass1",
                "pass_num": pass_num,
                "candidate_sha": sha,
                "manifest_sha256": got["manifest_sha256"],
                },
            },
        )
    monkeypatch.setattr(
        dispatch,
        "_terminal_from_committed_evidence",
        lambda receipt, sha: {"ok": True, "state": "passed", "execution_passed": True},
    )

    out = dispatch._poll_status(runner, "run-1", 1, timeout_min=1, candidate_sha=FULL_SHA)

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


def test_poll_status_timeout_rejects_stale_passed_without_destination_receipt(monkeypatch):
    dispatch = _load_dispatch()
    runner = dispatch.Runner(dry_run=False)
    monkeypatch.setattr(
        dispatch,
        "_mesh_read",
        lambda *_a, **_kw: {"ok": True, "stdout": json.dumps({"state": "passed"})},
    )
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)
    times = iter([0.0, 0.0, 2.0])
    monkeypatch.setattr(dispatch.time, "time", lambda: next(times))

    out = dispatch._poll_status(runner, "run-1", 1, timeout_min=0.01)

    assert out["state"] == "evidence_preservation_failed"
    assert out["preservation_error"] == (
        "collector terminal state timed out without destination-owned receipt"
    )


def test_reconcile_ignores_staging_directories(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging = root / "raw" / "run-1" / ".staging-pass1-attempt" / "pass1"
    staging.mkdir(parents=True)
    (staging / "result.json").write_text(
        json.dumps(
            {
                "candidate_commit": FULL_SHA,
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

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), FULL_SHA)

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
                "candidate_commit": FULL_SHA,
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

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), FULL_SHA)

    assert out["passes"] == []
    assert out["all_passed"] is False


def test_reconcile_rejects_forged_non_destination_receipt(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    for name, payload in {
        "result.json": json.dumps(
            {
                "candidate_commit": FULL_SHA,
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
    inventory_digest = dispatch.hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": 1,
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": FULL_SHA,
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
        "inventory_sha256": inventory_digest,
    }
    (pass_dir / "evidence_manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    digest = dispatch.hashlib.sha256((pass_dir / "evidence_manifest.json").read_bytes()).hexdigest()
    (pass_dir / "evidence_manifest.sha256").write_text(
        f"{digest}  evidence_manifest.json\n",
        encoding="utf-8",
    )
    _write_upload_marker(
        root,
        pass_dir,
        transaction_id="tx-forged",
        manifest_digest=digest,
        inventory_digest=inventory_digest,
    )
    receipt = dispatch._write_evidence_receipt(
        pass_dir,
        manifest=manifest,
        manifest_digest=digest,
        transaction_id="tx-forged",
    )
    receipt.pop("destination_owned")
    (pass_dir / "evidence_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), FULL_SHA)

    assert out["passes"] == []
    assert out["all_passed"] is False


def test_reconcile_accepts_only_verified_manifest_receipt(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    result = {
        "candidate_commit": FULL_SHA,
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
    inventory_digest = dispatch.hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": 1,
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": FULL_SHA,
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
        "inventory_sha256": inventory_digest,
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
    _write_upload_marker(
        root,
        pass_dir,
        manifest_digest=digest,
        inventory_digest=inventory_digest,
    )
    receipt = dispatch._write_evidence_receipt(
        pass_dir,
        manifest=manifest,
        manifest_digest=digest,
        transaction_id="tx-1",
    )
    _write_upload_marker(
        root,
        pass_dir,
        manifest_digest=digest,
        inventory_digest=inventory_digest,
    )

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), FULL_SHA)

    assert len(out["passes"]) == 1
    assert out["passes"][0]["evidence_receipt"]["receipt_id"] == receipt["receipt_id"]


def test_reconcile_accepts_full_candidate_commit_with_verified_receipt(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    sha = "a" * 40
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    (pass_dir / "result.json").write_text(
        json.dumps(
            {
                "candidate_commit": sha,
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
    files = []
    for name in ("result.json", "network.jsonl", "console.jsonl"):
        data = (pass_dir / name).read_bytes()
        files.append({"path": name, "size": len(data), "sha256": dispatch.hashlib.sha256(data).hexdigest()})
    inventory_digest = dispatch.hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": 1,
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": sha,
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
        "inventory_sha256": inventory_digest,
    }
    (pass_dir / "evidence_manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    digest = dispatch.hashlib.sha256((pass_dir / "evidence_manifest.json").read_bytes()).hexdigest()
    (pass_dir / "evidence_manifest.sha256").write_text(f"{digest}  evidence_manifest.json\n", encoding="utf-8")
    _write_upload_marker(root, pass_dir, candidate_sha=sha, manifest_digest=digest, inventory_digest=inventory_digest)
    dispatch._write_evidence_receipt(pass_dir, manifest=manifest, manifest_digest=digest, transaction_id="tx-1")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), sha)

    assert len(out["passes"]) == 1


def test_destination_commit_requires_exact_full_candidate_sha(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    full_sha = "a" * 40
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root, candidate_sha=full_sha[:12])
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        full_sha,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "binding mismatch candidate_sha"


def test_destination_commit_requires_full_40_hex_candidate_sha(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root, candidate_sha="abc123def456")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        "abc123def456",
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "dispatcher candidate sha must be full 40-hex"


def test_reconcile_rejects_prefix_candidate_commit_even_with_verified_receipt(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    full_sha = "a" * 40
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root, candidate_sha=full_sha)
    result_path = staging / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["candidate_commit"] = full_sha[:12]
    result_path.write_text(json.dumps(result), encoding="utf-8")

    def rehash_result(manifest: dict[str, object]) -> None:
        files = manifest["files"]
        assert isinstance(files, list)
        for item in files:
            if item["path"] == "result.json":
                data = result_path.read_bytes()
                item["size"] = len(data)
                item["sha256"] = dispatch.hashlib.sha256(data).hexdigest()
        manifest["inventory_sha256"] = dispatch.hashlib.sha256(
            json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    digest = _rewrite_staging_manifest(dispatch, staging, rehash_result)
    marker_path = staging / "upload_complete.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["manifest_sha256"] = digest
    marker["inventory_sha256"] = json.loads((staging / "evidence_manifest.json").read_text(encoding="utf-8"))[
        "inventory_sha256"
    ]
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    committed = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        full_sha,
        run_id="run-1",
        pass_num=1,
    )
    assert committed["ok"] is True
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), full_sha)

    assert out["passes"] == []
    assert out["all_passed"] is False


def test_reconcile_refuses_short_candidate_sha_even_if_bundle_matches(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    short_sha = "abc123def456"
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    (pass_dir / "result.json").write_text(
        json.dumps({"candidate_commit": short_sha, "scenario": "full", "run_tag": "tag", "stages": [], "pass_num": 1}),
        encoding="utf-8",
    )
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), short_sha)

    assert out["passes"] == []
    assert out["all_passed"] is False
    assert out["error"] == "candidate sha must be full 40-hex"


def test_verified_receipt_refuses_short_candidate_sha(tmp_path):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root, candidate_sha="abc123def456")
    canonical = root / "raw" / "run-1" / "pass1"
    canonical.parent.mkdir(parents=True)
    staging.rename(canonical)
    manifest = json.loads((canonical / "evidence_manifest.json").read_text(encoding="utf-8"))
    manifest["_computed_inventory_sha256"] = manifest["inventory_sha256"]
    dispatch._write_evidence_receipt(
        canonical,
        manifest=manifest,
        manifest_digest=digest,
        transaction_id="tx-1",
        canonical=canonical,
    )

    assert dispatch._verified_evidence_receipt(canonical, "abc123def456") is None


def test_poll_status_uses_canonical_result_not_beast_status_for_terminal_state(monkeypatch):
    dispatch = _load_dispatch()
    runner = dispatch.Runner(dry_run=False)
    upload = {
        "transaction_id": "tx-1",
        "staging_path": "/proof/raw/.incoming/c/run-1/pass1/tx-1",
        "canonical_path": "/proof/raw/run-1/pass1",
        "manifest_sha256": "m1",
    }
    monkeypatch.setattr(
        dispatch,
        "_mesh_read",
        lambda *_a, **_kw: {
            "ok": True,
            "stdout": json.dumps(
                {
                    "state": "evidence_uploaded",
                    "execution_passed": True,
                    "evidence_upload": upload,
                }
            ),
        },
    )
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        dispatch,
        "_commit_uploaded_evidence_transaction",
        lambda got, sha, *, run_id, pass_num: {
            "ok": True,
            "receipt": {"receipt_id": "receipt-1", "candidate_sha": sha},
        },
    )
    monkeypatch.setattr(
        dispatch,
        "_terminal_from_committed_evidence",
        lambda receipt, sha: {"ok": True, "state": "failed", "execution_passed": False},
    )

    out = dispatch._poll_status(runner, "run-1", 1, timeout_min=1, candidate_sha=FULL_SHA)

    assert out["state"] == "failed"
    assert out["execution_passed"] is False


def test_reconcile_requires_fresh_process_receipt_verification(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    (pass_dir / "result.json").write_text(
        json.dumps({"candidate_commit": FULL_SHA, "scenario": "full"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_verified_evidence_receipt", lambda *_a, **_kw: {"receipt_id": "in-process"})
    monkeypatch.setattr(dispatch, "_fresh_process_verified_evidence_receipt", lambda *_a, **_kw: None)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), FULL_SHA)

    assert out["passes"] == []
    assert out["all_passed"] is False


def test_reconcile_preserves_receipt_verified_failed_execution_as_failed_pass(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    result = {
        "execution_passed": False,
        "candidate_commit": FULL_SHA,
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
    inventory_digest = dispatch.hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": 1,
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": FULL_SHA,
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
        "inventory_sha256": inventory_digest,
    }
    (pass_dir / "evidence_manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    digest = dispatch.hashlib.sha256((pass_dir / "evidence_manifest.json").read_bytes()).hexdigest()
    (pass_dir / "evidence_manifest.sha256").write_text(f"{digest}  evidence_manifest.json\n", encoding="utf-8")
    dispatch._write_evidence_receipt(
        pass_dir,
        manifest=manifest,
        manifest_digest=digest,
        transaction_id="tx-1",
    )
    _write_upload_marker(
        root,
        pass_dir,
        manifest_digest=digest,
        inventory_digest=inventory_digest,
    )

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), FULL_SHA)

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
                "candidate_commit": FULL_SHA,
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
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": FULL_SHA,
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
                "candidate_sha": FULL_SHA,
                "manifest_sha256": digest,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), FULL_SHA)

    assert out["passes"] == []


def test_reconcile_rejects_unsafe_manifest_path(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    for name, payload in {
        "result.json": json.dumps(
            {
                "candidate_commit": FULL_SHA,
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
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": FULL_SHA,
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
                "candidate_sha": FULL_SHA,
                "manifest_sha256": digest,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), FULL_SHA)

    assert out["passes"] == []


def test_reconcile_rejects_required_artifact_missing_from_hash_inventory(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    pass_dir = root / "raw" / "run-1" / "pass1"
    pass_dir.mkdir(parents=True)
    for name, payload in {
        "result.json": json.dumps(
            {
                "candidate_commit": FULL_SHA,
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
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": FULL_SHA,
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
                "candidate_sha": FULL_SHA,
                "manifest_sha256": digest,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_read_state_records", lambda _sha: [])
    monkeypatch.setattr(dispatch, "_candidate_logs", lambda _runner: "")

    out = dispatch.reconcile(dispatch.Runner(dry_run=False), FULL_SHA)

    assert out["passes"] == []


def test_destination_commit_promotes_staging_and_writes_verified_receipt(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging = root / "raw" / ".incoming" / "campaign" / "run-1" / "pass1" / "tx-1"
    staging.mkdir(parents=True)
    for name, payload in {
        "result.json": json.dumps(
            {
                "execution_passed": True,
                "candidate_commit": FULL_SHA,
                "scenario": "full",
                "run_tag": "tag",
                "stages": [],
                "pass_num": 1,
            }
        ),
        "network.jsonl": "",
        "console.jsonl": "",
    }.items():
        (staging / name).write_text(payload, encoding="utf-8")
    files = []
    for name in ("result.json", "network.jsonl", "console.jsonl"):
        data = (staging / name).read_bytes()
        files.append({"path": name, "size": len(data), "sha256": dispatch.hashlib.sha256(data).hexdigest()})
    inventory_digest = dispatch.hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": 1,
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": FULL_SHA,
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
        "inventory_sha256": inventory_digest,
    }
    (staging / "evidence_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest_digest = dispatch.hashlib.sha256((staging / "evidence_manifest.json").read_bytes()).hexdigest()
    (staging / "evidence_manifest.sha256").write_text(
        f"{manifest_digest}  evidence_manifest.json\n",
        encoding="utf-8",
    )
    (staging / "upload_complete.json").write_text(
        json.dumps(
                {
                    "transaction_id": "tx-1",
                    "campaign_id": "campaign",
                    "manifest_sha256": manifest_digest,
                "run_id": "run-1",
                "pass_id": "pass1",
                "pass_num": 1,
                "candidate_sha": FULL_SHA,
                "inventory_sha256": inventory_digest,
                "staging_path": str(staging),
                "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fresh_process_verified_evidence_receipt",
        lambda pass_dir, sha: dispatch._verified_evidence_receipt(pass_dir, sha),
    )

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": manifest_digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is True
    canonical = root / "raw" / "run-1" / "pass1"
    assert canonical.is_dir()
    assert not staging.exists()
    assert out["receipt"]["transaction_id"] == "tx-1"
    assert out["receipt"]["inventory_sha256"] == inventory_digest
    assert dispatch._verified_evidence_receipt(canonical, FULL_SHA) is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("canonical_path", "/tmp/other-canonical"),
        ("campaign_id", "other-campaign"),
        ("pass_id", "pass9"),
        ("artifact_count", 999),
    ],
)
def test_verified_receipt_rejects_tampered_receipt_bindings(tmp_path, monkeypatch, field, value):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fresh_process_verified_evidence_receipt",
        lambda pass_dir, sha: dispatch._verified_evidence_receipt(pass_dir, sha),
    )
    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )
    assert out["ok"] is True
    canonical = root / "raw" / "run-1" / "pass1"
    receipt_path = canonical / "evidence_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt[field] = value
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")

    assert dispatch._verified_evidence_receipt(canonical, FULL_SHA) is None


def test_destination_commit_requires_fresh_process_receipt_recheck(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging = root / "raw" / ".incoming" / "campaign" / "run-1" / "pass1" / "tx-1"
    staging.mkdir(parents=True)
    for name in ("result.json", "network.jsonl", "console.jsonl"):
        (staging / name).write_text("", encoding="utf-8")
    files = [
        {
            "path": name,
            "size": 0,
            "sha256": dispatch.hashlib.sha256(b"").hexdigest(),
        }
        for name in ("result.json", "network.jsonl", "console.jsonl")
    ]
    manifest = {
        "schema_version": 1,
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": FULL_SHA,
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
        "inventory_sha256": dispatch.hashlib.sha256(
            json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    (staging / "evidence_manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    digest = dispatch.hashlib.sha256((staging / "evidence_manifest.json").read_bytes()).hexdigest()
    (staging / "evidence_manifest.sha256").write_text(
        f"{digest}  evidence_manifest.json\n",
        encoding="utf-8",
    )
    (staging / "upload_complete.json").write_text(
        json.dumps(
                {
                    "transaction_id": "tx-1",
                    "campaign_id": "campaign",
                    "manifest_sha256": digest,
                "run_id": "run-1",
                "pass_id": "pass1",
                "pass_num": 1,
                "candidate_sha": FULL_SHA,
                "inventory_sha256": manifest["inventory_sha256"],
                "staging_path": str(staging),
                "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(dispatch, "_fresh_process_verified_evidence_receipt", lambda *_a, **_kw: None)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert "fresh-process" in out["error"]


def test_destination_commit_does_not_write_receipt_before_atomic_promotion(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    canonical = root / "raw" / "run-1" / "pass1"
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fresh_process_verified_evidence_receipt",
        lambda pass_dir, sha: dispatch._verified_evidence_receipt(pass_dir, sha),
    )
    real_replace = dispatch.os.replace
    observed: list[bool] = []

    def guarded_replace(src, dst):
        if Path(src) == staging and Path(dst) == canonical:
            observed.append((staging / "evidence_commit.json").is_file() or (staging / "evidence_receipt.json").is_file())
        return real_replace(src, dst)

    monkeypatch.setattr(dispatch.os, "replace", guarded_replace)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(canonical),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is True
    assert observed == [False]
    assert (canonical / "evidence_commit.json").is_file()
    assert (canonical / "evidence_receipt.json").is_file()


def test_destination_commit_retry_after_pre_promotion_crash_is_idempotent(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    canonical = root / "raw" / "run-1" / "pass1"
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fresh_process_verified_evidence_receipt",
        lambda pass_dir, sha: dispatch._verified_evidence_receipt(pass_dir, sha),
    )
    real_replace = dispatch.os.replace

    def crash_before_promotion(src, dst):
        if Path(src) == staging and Path(dst) == canonical:
            raise OSError("simulated crash before promotion")
        return real_replace(src, dst)

    monkeypatch.setattr(dispatch.os, "replace", crash_before_promotion)
    first = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(canonical),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )
    assert first["ok"] is False
    assert "evidence durability failure" in first["error"]
    assert staging.exists()
    assert not (staging / "evidence_commit.json").exists()
    assert not (staging / "evidence_receipt.json").exists()

    monkeypatch.setattr(dispatch.os, "replace", real_replace)
    replay = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(canonical),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert replay["ok"] is True
    assert dispatch._verified_evidence_receipt(canonical, FULL_SHA) is not None


def test_destination_commit_recovers_after_promotion_before_receipt(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    canonical = root / "raw" / "run-1" / "pass1"
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fresh_process_verified_evidence_receipt",
        lambda pass_dir, sha: dispatch._verified_evidence_receipt(pass_dir, sha),
    )
    real_write_receipt = dispatch._write_evidence_receipt

    def crash_after_promotion(*_args, **_kwargs):
        raise OSError("simulated crash after promotion before receipt")

    monkeypatch.setattr(dispatch, "_write_evidence_receipt", crash_after_promotion)
    first = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(canonical),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )
    assert first["ok"] is False
    assert "evidence durability failure" in first["error"]
    assert canonical.exists()
    assert not staging.exists()
    assert not (canonical / "evidence_receipt.json").exists()

    monkeypatch.setattr(dispatch, "_write_evidence_receipt", real_write_receipt)
    replay = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(canonical),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert replay["ok"] is True
    assert replay["recovered_after_promotion"] is True
    assert replay["receipt"]["recovered_after_promotion"] is True
    assert dispatch._verified_evidence_receipt(canonical, FULL_SHA) is not None


def test_destination_commit_recovers_after_commit_marker_before_receipt(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    canonical = root / "raw" / "run-1" / "pass1"
    canonical.parent.mkdir(parents=True)
    staging.rename(canonical)
    manifest = json.loads((canonical / "evidence_manifest.json").read_text(encoding="utf-8"))
    manifest["_computed_inventory_sha256"] = manifest["inventory_sha256"]
    dispatch._write_evidence_receipt(
        canonical,
        manifest=manifest,
        manifest_digest=digest,
        transaction_id="tx-1",
        canonical=canonical,
    )
    (canonical / "evidence_receipt.json").unlink()
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fresh_process_verified_evidence_receipt",
        lambda pass_dir, sha: dispatch._verified_evidence_receipt(pass_dir, sha),
    )

    replay = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(canonical),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert replay["ok"] is True
    assert replay["recovered_after_promotion"] is True
    assert dispatch._verified_evidence_receipt(canonical, FULL_SHA) is not None


def test_destination_commit_recovers_canonical_tmp_sidecars_after_receipt_crash(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    canonical = root / "raw" / "run-1" / "pass1"
    canonical.parent.mkdir(parents=True)
    staging.rename(canonical)
    (canonical / "evidence_commit.json.tmp").write_text('{"partial":true}', encoding="utf-8")
    (canonical / "evidence_receipt.json.tmp").write_text('{"partial":true}', encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fresh_process_verified_evidence_receipt",
        lambda pass_dir, sha: dispatch._verified_evidence_receipt(pass_dir, sha),
    )

    replay = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(canonical),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert replay["ok"] is True
    assert replay["recovered_after_promotion"] is True
    assert not (canonical / "evidence_commit.json.tmp").exists()
    assert not (canonical / "evidence_receipt.json.tmp").exists()
    assert dispatch._verified_evidence_receipt(canonical, FULL_SHA) is not None


def test_destination_commit_fails_closed_when_directory_fsync_fails(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fsync_dir",
        lambda _path: (_ for _ in ()).throw(OSError("fsync denied")),
    )

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert "evidence durability failure" in out["error"]


def test_destination_commit_rejects_staged_dispatcher_owned_artifact(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    (staging / "evidence_receipt.json").write_text('{"ok":true}', encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"].startswith("destination commit artifact not allowed")


def test_destination_commit_rejects_wrong_incoming_staging_shape(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    wrong = root / "raw" / "wrong-parent" / ".incoming" / "campaign" / "run-1" / "pass1" / "tx-1"
    wrong.parent.mkdir(parents=True)
    staging.rename(wrong)
    marker_path = wrong / "upload_complete.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["staging_path"] = str(wrong)
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(wrong),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "staging path does not match evidence transaction identity"


def test_destination_commit_rejects_upload_marker_staging_path_mismatch(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    marker_path = staging / "upload_complete.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["staging_path"] = str(root / "raw" / ".incoming" / "campaign" / "other" / "pass1" / "tx-1")
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "upload_complete staging path mismatch"


def test_destination_commit_rejects_upload_marker_pass_id_mismatch_before_promotion(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    marker_path = staging / "upload_complete.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["pass_id"] = "pass9"
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "upload_complete pass_id mismatch"
    assert staging.is_dir()
    assert not (root / "raw" / "run-1" / "pass1").exists()


def test_destination_commit_rejects_lexical_alias_staging_path(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    alias = staging.parent / "alias" / ".." / "tx-1"
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(alias),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "bad transaction paths"
    assert staging.is_dir()
    assert not (root / "raw" / "run-1" / "pass1").exists()


def test_destination_commit_rejects_campaign_mismatch_before_promotion(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    manifest_path = staging / "evidence_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["campaign_id"] = "other-campaign"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    digest = dispatch.hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    (staging / "evidence_manifest.sha256").write_text(
        f"{digest}  evidence_manifest.json\n",
        encoding="utf-8",
    )
    marker_path = staging / "upload_complete.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["manifest_sha256"] = digest
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "upload_complete campaign mismatch"
    assert staging.is_dir()
    assert not (root / "raw" / "run-1" / "pass1").exists()


def test_destination_commit_rejects_staging_campaign_segment_mismatch_before_promotion(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    wrong = root / "raw" / ".incoming" / "other-campaign" / "run-1" / "pass1" / "tx-1"
    wrong.parent.mkdir(parents=True)
    staging.rename(wrong)
    marker_path = wrong / "upload_complete.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["staging_path"] = str(wrong)
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(wrong),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "staging campaign mismatch"
    assert wrong.is_dir()
    assert not (root / "raw" / "run-1" / "pass1").exists()


def test_destination_commit_rejects_nested_dispatcher_owned_artifact(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    nested = staging / "nested"
    nested.mkdir()
    (nested / "evidence_receipt.json").write_text('{"ok":true}', encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "destination commit artifact not allowed in uploaded bundle: nested/evidence_receipt.json"


def test_destination_commit_rejects_unmanifested_extra_file(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    (staging / "extra.log").write_text("not in manifest", encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "unmanifested evidence file extra.log"


def test_destination_commit_rejects_manifest_symlink_escape(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    outside = tmp_path / "outside-result.json"
    original_result = (staging / "result.json").read_bytes()
    outside.write_bytes(original_result)
    (staging / "result.json").unlink()
    (staging / "result.json").symlink_to(outside)
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "symlink evidence path result.json"


def test_destination_commit_rejects_symlinked_staging_transaction_directory(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    outside = tmp_path / "outside-staging"
    staging.rename(outside)
    staging.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "staging path contains symlink"
    assert staging.is_symlink()
    assert outside.is_dir()
    assert not (root / "raw" / "run-1" / "pass1").exists()


def test_verified_receipt_rejects_symlinked_canonical_pass_directory(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fresh_process_verified_evidence_receipt",
        lambda pass_dir, sha: dispatch._verified_evidence_receipt(pass_dir, sha),
    )
    committed = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )
    assert committed["ok"] is True
    canonical = root / "raw" / "run-1" / "pass1"
    outside = tmp_path / "outside-canonical"
    canonical.rename(outside)
    canonical.symlink_to(outside, target_is_directory=True)

    assert dispatch._verified_evidence_receipt(canonical, FULL_SHA) is None


def test_destination_commit_recovers_existing_canonical_without_receipt(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    canonical = root / "raw" / "run-1" / "pass1"
    canonical.mkdir(parents=True)
    for item in staging.iterdir():
        if item.is_file():
            (canonical / item.name).write_bytes(item.read_bytes())
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(canonical),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is True
    assert out["recovered_after_promotion"] is True
    assert dispatch._verified_evidence_receipt(canonical, FULL_SHA) is not None


def test_destination_commit_replay_requires_fresh_process_receipt(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    canonical = root / "raw" / "run-1" / "pass1"
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fresh_process_verified_evidence_receipt",
        lambda pass_dir, sha: dispatch._verified_evidence_receipt(pass_dir, sha),
    )
    first = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(canonical),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )
    assert first["ok"] is True
    replay_staging, replay_digest = _write_valid_staging_bundle(
        dispatch,
        root,
        transaction_id="tx-2",
    )
    monkeypatch.setattr(dispatch, "_fresh_process_verified_evidence_receipt", lambda *_a, **_kw: None)

    replay = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-2",
            "staging_path": str(replay_staging),
            "canonical_path": str(canonical),
            "manifest_sha256": replay_digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert replay["ok"] is False
    assert replay["error"] == "canonical destination exists with divergent receipt"


def test_destination_commit_replay_accepts_committed_canonical_without_staging(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    canonical = root / "raw" / "run-1" / "pass1"
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fresh_process_verified_evidence_receipt",
        lambda pass_dir, sha: dispatch._verified_evidence_receipt(pass_dir, sha),
    )
    upload = {
        "transaction_id": "tx-1",
        "staging_path": str(staging),
        "canonical_path": str(canonical),
        "manifest_sha256": digest,
    }
    first = dispatch._commit_uploaded_evidence_transaction(upload, FULL_SHA, run_id="run-1", pass_num=1)
    assert first["ok"] is True
    assert not staging.exists()

    replay = dispatch._commit_uploaded_evidence_transaction(upload, FULL_SHA, run_id="run-1", pass_num=1)

    assert replay["ok"] is True
    assert replay["idempotent_replay"] is True
    assert replay["receipt"]["transaction_id"] == "tx-1"


def test_destination_commit_rejects_missing_upload_complete(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    (staging / "upload_complete.json").unlink()
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "missing upload_complete marker"


def test_destination_commit_rejects_non_object_upload_complete(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    (staging / "upload_complete.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "upload_complete marker is not an object"


def test_destination_commit_rejects_upload_complete_inventory_mismatch(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    marker_path = staging / "upload_complete.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["inventory_sha256"] = "0" * 64
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "upload_complete inventory digest mismatch"


def test_destination_commit_rejects_upload_complete_missing_hash_bindings(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    marker_path = staging / "upload_complete.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker.pop("manifest_sha256")
    marker.pop("inventory_sha256")
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "upload_complete manifest digest mismatch"


def test_destination_commit_rejects_cross_run_binding(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging = root / "raw" / ".incoming" / "campaign" / "run-1" / "pass1" / "tx-1"
    staging.mkdir(parents=True)
    for name in ("result.json", "network.jsonl", "console.jsonl"):
        (staging / name).write_text("", encoding="utf-8")
    files = [
        {
            "path": name,
            "size": (staging / name).stat().st_size,
            "sha256": dispatch.hashlib.sha256((staging / name).read_bytes()).hexdigest(),
        }
        for name in ("result.json", "network.jsonl", "console.jsonl")
    ]
    manifest = {
        "schema_version": 1,
        "campaign_id": "campaign",
        "run_id": "other-run",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": FULL_SHA,
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
        "inventory_sha256": dispatch.hashlib.sha256(
            json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    (staging / "evidence_manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    digest = dispatch.hashlib.sha256((staging / "evidence_manifest.json").read_bytes()).hexdigest()
    (staging / "upload_complete.json").write_text(json.dumps({"transaction_id": "tx-1", "run_id": "run-1", "pass_num": 1, "candidate_sha": FULL_SHA}), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert "binding mismatch" in out["error"]


def test_destination_commit_rejects_wrong_candidate_binding(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging = root / "raw" / ".incoming" / "campaign" / "run-1" / "pass1" / "tx-1"
    staging.mkdir(parents=True)
    for name in ("result.json", "network.jsonl", "console.jsonl"):
        (staging / name).write_text("", encoding="utf-8")
    files = [
        {
            "path": name,
            "size": 0,
            "sha256": dispatch.hashlib.sha256(b"").hexdigest(),
        }
        for name in ("result.json", "network.jsonl", "console.jsonl")
    ]
    manifest = {
        "schema_version": 1,
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": "wrong-sha",
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
        "inventory_sha256": dispatch.hashlib.sha256(
            json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    (staging / "evidence_manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    digest = dispatch.hashlib.sha256((staging / "evidence_manifest.json").read_bytes()).hexdigest()
    (staging / "upload_complete.json").write_text(json.dumps({"transaction_id": "tx-1", "run_id": "run-1", "pass_num": 1, "candidate_sha": FULL_SHA}), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert "candidate_sha" in out["error"]


def test_destination_commit_rejects_unhashable_manifest_candidate(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    digest = _rewrite_staging_manifest(
        dispatch,
        staging,
        lambda manifest: manifest.__setitem__("candidate_sha", [FULL_SHA]),
    )
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "binding mismatch candidate_sha"


def test_destination_commit_requires_manifest_sidecar(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    (staging / "evidence_manifest.sha256").unlink()
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "missing evidence_manifest.sha256"


def test_destination_commit_rejects_unhashable_marker_candidate(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    marker_path = staging / "upload_complete.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["candidate_sha"] = [FULL_SHA]
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "upload_complete candidate mismatch"


def test_destination_commit_rejects_nonlist_required_artifacts(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    digest = _rewrite_staging_manifest(
        dispatch,
        staging,
        lambda manifest: manifest.__setitem__("required_artifacts", 123),
    )
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "required artifact contract mismatch"


def test_destination_commit_rejects_bad_manifest_size_without_raising(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging = root / "raw" / ".incoming" / "campaign" / "run-1" / "pass1" / "tx-1"
    staging.mkdir(parents=True)
    for name in ("result.json", "network.jsonl", "console.jsonl"):
        (staging / name).write_text("", encoding="utf-8")
    files = [
        {"path": "result.json", "size": "not-an-int", "sha256": dispatch.hashlib.sha256(b"").hexdigest()},
        {"path": "network.jsonl", "size": 0, "sha256": dispatch.hashlib.sha256(b"").hexdigest()},
        {"path": "console.jsonl", "size": 0, "sha256": dispatch.hashlib.sha256(b"").hexdigest()},
    ]
    manifest = {
        "schema_version": 1,
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": FULL_SHA,
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
    }
    (staging / "evidence_manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    digest = dispatch.hashlib.sha256((staging / "evidence_manifest.json").read_bytes()).hexdigest()
    (staging / "upload_complete.json").write_text(
        json.dumps(
            {
                "transaction_id": "tx-1",
                "run_id": "run-1",
                "pass_num": 1,
                "candidate_sha": FULL_SHA,
                "manifest_sha256": digest,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert out["error"] == "bad size result.json"


def test_destination_commit_rejects_file_hash_mismatch(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging = root / "raw" / ".incoming" / "campaign" / "run-1" / "pass1" / "tx-1"
    staging.mkdir(parents=True)
    for name in ("result.json", "network.jsonl", "console.jsonl"):
        (staging / name).write_text("original", encoding="utf-8")
    files = [
        {
            "path": name,
            "size": len("original"),
            "sha256": dispatch.hashlib.sha256(b"original").hexdigest(),
        }
        for name in ("result.json", "network.jsonl", "console.jsonl")
    ]
    manifest = {
        "schema_version": 1,
        "campaign_id": "campaign",
        "run_id": "run-1",
        "pass_id": "pass1",
        "pass_num": 1,
        "candidate_sha": FULL_SHA,
        "required_artifacts": ["result.json", "network.jsonl", "console.jsonl"],
        "files": files,
        "inventory_sha256": dispatch.hashlib.sha256(
            json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }
    (staging / "evidence_manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    digest = dispatch.hashlib.sha256((staging / "evidence_manifest.json").read_bytes()).hexdigest()
    (staging / "result.json").write_text("tampered", encoding="utf-8")
    (staging / "upload_complete.json").write_text(
        json.dumps(
            {
                "transaction_id": "tx-1",
                "manifest_sha256": digest,
                "inventory_sha256": manifest["inventory_sha256"],
                "run_id": "run-1",
                "pass_id": "pass1",
                "pass_num": 1,
                "candidate_sha": FULL_SHA,
                "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)

    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(root / "raw" / "run-1" / "pass1"),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )

    assert out["ok"] is False
    assert "digest mismatch" in out["error"]


def test_verified_receipt_rejects_transaction_mismatch_with_marker(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    root = tmp_path / "proof"
    staging, digest = _write_valid_staging_bundle(dispatch, root)
    canonical = root / "raw" / "run-1" / "pass1"
    monkeypatch.setattr(dispatch, "_proof_root", lambda: root)
    monkeypatch.setattr(
        dispatch,
        "_fresh_process_verified_evidence_receipt",
        lambda pass_dir, sha: dispatch._verified_evidence_receipt(pass_dir, sha),
    )
    out = dispatch._commit_uploaded_evidence_transaction(
        {
            "transaction_id": "tx-1",
            "staging_path": str(staging),
            "canonical_path": str(canonical),
            "manifest_sha256": digest,
        },
        FULL_SHA,
        run_id="run-1",
        pass_num=1,
    )
    assert out["ok"] is True
    receipt = json.loads((canonical / "evidence_receipt.json").read_text(encoding="utf-8"))
    receipt["transaction_id"] = "other-tx"
    (canonical / "evidence_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")

    assert dispatch._verified_evidence_receipt(canonical, FULL_SHA) is None


def test_fsync_dir_propagates_durability_failure(tmp_path, monkeypatch):
    dispatch = _load_dispatch()
    monkeypatch.setattr(dispatch.os, "fsync", lambda _fd: (_ for _ in ()).throw(OSError("fsync denied")))

    with pytest.raises(OSError, match="fsync denied"):
        dispatch._fsync_dir(tmp_path)


def test_manifest_rewrite_is_idempotent_after_sidecars(tmp_path):
    _mod, c = _collector(tmp_path)
    (c.pass_dir / "result.json").write_text("{}", encoding="utf-8")
    (c.pass_dir / "network.jsonl").write_text("", encoding="utf-8")
    (c.pass_dir / "console.jsonl").write_text("", encoding="utf-8")

    first = c._write_artifact_manifest()
    (c.pass_dir / "status.json").write_text('{"state":"passed"}', encoding="utf-8")
    (c.pass_dir / "evidence_receipt.json").write_text('{"ok":true}', encoding="utf-8")
    (c.pass_dir / "upload_complete.json").write_text('{"transaction_id":"stale"}', encoding="utf-8")
    second = c._write_artifact_manifest()

    assert second["created_at"] == first["created_at"]
    assert second["manifest_sha256"] == first["manifest_sha256"]
    assert {item["path"] for item in second["files"]} == {
        "result.json",
        "network.jsonl",
        "console.jsonl",
    }


def test_collector_upload_does_not_invoke_remote_verification(tmp_path, monkeypatch):
    mod, c = _collector(tmp_path)
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setenv("UMH_VPS_SSH", "vps")
    (c.pass_dir / "result.json").write_text("{}", encoding="utf-8")
    (c.pass_dir / "network.jsonl").write_text("", encoding="utf-8")
    (c.pass_dir / "console.jsonl").write_text("", encoding="utf-8")
    (c.pass_dir / "status.json").write_text('{"state":"passed"}', encoding="utf-8")
    (c.pass_dir / "evidence_receipt.json").write_text('{"ok":true}', encoding="utf-8")
    (c.pass_dir / "evidence_commit.json").write_text('{"ok":true}', encoding="utf-8")

    out = c._publish_evidence(True)

    assert out["ok"] is True
    assert out["state"] == "evidence_uploaded"
    assert not any("python3 - <<'PY'" in " ".join(cmd) for cmd in calls)
    assert any(cmd[0] == "scp" for cmd in calls)
    scp_sources = [Path(cmd[1]).name for cmd in calls if cmd[0] == "scp"]
    assert set(scp_sources) == {
        "result.json",
        "network.jsonl",
        "console.jsonl",
        "evidence_manifest.json",
        "evidence_manifest.sha256",
        "upload_complete.json",
    }
    assert "status.json" not in scp_sources
    assert "evidence_receipt.json" not in scp_sources
    assert "evidence_commit.json" not in scp_sources


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

    out = dispatch.teardown(dispatch.Runner(dry_run=False), sha=FULL_SHA, run_id="run-1")

    assert stop_called is False
    assert out["collector"]["stopped"] is False
    assert out["collector"]["reason"] == "evidence publication active; teardown refused"
    assert out["runner"] == {}
    assert out["serve_restored"] is False


def test_evidence_transaction_guard_treats_shipping_as_active(monkeypatch):
    dispatch = _load_dispatch()
    monkeypatch.setattr(
        dispatch,
        "_read_collector_status",
        lambda *_a, **_kw: {"state": "evidence_shipping", "read_ok": True},
    )
    monkeypatch.setattr(dispatch.time, "sleep", lambda _seconds: None)
    times = iter([0.0, 0.0, 2.0])
    monkeypatch.setattr(dispatch.time, "time", lambda: next(times))

    out = dispatch._wait_for_evidence_transaction_clear(
        dispatch.Runner(dry_run=False),
        run_id="run-1",
        timeout_s=1,
    )

    assert out["ok"] is False
    assert out["reason"] == "evidence publication still active"


def test_evidence_transaction_guard_commits_uploaded_before_teardown(monkeypatch):
    dispatch = _load_dispatch()
    status = {
        "state": "evidence_uploaded",
        "execution_passed": True,
        "evidence_upload": {"transaction_id": "tx-1"},
    }
    committed_calls: list[tuple[dict, str, str, int]] = []
    monkeypatch.setattr(dispatch, "_read_collector_status", lambda *_a, **_kw: status)
    monkeypatch.setattr(
        dispatch,
        "_commit_uploaded_evidence_transaction",
        lambda upload, sha, *, run_id, pass_num: committed_calls.append((upload, sha, run_id, pass_num))
        or {"ok": True, "receipt": {"receipt_id": "receipt-1"}},
    )
    monkeypatch.setattr(
        dispatch,
        "_terminal_from_committed_evidence",
        lambda receipt, sha: {"ok": True, "state": "passed", "execution_passed": True},
    )

    out = dispatch._wait_for_evidence_transaction_clear(
        dispatch.Runner(dry_run=False),
        run_id="run-1",
        pass_num=1,
        candidate_sha=FULL_SHA,
        timeout_s=1,
    )

    assert out["ok"] is True
    assert out["terminal"]["state"] == "passed"
    assert out["terminal"]["evidence_receipt"]["receipt_id"] == "receipt-1"
    assert committed_calls == [(status["evidence_upload"], FULL_SHA, "run-1", 1)]


def test_evidence_transaction_guard_rejects_terminal_without_receipt(monkeypatch):
    dispatch = _load_dispatch()
    monkeypatch.setattr(
        dispatch,
        "_read_collector_status",
        lambda *_a, **_kw: {"state": "passed", "read_ok": True},
    )

    out = dispatch._wait_for_evidence_transaction_clear(
        dispatch.Runner(dry_run=False),
        run_id="run-1",
        pass_num=1,
        candidate_sha=FULL_SHA,
        timeout_s=1,
    )

    assert out["ok"] is False
    assert out["reason"] == "collector terminal state is not destination-owned authority"


def test_beast_collector_commit_requires_exact_full_sha(monkeypatch):
    dispatch = _load_dispatch()
    runner = dispatch.Runner(dry_run=False)
    full_sha = FULL_SHA
    other = full_sha[:12] + ("b" * 28)
    commands: list[str] = []

    def fake_mesh_read(_runner, command, **_kwargs):
        commands.append(command)
        return {"ok": True, "stdout": other}

    monkeypatch.setattr(dispatch, "_mesh_read", fake_mesh_read)

    out = dispatch._verify_beast_collector_commit(runner, full_sha)

    assert out["ok"] is False
    assert commands == [rf"git -C {dispatch._BEAST_WT} rev-parse HEAD"]
    assert out["beast_worktree_head"] == other


def test_beast_collector_commit_rejects_short_candidate_sha(monkeypatch):
    dispatch = _load_dispatch()
    runner = dispatch.Runner(dry_run=False)
    monkeypatch.setattr(dispatch, "_mesh_read", lambda *_a, **_kw: pytest.fail("mesh read should not run"))

    out = dispatch._verify_beast_collector_commit(runner, "abc123def456")

    assert out["ok"] is False
    assert out["error"] == "candidate sha must be full 40-hex"


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
