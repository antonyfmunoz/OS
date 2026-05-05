"""UMH Configuration — central config loaded from environment variables.

All configuration is read from env vars with sensible defaults.
No config files. No YAML. No complexity.
"""

from __future__ import annotations

import os


def _int(key: str, default: int) -> int:
    return int(os.environ.get(key, str(default)))


def _float(key: str, default: float) -> float:
    return float(os.environ.get(key, str(default)))


def _str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, str(default)).lower()
    return val in ("true", "1", "yes")


# API
API_PORT: int = _int("UMH_API_PORT", 8000)
API_HOST: str = _str("UMH_API_HOST", "127.0.0.1")

# Database
DB_PATH: str = _str("UMH_DB_PATH", "/opt/OS/data/runtime/tasks.sqlite")
APPROVAL_DB_PATH: str = _str("UMH_APPROVAL_DB_PATH", "/opt/OS/data/runtime/approvals.sqlite")

# Worker
WORKER_POLL_INTERVAL: float = _float("UMH_WORKER_INTERVAL", 2.0)
WORKER_AUTO_START: bool = _bool("UMH_WORKER_AUTO_START", True)
LEASE_TIMEOUT: float = _float("UMH_LEASE_TIMEOUT", 300.0)

# Retry
RETRY_MAX_ATTEMPTS: int = _int("UMH_RETRY_MAX_ATTEMPTS", 2)
RETRY_BACKOFF: float = _float("UMH_RETRY_BACKOFF", 5.0)

# Logging
LOG_DIR: str = _str("UMH_LOG_DIR", "/opt/OS/data/logs")
LOG_LEVEL: str = _str("UMH_LOG_LEVEL", "INFO")

# Task
MAX_STEPS: int = _int("UMH_MAX_STEPS", 10)
TASK_BACKEND: str = _str("UMH_TASK_BACKEND", "sqlite")
