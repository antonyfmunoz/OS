"""ZMQ command client for live FFmpeg filter parameter control.

Sends commands to named filters in a running FFmpeg filtergraph via the
zmq filter's REQ/REP protocol. Used for blip-free scene switching by
repositioning/enabling/disabling overlay filters at runtime.

Protocol: "FILTERNAME COMMAND ARG" -> "0 Success" or "1 Error message"
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_ZMQ_DEFAULT_PORT = 5555


class ZmqCommandResult:
    """Result of a single zmq command."""

    __slots__ = ("filter_name", "command", "arg", "success", "reply", "latency_ms")

    def __init__(
        self,
        filter_name: str,
        command: str,
        arg: str,
        success: bool,
        reply: str,
        latency_ms: float,
    ) -> None:
        self.filter_name = filter_name
        self.command = command
        self.arg = arg
        self.success = success
        self.reply = reply
        self.latency_ms = latency_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "filter": self.filter_name,
            "command": self.command,
            "arg": self.arg,
            "success": self.success,
            "reply": self.reply,
            "latency_ms": round(self.latency_ms, 2),
        }


class ZmqBatchResult:
    """Result of a batched scene switch — all commands sent sequentially."""

    __slots__ = ("results", "total_ms", "all_ok")

    def __init__(self, results: list[ZmqCommandResult], total_ms: float) -> None:
        self.results = results
        self.total_ms = total_ms
        self.all_ok = all(r.success for r in results)


class ZmqFilterClient:
    """Sends commands to FFmpeg's zmq filter.

    One socket per call (connect, send, recv, close). This avoids
    stale socket state across scene switches. The overhead (~1ms)
    is negligible vs the zmq filter's ~30ms round-trip.
    """

    def __init__(self, port: int = _ZMQ_DEFAULT_PORT, host: str = "127.0.0.1") -> None:
        self._address = f"tcp://{host}:{port}"

    def send_command(
        self, filter_name: str, command: str, arg: str,
    ) -> ZmqCommandResult:
        """Send a single command to a named filter. Returns result."""
        import zmq

        msg = f"{filter_name} {command} {arg}"
        t0 = time.monotonic()

        ctx = zmq.Context()
        sock = ctx.socket(zmq.REQ)
        sock.setsockopt(zmq.RCVTIMEO, 2000)
        sock.setsockopt(zmq.SNDTIMEO, 2000)
        sock.setsockopt(zmq.LINGER, 0)
        try:
            sock.connect(self._address)
            sock.send_string(msg)
            reply = sock.recv_string()
            latency = (time.monotonic() - t0) * 1000
            success = reply.startswith("0 ")
            if not success:
                logger.warning("[ZMQ] command failed: %s -> %s", msg, reply)
            return ZmqCommandResult(filter_name, command, arg, success, reply, latency)
        except zmq.ZMQError as exc:
            latency = (time.monotonic() - t0) * 1000
            logger.error("[ZMQ] send error: %s -> %s", msg, exc)
            return ZmqCommandResult(
                filter_name, command, arg, False, f"zmq_error: {exc}", latency,
            )
        finally:
            sock.close()
            ctx.term()

    def apply_scene(
        self,
        commands: list[tuple[str, str, str]],
    ) -> ZmqBatchResult:
        """Apply a batch of commands for a scene switch.

        Each tuple is (filter_name, command, arg).
        Sent sequentially as fast as possible for near-atomic application.
        At ~34ms per command, 6 sources = ~200ms — well within one frame
        evaluation window since overlay eval=frame re-reads params each frame.
        """
        t0 = time.monotonic()
        results: list[ZmqCommandResult] = []
        for filter_name, cmd, arg in commands:
            r = self.send_command(filter_name, cmd, arg)
            results.append(r)
            if not r.success:
                logger.error(
                    "[ZMQ] scene apply aborted at %s %s %s: %s",
                    filter_name, cmd, arg, r.reply,
                )
                break
        total_ms = (time.monotonic() - t0) * 1000
        batch = ZmqBatchResult(results, total_ms)
        if batch.all_ok:
            logger.info(
                "[ZMQ] scene applied: %d commands in %.1fms",
                len(results), total_ms,
            )
        return batch
