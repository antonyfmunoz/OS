"""ProfileStore — canonical write API for human_profiles, user_profiles, user_intelligence_profiles."""

import json
import uuid
from datetime import datetime, timezone

from state.storage.db import get_conn


def _j(val: object) -> str | None:
    """JSON-serialize if not None."""
    return json.dumps(val) if val is not None else None


class ProfileStore:

    def upsert_human_profile(
        self,
        org_id: str,
        username: str,
        venture_uuid: str,
        profile: dict,
    ) -> None:
        """Upsert a human behavioral profile by (org_id, username)."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO human_profiles (org_id, username, venture_id, profile_json, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (org_id, username)
                DO UPDATE SET venture_id   = EXCLUDED.venture_id,
                              profile_json = EXCLUDED.profile_json,
                              updated_at   = EXCLUDED.updated_at
                """,
                (org_id, username, venture_uuid, json.dumps(profile),
                 datetime.now(timezone.utc).isoformat()),
            )

    def upsert_user_profile(
        self,
        org_id: str,
        user_id: str,
        profile: dict,
    ) -> None:
        """Upsert a user communication profile by (user_id, org_id)."""
        with get_conn(org_id) as cur:
            cur.execute(
                """
                INSERT INTO user_profiles (user_id, org_id, profile_json, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (user_id, org_id)
                DO UPDATE SET
                    profile_json = EXCLUDED.profile_json,
                    updated_at   = NOW()
                """,
                (user_id, org_id, json.dumps(profile)),
            )

    def upsert_intelligence_profile(
        self,
        org_id: str,
        user_id: str,
        updates: dict,
    ) -> None:
        """Upsert a user intelligence profile with COALESCE merge semantics."""
        with get_conn(org_id) as cur:
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
                      communication_style     = COALESCE(%s::jsonb, communication_style),
                      peak_performance_windows= COALESCE(%s::jsonb, peak_performance_windows),
                      decision_patterns       = COALESCE(%s::jsonb, decision_patterns),
                      content_strengths       = COALESCE(%s::jsonb, content_strengths),
                      learning_style          = COALESCE(%s::jsonb, learning_style),
                      stress_indicators       = COALESCE(%s::jsonb, stress_indicators),
                      north_star              = COALESCE(%s, north_star),
                      cross_product_insights  = COALESCE(%s::jsonb, cross_product_insights),
                      last_updated            = %s
                    WHERE user_id = %s::uuid
                    """,
                    (
                        _j(updates.get("communication_style"))
                        if "communication_style" in updates else None,
                        _j(updates.get("peak_performance_windows"))
                        if "peak_performance_windows" in updates else None,
                        _j(updates.get("decision_patterns"))
                        if "decision_patterns" in updates else None,
                        _j(updates.get("content_strengths"))
                        if "content_strengths" in updates else None,
                        _j(updates.get("learning_style"))
                        if "learning_style" in updates else None,
                        _j(updates.get("stress_indicators"))
                        if "stress_indicators" in updates else None,
                        updates.get("north_star"),
                        _j(updates.get("cross_product_insights"))
                        if "cross_product_insights" in updates else None,
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
                        json.dumps(updates.get("communication_style", {})),
                        json.dumps(updates.get("peak_performance_windows", [])),
                        json.dumps(updates.get("decision_patterns", {})),
                        json.dumps(updates.get("content_strengths", {})),
                        json.dumps(updates.get("learning_style", {})),
                        json.dumps(updates.get("stress_indicators", {})),
                        updates.get("north_star", ""),
                        json.dumps(updates.get("cross_product_insights", {})),
                        datetime.now(timezone.utc),
                    ),
                )
