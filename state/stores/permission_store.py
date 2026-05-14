"""PermissionStore — canonical write API for cross_product_permissions and product_connections tables."""

import json
import uuid
from datetime import datetime, timezone

from state.storage.db import get_conn


class PermissionStore:

    def grant_permission(
        self,
        org_id: str,
        user_id: str,
        source_product: str,
        target_product: str,
        data_category: str,
    ) -> None:
        """Upsert a cross-product permission grant. Clears revoked_at on re-grant."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO cross_product_permissions
                  (id, user_id, source_product, target_product,
                   data_category, permitted, granted_at)
                VALUES (%s, %s::uuid, %s, %s, %s, true, %s)
                ON CONFLICT (user_id, source_product,
                             target_product, data_category)
                DO UPDATE SET
                  permitted  = true,
                  granted_at = EXCLUDED.granted_at,
                  revoked_at = NULL
                """,
                (
                    str(uuid.uuid4()),
                    user_id,
                    source_product,
                    target_product,
                    data_category,
                    datetime.now(timezone.utc),
                ),
            )

    def revoke_permission(
        self,
        org_id: str,
        user_id: str,
        source_product: str,
        target_product: str,
        data_category: str,
    ) -> None:
        """Revoke a previously granted permission."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                UPDATE cross_product_permissions
                SET permitted  = false,
                    revoked_at = %s
                WHERE user_id        = %s::uuid
                  AND source_product = %s
                  AND target_product = %s
                  AND data_category  = %s
                """,
                (
                    datetime.now(timezone.utc),
                    user_id,
                    source_product,
                    target_product,
                    data_category,
                ),
            )

    def register_product(
        self,
        org_id: str,
        user_id: str,
        product: str,
        connection_config: dict,
    ) -> None:
        """Upsert a product connection for a user."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                SELECT id FROM product_connections
                WHERE user_id = %s::uuid AND product = %s AND status = 'connected'
                """,
                (user_id, product),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE product_connections
                    SET connection_config = %s::jsonb
                    WHERE id = %s
                    """,
                    (json.dumps(connection_config), existing["id"]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO product_connections
                      (id, user_id, product, connection_config,
                       status, connected_at)
                    VALUES (%s, %s::uuid, %s, %s::jsonb, 'connected', %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        user_id,
                        product,
                        json.dumps(connection_config),
                        datetime.now(timezone.utc),
                    ),
                )
