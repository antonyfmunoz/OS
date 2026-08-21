"""Cockpit audit event emitter — settings + unified mutation audit trail.

Settings mutations append to data/umh/settings/audit.jsonl.
All other mutations append to data/umh/audit/mutation_ledger.jsonl.

UMH transport layer.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from substrate.state.runtime_paths import runtime_state_path

logger = logging.getLogger(__name__)

_AUDIT_PATH = str(runtime_state_path("audit/settings", "audit.jsonl", create_parent=False))
_MUTATION_LEDGER_PATH = str(
    runtime_state_path("audit", "mutation_ledger.jsonl", create_parent=False)
)
_MUTATION_LEDGER_SCHEMA = "mutation-ledger-v2"
_MAX_MUTATION_RECORD_BYTES = 1 << 20
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()
_SECRET_KEY_RE = re.compile(r"(token|secret|password|api[_-]?key|credential)", re.I)
_SECRET_VALUE_RE = re.compile(r"\b(?:sk|ghp|xox[baprs])-[-A-Za-z0-9_]{12,}\b")


class MutationLedgerDurabilityError(RuntimeError):
    """Raised when a mutation audit record cannot be durably committed."""


class MutationLedgerRepairError(RuntimeError):
    """Raised when a mutation ledger repair cannot be proven safe."""


def _lock_for(path: str) -> threading.Lock:
    with _LOCKS_GUARD:
        lock = _LOCKS.get(path)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[path] = lock
        return lock


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def file_sha256(path: str | os.PathLike[str]) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, val in value.items():
            if _SECRET_KEY_RE.search(str(key)):
                out[key] = "<redacted>"
            else:
                out[key] = _redact(val)
        return out
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, tuple):
        return [_redact(v) for v in value]
    if isinstance(value, str):
        return _SECRET_VALUE_RE.sub("<redacted>", value)
    return value


def _payload_sha256(record: dict[str, Any]) -> str:
    payload = {k: v for k, v in record.items() if k != "_ledger"}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _integrity_sha256(record: dict[str, Any]) -> str:
    meta = dict(record.get("_ledger") or {})
    meta.pop("integrity_sha256", None)
    bounded = dict(record)
    bounded["_ledger"] = meta
    return hashlib.sha256(_canonical_json(bounded).encode("utf-8")).hexdigest()


def _with_ledger_metadata(record: dict[str, Any], record_type: str) -> dict[str, Any]:
    redacted = _redact(record)
    meta = dict(redacted.get("_ledger") or {})
    meta["schema_version"] = _MUTATION_LEDGER_SCHEMA
    meta["record_type"] = record_type
    redacted["_ledger"] = meta
    meta["payload_sha256"] = _payload_sha256(redacted)
    meta["integrity_sha256"] = _integrity_sha256(redacted)
    return redacted


def _durable_append_jsonl(path: str | os.PathLike[str], record: dict[str, Any]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    line = _canonical_json(record)
    encoded = (line + "\n").encode("utf-8")
    if len(encoded) > _MAX_MUTATION_RECORD_BYTES:
        raise MutationLedgerDurabilityError("mutation ledger record exceeds size limit")
    key = str(target.resolve())
    with _lock_for(key):
        try:
            with _ledger_lock_file(target) as lock_fh:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
                try:
                    with open(target, "a+", encoding="utf-8") as fh:
                        fh.seek(0, os.SEEK_END)
                        start = fh.tell()
                        try:
                            fh.write(line + "\n")
                            fh.flush()
                            os.fsync(fh.fileno())
                        except Exception as exc:  # noqa: BLE001
                            try:
                                fh.truncate(start)
                                fh.flush()
                                os.fsync(fh.fileno())
                            except Exception:
                                pass
                            raise MutationLedgerDurabilityError(
                                f"mutation ledger durable append failed: {exc}"
                            ) from exc
                finally:
                    fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        except MutationLedgerDurabilityError:
            raise
        except OSError as exc:
            raise MutationLedgerDurabilityError(
                f"mutation ledger durable append failed: {exc}"
            ) from exc
    return line


def _append_mutation_record(record: dict[str, Any], *, record_type: str | None = None) -> str:
    kind = record_type or (record.get("_ledger") or {}).get("record_type") or "mutation_audit"
    return _durable_append_jsonl(_MUTATION_LEDGER_PATH, _with_ledger_metadata(record, kind))


def _validate_ledger_record(record: dict[str, Any]) -> tuple[bool, str]:
    meta = record.get("_ledger")
    if meta is None:
        return True, "legacy_record_without_integrity_metadata"
    if not isinstance(meta, dict):
        return False, "ledger metadata is not an object"
    if meta.get("schema_version") != _MUTATION_LEDGER_SCHEMA:
        return False, "unsupported mutation ledger schema"
    if meta.get("record_type") not in {"mutation_audit", "integrity_gap"}:
        return False, "unsupported mutation ledger record_type"
    expected = meta.get("payload_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        return False, "missing payload_sha256"
    actual = _payload_sha256(record)
    if actual != expected:
        return False, "payload_sha256 mismatch"
    expected_integrity = meta.get("integrity_sha256")
    if not isinstance(expected_integrity, str) or len(expected_integrity) != 64:
        return False, "missing integrity_sha256"
    actual_integrity = _integrity_sha256(record)
    if actual_integrity != expected_integrity:
        return False, "integrity_sha256 mismatch"
    return True, "ok"


def read_mutation_ledger(
    path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    ledger = Path(path or _MUTATION_LEDGER_PATH)
    records: list[dict[str, Any]] = []
    malformed: list[dict[str, Any]] = []
    integrity_errors: list[dict[str, Any]] = []
    duplicate_request_ids: list[str] = []
    seen: set[str] = set()
    if not ledger.exists():
        return {
            "path": str(ledger),
            "parse_ok": True,
            "integrity_ok": True,
            "degraded": False,
            "records": [],
            "malformed": [],
            "integrity_errors": [],
            "duplicate_request_ids": [],
        }
    byte_offset = 0
    with ledger.open("rb") as fh:
        for line_no, raw in enumerate(fh, 1):
            stripped = raw.strip()
            if not stripped:
                byte_offset += len(raw)
                continue
            try:
                text = stripped.decode("utf-8")
                record = json.loads(text)
                if not isinstance(record, dict):
                    raise ValueError("record is not an object")
            except Exception as exc:  # noqa: BLE001
                malformed.append(
                    {
                        "line": line_no,
                        "byte_start": byte_offset,
                        "byte_end": byte_offset + len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                byte_offset += len(raw)
                continue
            ok, reason = _validate_ledger_record(record)
            if not ok:
                integrity_errors.append({"line": line_no, "request_id": record.get("request_id"), "error": reason})
            request_id = record.get("request_id")
            if isinstance(request_id, str):
                if request_id in seen:
                    duplicate_request_ids.append(request_id)
                seen.add(request_id)
            records.append(record)
            byte_offset += len(raw)
    if duplicate_request_ids:
        for request_id in sorted(set(duplicate_request_ids)):
            integrity_errors.append(
                {"line": None, "request_id": request_id, "error": "duplicate request_id"}
            )
    return {
        "path": str(ledger),
        "parse_ok": not malformed,
        "integrity_ok": not integrity_errors,
        "degraded": bool(malformed or integrity_errors),
        "records": records,
        "malformed": malformed,
        "integrity_errors": integrity_errors,
        "duplicate_request_ids": sorted(set(duplicate_request_ids)),
    }


def build_integrity_gap_record(
    *,
    unresolved_request_id: str,
    original_file_sha256: str,
    malformed_line_sha256: str,
    byte_range: list[int],
    preserved_fragment_path: str,
    preserved_fragment_sha256: str,
    visible_fields: dict[str, Any],
    unknown_fields: list[str],
    repair_id: str,
    repair_authority: str,
    recovered_second_object_sha256: str,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "request_id": unresolved_request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": "repair",
        "domain": "audit_integrity",
        "surface": "runtime_repair",
        "action": "record_integrity_gap",
        "target": f"mutation_ledger:{unresolved_request_id}",
        "old_value": None,
        "new_value": None,
        "persisted": False,
        "constraint_warnings": ["canonical truth gap: original mutation outcome unknown"],
        "repair_id": repair_id,
        "resolution_status": "unresolved",
        "authority_disposition": "fail_closed",
        "replay_prohibited": True,
        "may_derive_authority": False,
        "visible_fields": visible_fields,
        "unknown_fields": unknown_fields,
        "original_file_sha256": original_file_sha256,
        "malformed_line_sha256": malformed_line_sha256,
        "byte_range": byte_range,
        "preserved_fragment_path": preserved_fragment_path,
        "preserved_fragment_sha256": preserved_fragment_sha256,
        "recovered_second_object_sha256": recovered_second_object_sha256,
        "repair_authority": repair_authority,
    }
    return _with_ledger_metadata(record, "integrity_gap")


def request_authority_disposition(request_id: str) -> dict[str, Any]:
    rows = read_mutation_ledger()
    if not rows["parse_ok"] or not rows["integrity_ok"]:
        return {
            "request_id": request_id,
            "authority_disposition": "unknown_fail_closed",
            "may_derive_authority": False,
            "may_replay": False,
            "reason": "mutation ledger degraded",
        }
    if request_id in rows.get("duplicate_request_ids", []):
        return {
            "request_id": request_id,
            "authority_disposition": "duplicate_fail_closed",
            "may_derive_authority": False,
            "may_replay": False,
            "reason": "duplicate mutation ledger request_id",
        }
    for record in rows["records"]:
        if record.get("request_id") != request_id:
            continue
        if (record.get("_ledger") or {}).get("record_type") == "integrity_gap":
            return {
                "request_id": request_id,
                "authority_disposition": "fail_closed",
                "may_derive_authority": False,
                "may_replay": False,
                "resolution_status": record.get("resolution_status"),
                "repair_id": record.get("repair_id"),
            }
        return {
            "request_id": request_id,
            "authority_disposition": "recorded_mutation",
            "may_derive_authority": bool(record.get("persisted")),
            "may_replay": False,
        }
    return {
        "request_id": request_id,
        "authority_disposition": "absent",
        "may_derive_authority": False,
        "may_replay": False,
    }


def _fsync_parent(path: Path) -> None:
    fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _ledger_lock_file(path: Path):
    lock_path = path.with_name(f".{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    return open(lock_path, "a+b")


def _write_preserved_bytes(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    fh = None
    try:
        fh = os.fdopen(fd, "wb")
        fd = -1
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
        fh.close()
    except Exception:
        if fh is not None and not fh.closed:
            fh.close()
        elif fd >= 0:
            os.close(fd)
        raise
    _fsync_parent(path)


def _write_preserved_text(path: Path, text: str, mode: int = 0o600) -> None:
    _write_preserved_bytes(path, text.encode("utf-8"), mode=mode)


def _repair_manifest_path(preservation_dir: Path, repair_id: str) -> Path:
    return preservation_dir / f"{repair_id}.manifest.json"


def _find_recoverable_json_object(raw_body: bytes, request_id: str) -> tuple[int, bytes, dict[str, Any]]:
    for match in re.finditer(rb"\{", raw_body):
        offset = match.start()
        candidate = raw_body[offset:]
        try:
            obj = json.loads(candidate.decode("utf-8"))
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("request_id") == request_id:
            return offset, candidate, obj
    raise MutationLedgerRepairError("recoverable second object boundary not found")


def _replay_manifest_if_valid(
    *,
    ledger: Path,
    preservation_dir: Path,
    repair_id: str,
    expected_original_sha256: str,
) -> dict[str, Any] | None:
    manifest_path = _repair_manifest_path(preservation_dir, repair_id)
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("original_sha256") != expected_original_sha256:
        raise MutationLedgerRepairError("repair manifest original digest mismatch")
    current = file_sha256(ledger) if ledger.exists() else ""
    if current != manifest.get("repaired_sha256"):
        raise MutationLedgerRepairError("ledger changed after prior repair")
    manifest = dict(manifest)
    manifest["ok"] = True
    manifest["replayed"] = True
    return manifest


def _validate_append_tail(
    tail: bytes,
    *,
    unresolved_request_id: str,
    recoverable_request_id: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_tail: set[str] = set()
    for line_no, raw in enumerate(tail.splitlines(keepends=True), 1):
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise MutationLedgerRepairError("append tail failed validation") from exc
        if not isinstance(record, dict):
            raise MutationLedgerRepairError("append tail failed validation")
        ok, reason = _validate_ledger_record(record)
        if not ok:
            raise MutationLedgerRepairError(f"append tail failed validation: {reason}")
        request_id = record.get("request_id")
        if isinstance(request_id, str):
            if request_id in seen_tail or request_id in {
                unresolved_request_id,
                recoverable_request_id,
            }:
                raise MutationLedgerRepairError("append tail conflicts with repaired request ids")
            seen_tail.add(request_id)
        records.append(record)
    return records


def repair_mutation_ledger_truth_gap(
    *,
    expected_original_sha256: str,
    malformed_line: int,
    unresolved_request_id: str,
    recoverable_request_id: str,
    preservation_dir: str | os.PathLike[str],
    repair_authority: str,
    preserved_original_path: str | os.PathLike[str] | None = None,
    expected_current_sha256: str | None = None,
    expected_malformed_line_sha256: str | None = None,
) -> dict[str, Any]:
    ledger = Path(_MUTATION_LEDGER_PATH)
    repair_binding = expected_current_sha256 or expected_original_sha256
    repair_id = (
        f"mutation-ledger-repair-{expected_original_sha256[:16]}-"
        f"{repair_binding[:16]}-line-{malformed_line}"
    )
    preservation = Path(preservation_dir)
    preservation.mkdir(parents=True, exist_ok=True)
    replay = _replay_manifest_if_valid(
        ledger=ledger,
        preservation_dir=preservation,
        repair_id=repair_id,
        expected_original_sha256=expected_original_sha256,
    )
    if replay is not None:
        return replay

    key = str(ledger.resolve())
    with _lock_for(key):
        with _ledger_lock_file(ledger) as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                original_bytes = ledger.read_bytes()
                current_sha = hashlib.sha256(original_bytes).hexdigest()
                append_extension = expected_current_sha256 is not None
                if append_extension:
                    if current_sha != expected_current_sha256:
                        raise MutationLedgerRepairError("frozen current digest mismatch")
                    if preserved_original_path is None:
                        raise MutationLedgerRepairError("preserved original path required")
                    preserved_original = Path(preserved_original_path).read_bytes()
                    preserved_sha = hashlib.sha256(preserved_original).hexdigest()
                    if preserved_sha != expected_original_sha256:
                        raise MutationLedgerRepairError("preserved original digest mismatch")
                    if not original_bytes.startswith(preserved_original):
                        raise MutationLedgerRepairError(
                            "ledger is not a strict append-only extension"
                        )
                    tail = original_bytes[len(preserved_original) :]
                    _validate_append_tail(
                        tail,
                        unresolved_request_id=unresolved_request_id,
                        recoverable_request_id=recoverable_request_id,
                    )
                    prefix_sha = preserved_sha
                    frozen_sha = current_sha
                    tail_sha = hashlib.sha256(tail).hexdigest()
                elif current_sha != expected_original_sha256:
                    raise MutationLedgerRepairError("mutation ledger digest changed before repair")
                else:
                    preserved_original = original_bytes
                    tail = b""
                    prefix_sha = expected_original_sha256
                    frozen_sha = current_sha
                    tail_sha = hashlib.sha256(tail).hexdigest()
                original_copy = preservation / f"{repair_id}.original.jsonl"
                _write_preserved_bytes(original_copy, original_bytes)
                prefix_copy = preservation / f"{repair_id}.preserved-prefix.jsonl"
                _write_preserved_bytes(prefix_copy, preserved_original)
                if append_extension:
                    tail_copy = preservation / f"{repair_id}.append-tail.jsonl"
                    _write_preserved_bytes(tail_copy, tail)
                raw_lines = original_bytes.splitlines(keepends=True)
                if malformed_line < 1 or malformed_line > len(raw_lines):
                    raise MutationLedgerRepairError("malformed line out of range")
                raw_line = raw_lines[malformed_line - 1]
                raw_line_sha = hashlib.sha256(raw_line).hexdigest()
                if (
                    expected_malformed_line_sha256 is not None
                    and raw_line_sha != expected_malformed_line_sha256
                ):
                    raise MutationLedgerRepairError("malformed line digest mismatch")
                raw_body = raw_line.rstrip(b"\r\n")
                split, recovered_raw, recovered = _find_recoverable_json_object(
                    raw_body, recoverable_request_id
                )
                if split <= 0:
                    raise MutationLedgerRepairError("recoverable object cannot be first fragment")
                fragment = raw_body[:split]
                if unresolved_request_id.encode("utf-8") not in fragment:
                    raise MutationLedgerRepairError("unresolved request id not present in fragment")
                if recovered.get("request_id") != recoverable_request_id:
                    raise MutationLedgerRepairError("recoverable object request id mismatch")
                fragment_path = preservation / f"{repair_id}.fragment.raw"
                _write_preserved_bytes(fragment_path, fragment)
                recovered_path = preservation / f"{repair_id}.recovered.json"
                _write_preserved_bytes(recovered_path, recovered_raw + b"\n")
                starts: list[int] = []
                pos = 0
                for line in raw_lines:
                    starts.append(pos)
                    pos += len(line)
                visible = {"request_id": unresolved_request_id}
                text = fragment.decode("utf-8", "replace")
                if '"timestamp":' in text:
                    visible["timestamp_prefix"] = text.rsplit('"timestamp":', 1)[-1].strip()
                gap = build_integrity_gap_record(
                    unresolved_request_id=unresolved_request_id,
                    original_file_sha256=prefix_sha,
                    malformed_line_sha256=raw_line_sha,
                    byte_range=[
                        starts[malformed_line - 1],
                        starts[malformed_line - 1] + len(raw_line),
                    ],
                    preserved_fragment_path=str(fragment_path),
                    preserved_fragment_sha256=hashlib.sha256(fragment).hexdigest(),
                    visible_fields=visible,
                    unknown_fields=[
                        "actor",
                        "domain",
                        "surface",
                        "action",
                        "target",
                        "old_value",
                        "new_value",
                        "persisted",
                        "outcome",
                    ],
                    repair_id=repair_id,
                    repair_authority=repair_authority,
                    recovered_second_object_sha256=hashlib.sha256(recovered_raw).hexdigest(),
                )
                replacement = _canonical_json(gap).encode("utf-8") + b"\n" + recovered_raw + b"\n"
                repaired = b"".join(
                    replacement if i == malformed_line - 1 else line
                    for i, line in enumerate(raw_lines)
                )
                fd, tmp_name = tempfile.mkstemp(prefix=f".{ledger.name}.repair.", dir=str(ledger.parent))
                tmp = Path(tmp_name)
                try:
                    with os.fdopen(fd, "wb") as fh:
                        fh.write(repaired)
                        fh.flush()
                        os.fsync(fh.fileno())
                    st = ledger.stat()
                    os.chmod(tmp, st.st_mode & 0o777)
                    try:
                        os.chown(tmp, st.st_uid, st.st_gid)
                    except PermissionError:
                        pass
                    validation = read_mutation_ledger(tmp)
                    if not validation["parse_ok"] or not validation["integrity_ok"]:
                        raise MutationLedgerRepairError("repaired ledger failed validation")
                    repaired_sha = hashlib.sha256(repaired).hexdigest()
                    manifest = {
                        "ok": True,
                        "replayed": False,
                        "repair_id": repair_id,
                        "ledger_path": str(ledger),
                        "original_sha256": expected_original_sha256,
                        "append_extension": append_extension,
                        "frozen_current_sha256": frozen_sha,
                        "prefix_sha256": prefix_sha,
                        "prefix_path": str(prefix_copy),
                        "tail_sha256": tail_sha,
                        "tail_size": len(tail),
                        "repaired_sha256": repaired_sha,
                        "malformed_line": malformed_line,
                        "malformed_line_sha256": raw_line_sha,
                        "unresolved_request_id": unresolved_request_id,
                        "recoverable_request_id": recoverable_request_id,
                        "fragment_path": str(fragment_path),
                        "fragment_sha256": hashlib.sha256(fragment).hexdigest(),
                        "recovered_path": str(recovered_path),
                        "recovered_sha256": hashlib.sha256(recovered_raw).hexdigest(),
                        "repair_authority": repair_authority,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    manifest_path = _repair_manifest_path(preservation, repair_id)
                    _write_preserved_text(manifest_path, _canonical_json(manifest) + "\n")
                    os.replace(tmp, ledger)
                    _fsync_parent(ledger)
                finally:
                    if tmp.exists():
                        tmp.unlink()
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
    return manifest


def emit_settings_audit(
    action: str,
    target: str,
    old_value: Any,
    new_value: Any,
    domain: str,
    surface: str = "cockpit_settings",
    persisted: bool = True,
    constraint_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Emit and persist a settings audit event. Returns the event dict."""
    event = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": "operator",
        "surface": surface,
        "action": action,
        "target": target,
        "domain": domain,
        "old_value": old_value,
        "new_value": new_value,
        "persisted": persisted,
        "constraint_warnings": constraint_warnings or [],
    }

    try:
        os.makedirs(os.path.dirname(_AUDIT_PATH), exist_ok=True)
        with open(_AUDIT_PATH, "a") as f:
            f.write(json.dumps(event, default=str) + "\n")
    except OSError as exc:
        logger.error("Failed to write audit event: %s", exc)

    logger.info("Audit: %s %s.%s", action, domain, target)
    return event


def emit_mutation_audit(
    domain: str,
    action: str,
    target: str,
    *,
    actor: str = "operator",
    surface: str = "cockpit",
    old_value: Any = None,
    new_value: Any = None,
    persisted: bool = True,
    constraint_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Emit a mutation audit event to the unified ledger.

    Writes to data/umh/audit/mutation_ledger.jsonl using file-level
    locking (fcntl.flock) for safe concurrent appends.

    Returns the event dict so callers can include it in responses.
    """
    event: dict[str, Any] = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "domain": domain,
        "surface": surface,
        "action": action,
        "target": target,
        "old_value": old_value,
        "new_value": new_value,
        "persisted": persisted,
        "constraint_warnings": constraint_warnings or [],
    }

    _append_mutation_record(event)

    logger.info("MutationAudit: %s %s.%s", action, domain, target)
    return event
