"""PreferenceStore — canonical write API for the model_preferences table."""

import json

from state.storage.db import get_conn


class PreferenceStore:
    def ensure_defaults(self, org_id: str) -> None:
        """Insert default preferences if no row exists for this org."""
        with get_conn(org_id) as cur:
            cur.execute(
                "INSERT INTO model_preferences (org_id, cost_mode, prefer_local) "
                "VALUES (%s, 'auto', false) "
                "ON CONFLICT (org_id) DO NOTHING",
                (org_id,),
            )

    def set_field(
        self,
        org_id: str,
        field: str,
        value: object,
    ) -> None:
        """Update a single preference field. Caller validates field name."""
        _ALLOWED = {
            "cost_mode",
            "prefer_local",
            "session_override",
            "per_task_overrides",
        }
        if field not in _ALLOWED:
            raise ValueError(f"field must be one of {_ALLOWED}")

        if field == "per_task_overrides":
            sql = (
                f"UPDATE model_preferences SET {field} = %s::jsonb, "
                "updated_at = NOW() WHERE org_id = %s"
            )
            val = json.dumps(value) if isinstance(value, dict) else value
        else:
            sql = f"UPDATE model_preferences SET {field} = %s, updated_at = NOW() WHERE org_id = %s"
            val = value

        with get_conn(org_id) as cur:
            cur.execute(sql, (val, org_id))
