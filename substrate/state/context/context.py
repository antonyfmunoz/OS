from dataclasses import dataclass, field
import json
import os
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_REPO_ROOT / ".env")


@dataclass
class SubstrateContext:
    org_id: str
    user_id: str
    portfolio_id: str | None = None
    active_venture_id: str | None = None
    active_agent_id: str | None = None
    ventures: list = field(default_factory=list)


def load_ventures_from_env() -> list:
    """
    Load venture/company primitives from environment.
    Falls back to empty list if not configured.
    Format: VENTURES_JSON env var containing JSON array.
    """
    raw = os.getenv("VENTURES_JSON", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


def load_context_from_env() -> SubstrateContext:
    return SubstrateContext(
        org_id=os.environ.get("UMH_ORG_ID") or os.environ["EOS_ORG_ID"],
        user_id=os.environ.get("UMH_USER_ID") or os.environ["EOS_USER_ID"],
        portfolio_id=os.environ.get("UMH_PORTFOLIO_ID") or os.environ.get("EOS_PORTFOLIO_ID"),
        ventures=load_ventures_from_env(),
    )


def try_load_context_from_env() -> SubstrateContext | None:
    """Non-fatal loader — returns None if identity env is missing."""
    org = os.environ.get("UMH_ORG_ID") or os.environ.get("EOS_ORG_ID")
    user = os.environ.get("UMH_USER_ID") or os.environ.get("EOS_USER_ID")
    if not org or not user:
        return None
    return SubstrateContext(
        org_id=org,
        user_id=user,
        portfolio_id=os.environ.get("UMH_PORTFOLIO_ID") or os.environ.get("EOS_PORTFOLIO_ID"),
        ventures=load_ventures_from_env(),
    )


# Backward compatibility
EntrepreneurOSContext = SubstrateContext
