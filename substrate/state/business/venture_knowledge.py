from dataclasses import dataclass, field
from typing import Literal

from substrate.state.storage.db import get_conn


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


class VentureKnowledgeBase:
    _ventures: dict[str, Venture] = {
        # ─────────────────────────────────────────────────────────────────────
        # EMPYREAN CREATIVE (aka Empyrean Studio / Lyfe Studio)
        #
        # Two-function entity under Munoz Holdings / Lyfe Corp:
        #
        #   FUNCTION 1 — Internal incubator
        #     Antony builds and validates his own products, frameworks, and
        #     systems here. When validated, they spin off as separate companies.
        #     Lyfe Institute is the first validated spinoff. Future spinoffs
        #     could include SaaS, AI products, and other verticals.
        #
        #   FUNCTION 2 — B2B studio
        #     Learnings, systems, and tools proven internally get packaged as
        #     B2B offers sold to other founders. Current B2B offer candidates:
        #     EntrepreneurOS AI system, creative strategy, brand positioning.
        #
        # This is NOT a traditional branding/creative agency.
        #
        # Source documents: Conglomerate Brands (Drive), Antony F. Munoz
        # Personal Brand (Drive), Empyrean Studios Agency Brand (Drive — empty)
        # ─────────────────────────────────────────────────────────────────────
        "empyrean_creative": Venture(
            stage="building",
            monthly_revenue=0.0,  # TODO: update with real revenue when B2B clients close
            monthly_target=0.0,  # TODO: no monthly target documented — set when B2B offer goes active
            primary_icp=(
                "TODO: no ICP language found in any Drive document or local file. "
                "The Empyrean Studios (Agency Brand) doc in Drive exists but contains no content. "
                "Likely target: founder-operators who need brand strategy and/or AI infrastructure, "
                "but no verbatim language from Antony has been captured. "
                "Write this when the B2B offer is being actively pitched."
            ),
            core_offer=(
                "Dual-function entity. "
                "INTERNAL: Incubator that builds and validates Antony's own products and systems — "
                "validated outputs spin off as standalone companies (Lyfe Institute is the first). "
                "EXTERNAL (B2B): Proven internal systems packaged as offers for other founders. "
                "Current B2B offer candidates: EntrepreneurOS AI system, creative strategy, brand positioning. "
                "Revenue model: project fees ($1,500–$3,000/project) + future recurring AI system licenses."
            ),
            price_point="$1,500–$3,000 per project (current) | recurring AI system licenses (future)",
            positioning=(
                # Source: Conglomerate Brands (Drive)
                "A centralized forge that turns philosophy into systems, products, and media without "
                "trend dependence. Not a traditional agency. "
                "Mission: Enable authentic expression through disciplined creation. "
                "Enemy: Trend chasing, aesthetic emptiness, creative laziness. "
                "Narrative: Where Mastery Is Forged. "
                "The production engine and proof-of-concept lab for Munoz Holdings — "
                "proves systems internally first, then sells externally."
            ),
            competitors=[
                "TODO: no competitor research found in any Drive document or local file for the B2B side",
                "TODO: identify when B2B offer is being actively pitched",
            ],
            winning_content_angles=[
                "TODO: no content angles documented for Empyrean — "
                "content strategy for this entity has not been built yet",
            ],
            proven_outreach_openers=[
                "TODO: no B2B outreach openers found in any document — "
                "Empyrean has no active outreach operation yet",
            ],
            common_objections=[
                "TODO: no objection data found — entity has no active sales conversations yet",
            ],
            north_star_metric=(
                "Become the production engine and proof-of-concept lab that funds and "
                "validates all other ventures under Munoz Holdings"
            ),
            active_blockers=[
                "No active B2B clients — entity is pre-revenue on the external side",
                "No case studies yet — internal work (EntrepreneurOS) is the first proof of concept",
                "Initiate Arena (Lyfe Institute) is the current primary focus — "
                "Empyrean B2B offer gets real attention after $10K/mo is stable",
            ],
        ),
        # ─────────────────────────────────────────────────────────────────────
        # LYFE INSTITUTE
        #
        # Educational company — Antony's first validated spinoff from Empyrean.
        # Full offer ladder exists but ONLY Initiate Arena is the active focus.
        # No resources shift to the next tier until Initiate Arena hits its target.
        #
        # Offer ladder (in order):
        #   1. Initiate Arena            — $750     (ACTIVE — only current focus)
        #   2. Game of Lyfe              — $5,000   (roadmap — not active)
        #   3. Sovereign Path            — $15,000  (roadmap — not active)
        #   4. Modern Monarch Mastermind — $25,000  (roadmap — not active)
        #
        # Source documents: Untitled document (Drive, 2026-03-13),
        # Life Coaching E-Learning/Info-Product Brand (Drive),
        # Conglomerate Brands (Drive), local ICP + outreach files
        # ─────────────────────────────────────────────────────────────────────
        "lyfe_institute": Venture(
            stage="building",
            monthly_revenue=0.0,  # TODO: update with real revenue when first sale closes
            monthly_target=10000.0,  # $10K/month net profit — trigger to shift focus to next offer
            primary_icp=(
                # Verbatim from Antony's Initiate Arena planning doc (Drive, 2026-03-13)
                "One sentence: 'Ambitious young men (18–25) who feel lost but know they're capable of more.'\n"
                "\n"
                "WHO THIS IS FOR (verbatim):\n"
                "- Feels behind in life\n"
                "- Knows they're capable of more\n"
                "- Lacks daily structure\n"
                "- Scrolls too much / escapes too much\n"
                "- Doesn't have a clear 12-month direction\n"
                "- Is willing to do uncomfortable work\n"
                "\n"
                "NOT FOR (verbatim):\n"
                "- Victim mindset\n"
                "- Blames others\n"
                "- Wants motivation without execution\n"
                "\n"
                "Two documented psychological states (from ICP research):\n"
                "\n"
                "AMBITIOUS BUT STUCK: Self-aware, high perceived potential, zero output system. "
                "Language: 'I feel like I'm capable of more' / 'every week just disappears' / "
                "'scrolling or gaming instead of building anything.' "
                "Not burned out — unstructured. Slowly losing faith the gap will close on its own.\n"
                "\n"
                "FRUSTRATED DRIFTER: High energy and curiosity. Starts constantly, finishes rarely. "
                "Language: 'I keep starting' / 'never finishing them' / 'makes me feel like I'm wasting my life.' "
                "Abandonment loop (excitement → momentum fade → quit → shame → repeat) has compounded "
                "into identity damage. High emotional urgency. Ready to act."
            ),
            core_offer=(
                "Initiate Arena — 90-day structured execution program for men 18–25. "
                "Delivery: WHOP (curriculum + PDFs/assignments) + Discord (community + live coaching calls). "
                "Included: weekly 90-min group call, private accountability group, weekly execution assignment, "
                "Initiate Diagnostic Report (weeks 1–2), 90-Day Personal Execution Plan, end-of-program Roadmap Call. "
                "4-phase transformation map: Phase 1 (weeks 1–2) Stabilization — stop drift, install structure. "
                "Phase 2 (weeks 3–6) Direction + Skill Activation — install one primary execution lane. "
                "Phase 3 (weeks 7–10) Pressure + Exposure — real-world friction and proof under discomfort. "
                "Phase 4 (weeks 11–12) Identity Lock-In — Personal Operating Code, 12-Month Execution Plan. "
                "Full offer ladder exists (Game of Lyfe → Sovereign Path → Modern Monarch Mastermind) "
                "but is roadmap only — no resources allocated until Initiate Arena hits $10K/mo net."
            ),
            price_point=(
                "Initiate Arena: $750 founding (ACTIVE) | "
                "Game of Lyfe: $5,000 (roadmap) | "
                "Sovereign Path: $15,000 1-on-1 (roadmap) | "
                "Modern Monarch Mastermind: $25,000 (roadmap)"
            ),
            positioning=(
                # Sources: Conglomerate Brands (Drive) + Life Coaching doc (Drive) + planning doc
                "Not a coaching program — an educational institution that develops sovereign individuals. "
                "From Dependence To Sovereignty. "
                "Mission: Develop sovereign individuals. "
                "USP: Education designed to eliminate dependence. "
                "Enemy: Indoctrination, dishonesty, ineffectiveness. "
                "Theme: Agency. Archetype: The Mentor & Sage. "
                "Competes where Robbins and Dispenza can't: "
                "depth of frameworks + gamification + AI + daily-use community platform. "
                "Robbins = hype events + surface-level motivation. "
                "Dispenza = meditation + neuroscience → spirituality. "
                "Neither dominates Gen Z + Millennial attention markets. "
                "You = LYFEOS + Game of Lyfe → the OS of transformation."
            ),
            competitors=[
                # Source: Life Coaching E-Learning/Info-Product Brand doc (Drive)
                "Tony Robbins — hype events, surface-level motivation, passive audience",
                "Joe Dispenza — meditation, neuroscience, spirituality, retreat-based",
                "TODO: research execution-based accountability cohorts and masculine development "
                "programs targeting 18–25 men (e.g. Modern Wisdom adjacent, discipline-focused creators)",
            ],
            winning_content_angles=[
                # Sources: Market intelligence report (local) + Antony's planning doc (Drive)
                '"You don\'t have a discipline problem. You have a structure problem."',
                "\"You're not confused. You're undisciplined.\"",
                '"You don\'t lack purpose. You lack structure."',
                '"Scrolling is the new sedation."',
                '"You don\'t need more podcasts. You need constraints."',
                '"Capable people go broke on potential. Builders go broke on execution."',
                '"If every week disappears, your environment is built for consumption — not output."',
                '"Starting is easy. Finishing is a skill. Here\'s how to build it."',
                '"Every unfinished project is a loan against your future self-belief."',
                'Myth-bust: "Working harder isn\'t the fix if your week has no architecture."',
                'Discussion prompt: "What\'s the gap between who you think you are and what you shipped this week?"',
                'Discussion prompt: "How many half-finished projects are sitting in your notes right now?"',
                'Vulnerable/story: "I used to abandon everything I started — here\'s what actually changed that."',
                "Document the rebuild publicly — show wake time, focus blocks, outreach numbers, honest struggles. "
                "The hero is the system, not you.",
            ],
            proven_outreach_openers=[
                # Verbatim DM scripts from Antony's planning doc (Drive, 2026-03-13)
                # — these are his own written words, not AI-generated
                "WARM (verbatim): 'Yo — quick honest question: do you feel clear and structured about "
                "your direction right now? I'm opening a small founding group for ambitious guys 18–25 "
                "who feel lost but know they're capable of more. Want me to send you the details?'",
                "COLD (verbatim): 'Random but real question — do you feel clear about where your life "
                "is going right now? I'm building something for ambitious young men who feel stuck but "
                "capable of more.'",
                # AI-generated openers from outreach batches (2026-03-14, 2026-03-16) — Ambitious but Stuck
                "Do you feel like you're capable of more than what you're actually shipping each week?",
                "You don't have a motivation problem. You have an architecture problem. Sound familiar?",
                "Most people who feel stuck aren't lazy. They're just running without a track. Does that land for you?",
                "If discipline was going to fix it, it would've fixed it by now. What do you think is actually missing?",
                "When you do have a productive week, what made it different from the others?",
                # AI-generated openers — Frustrated Drifter
                "Do you find it easier to start things than to finish them?",
                "Be honest — how many projects are sitting half-done right now?",
                "You're not someone who doesn't finish things. You're someone who never had a system "
                "that made finishing inevitable. Big difference.",
                "Every abandoned project costs something — not just time, but belief. "
                "How much has the cycle cost you?",
            ],
            common_objections=[
                "TODO: no objection data captured in any document yet — "
                "log objections from sales calls and DM conversations as they come in. "
                "Likely to encounter: "
                "'I've tried courses before and didn't finish', "
                "'I don't have the money right now', "
                "'I need to think about it', "
                "'I can figure this out on my own'",
            ],
            north_star_metric="$10K/month net profit from Initiate Arena",
            active_blockers=[
                "Pre-revenue — no sales closed yet, first close is the immediate target",
                "Outreach is the primary acquisition channel — volume and conversion are the only levers",
                "No case studies or testimonials yet — social proof gap at point of sale",
                "Game of Lyfe, Sovereign Path, and Mastermind are frozen until $10K/mo is stable",
            ],
        ),
    }

    @classmethod
    def get_ventures_from_db(cls, org_id: str) -> dict:
        """
        Query the ventures table for the given org_id and return a dict
        matching the _ventures structure keyed by slug (name lowercased, spaces → _).

        Called by to_agent_context() as fallthrough when venture_id is not in
        the hardcoded _ventures dict. Returns {} on any DB error.
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
            print(f"[VentureKnowledgeBase] DB fallthrough failed: {e}")
            return {}

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
        # Try hardcoded data first; fall through to DB if not found
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
