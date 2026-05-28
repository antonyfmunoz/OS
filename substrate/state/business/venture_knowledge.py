import json
import logging
import os
from dataclasses import dataclass, field
from typing import Literal

from substrate.state.storage.db import get_conn

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or "/opt/OS"
_VENTURES_JSON = os.path.join(_ROOT, "data", "umh", "ventures.json")


@dataclass
class Venture:
    stage: str  # building | scaling | optimizing
    monthly_revenue: float
    monthly_target: float
    primary_icp: str
    core_offer: str
    price_point: str
    positioning: str
    competitors: list[str]
    winning_content_angles: list[str]
    proven_outreach_openers: list[str]
    common_objections: list[str]
    north_star_metric: str
    active_blockers: list[str]


def _load_ventures_from_json() -> dict[str, Venture]:
    """
    Load venture knowledge from data/umh/ventures.json.
    Returns an empty dict if the file is missing or malformed.
    """
    try:
        with open(_VENTURES_JSON, "r") as f:
            raw = json.load(f)
        result: dict[str, Venture] = {}
        for vid, vdata in raw.items():
            result[vid] = Venture(
                stage=vdata.get("stage", "building"),
                monthly_revenue=float(vdata.get("monthly_revenue", 0)),
                monthly_target=float(vdata.get("monthly_target", 0)),
                primary_icp=vdata.get("primary_icp", ""),
                core_offer=vdata.get("core_offer", ""),
                price_point=vdata.get("price_point", ""),
                positioning=vdata.get("positioning", ""),
                competitors=vdata.get("competitors", []),
                winning_content_angles=vdata.get("winning_content_angles", []),
                proven_outreach_openers=vdata.get("proven_outreach_openers", []),
                common_objections=vdata.get("common_objections", []),
                north_star_metric=vdata.get("north_star_metric", ""),
                active_blockers=vdata.get("active_blockers", []),
            )
        return result
    except FileNotFoundError:
        logger.debug(f"[VentureKnowledgeBase] {_VENTURES_JSON} not found — using empty defaults")
        return {}
    except Exception as e:
        logger.warning(f"[VentureKnowledgeBase] Failed to load ventures.json: {e}")
        return {}


def get_venture_name(venture_id: str, fallback: str = "") -> str:
    """Module-level shortcut: return a venture's display name or fallback."""
    return VentureKnowledgeBase.name(venture_id, fallback)


class VentureKnowledgeBase:
    _ventures: dict[str, Venture] = _load_ventures_from_json()

    @classmethod
    def get_ventures_from_db(cls, org_id: str) -> dict:
        """
        Query the ventures table for the given org_id and return a dict
        matching the _ventures structure keyed by slug (name lowercased, spaces -> _).

        Called by to_agent_context() as fallthrough when venture_id is not in
        the loaded _ventures dict. Returns {} on any DB error.
        """
        try:
            with get_conn(org_id) as cur:
                cur.execute(
                    """
                    SELECT id, name, monthly_revenue, monthly_target
                    FROM ventures
                    WHERE org_id = %s
                    """,
                    (org_id,),
                )
                rows = cur.fetchall()

            result: dict = {}
            for row in rows:
                slug = row["name"].lower().replace(" ", "_")
                result[slug] = Venture(
                    stage="building",
                    monthly_revenue=float(row["monthly_revenue"] or 0),
                    monthly_target=float(row["monthly_target"] or 0),
                    primary_icp="",
                    core_offer=row["name"],
                    price_point="",
                    positioning="",
                    competitors=[],
                    winning_content_angles=[],
                    proven_outreach_openers=[],
                    common_objections=[],
                    north_star_metric="",
                    active_blockers=[],
                )
            return result
        except Exception as e:
            logger.warning(f"[VentureKnowledgeBase] DB fallthrough failed: {e}")
            return {}

    @classmethod
    def name(cls, venture_id: str, fallback: str = "") -> str:
        """Return the display name for a venture, or fallback if unknown."""
        if venture_id in cls._ventures:
            return venture_id.replace("_", " ").title()
        return fallback

    @classmethod
    def get(cls, venture_id: str) -> Venture:
        if venture_id not in cls._ventures:
            raise KeyError(
                f"Unknown venture: '{venture_id}'. Valid options: {list(cls._ventures.keys())}"
            )
        return cls._ventures[venture_id]

    @classmethod
    def list_ventures(cls) -> list[str]:
        return list(cls._ventures.keys())

    @classmethod
    def to_agent_context(
        cls,
        venture_id: str,
        detail: Literal["full", "brief"] = "full",
        org_id: str | None = None,
    ) -> str:
        # Try loaded data first; fall through to DB if not found
        if venture_id not in cls._ventures:
            if org_id:
                db_ventures = cls.get_ventures_from_db(org_id)
                if venture_id in db_ventures:
                    cls._ventures[venture_id] = db_ventures[venture_id]
        v = cls.get(venture_id)
        label = venture_id.replace("_", " ").title()

        if detail == "brief":
            return (
                f"VENTURE: {label}\n"
                f"Stage: {v.stage}\n"
                f"Revenue: ${v.monthly_revenue:,.0f}/mo  |  Target: ${v.monthly_target:,.0f}/mo\n"
                f"Offer: {v.core_offer}\n"
                f"ICP: {v.primary_icp}\n"
                f"Price: {v.price_point}\n"
                f"North star: {v.north_star_metric}\n"
            )

        competitors = "\n".join(f"  - {c}" for c in v.competitors)
        content_angles = "\n".join(f"  - {a}" for a in v.winning_content_angles)
        openers = "\n".join(f"  - {o}" for o in v.proven_outreach_openers)
        objections = "\n".join(f"  - {o}" for o in v.common_objections)
        blockers = "\n".join(f"  - {b}" for b in v.active_blockers)

        return (
            f"VENTURE CONTEXT: {label}\n"
            f"{'=' * 48}\n"
            f"Stage:             {v.stage}\n"
            f"Monthly revenue:   ${v.monthly_revenue:,.0f}\n"
            f"Monthly target:    ${v.monthly_target:,.0f}\n"
            f"North star metric: {v.north_star_metric}\n"
            f"\n"
            f"OFFER\n"
            f"Core offer:  {v.core_offer}\n"
            f"Price point: {v.price_point}\n"
            f"Positioning: {v.positioning}\n"
            f"\n"
            f"IDEAL CUSTOMER\n"
            f"{v.primary_icp}\n"
            f"\n"
            f"COMPETITORS\n"
            f"{competitors}\n"
            f"\n"
            f"WINNING CONTENT ANGLES\n"
            f"{content_angles}\n"
            f"\n"
            f"PROVEN OUTREACH OPENERS\n"
            f"{openers}\n"
            f"\n"
            f"COMMON OBJECTIONS\n"
            f"{objections}\n"
            f"\n"
            f"ACTIVE BLOCKERS\n"
            f"{blockers}\n"
        )
