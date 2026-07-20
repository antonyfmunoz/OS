#!/usr/bin/env python3
"""Wave 0 runtime-state migration — state-safe cutover of live journals.

Moves the migrated subsystems' runtime files from their legacy homes under
``data/umh/`` to the runtime-state root (``data/runtime/umh`` by default,
``UMH_STATE_DIR`` override) without losing a record.

Modes (Amendment E — run in this order):
  --plan           print/emit the complete migration manifest; NO mutation
  --snapshot       initial ONLINE byte copy + external backup; records source
                   byte offsets for append-only files
  --finalize       QUIESCENT final delta: append bytes written since snapshot,
                   re-copy changed snapshots, verify hashes. All writers to
                   the migrating files must be stopped first.
  --verify         read-only integrity comparison of old vs new
  --rollback-plan  print exact rollback instructions; NO automatic rollback

Migration classes:
  append_jsonl  — copy original bytes, record offset, append only the verified
                  final delta during quiescence; bytes never reserialized
  snapshot_json — validate JSON, copy the final quiescent version atomically
  ephemeral     — heartbeats/locks/tmp/sockets are NOT migrated; the owning
                  runtime recreates them at the new home
  unknown       — never moved automatically; recorded, and the run STOPS

Backups + manifests live OUTSIDE the source checkout
(``--backup-dir``, default /var/backups/umh/runtime-state/<cutover-id>).
Nothing in the source tree is deleted or reset by this script.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

_REPO_DEFAULT = os.environ.get("UMH_ROOT", "/opt/OS")

# ── The migration manifest rules (Amendment C census, encoded) ─────────────
# (legacy dir under repo, runtime-state subsystem, notes on writers/readers)
SUBSYSTEMS: list[dict[str, Any]] = [
    {
        "old_dir": "data/umh/organism",
        "subsystem": "organism",
        "writers": "OrganismDaemon/EventSpine/ExecutionJournal/OrganismStore/ApprovalStore/"
        "ReportDispatcher/OutcomeLearningLoop/ProofRuntime/TemplateSeeder/DevSessionTracker",
        "recovery_readers": "EventSpine.recover, ExecutionJournal.recover",
    },
    {
        "old_dir": "data/umh/c35",
        "subsystem": "c35",
        "writers": "qualification_harness",
        "recovery_readers": "",
    },
    {
        "old_dir": "data/umh/qualification",
        "subsystem": "qualification",
        "writers": "self_model_predictor",
        "recovery_readers": "",
    },
    {
        "old_dir": "data/umh/fleet",
        "subsystem": "fleet",
        "writers": "agent_fleet_runtime",
        "recovery_readers": "",
    },
    {
        "old_dir": "data/umh/execution_coordinator",
        "subsystem": "execution_coordinator",
        "writers": "execution_coordinator (PlanStore/queue/lifecycle)",
        "recovery_readers": "ExecutionCoordinator queue reload",
    },
    {
        "old_dir": "data/umh/projections",
        "subsystem": "projections",
        "writers": "substrate.sockets.projection_port",
        "recovery_readers": "ProjectionPort._load",
        # campaign artifact validated by test_p4_sync_campaign_artifacts — static
        "keep_patterns": ["projection_connection_matrix.json"],
    },
    {
        "old_dir": "data/umh/reality_model",
        "subsystem": "reality_model",
        "writers": "reality_model.instance / reality_model.canonical",
        "recovery_readers": "InstanceRealityModel load, CanonicalRealityModel load",
    },
    {
        "old_dir": "data/umh/universal_work",
        "subsystem": "universal_work",
        "writers": "work_packet_engine/workcell/role_contracts/knowledge_model_registry",
        "recovery_readers": "load_packets/load_workcells/load_role_contracts",
        # historical phase11 proof JSONs are STATIC TRACKED EVIDENCE — not runtime
        "keep_patterns": ["phase11_1*.json"],
    },
    {
        "old_dir": "data/umh/work_portfolio",
        "subsystem": "work_portfolio",
        "writers": "work_portfolio_runtime",
        "recovery_readers": "",
    },
    {
        "old_dir": "data/umh/operator_experience",
        "subsystem": "operator_experience",
        "writers": "advisor_conversation (live); operator_session/operator_response (sessions/turns/intents/responses)",
        "recovery_readers": "conversation history load",
        # phase13 proofs are STATIC TRACKED EVIDENCE — not runtime
        "keep_patterns": ["phase13_*"],
        # Wave 0 rename: the conversation store was renamed dex_→advisor_ in
        # code; the byte copy must land under the NEW name or history is
        # orphaned (review finding C4).
        "renames": {"dex_conversations.jsonl": "advisor_conversations.jsonl"},
    },
    {
        "old_dir": "data/umh/operator/intent_loop",
        "subsystem": "operator/intent_loop",
        "writers": "substrate.execution.intent.loop IntentLoopStore",
        "recovery_readers": "IntentLoopStore.load_all",
    },
    {
        "old_dir": "data/umh/workcell_daemon",
        "subsystem": "workcell_daemon",
        "writers": "WorkcellDaemon._persist_state",
        "recovery_readers": "",
    },
]

EPHEMERAL_PATTERNS = ["heartbeat.json", "*.lock", "*.tmp", "*.sock", "*.pid"]


def _classify(rel_name: str) -> str:
    base = os.path.basename(rel_name)
    for pat in EPHEMERAL_PATTERNS:
        if fnmatch.fnmatch(base, pat):
            return "ephemeral"
    if base.endswith((".jsonl", ".jsonl.old")):
        return "append_jsonl"
    if base.endswith(".json"):
        return "snapshot_json"
    if base == ".gitkeep":
        return "ephemeral"  # placeholder file, regenerated/not needed at new home
    return "unknown"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _tracked_set(repo: Path) -> set[str]:
    import subprocess  # scripts/ is CPU-gate exempt

    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "ls-files"],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        ).stdout
        return set(out.splitlines())
    except Exception as exc:
        print(f"[migrate] WARNING: git ls-files failed ({exc}); tracked status unknown")
        return set()


def build_manifest(repo: Path, state_root: Path) -> list[dict[str, Any]]:
    tracked = _tracked_set(repo)
    entries: list[dict[str, Any]] = []
    for sub in SUBSYSTEMS:
        old_dir = repo / sub["old_dir"]
        if not old_dir.is_dir():
            continue
        keep = sub.get("keep_patterns", [])
        for path in sorted(old_dir.rglob("*")):
            if not path.is_file():
                continue
            rel_in_sub = path.relative_to(old_dir).as_posix()
            rel_repo = path.relative_to(repo).as_posix()
            if any(fnmatch.fnmatch(os.path.basename(rel_in_sub), k) for k in keep):
                entries.append(
                    {
                        "old_rel": rel_repo,
                        "new_rel": None,
                        "mode": "keep_tracked_static",
                        "classification": "canonical_seed",
                        "tracked": rel_repo in tracked,
                        "writers": "none (historical proof)",
                        "readers": "tests/audits",
                        "recovery_reader": "",
                        "size": path.stat().st_size,
                    }
                )
                continue
            mode = _classify(rel_in_sub)
            renames = sub.get("renames", {})
            dest_rel = renames.get(rel_in_sub, rel_in_sub)
            new_path = state_root / sub["subsystem"] / dest_rel
            entry = {
                "old_rel": rel_repo,
                "new_rel": new_path.relative_to(state_root).as_posix(),
                "new_abs": str(new_path),
                "mode": mode,
                "classification": "ephemeral" if mode == "ephemeral" else "runtime_state",
                "tracked": rel_repo in tracked,
                "writers": sub["writers"],
                "readers": "same modules (constants migrated in Wave 0 commit)",
                "recovery_reader": sub["recovery_readers"],
                "size": path.stat().st_size,
            }
            if mode in ("append_jsonl", "snapshot_json"):
                entry["old_sha256"] = _sha256(path)
            entries.append(entry)
    return entries


def _atomic_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".migrating")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def do_snapshot(repo: Path, state_root: Path, backup_dir: Path) -> int:
    manifest = build_manifest(repo, state_root)
    unknowns = [e for e in manifest if e["mode"] == "unknown"]
    if unknowns:
        print("[migrate] STOP — unknown-mode files need adjudication before any move:")
        for e in unknowns:
            print(f"  {e['old_rel']}")
        _write_manifest(backup_dir, manifest, phase="snapshot_blocked")
        return 2

    backup_root = backup_dir / "originals"
    for e in manifest:
        if e["mode"] not in ("append_jsonl", "snapshot_json"):
            continue
        src = repo / e["old_rel"]
        # external backup first
        bdst = backup_root / e["old_rel"]
        bdst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, bdst)
        # online copy to the new home. The append offset MUST be the byte
        # count actually captured in dst — a writer may append to src between
        # the copy and any later stat; those bytes belong to the finalize
        # delta, never silently skipped (review finding C3).
        dst = Path(e["new_abs"])
        _atomic_copy(src, dst)
        e["snapshot_offset"] = dst.stat().st_size
        e["snapshot_new_sha256"] = _sha256(dst)
        e["backup_path"] = str(bdst)
    _write_manifest(backup_dir, manifest, phase="snapshot")
    moved = sum(1 for e in manifest if "snapshot_offset" in e)
    print(
        f"[migrate] snapshot complete: {moved} durable files copied "
        f"(+{sum(1 for e in manifest if e['mode'] == 'ephemeral')} ephemeral skipped, "
        f"{sum(1 for e in manifest if e['mode'] == 'keep_tracked_static')} static kept)"
    )
    print(f"[migrate] manifest + backups: {backup_dir}")
    return 0


def do_finalize(repo: Path, state_root: Path, backup_dir: Path) -> int:
    manifest = _read_manifest(backup_dir, "snapshot")
    if manifest is None:
        print("[migrate] ERROR: no snapshot manifest found — run --snapshot first")
        return 2
    failures: list[str] = []
    for e in manifest:
        src = repo / e["old_rel"]
        if e["mode"] == "append_jsonl":
            dst = Path(e["new_abs"])
            if not src.exists():
                e["finalize_status"] = "source_gone"
                failures.append(e["old_rel"])
                continue
            size_now = src.stat().st_size
            offset = int(e["snapshot_offset"])
            if size_now < offset:
                e["finalize_status"] = "source_truncated_since_snapshot"
                failures.append(e["old_rel"])
                continue
            # quiescence check: size must be stable across a short window
            time.sleep(1.0)
            if src.stat().st_size != size_now:
                e["finalize_status"] = "still_being_written"
                failures.append(e["old_rel"])
                continue
            if size_now > offset:
                with open(src, "rb") as fsrc:
                    fsrc.seek(offset)
                    delta = fsrc.read()
                with open(dst, "ab") as fdst:
                    fdst.write(delta)
                e["delta_bytes"] = size_now - offset
            else:
                e["delta_bytes"] = 0
            e["final_old_sha256"] = _sha256(src)
            e["final_new_sha256"] = _sha256(dst)
            e["finalize_status"] = (
                "verified" if e["final_old_sha256"] == e["final_new_sha256"] else "hash_mismatch"
            )
            if e["finalize_status"] != "verified":
                failures.append(e["old_rel"])
        elif e["mode"] == "snapshot_json":
            dst = Path(e["new_abs"])
            if not src.exists():
                e["finalize_status"] = "source_gone"
                failures.append(e["old_rel"])
                continue
            # quiescence guard (review finding W1): a snapshot captured while
            # its writer is mid-update is torn state that still hash-verifies
            stat_before = src.stat()
            time.sleep(1.0)
            stat_after = src.stat()
            if (stat_before.st_size, stat_before.st_mtime_ns) != (
                stat_after.st_size,
                stat_after.st_mtime_ns,
            ):
                e["finalize_status"] = "still_being_written"
                failures.append(e["old_rel"])
                continue
            try:
                json.loads(src.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError):
                e["finalize_status"] = "invalid_json_source"
                failures.append(e["old_rel"])
                continue
            _atomic_copy(src, dst)
            e["final_old_sha256"] = _sha256(src)
            e["final_new_sha256"] = _sha256(dst)
            e["finalize_status"] = (
                "verified" if e["final_old_sha256"] == e["final_new_sha256"] else "hash_mismatch"
            )
            if e["finalize_status"] != "verified":
                failures.append(e["old_rel"])
        else:
            e["finalize_status"] = "not_migrated_" + e["mode"]
    _write_manifest(backup_dir, manifest, phase="finalize")
    if failures:
        print(f"[migrate] FINALIZE FAILED for {len(failures)} file(s):")
        for f in failures:
            print(f"  {f}")
        return 2
    print("[migrate] finalize verified: every durable file byte-identical at the new home")
    print(f"[migrate] manifest: {backup_dir}/manifest_finalize.json")
    return 0


def do_verify(repo: Path, state_root: Path, backup_dir: Path) -> int:
    manifest = _read_manifest(backup_dir, "finalize") or _read_manifest(backup_dir, "snapshot")
    if manifest is None:
        print("[migrate] ERROR: no manifest found")
        return 2
    bad = 0
    for e in manifest:
        if e["mode"] not in ("append_jsonl", "snapshot_json"):
            continue
        dst = Path(e["new_abs"])
        if not dst.exists():
            print(f"[verify] MISSING new file: {e['new_abs']}")
            bad += 1
            continue
        expected = e.get("final_new_sha256") or e.get("snapshot_new_sha256")
        actual = _sha256(dst)
        if expected and actual != expected:
            print(f"[verify] HASH MISMATCH: {e['new_abs']}")
            bad += 1
    print(f"[verify] {'FAILED' if bad else 'OK'} — {bad} problem(s)")
    return 2 if bad else 0


def print_rollback_plan(repo: Path, backup_dir: Path) -> int:
    manifest = _read_manifest(backup_dir, "finalize") or _read_manifest(backup_dir, "snapshot")
    print("# Wave 0 runtime-state migration — ROLLBACK PLAN (manual, never automatic)")
    print(f"# Backups: {backup_dir}/originals/ (byte copies of every durable file)")
    print("# To roll back:")
    print("#  1. Stop all services writing runtime state.")
    print(f"#  2. Copy each file from {backup_dir}/originals/<old_rel> back to <repo>/<old_rel>.")
    print("#  3. Check out the pre-Wave-0 commit (writers then resolve the old paths).")
    print("#  4. Restart services individually; verify journals replay.")
    if manifest:
        print(f"# {len(manifest)} manifest entries; durable files:")
        for e in manifest:
            if e["mode"] in ("append_jsonl", "snapshot_json"):
                print(f"#   {e['old_rel']}")
    return 0


def _write_manifest(backup_dir: Path, manifest: list[dict[str, Any]], phase: str) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    out = backup_dir / f"manifest_{phase}.json"
    out.write_text(json.dumps({"phase": phase, "entries": manifest}, indent=2))


def _read_manifest(backup_dir: Path, phase: str) -> list[dict[str, Any]] | None:
    p = backup_dir / f"manifest_{phase}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())["entries"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--snapshot", action="store_true")
    mode.add_argument("--finalize", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--rollback-plan", action="store_true")
    ap.add_argument("--repo", default=_REPO_DEFAULT)
    ap.add_argument(
        "--backup-dir",
        default=None,
        help="cutover workspace OUTSIDE the checkout "
        "(default /var/backups/umh/runtime-state/<cutover-id>)",
    )
    ap.add_argument("--cutover-id", default=None)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    # import the resolver from the CODE repo (where this script lives) while
    # resolving the state root under the TARGET repo
    code_repo = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(code_repo))
    os.environ["UMH_ROOT"] = str(repo)
    from substrate.state.runtime_paths import runtime_state_root

    state_root = runtime_state_root()
    cutover_id = args.cutover_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup_dir = (
        Path(args.backup_dir)
        if args.backup_dir
        else (Path("/var/backups/umh/runtime-state") / cutover_id)
    )
    if repo in backup_dir.parents or backup_dir == repo:
        print("[migrate] ERROR: backup dir must live OUTSIDE the source checkout")
        return 2

    if args.plan:
        manifest = build_manifest(repo, state_root)
        print(
            json.dumps(
                {"repo": str(repo), "state_root": str(state_root), "entries": manifest}, indent=2
            )
        )
        unknowns = [e for e in manifest if e["mode"] == "unknown"]
        durable = [e for e in manifest if e["mode"] in ("append_jsonl", "snapshot_json")]
        print(
            f"\n[plan] {len(manifest)} files: {len(durable)} durable, "
            f"{sum(1 for e in manifest if e['mode'] == 'ephemeral')} ephemeral, "
            f"{sum(1 for e in manifest if e['mode'] == 'keep_tracked_static')} static-kept, "
            f"{len(unknowns)} UNKNOWN",
            file=sys.stderr,
        )
        return 2 if unknowns else 0
    if args.snapshot:
        return do_snapshot(repo, state_root, backup_dir)
    if args.finalize:
        return do_finalize(repo, state_root, backup_dir)
    if args.verify:
        return do_verify(repo, state_root, backup_dir)
    if args.rollback_plan:
        return print_rollback_plan(repo, backup_dir)
    return 2


if __name__ == "__main__":
    sys.exit(main())
