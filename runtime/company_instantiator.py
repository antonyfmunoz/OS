"""
CompanyInstantiator — instantiate the 6 Munoz Conglomerate companies
as formal template instances with offer ladder rows in Neon.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from state.registries.template_registry import TemplateRegistry, TemplateInstance
from state.storage.db import get_conn

ORG_ID = "72727be3-e24d-48f2-bcea-de760ecb4c23"

# ─── Company definitions ─────────────────────────────────────────────────────

COMPANIES = [
    {
        "name": "Operating System Technologies Inc",
        "venture_id": "ost",
        "template_id": "saas",
        "slots": {
            "offer_name": "EntrepreneurOS",
            "icp_description": "Solo founders running 1-5 ventures who need an AI operating system to replace manual operations",
            "primary_channel": "Direct outreach + Empyrean referrals",
            "price_point": 297,
            "delivery_method": "SaaS platform + AI agents",
            "success_metric": "Customer retains 60+ days",
            "stage": 1,
            "core_problem": "Founders waste 20+ hours/week on operations that AI could handle",
            "platform": "Web (React + Python backend)",
            "retention_target_days": 60,
        },
        "offers": [
            (
                "EntrepreneurOS Monthly",
                1,
                29700,
                "subscription",
                "Monthly SaaS subscription",
            ),
            (
                "EntrepreneurOS Annual",
                2,
                237600,
                "subscription",
                "Annual SaaS subscription — 2 months free",
            ),
        ],
    },
    {
        "name": "Empyrean Studios",
        "venture_id": "empyrean_creative",
        "template_id": "incubator_studio",
        "slots": {
            "offer_name": "AI Infrastructure Buildout",
            "icp_description": "Small to mid-size businesses that need AI infrastructure but lack technical expertise",
            "primary_channel": "Direct outreach",
            "price_point": 3000,
            "delivery_method": "Done-for-you project + handoff",
            "success_metric": "Client has working AI system within 30 days",
            "stage": 1,
            "internal_product": "EntrepreneurOS",
            "b2b_offer_type": "Done-for-you project",
            "spinoff_threshold": "$10K/month net profit",
        },
        "offers": [
            (
                "AI Infrastructure Project",
                1,
                300000,
                "project",
                "Custom AI system buildout",
            ),
            (
                "AI System Retainer",
                2,
                200000,
                "retainer",
                "Monthly AI system maintenance and optimization",
            ),
        ],
    },
    {
        "name": "Lyfe Institute",
        "venture_id": "lyfe_institute",
        "template_id": "coaching_program",
        "slots": {
            "offer_name": "Initiate Arena",
            "icp_description": "Ambitious young men 18-25 who feel lost but know they are capable of more",
            "primary_channel": "Instagram DMs",
            "price_point": 750,
            "delivery_method": "WHOP curriculum + Discord community + live coaching calls",
            "success_metric": "Client completes 90-day program",
            "stage": 1,
            "transformation_promise": "From drifting to executing — install the identity and structure of someone who ships",
            "program_duration_days": 90,
            "cohort_size": 10,
        },
        "offers": [
            (
                "Initiate Arena",
                1,
                75000,
                "coaching",
                "90-day structured execution program",
            ),
            (
                "Game of Lyfe",
                2,
                500000,
                "coaching",
                "Advanced execution + life architecture — ROADMAP",
            ),
            (
                "Sovereign Path",
                3,
                1500000,
                "coaching",
                "1-on-1 sovereign development — ROADMAP",
            ),
            (
                "Modern Monarch Mastermind",
                4,
                2500000,
                "mastermind",
                "Elite mastermind for proven executors — ROADMAP",
            ),
        ],
    },
    {
        "name": "Antony F. Munoz Personal Brand",
        "venture_id": "personal_brand",
        "template_id": "personal_brand",
        "slots": {
            "offer_name": "The Vigilante Architect",
            "icp_description": "Founders and entrepreneurs who want to build an AI-native business",
            "primary_channel": "Instagram",
            "price_point": 0,
            "delivery_method": "Content — brand IS the advertising for all ventures",
            "success_metric": "10K engaged followers who are potential EOS customers",
            "stage": 1,
            "content_platform": "Instagram",
            "brand_archetype": "The Vigilante Architect — rebel builder",
            "monetization_path": "Product placement for owned ventures + audience-to-pipeline conversion",
            "content_cadence": "Daily",
        },
        "offers": [
            (
                "Content Audience",
                1,
                0,
                "content",
                "Free content — audience IS the product for venture pipeline",
            ),
        ],
    },
    {
        "name": "Lyfe Spectrum",
        "venture_id": "lyfe_spectrum",
        "template_id": "ecommerce",
        "slots": {
            "offer_name": "Lyfe Spectrum Apparel",
            "icp_description": "Life-maxing men 18-30 who want to wear their philosophy",
            "primary_channel": "Instagram + personal brand",
            "price_point": 45,
            "delivery_method": "Print-on-demand + direct ship",
            "success_metric": "10 profitable orders per month",
            "stage": 1,
            "product_type": "Print-on-demand apparel",
            "unit_cost": 15,
            "fulfillment_method": "Print-on-demand (Printful)",
        },
        "offers": [
            ("Lyfe Spectrum Tee", 1, 4500, "product", "Premium graphic tee"),
            ("Lyfe Spectrum Hoodie", 2, 7500, "product", "Premium graphic hoodie"),
        ],
    },
    {
        "name": "Select Developments",
        "venture_id": "select_developments",
        "template_id": "real_estate_development",
        "slots": {
            "offer_name": "Select Developments Projects",
            "icp_description": "Residential properties in Portland metro area with value-add potential",
            "primary_channel": "MLS + wholesale deals",
            "price_point": 0,
            "delivery_method": "Buy, renovate, sell or hold",
            "success_metric": "20% ROI per project",
            "stage": 1,
            "property_type": "Residential",
            "strategy": "Fix and flip → transition to buy and hold",
            "market_area": "Portland, Oregon metro",
            "capital_source": "Self-funded initially",
        },
        "offers": [
            (
                "Fix and Flip Project",
                1,
                0,
                "project",
                "Buy, renovate, sell residential property",
            ),
            (
                "Buy and Hold Unit",
                2,
                0,
                "rental",
                "Buy, renovate, hold for rental income",
            ),
        ],
    },
]


# ─── CompanyInstantiator ─────────────────────────────────────────────────────


class CompanyInstantiator:
    """Instantiate all 6 Munoz Conglomerate companies as template instances."""

    def __init__(self, org_id: str = ORG_ID):
        self.org_id = org_id
        self.registry = TemplateRegistry()
        self.instances: dict[str, TemplateInstance] = {}

    def instantiate_all(self) -> dict[str, TemplateInstance]:
        """Instantiate all 6 companies. Returns dict of venture_id -> TemplateInstance."""
        for company in COMPANIES:
            context = {**company["slots"], "org_id": self.org_id}
            instance = self.registry.instantiate(company["template_id"], context)
            if instance:
                instance.org_id = self.org_id
                self.instances[company["venture_id"]] = instance
        return self.instances

    def seed_offers(self) -> int:
        """Insert offer ladder rows for all companies. Returns total rows inserted."""
        count = 0
        with get_conn(self.org_id) as cur:
            for company in COMPANIES:
                for offer in company["offers"]:
                    name, position, price_cents, offer_type, description = offer
                    # Check if offer already exists (idempotent)
                    cur.execute(
                        "SELECT id FROM offers WHERE name = %s AND venture_id = %s",
                        (name, company["venture_id"]),
                    )
                    if cur.fetchone():
                        continue
                    cur.execute(
                        """INSERT INTO offers (org_id, venture_id, name, position_in_ladder, price_cents, offer_type, description, validated)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            self.org_id,
                            company["venture_id"],
                            name,
                            position,
                            price_cents,
                            offer_type,
                            description,
                            False,
                        ),
                    )
                    count += 1
        return count

    def ensure_ventures(self) -> int:
        """Ensure all venture_ids exist in the ventures table. Returns count of new rows."""
        new = 0
        with get_conn(self.org_id) as cur:
            for company in COMPANIES:
                # Check by name only — id column is UUID, venture_id here is a slug
                cur.execute(
                    "SELECT id FROM ventures WHERE name = %s",
                    (company["name"],),
                )
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO ventures (org_id, name) VALUES (%s, %s)",
                        (self.org_id, company["name"]),
                    )
                    new += 1
        return new

    def run(self) -> None:
        """Full instantiation: ensure ventures -> instantiate templates -> seed offers."""
        new_ventures = self.ensure_ventures()
        instances = self.instantiate_all()
        offers = self.seed_offers()
        print(f"Ventures: {new_ventures} new")
        print(f"Instances: {len(instances)} created")
        print(f"Offers: {offers} seeded")
        for vid, inst in instances.items():
            print(
                f"  {vid}: template={inst.template_id}, slots={len(inst.filled_slots)}"
            )


if __name__ == "__main__":
    ci = CompanyInstantiator()
    ci.run()
