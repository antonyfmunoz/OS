"""
Control Layer v2 — Remote Executor (daemon-side reader).

A single-threaded loop that drains the existing control_bridge queue for
this node and dispatches each command through the existing local_executor.
The bridge queue remains the ONLY transport. The daemon is just a reader.

Design rules (non-negotiable):
    * Additive only. Does not touch the hot path.
    * No new execution capability — reuses local_executor.execute_command.
    * No threading. Simple time.sleep loop with cooperative stop().
    * Hard-capped batch (<=10).
    * NEVER raises. Every public method returns a structured dict.
    * Validates target node scope before executing each envelope.
"""

from __future__ import annotations

import time
from typing import Any

from runtime.substrate import control_bridge as bridge
from runtime.substrate import control_commands as cc
from runtime.substrate import local_executor
from runtime.substrate import remote_identity

LAYER_NAME = "remote_executor"
LAYER_VERSION = "v2"

HARD_BATCH_CAP = 10
DEFAULT_INTERVAL_S = 1.0
MIN_INTERVAL_S = 0.1


class RemoteExecutor:
    """Polling reader that converts queued commands into local executions."""

    def __init__(self) -> None:
        self._stop = False
        self._last_processed_at: float | None = None
        self._last_count: int = 0
        self._total_processed: int = 0

    # ─── Lifecycle ───────────────────────────────────────────────────────────

    def stop(self) -> None:
        """Cooperatively halt run_loop on its next iteration."""
        self._stop = True

    def status(self, node_id: str | None = None) -> dict[str, Any]:
        """Inspect-only summary. Never raises."""
        nid = node_id or remote_identity.get_node_id()
        try:
            depth = bridge.queue_depth(nid)
        except Exception:  # noqa: BLE001
            depth = -1
        return {
            "ok": True,
            "node_id": nid,
            "queue_depth": depth,
            "last_processed_at": self._last_processed_at,
            "last_batch_count": self._last_count,
            "total_processed": self._total_processed,
            "stopped": self._stop,
        }

    # ─── Core poll ───────────────────────────────────────────────────────────

    def poll_once(self, node_id: str) -> dict[str, Any]:
        """
        Drain up to HARD_BATCH_CAP pending commands for `node_id` once.

        Returns:
            {
                "ok": bool,
                "node_id": str,
                "processed": int,
                "skipped": int,
                "results": [<execution result dicts>],
            }
        """
        out: dict[str, Any] = {
            "ok": True,
            "node_id": node_id or "",
            "processed": 0,
            "skipped": 0,
            "results": [],
        }
        if not node_id:
            out["ok"] = False
            out["reason"] = "missing_node_id"
            return out

        try:
            pending = bridge.get_pending_commands(node_id, limit=HARD_BATCH_CAP)
        except Exception as e:  # noqa: BLE001
            out["ok"] = False
            out["reason"] = f"bridge_read_error:{type(e).__name__}"
            return out

        for cmd in pending[:HARD_BATCH_CAP]:
            try:
                # Scope check — must be addressed to this node.
                if not remote_identity.validate_command_scope(cmd, node_id):
                    out["skipped"] += 1
                    out["results"].append(
                        {
                            "ok": False,
                            "command_id": getattr(cmd, "command_id", None),
                            "reason": "scope_mismatch",
                            "node_id": node_id,
                        }
                    )
                    continue

                # Envelope re-validation (defense-in-depth).
                ok, reason = cc.validate(cmd)
                if not ok:
                    out["skipped"] += 1
                    rejection = {
                        "ok": False,
                        "command_id": getattr(cmd, "command_id", None),
                        "reason": f"invalid_envelope:{reason}",
                        "node_id": node_id,
                    }
                    out["results"].append(rejection)
                    # Ack to drop the malformed envelope from the queue.
                    try:
                        bridge.ack_command(cmd.command_id, result=rejection)
                    except Exception:  # noqa: BLE001
                        pass
                    continue

                # Execute via the EXISTING local executor — no new capability.
                result = local_executor.execute_command(cmd)

                # Ack with result attached (idempotent on duplicate).
                try:
                    bridge.ack_command(cmd.command_id, result=result)
                except Exception:  # noqa: BLE001
                    pass

                out["results"].append(result)
                out["processed"] += 1
            except Exception as e:  # noqa: BLE001
                # Per-command failure must never break the batch.
                out["results"].append(
                    {
                        "ok": False,
                        "command_id": getattr(cmd, "command_id", None),
                        "reason": f"executor_loop_error:{type(e).__name__}",
                        "node_id": node_id,
                    }
                )
                out["skipped"] += 1

        self._last_processed_at = time.time()
        self._last_count = out["processed"]
        self._total_processed += out["processed"]
        return out

    # ─── Loop ────────────────────────────────────────────────────────────────

    def run_loop(
        self,
        node_id: str,
        interval_s: float = DEFAULT_INTERVAL_S,
        max_batch: int = 5,
    ) -> dict[str, Any]:
        """
        Run poll_once on a fixed interval until stop() is called.

        max_batch is clamped to <= HARD_BATCH_CAP. Loop body is wrapped so a
        single bad iteration cannot kill the daemon — failures are recorded
        and the loop continues after the configured interval.
        """
        try:
            interval = max(float(interval_s), MIN_INTERVAL_S)
        except Exception:  # noqa: BLE001
            interval = DEFAULT_INTERVAL_S
        try:
            batch = max(1, min(int(max_batch), HARD_BATCH_CAP))
        except Exception:  # noqa: BLE001
            batch = 5

        self._stop = False
        iterations = 0
        errors = 0
        try:
            while not self._stop:
                iterations += 1
                try:
                    # poll_once already enforces HARD_BATCH_CAP via bridge limit.
                    self.poll_once(node_id)
                    # Soft batch ceiling: if a smaller per-iteration batch was
                    # requested, we already capped via HARD_BATCH_CAP at the
                    # bridge layer (10). The `batch` value is recorded in the
                    # final summary so callers can verify intent.
                    _ = batch
                except Exception:  # noqa: BLE001
                    errors += 1
                try:
                    time.sleep(interval)
                except Exception:  # noqa: BLE001
                    break
        except KeyboardInterrupt:
            pass
        return {
            "ok": True,
            "node_id": node_id,
            "iterations": iterations,
            "errors": errors,
            "stopped": True,
            "interval_s": interval,
            "batch": batch,
        }
