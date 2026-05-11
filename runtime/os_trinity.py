"""
OSTrinity — OS Trinity harness layer.

Manages three cross-product concerns:
  1. cross_product_permissions  — user-granted data sharing between products
  2. user_intelligence_profiles — harness-level user profile (survives product boundaries)
  3. product_connections        — registry of which products are connected for a user

Default posture: all products are siloed. Zero data flows between products
without an explicit, revocable user grant.

Usage:
    from runtime.context import load_context_from_env
    from runtime.os_trinity import OSTrinity

    ctx     = load_context_from_env()
    trinity = OSTrinity(ctx)

    trinity.grant_permission(ctx.user_id, 'lyfeos', 'eos', 'health')
    ok = trinity.check_permission(ctx.user_id, 'lyfeos', 'eos', 'health')  # True
    print(trinity.format_permissions_summary(ctx.user_id))
"""

import json
import uuid
from datetime import datetime, timezone

from runtime.context import EOSContext


VALID_PRODUCTS: list[str] = ['lyfeos', 'creatorOS', 'eos']
VALID_CATEGORIES: list[str] = [
    'health', 'content_performance', 'finance',
    'goals', 'audience', 'habits', 'calendar',
    'tasks', 'all',
]


class OSTrinity:
    """
    Harness-level data sharing, user intelligence, and product connection registry.

    All methods are safe to call at any time — DB failures are caught and logged
    without crashing the caller. Default for permission checks is always DENIED.
    """

    def __init__(self, ctx: EOSContext) -> None:
        self.ctx = ctx

    # ─── Cross-product permissions ────────────────────────────────────────────

    def grant_permission(
        self,
        user_id: str,
        source_product: str,
        target_product: str,
        data_category: str,
    ) -> bool:
        """
        User explicitly grants target_product permission to read
        source_product data in data_category.

        Upserts to cross_product_permissions. Clears revoked_at on re-grant.
        Returns True on success.
        """
        from runtime.db import get_conn
        try:
            with get_conn(self.ctx.org_id) as cur:
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
            return True
        except Exception as e:
            print(f"[OSTrinity] grant_permission failed: {e}")
            return False

    def revoke_permission(
        self,
        user_id: str,
        source_product: str,
        target_product: str,
        data_category: str,
    ) -> bool:
        """
        Revoke a previously granted permission.
        Sets permitted=false and stamps revoked_at.
        Returns True on success.
        """
        from runtime.db import get_conn
        try:
            with get_conn(self.ctx.org_id) as cur:
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
            return True
        except Exception as e:
            print(f"[OSTrinity] revoke_permission failed: {e}")
            return False

    def check_permission(
        self,
        user_id: str,
        source_product: str,
        target_product: str,
        data_category: str,
    ) -> bool:
        """
        Returns True ONLY if an explicit, un-revoked permission exists.
        Default is always DENIED — no implicit cross-product data access.
        """
        from runtime.db import get_conn
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT permitted
                    FROM cross_product_permissions
                    WHERE user_id        = %s::uuid
                      AND source_product = %s
                      AND target_product = %s
                      AND data_category  = %s
                      AND revoked_at     IS NULL
                    """,
                    (user_id, source_product, target_product, data_category),
                )
                row = cur.fetchone()
                return bool(row and row['permitted'])
        except Exception as e:
            print(f"[OSTrinity] check_permission failed: {e}")
            return False  # fail closed — always deny on error

    def get_user_permissions(self, user_id: str) -> list[dict]:
        """
        Return all permission records for this user (active and revoked).
        """
        from runtime.db import get_conn
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT source_product, target_product,
                           data_category, permitted, granted_at
                    FROM cross_product_permissions
                    WHERE user_id = %s::uuid
                    ORDER BY granted_at DESC
                    """,
                    (user_id,),
                )
                return [
                    {
                        'source':     row['source_product'],
                        'target':     row['target_product'],
                        'category':   row['data_category'],
                        'permitted':  bool(row['permitted']),
                        'granted_at': (
                            row['granted_at'].isoformat()
                            if row['granted_at'] else None
                        ),
                    }
                    for row in cur.fetchall()
                ]
        except Exception as e:
            print(f"[OSTrinity] get_user_permissions failed: {e}")
            return []

    # ─── User intelligence profile ────────────────────────────────────────────

    def update_intelligence_profile(
        self,
        user_id: str,
        updates: dict,
    ) -> bool:
        """
        Upsert the harness-level user intelligence profile.

        Only fields present in `updates` are written — all others are
        preserved. JSONB fields are fully replaced when included; scalars
        (north_star) are replaced directly.

        Returns True on success.
        """
        from runtime.db import get_conn

        def _j(val):
            """Serialize to JSON string for JSONB columns, or None to skip."""
            return json.dumps(val) if val is not None else None

        try:
            with get_conn(self.ctx.org_id) as cur:
                # Check for existing row
                cur.execute(
                    "SELECT id FROM user_intelligence_profiles WHERE user_id = %s::uuid",
                    (user_id,),
                )
                existing = cur.fetchone()

                if existing:
                    cur.execute(
                        """
                        UPDATE user_intelligence_profiles
                        SET
                          communication_style     = COALESCE(%s::jsonb,
                                                    communication_style),
                          peak_performance_windows= COALESCE(%s::jsonb,
                                                    peak_performance_windows),
                          decision_patterns       = COALESCE(%s::jsonb,
                                                    decision_patterns),
                          content_strengths       = COALESCE(%s::jsonb,
                                                    content_strengths),
                          learning_style          = COALESCE(%s::jsonb,
                                                    learning_style),
                          stress_indicators       = COALESCE(%s::jsonb,
                                                    stress_indicators),
                          north_star              = COALESCE(%s,
                                                    north_star),
                          cross_product_insights  = COALESCE(%s::jsonb,
                                                    cross_product_insights),
                          last_updated            = %s
                        WHERE user_id = %s::uuid
                        """,
                        (
                            _j(updates.get('communication_style'))
                            if 'communication_style' in updates else None,
                            _j(updates.get('peak_performance_windows'))
                            if 'peak_performance_windows' in updates else None,
                            _j(updates.get('decision_patterns'))
                            if 'decision_patterns' in updates else None,
                            _j(updates.get('content_strengths'))
                            if 'content_strengths' in updates else None,
                            _j(updates.get('learning_style'))
                            if 'learning_style' in updates else None,
                            _j(updates.get('stress_indicators'))
                            if 'stress_indicators' in updates else None,
                            updates.get('north_star'),
                            _j(updates.get('cross_product_insights'))
                            if 'cross_product_insights' in updates else None,
                            datetime.now(timezone.utc),
                            user_id,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO user_intelligence_profiles
                          (id, user_id,
                           communication_style, peak_performance_windows,
                           decision_patterns, content_strengths,
                           learning_style, stress_indicators,
                           north_star, cross_product_insights,
                           last_updated)
                        VALUES (%s, %s::uuid,
                                %s::jsonb, %s::jsonb,
                                %s::jsonb, %s::jsonb,
                                %s::jsonb, %s::jsonb,
                                %s, %s::jsonb,
                                %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            user_id,
                            json.dumps(updates.get('communication_style', {})),
                            json.dumps(updates.get('peak_performance_windows', [])),
                            json.dumps(updates.get('decision_patterns', {})),
                            json.dumps(updates.get('content_strengths', {})),
                            json.dumps(updates.get('learning_style', {})),
                            json.dumps(updates.get('stress_indicators', {})),
                            updates.get('north_star', ''),
                            json.dumps(updates.get('cross_product_insights', {})),
                            datetime.now(timezone.utc),
                        ),
                    )
            return True
        except Exception as e:
            print(f"[OSTrinity] update_intelligence_profile failed: {e}")
            return False

    def get_intelligence_profile(self, user_id: str) -> dict | None:
        """
        Load the harness-level intelligence profile for a user.
        Returns None if no profile has been created yet.
        """
        from runtime.db import get_conn
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT communication_style, peak_performance_windows,
                           decision_patterns, content_strengths,
                           learning_style, stress_indicators,
                           north_star, cross_product_insights, last_updated
                    FROM user_intelligence_profiles
                    WHERE user_id = %s::uuid
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None

                def _parse(val):
                    if val is None:
                        return {}
                    if isinstance(val, (dict, list)):
                        return val
                    try:
                        return json.loads(val)
                    except Exception:
                        return {}

                return {
                    'communication_style':      _parse(row['communication_style']),
                    'peak_performance_windows': _parse(row['peak_performance_windows']),
                    'decision_patterns':        _parse(row['decision_patterns']),
                    'content_strengths':        _parse(row['content_strengths']),
                    'learning_style':           _parse(row['learning_style']),
                    'stress_indicators':        _parse(row['stress_indicators']),
                    'north_star':               row['north_star'] or '',
                    'cross_product_insights':   _parse(row['cross_product_insights']),
                    'last_updated': (
                        row['last_updated'].isoformat()
                        if row['last_updated'] else None
                    ),
                }
        except Exception as e:
            print(f"[OSTrinity] get_intelligence_profile failed: {e}")
            return None

    def sync_from_user_model(self, user_id: str) -> bool:
        """
        Read the EOS-specific user_profiles row and promote relevant fields
        to the harness-level user_intelligence_profiles table.

        Syncs: communication_style, north_star, decision_patterns.
        Returns True if sync succeeded (even partially).
        """
        from runtime.db import get_conn
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT profile_json FROM user_profiles
                    WHERE user_id = %s AND org_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (user_id, self.ctx.org_id),
                )
                row = cur.fetchone()
        except Exception as e:
            print(f"[OSTrinity] sync_from_user_model query failed: {e}")
            return False

        if not row:
            return False

        pj = row['profile_json']
        profile: dict = (
            pj if isinstance(pj, dict)
            else json.loads(pj or '{}')
        )

        updates: dict = {}
        if profile.get('communication_style'):
            updates['communication_style'] = {'eos': profile['communication_style']}
        if profile.get('north_star'):
            updates['north_star'] = profile['north_star']
        if profile.get('decision_style'):
            updates['decision_patterns'] = {'style': profile['decision_style']}

        if not updates:
            return False

        return self.update_intelligence_profile(user_id, updates)

    # ─── Product connections ──────────────────────────────────────────────────

    def register_product(
        self,
        user_id: str,
        product: str,
        connection_config: dict,
    ) -> bool:
        """
        Register a product as connected for this user.
        Safe to call repeatedly — does not create duplicates.
        Returns True on success.
        """
        from runtime.db import get_conn
        try:
            with get_conn(self.ctx.org_id) as cur:
                # Check if already connected
                cur.execute(
                    """
                    SELECT id FROM product_connections
                    WHERE user_id = %s::uuid AND product = %s AND status = 'connected'
                    """,
                    (user_id, product),
                )
                existing = cur.fetchone()
                if existing:
                    # Update config silently
                    cur.execute(
                        """
                        UPDATE product_connections
                        SET connection_config = %s::jsonb
                        WHERE id = %s
                        """,
                        (json.dumps(connection_config), existing['id']),
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
            return True
        except Exception as e:
            print(f"[OSTrinity] register_product failed: {e}")
            return False

    def get_connected_products(self, user_id: str) -> list[str]:
        """Return list of product names currently connected for this user."""
        from runtime.db import get_conn
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT product FROM product_connections
                    WHERE user_id = %s::uuid AND status = 'connected'
                    """,
                    (user_id,),
                )
                return [row['product'] for row in cur.fetchall()]
        except Exception as e:
            print(f"[OSTrinity] get_connected_products failed: {e}")
            return []

    # ─── Summary ──────────────────────────────────────────────────────────────

    def format_permissions_summary(self, user_id: str) -> str:
        """
        Human-readable OS Trinity status for Telegram /trinity command.
        """
        perms    = self.get_user_permissions(user_id)
        products = self.get_connected_products(user_id)
        profile  = self.get_intelligence_profile(user_id)

        lines = ['OS Trinity Status\n']
        lines.append(
            f'Connected products: {", ".join(products) or "EOS only"}'
        )

        if perms:
            active = [p for p in perms if p['permitted']]
            if active:
                lines.append('\nActive permissions:')
                for p in active:
                    lines.append(
                        f'  {p["source"]} -> {p["target"]} ({p["category"]})'
                    )
            else:
                lines.append('\nNo active cross-product permissions')
        else:
            lines.append('\nNo cross-product permissions set')
            lines.append('Default: all products siloed')

        if profile:
            lines.append('\nHarness profile: active')
            ns = profile.get('north_star', 'not set')
            lines.append(f'North star: {ns[:80]}')
        else:
            lines.append('\nHarness profile: not yet created')

        return '\n'.join(lines)
