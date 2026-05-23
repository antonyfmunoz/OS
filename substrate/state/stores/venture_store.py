"""VentureStore — canonical write API for the ventures table."""

import json
import uuid

from substrate.state.storage.db import get_conn, resolve_venture


class VentureStore:
    def save_venture(
        self,
        org_id: str,
        venture_id_slug: str,
        name: str,
        config: dict,
    ) -> None:
        """Upsert venture config. Updates if venture exists, inserts otherwise."""
        with get_conn(org_id) as cur:
            venture_uuid = resolve_venture(venture_id_slug)
            if venture_uuid:
                cur.execute(
                    """
                    UPDATE ventures
                    SET config_json = %s::jsonb
                    WHERE org_id = %s AND id = %s
                    """,
                    (json.dumps(config), org_id, venture_uuid),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO ventures (id, org_id, name, config_json)
                    VALUES (%s, %s, %s, %s::jsonb)
                    """,
                    (str(uuid.uuid4()), org_id, name, json.dumps(config)),
                )
