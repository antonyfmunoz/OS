"""Local Worker Runtime Daemon v1.

Persistent loop that:
- loads config and adapter registry
- emits heartbeat
- polls a filesystem inbox for work packets
- routes to the correct adapter (ping, open_application_url)
- persists RuntimeProof for each action
- handles SIGINT/SIGTERM gracefully

Intentionally minimal. No orchestration, no autonomy, no LLM calls.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from adapters.adapter_engine.adapter_registry_contracts import AdapterRegistry
from execution.runtime.worker_runtime_contracts import (
    EnvironmentType,
    MessageBusType,
    ProofStatus,
    RuntimeProofRecord,
    WorkerHeartbeat,
    WorkerRuntimeDescriptor,
    WSL_AUTHORITY,
)
from runtime.transport.windows_desktop_relay_client import (

    resolve_relay_paths,
    send_request_and_wait,
)



# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [daemon] {msg}", flush=True)


def _log_error(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [daemon] ERROR: {msg}", flush=True)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = f"{_ROOT}/config/local_worker_runtime_daemon_v1.json"


def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with open(config_path, encoding="utf-8-sig") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Daemon
# ---------------------------------------------------------------------------


class LocalWorkerRuntimeDaemon:
    """Minimal persistent worker runtime daemon."""

    def __init__(self, config: dict[str, Any], base_dir: Path = Path(_ROOT)) -> None:
        self.config = config
        self.base_dir = base_dir
        self.worker_id: str = config["worker_id"]
        self.poll_interval: int = config.get("poll_interval_seconds", 3)
        self.heartbeat_interval: int = config.get("heartbeat_interval_seconds", 30)
        self.dry_run: bool = config.get("dry_run", False)
        self.supported_capabilities: list[str] = config.get("supported_capabilities", [])

        self.state_dir = base_dir / config.get("state_dir", "data/runtime/local_worker_runtime")
        self.work_inbox = base_dir / config.get(
            "work_inbox", "data/runtime/local_worker_runtime/inbox"
        )
        self.proof_dir = base_dir / config.get("proof_dir", "data/runtime/runtime_proofs")
        self.processed_dir = self.state_dir / "processed"
        self.failed_dir = self.state_dir / "failed"

        relay_root_cfg = config.get("relay_root")
        self.relay_root, self.relay_inbox, self.relay_outbox = resolve_relay_paths(relay_root_cfg)

        registry_path = base_dir / config.get(
            "adapter_registry_path",
            "data/registries/local_worker_adapter_registry_v1.json",
        )
        self.registry = AdapterRegistry.from_json_file(registry_path)

        self.descriptor = WorkerRuntimeDescriptor(
            worker_id=self.worker_id,
            environment_type=EnvironmentType.LOCAL_WSL,
            authority=WSL_AUTHORITY,
            capabilities=self.supported_capabilities,
            message_bus=MessageBusType.FILESYSTEM_JSON,
        )

        self._running = False
        self._last_heartbeat = 0.0

    # -- Directory setup ---------------------------------------------------

    def ensure_directories(self) -> None:
        for d in [
            self.work_inbox,
            self.state_dir,
            self.proof_dir,
            self.processed_dir,
            self.failed_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    # -- Heartbeat ---------------------------------------------------------

    def emit_heartbeat(self) -> None:
        hb = WorkerHeartbeat(
            worker_id=self.worker_id,
            capabilities_active=self.supported_capabilities,
        )
        hb_path = self.state_dir / "heartbeat.json"
        with open(hb_path, "w") as f:
            json.dump(dataclasses.asdict(hb), f, indent=2)
        self._last_heartbeat = time.time()
        _log(f"heartbeat emitted: {hb.timestamp}")

    def maybe_emit_heartbeat(self) -> None:
        if time.time() - self._last_heartbeat >= self.heartbeat_interval:
            self.emit_heartbeat()

    # -- Runtime status ----------------------------------------------------

    def write_runtime_status(self, status: str) -> None:
        status_data = {
            "worker_id": self.worker_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities": self.supported_capabilities,
            "relay_root": str(self.relay_root),
            "work_inbox": str(self.work_inbox),
            "dry_run": self.dry_run,
        }
        status_path = self.state_dir / "runtime_status.json"
        with open(status_path, "w") as f:
            json.dump(status_data, f, indent=2)

    # -- Proof persistence -------------------------------------------------

    def persist_proof(self, proof: RuntimeProofRecord) -> Path:
        filename = f"{proof.proof_id}.json"
        path = self.proof_dir / filename
        with open(path, "w") as f:
            json.dump(dataclasses.asdict(proof), f, indent=2, default=str)
        _log(f"proof persisted: {filename}")
        return path

    # -- Packet processing -------------------------------------------------

    def process_packet(self, packet_path: Path) -> RuntimeProofRecord | None:
        _log(f"processing: {packet_path.name}")

        try:
            with open(packet_path, encoding="utf-8-sig") as f:
                packet = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            _log_error(f"failed to parse {packet_path.name}: {e}")
            self._move_to_failed(packet_path)
            return None

        action_type = packet.get("action_type", "")
        request_id = packet.get("request_id", "unknown")
        trace_id = packet.get("trace_id", "")

        _log(f"  action_type={action_type} request_id={request_id}")

        if action_type not in self.supported_capabilities:
            _log_error(f"unsupported capability: {action_type}")
            proof = RuntimeProofRecord(
                proof_id=f"PROOF-{uuid.uuid4().hex[:8]}",
                worker_id=self.worker_id,
                adapter_id="none",
                action_type=action_type,
                proof_status=ProofStatus.FAILED,
                adapter_status="rejected",
                request_id=request_id,
                trace_id=trace_id,
                notes=[f"Unsupported capability: {action_type}"],
            )
            self.persist_proof(proof)
            self._move_to_failed(packet_path)
            return proof

        adapter = self.registry.find_adapter_for_action(action_type)
        if adapter is None:
            _log_error(f"no adapter found for: {action_type}")
            proof = RuntimeProofRecord(
                proof_id=f"PROOF-{uuid.uuid4().hex[:8]}",
                worker_id=self.worker_id,
                adapter_id="none",
                action_type=action_type,
                proof_status=ProofStatus.FAILED,
                adapter_status="no_adapter",
                request_id=request_id,
                trace_id=trace_id,
                notes=[f"No adapter registered for: {action_type}"],
            )
            self.persist_proof(proof)
            self._move_to_failed(packet_path)
            return proof

        _log(f"  routing to adapter: {adapter.adapter_id} via {adapter.message_bus.value}")

        try:
            result = send_request_and_wait(
                packet,
                relay_inbox=self.relay_inbox,
                relay_outbox=self.relay_outbox,
                timeout_seconds=60,
                dry_run=self.dry_run,
            )
        except Exception as e:
            _log_error(f"adapter call failed: {e}")
            proof = RuntimeProofRecord(
                proof_id=f"PROOF-{uuid.uuid4().hex[:8]}",
                worker_id=self.worker_id,
                adapter_id=adapter.adapter_id,
                action_type=action_type,
                proof_status=ProofStatus.FAILED,
                adapter_status="exception",
                request_id=request_id,
                trace_id=trace_id,
                notes=[f"Exception during adapter call: {e}"],
            )
            self.persist_proof(proof)
            self._move_to_failed(packet_path)
            return proof

        relay_status = result.get("status", "unknown")
        relay_result = result.get("result") or {}
        adapter_status = relay_result.get("adapter_status", relay_status)

        if relay_status in ("completed", "dry_run"):
            proof_status = ProofStatus.COMPLETED
        elif relay_status == "timeout":
            proof_status = ProofStatus.TIMEOUT
        else:
            proof_status = ProofStatus.FAILED

        proof = RuntimeProofRecord(
            proof_id=f"PROOF-{uuid.uuid4().hex[:8]}",
            worker_id=self.worker_id,
            adapter_id=adapter.adapter_id,
            action_type=action_type,
            proof_status=proof_status,
            adapter_status=adapter_status,
            request_id=request_id,
            trace_id=trace_id,
            evidence=relay_result,
        )

        self.persist_proof(proof)
        self._move_to_processed(packet_path)
        _log(f"  completed: proof_status={proof_status.value} adapter_status={adapter_status}")
        return proof

    # -- File management ---------------------------------------------------

    def _move_to_processed(self, path: Path) -> None:
        try:
            dest = self.processed_dir / path.name
            path.rename(dest)
        except OSError as e:
            _log_error(f"could not move to processed: {e}")

    def _move_to_failed(self, path: Path) -> None:
        try:
            dest = self.failed_dir / path.name
            path.rename(dest)
        except OSError as e:
            _log_error(f"could not move to failed: {e}")

    # -- Main loop ---------------------------------------------------------

    def run(self) -> None:
        self._running = True
        self.ensure_directories()
        self.write_runtime_status("starting")
        self.emit_heartbeat()

        _log("=" * 50)
        _log(f"Local Worker Runtime Daemon v1")
        _log(f"worker_id: {self.worker_id}")
        _log(f"capabilities: {self.supported_capabilities}")
        _log(f"relay_root: {self.relay_root}")
        _log(f"work_inbox: {self.work_inbox}")
        _log(f"proof_dir: {self.proof_dir}")
        _log(f"poll_interval: {self.poll_interval}s")
        _log(f"heartbeat_interval: {self.heartbeat_interval}s")
        _log(f"dry_run: {self.dry_run}")
        _log("=" * 50)

        self.write_runtime_status("running")

        while self._running:
            try:
                self.maybe_emit_heartbeat()

                packets = sorted(self.work_inbox.glob("*.json"))
                for packet_path in packets:
                    if not self._running:
                        break
                    self.process_packet(packet_path)

            except Exception as e:
                _log_error(f"loop iteration failed: {e}")

            time.sleep(self.poll_interval)

        self.write_runtime_status("stopped")
        _log("daemon stopped cleanly")

    def stop(self) -> None:
        _log("shutdown requested")
        self._running = False


# ---------------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------------


def _make_signal_handler(daemon: LocalWorkerRuntimeDaemon):
    def handler(signum: int, frame: Any) -> None:
        _log(f"received signal {signum}")
        daemon.stop()

    return handler


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Worker Runtime Daemon v1")
    parser.add_argument(
        "--config",
        type=str,
        default=DEFAULT_CONFIG_PATH,
        help="Path to daemon config JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Override config to run in dry-run mode",
    )
    parser.add_argument(
        "--relay-root",
        type=str,
        default=None,
        help="Override relay root path",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one batch then exit (for testing)",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    if args.dry_run:
        config["dry_run"] = True
    if args.relay_root:
        config["relay_root"] = args.relay_root

    daemon = LocalWorkerRuntimeDaemon(config)

    signal.signal(signal.SIGINT, _make_signal_handler(daemon))
    signal.signal(signal.SIGTERM, _make_signal_handler(daemon))

    if args.once:
        daemon.ensure_directories()
        daemon.write_runtime_status("once")
        daemon.emit_heartbeat()
        packets = sorted(daemon.work_inbox.glob("*.json"))
        _log(f"--once mode: {len(packets)} packet(s) found")
        for p in packets:
            daemon.process_packet(p)
        daemon.write_runtime_status("stopped")
        _log("--once mode complete")
    else:
        daemon.run()


if __name__ == "__main__":
    main()
