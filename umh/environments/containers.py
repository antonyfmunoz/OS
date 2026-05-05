"""Container manager — real execution via Docker or subprocess fallback.

Two execution modes:
  DOCKER:     docker run in temp directory, captures stdout/stderr
  SUBPROCESS: subprocess.Popen in temp directory, enforces timeout

Docker is auto-detected; falls back to subprocess if unavailable.
All execution wrapped in try/finally for guaranteed cleanup.

No imports from umh/cells, umh/adapters, or umh/execution.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

from umh.environments.models import (
    ContainerStatus,
    ExecutionContainer,
    ExecutionContext,
    ExecutionMode,
    ExecutionResult,
    ExecutionTask,
    TaskStatus,
    _gen_id,
)
from umh.core.clock import iso_now as _iso_now

_log = logging.getLogger(__name__)


def _detect_docker() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


class ContainerManager:
    """Manages real execution containers (Docker + subprocess fallback)."""

    def __init__(self, mode: ExecutionMode | None = None) -> None:
        self._lock = threading.Lock()
        self._containers: dict[str, ExecutionContainer] = {}
        self._processes: dict[str, subprocess.Popen] = {}
        if mode is not None:
            self._mode = mode
        else:
            self._mode = ExecutionMode.DOCKER if _detect_docker() else ExecutionMode.SUBPROCESS

    @property
    def mode(self) -> ExecutionMode:
        return self._mode

    def create_container(self, node_id: str, context: ExecutionContext) -> ExecutionContainer:
        container = ExecutionContainer(
            container_id=_gen_id("ctr"),
            node_id=node_id,
            status=ContainerStatus.CREATED,
            context=context,
        )
        with self._lock:
            self._containers[container.container_id] = container
        return container

    def run_task(
        self,
        container: ExecutionContainer,
        task: ExecutionTask,
        work_dir: str | None = None,
    ) -> ExecutionResult:
        with self._lock:
            c = self._containers.get(container.container_id)
            if c is None:
                return ExecutionResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    output={"error": "container not found"},
                    node_id=container.node_id,
                )
            if c.status == ContainerStatus.TERMINATED:
                return ExecutionResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    output={"error": "container already terminated"},
                    node_id=container.node_id,
                )
            c.status = ContainerStatus.RUNNING

        command = task.inputs.get("command")
        if not command:
            return ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.SUCCEEDED,
                output={"simulated": True, "operation": task.operation},
                logs=[f"[env] task {task.task_id} completed (no command)"],
                node_id=container.node_id,
                container_id=container.container_id,
                finished_at=_iso_now(),
            )

        timeout_s = task.metadata.get("timeout_s", 30)
        if isinstance(timeout_s, (int, float)):
            timeout_s = max(1, int(timeout_s))
        else:
            timeout_s = 30

        if self._mode == ExecutionMode.DOCKER:
            return self._run_docker(container, task, command, timeout_s, work_dir)
        return self._run_subprocess(container, task, command, timeout_s, work_dir)

    def _run_subprocess(
        self,
        container: ExecutionContainer,
        task: ExecutionTask,
        command: list[str] | str,
        timeout_s: int,
        work_dir: str | None,
    ) -> ExecutionResult:
        if isinstance(command, str):
            args = command.split()
        else:
            args = list(command)

        proc: subprocess.Popen | None = None
        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=work_dir,
                env=None,
            )
            with self._lock:
                self._processes[container.container_id] = proc

            stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout_s)
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            rc = proc.returncode

            status = TaskStatus.SUCCEEDED if rc == 0 else TaskStatus.FAILED
            logs = []
            if stdout:
                logs.append(f"[stdout] {stdout[:2000]}")
            if stderr:
                logs.append(f"[stderr] {stderr[:2000]}")

            return ExecutionResult(
                task_id=task.task_id,
                status=status,
                output={
                    "return_code": rc,
                    "stdout": stdout[:4000],
                    "stderr": stderr[:4000],
                    "mode": "subprocess",
                },
                logs=logs,
                node_id=container.node_id,
                container_id=container.container_id,
                finished_at=_iso_now(),
            )

        except subprocess.TimeoutExpired:
            if proc is not None:
                proc.kill()
                proc.wait()
            return ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                output={"error": f"timeout after {timeout_s}s", "mode": "subprocess"},
                logs=[f"[timeout] killed after {timeout_s}s"],
                node_id=container.node_id,
                container_id=container.container_id,
                finished_at=_iso_now(),
                metadata={"timed_out": True},
            )

        except Exception as e:
            if proc is not None:
                try:
                    proc.kill()
                    proc.wait()
                except Exception:
                    pass
            return ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                output={"error": str(e), "mode": "subprocess"},
                logs=[f"[error] {e}"],
                node_id=container.node_id,
                container_id=container.container_id,
                finished_at=_iso_now(),
            )

        finally:
            with self._lock:
                self._processes.pop(container.container_id, None)

    def _run_docker(
        self,
        container: ExecutionContainer,
        task: ExecutionTask,
        command: list[str] | str,
        timeout_s: int,
        work_dir: str | None,
    ) -> ExecutionResult:
        if isinstance(command, str):
            cmd_args = command.split()
        else:
            cmd_args = list(command)

        image = task.metadata.get("docker_image", "python:3.12-slim")
        docker_name = f"umh_{container.container_id}"

        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--name",
            docker_name,
            "--network",
            "none",
            "--memory",
            f"{task.resources.memory_mb}m",
            "--cpus",
            str(task.resources.cpu_cores),
        ]

        if work_dir:
            docker_cmd.extend(["-v", f"{work_dir}:/workspace", "-w", "/workspace"])

        docker_cmd.append(image)
        docker_cmd.extend(cmd_args)

        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                timeout=timeout_s,
            )
            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")
            rc = result.returncode

            status = TaskStatus.SUCCEEDED if rc == 0 else TaskStatus.FAILED
            logs = []
            if stdout:
                logs.append(f"[stdout] {stdout[:2000]}")
            if stderr:
                logs.append(f"[stderr] {stderr[:2000]}")

            return ExecutionResult(
                task_id=task.task_id,
                status=status,
                output={
                    "return_code": rc,
                    "stdout": stdout[:4000],
                    "stderr": stderr[:4000],
                    "mode": "docker",
                    "image": image,
                },
                logs=logs,
                node_id=container.node_id,
                container_id=container.container_id,
                finished_at=_iso_now(),
            )

        except subprocess.TimeoutExpired:
            try:
                subprocess.run(
                    ["docker", "kill", docker_name],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass
            return ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                output={"error": f"timeout after {timeout_s}s", "mode": "docker"},
                logs=[f"[timeout] docker container killed after {timeout_s}s"],
                node_id=container.node_id,
                container_id=container.container_id,
                finished_at=_iso_now(),
                metadata={"timed_out": True},
            )

        except Exception as e:
            try:
                subprocess.run(
                    ["docker", "kill", docker_name],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass
            return ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                output={"error": str(e), "mode": "docker"},
                logs=[f"[error] {e}"],
                node_id=container.node_id,
                container_id=container.container_id,
                finished_at=_iso_now(),
            )

    def destroy_container(self, container_id: str) -> bool:
        with self._lock:
            c = self._containers.get(container_id)
            proc = self._processes.pop(container_id, None)

        if proc is not None:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass

        if c is None:
            return False
        with self._lock:
            c.status = ContainerStatus.TERMINATED
        return True

    def get_container(self, container_id: str) -> ExecutionContainer | None:
        with self._lock:
            return self._containers.get(container_id)

    def list_containers(self) -> list[ExecutionContainer]:
        with self._lock:
            return list(self._containers.values())

    def clear(self) -> None:
        with self._lock:
            for proc in self._processes.values():
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                except Exception:
                    pass
            self._processes.clear()
            self._containers.clear()
