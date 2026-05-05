"""
control_plane.py — Unified control plane composing the orchestrator with
persistent agents.

Design:
  * We do NOT modify scripts/orchestrator.py. Instead, ControlPlane wraps
    an Orchestrator instance, registers jobs, and runs its own tiny loop
    that ticks persistent agents on their interval.
  * Persistent-agent ticks share the orchestrator's lifecycle: start()
    brings both up, stop() shuts both down, and a single SIGINT handler
    covers both.
  * Every control-plane action is written to data/control_plane_log.jsonl
    so observability picks it up without any extra wiring.

Usage:
    from core.control_plane import ControlPlane

    cp = ControlPlane()
    cp.start()
    # ... cp.wait() or cp.loop_until_signal() ...
    cp.stop()

CLI:
    python3 -m core.control_plane start
    python3 -m core.control_plane start --once
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = "/opt/OS"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.persistent_agents import PersistentAgent, default_agents  # noqa: E402
from scripts.orchestrator import (  # noqa: E402
    Orchestrator,
    build_default_jobs,
    _install_signal_handlers,
)


DATA_DIR = Path(_REPO_ROOT) / "data"
CONTROL_LOG = DATA_DIR / "control_plane_log.jsonl"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _log(event: str, **fields: Any) -> None:
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
        }
        entry.update(fields)
        with CONTROL_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Control plane
# ---------------------------------------------------------------------------


@dataclass
class ControlPlaneState:
    started: bool = False
    agent_ticks: int = 0
    agent_tick_failures: int = 0
    last_agent_tick_at: str | None = None
    agents_registered: list[str] = field(default_factory=list)


class ControlPlane:
    """Wraps Orchestrator + PersistentAgents behind one lifecycle."""

    def __init__(
        self,
        *,
        max_concurrent: int = 2,
        max_queue: int = 100,
        verbose: bool = False,
        register_default_jobs: bool = True,
        register_default_agents: bool = True,
    ) -> None:
        self.verbose = verbose
        self.state = ControlPlaneState()
        self.orchestrator = Orchestrator(
            max_concurrent=max_concurrent,
            max_queue=max_queue,
            verbose=verbose,
        )
        self._agents: list[PersistentAgent] = []
        self._agent_loop_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        if register_default_jobs:
            for j in build_default_jobs():
                try:
                    self.orchestrator.register(j)
                except Exception as e:
                    _log("job_register_failed", job=j.id, error=str(e))

        if register_default_agents:
            self._agents = default_agents()
            self.state.agents_registered = [a.name for a in self._agents]

    # ── Registration passthroughs ───────────────────────────────────────

    def register_agent(self, agent: PersistentAgent) -> None:
        self._agents.append(agent)
        self.state.agents_registered.append(agent.name)
        _log("agent_registered", agent=agent.name)

    def register_job(self, job: Any) -> None:
        self.orchestrator.register(job)

    def agents(self) -> list[PersistentAgent]:
        return list(self._agents)

    # ── Lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.state.started:
            return
        self._stop_event.clear()
        self.orchestrator.start()
        self._agent_loop_thread = threading.Thread(
            target=self._agent_loop,
            name="cp-agent-loop",
            daemon=True,
        )
        self._agent_loop_thread.start()
        self.state.started = True
        _log(
            "control_plane_started",
            jobs=len(self.orchestrator.jobs()),
            agents=[a.name for a in self._agents],
        )

    def stop(self) -> None:
        if not self.state.started:
            return
        self._stop_event.set()
        if self._agent_loop_thread is not None:
            self._agent_loop_thread.join(timeout=5.0)
        # Stop event agent (watchdog) FIRST — its C++ observer thread
        # causes 'terminate called without an active exception' (SIGABRT)
        # if it outlives the Python interpreter shutdown.
        try:
            self.orchestrator.events.stop(timeout=3.0)
        except Exception:
            pass
        self.orchestrator.stop()
        self.state.started = False
        _log("control_plane_stopped")

    def loop_until_signal(self, save_every: float = 5.0) -> None:
        """Block until stop() or SIGINT. Saves orchestrator state periodically."""
        try:
            while self.state.started and not self._stop_event.is_set():
                time.sleep(save_every)
                self.orchestrator.save_state()
        except KeyboardInterrupt:
            self.stop()

    # ── Agent loop ───────────────────────────────────────────────────────

    def _agent_loop(self) -> None:
        """Tick each persistent agent whenever its interval elapses."""
        # Initial tick so state files exist immediately
        self._tick_all(force=True)
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=10.0)
            if self._stop_event.is_set():
                break
            try:
                self._tick_all(force=False)
            except Exception as e:
                _log("agent_loop_error", error=str(e))

    def _tick_all(self, *, force: bool) -> None:
        for agent in self._agents:
            if not force and not agent.should_tick():
                continue
            try:
                result = agent.tick()
            except Exception as e:
                self.state.agent_tick_failures += 1
                _log("agent_tick_exception", agent=agent.name, error=str(e))
                continue
            self.state.agent_ticks += 1
            self.state.last_agent_tick_at = datetime.now(timezone.utc).isoformat()
            if not result.ok:
                self.state.agent_tick_failures += 1
            _log(
                "agent_ticked",
                agent=agent.name,
                ok=result.ok,
                summary=result.summary,
                alerts=result.alerts,
            )

    # ── Status ───────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        return {
            "started": self.state.started,
            "orchestrator": self.orchestrator.status(),
            "agents": [
                {
                    "name": a.name,
                    "interval_sec": a.interval_sec,
                    "state": a.state(),
                }
                for a in self._agents
            ],
            "agent_ticks": self.state.agent_ticks,
            "agent_tick_failures": self.state.agent_tick_failures,
            "last_agent_tick_at": self.state.last_agent_tick_at,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_start(args: argparse.Namespace) -> int:
    cp = ControlPlane(
        max_concurrent=args.max_concurrent,
        max_queue=args.max_queue,
        verbose=args.verbose,
    )

    # Install signal handlers — delegate orchestrator's handlers, plus cp.stop
    def _handler(signum: int, frame: Any) -> None:
        print(f"\n[control_plane] signal {signum} — stopping")
        cp.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handler)
        except ValueError:
            pass

    cp.start()
    print(
        f"[control_plane] started  "
        f"jobs={len(cp.orchestrator.jobs())}  "
        f"agents={[a.name for a in cp.agents()]}"
    )
    print("[control_plane] Ctrl-C to stop")

    if args.once:
        # One scheduler tick, one agent tick, save, stop.
        # Stop the watchdog observer early — its C++ thread causes
        # SIGABRT ('terminate called without an active exception')
        # if it outlives the Python interpreter shutdown.
        cp.orchestrator.scheduler.tick_once()
        cp._tick_all(force=True)
        try:
            cp.orchestrator.events.stop(timeout=3.0)
        except Exception:
            pass
        time.sleep(1.0)
        cp.orchestrator.save_state()
        cp.stop()
        return 0

    try:
        cp.loop_until_signal()
    except KeyboardInterrupt:
        cp.stop()
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    cp = ControlPlane(register_default_jobs=True, register_default_agents=True)
    print(json.dumps(cp.status(), indent=2, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="control_plane",
        description="EOS control plane — orchestrator + persistent agents.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start", help="start control plane in foreground")
    p_start.add_argument("--max-concurrent", type=int, default=2)
    p_start.add_argument("--max-queue", type=int, default=100)
    p_start.add_argument("--once", action="store_true")
    p_start.add_argument("-v", "--verbose", action="store_true")
    p_start.set_defaults(func=_cmd_start)

    p_status = sub.add_parser("status", help="show live status (without running)")
    p_status.set_defaults(func=_cmd_status)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
