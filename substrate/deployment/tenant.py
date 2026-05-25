"""Tenant Management — multi-tenant isolation and configuration.

Each tenant (organization) gets:
  - Isolated reality model (canonical + instance)
  - Separate governance configuration
  - Independent budget tracking
  - Own execution history and traces

Tenant data is stored in per-tenant directories under data/umh/tenants/.
The default tenant ("default") is used for single-tenant deployments.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_ROOT = Path("data/umh/tenants")


@dataclass
class TenantConfig:
    """Configuration for a single tenant."""

    org_id: str
    org_name: str = ""
    owner_name: str = ""
    plan: str = "free"
    budget_limit_usd: float = 50.0
    max_signals_per_minute: int = 60
    max_observations: int = 5000
    governance_level: str = "standard"
    enabled: bool = True
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "org_name": self.org_name,
            "owner_name": self.owner_name,
            "plan": self.plan,
            "budget_limit_usd": self.budget_limit_usd,
            "max_signals_per_minute": self.max_signals_per_minute,
            "max_observations": self.max_observations,
            "governance_level": self.governance_level,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TenantConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TenantState:
    """Runtime state for a tenant."""

    org_id: str
    budget_spent_usd: float = 0.0
    signal_count: int = 0
    observation_count: int = 0
    trace_count: int = 0
    error_count: int = 0
    last_activity: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "budget_spent_usd": round(self.budget_spent_usd, 4),
            "signal_count": self.signal_count,
            "observation_count": self.observation_count,
            "trace_count": self.trace_count,
            "error_count": self.error_count,
            "last_activity": self.last_activity,
        }


class TenantManager:
    """Manages tenant lifecycle, isolation, and configuration."""

    def __init__(self, data_root: Path | str = _DATA_ROOT) -> None:
        self._root = Path(data_root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._configs: dict[str, TenantConfig] = {}
        self._states: dict[str, TenantState] = {}
        self._load_all()

    def _tenant_dir(self, org_id: str) -> Path:
        return self._root / org_id

    def _config_path(self, org_id: str) -> Path:
        return self._tenant_dir(org_id) / "config.json"

    def _state_path(self, org_id: str) -> Path:
        return self._tenant_dir(org_id) / "state.json"

    def _load_all(self) -> None:
        if not self._root.exists():
            return
        for tenant_dir in self._root.iterdir():
            if tenant_dir.is_dir():
                config_path = tenant_dir / "config.json"
                if config_path.exists():
                    try:
                        data = json.loads(config_path.read_text())
                        config = TenantConfig.from_dict(data)
                        self._configs[config.org_id] = config
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning("failed to load tenant %s: %s", tenant_dir.name, e)

                state_path = tenant_dir / "state.json"
                if state_path.exists():
                    try:
                        data = json.loads(state_path.read_text())
                        self._states[tenant_dir.name] = TenantState(
                            org_id=tenant_dir.name, **{
                                k: v for k, v in data.items()
                                if k in TenantState.__dataclass_fields__ and k != "org_id"
                            }
                        )
                    except (json.JSONDecodeError, KeyError):
                        pass

    def create_tenant(self, config: TenantConfig) -> TenantConfig:
        """Create a new tenant with isolated data directories."""
        tenant_dir = self._tenant_dir(config.org_id)
        tenant_dir.mkdir(parents=True, exist_ok=True)

        for subdir in ["reality_model", "traces", "memory", "audit"]:
            (tenant_dir / subdir).mkdir(exist_ok=True)

        self._config_path(config.org_id).write_text(
            json.dumps(config.to_dict(), indent=2)
        )

        state = TenantState(org_id=config.org_id)
        self._state_path(config.org_id).write_text(
            json.dumps(state.to_dict(), indent=2)
        )

        self._configs[config.org_id] = config
        self._states[config.org_id] = state

        logger.info("tenant created: %s (%s)", config.org_id, config.org_name)
        return config

    def get_config(self, org_id: str) -> TenantConfig | None:
        return self._configs.get(org_id)

    def get_state(self, org_id: str) -> TenantState | None:
        return self._states.get(org_id)

    def list_tenants(self) -> list[TenantConfig]:
        return list(self._configs.values())

    def update_config(self, org_id: str, updates: dict[str, Any]) -> TenantConfig | None:
        config = self._configs.get(org_id)
        if not config:
            return None

        for key, value in updates.items():
            if hasattr(config, key) and key != "org_id":
                setattr(config, key, value)

        self._config_path(org_id).write_text(
            json.dumps(config.to_dict(), indent=2)
        )
        return config

    def record_activity(self, org_id: str, signal_count: int = 1, cost_usd: float = 0.0) -> None:
        state = self._states.get(org_id)
        if not state:
            state = TenantState(org_id=org_id)
            self._states[org_id] = state

        state.signal_count += signal_count
        state.budget_spent_usd += cost_usd
        state.trace_count += 1
        state.last_activity = datetime.now(timezone.utc).isoformat()

    def check_limits(self, org_id: str) -> dict[str, bool]:
        """Check if tenant is within configured limits."""
        config = self._configs.get(org_id)
        state = self._states.get(org_id)

        if not config or not state:
            return {"within_limits": True, "tenant_found": False}

        return {
            "within_limits": (
                state.budget_spent_usd < config.budget_limit_usd
                and state.observation_count < config.max_observations
                and config.enabled
            ),
            "tenant_found": True,
            "budget_ok": state.budget_spent_usd < config.budget_limit_usd,
            "observations_ok": state.observation_count < config.max_observations,
            "enabled": config.enabled,
        }

    def disable_tenant(self, org_id: str) -> bool:
        config = self._configs.get(org_id)
        if not config:
            return False
        config.enabled = False
        self._config_path(org_id).write_text(
            json.dumps(config.to_dict(), indent=2)
        )
        return True

    def tenant_data_path(self, org_id: str, subdir: str = "") -> Path:
        """Get the isolated data path for a tenant."""
        base = self._tenant_dir(org_id)
        if subdir:
            return base / subdir
        return base

    def save_states(self) -> None:
        """Persist all tenant states to disk."""
        for org_id, state in self._states.items():
            try:
                self._state_path(org_id).write_text(
                    json.dumps(state.to_dict(), indent=2)
                )
            except OSError as e:
                logger.warning("failed to save state for %s: %s", org_id, e)
