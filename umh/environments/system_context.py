"""System context — runtime identity and environment configuration.

Provides the canonical context object for UMH operations: org identity,
user identity, active ventures, and portfolio scope. Loaded from
environment variables at runtime.

This is the UMH-owned extraction of umh/context.py.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SystemContext:
    """Runtime identity for a UMH session."""

    org_id: str
    user_id: str
    portfolio_id: str | None = None
    active_venture_id: str | None = None
    active_agent_id: str | None = None
    ventures: list[Any] = field(default_factory=list)


def load_ventures_from_env() -> list[Any]:
    """Load venture/company primitives from VENTURES_JSON env var."""
    raw = os.getenv("VENTURES_JSON", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


def load_context_from_env(
    env_file: str | Path | None = None,
) -> SystemContext:
    """Build a SystemContext from environment variables.

    If env_file is provided, loads it via dotenv first.
    Falls back to services/.env then eos/.env if they exist.
    """
    if env_file is not None:
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file)
        except ImportError:
            pass
    else:
        for candidate in (
            Path("/opt/OS/services/.env"),
            Path("/opt/OS/umh/.env"),
        ):
            if candidate.exists():
                try:
                    from dotenv import load_dotenv

                    load_dotenv(candidate)
                except ImportError:
                    pass
                break

    return SystemContext(
        org_id=os.environ.get("EOS_ORG_ID", "default"),
        user_id=os.environ.get("EOS_USER_ID", "default"),
        portfolio_id=os.environ.get("EOS_PORTFOLIO_ID"),
        ventures=load_ventures_from_env(),
    )


# Backward-compatible alias
EOSContext = SystemContext
