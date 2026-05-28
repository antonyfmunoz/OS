"""
TemplateRegistry — formal template schema for the Meta Harness.

Templates are composable blueprints made of ontological primitives.
Each template defines typed slots that must be filled at instantiation.

Migrates the 5 business templates from template_library.py into formal schema.
"""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ─── Schema ──────────────────────────────────────────────────────────────────


@dataclass
class TemplateSlot:
    """A typed parameter that must be filled when instantiating a template."""

    id: str
    name: str
    description: str
    required: bool
    slot_type: str  # "text", "number", "entity", "list", "primitive"
    default: Any = None
    constraints: list[str] = field(default_factory=list)


@dataclass
class Template:
    """A composable blueprint made of ontological primitives."""

    id: str
    name: str
    domain: str  # "business", "personal", "audience", "universal"
    level: int  # 1=universal, 2=domain, 3=instance
    description: str
    primitive_ids: list[str]  # which ontological primitives compose this template
    slots: list[TemplateSlot]  # what must be filled at instantiation
    execution_logic: str  # description of how this template runs
    adaptation_rules: list[str]  # how it self-modifies from outcomes
    version: int = 1


@dataclass
class TemplateInstance:
    """A concrete instantiation of a template with filled slots."""

    template_id: str
    filled_slots: dict
    declared_context: dict
    observed_context: dict | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    org_id: str = ""
    status: str = "active"
    instance_id: str = field(default_factory=lambda: str(_uuid.uuid4()))


# ─── Common slots shared across all business templates ────────────────────────


def _common_business_slots() -> list[TemplateSlot]:
    """Slots required by every business template."""
    return [
        TemplateSlot(
            id="offer_name",
            name="Offer Name",
            description="The name of the core offer being sold",
            required=True,
            slot_type="text",
        ),
        TemplateSlot(
            id="icp_description",
            name="ICP Description",
            description="Who the ideal customer is and what pain they carry",
            required=True,
            slot_type="text",
        ),
        TemplateSlot(
            id="primary_channel",
            name="Primary Channel",
            description="The single channel used for customer acquisition",
            required=True,
            slot_type="text",
        ),
        TemplateSlot(
            id="price_point",
            name="Price Point",
            description="Price of the core offer in USD",
            required=True,
            slot_type="number",
        ),
        TemplateSlot(
            id="delivery_method",
            name="Delivery Method",
            description="How the offer is delivered to the customer",
            required=True,
            slot_type="text",
        ),
        TemplateSlot(
            id="success_metric",
            name="Success Metric",
            description="The measurable outcome that proves the offer works",
            required=True,
            slot_type="text",
        ),
        TemplateSlot(
            id="stage",
            name="Business Stage",
            description="Current business stage (1=validation, 2=scaling)",
            required=True,
            slot_type="number",
            default=1,
        ),
    ]


# ─── Ontological primitive base set for all business templates ────────────────

_BUSINESS_PRIMITIVE_BASE = [
    "state",
    "change",
    "goal",
    "action",
    "outcome",
    "resource",
    "constraint",
]


# ─── Template definitions ────────────────────────────────────────────────────

_TEMPLATES: dict[str, Template] = {
    "coaching_program": Template(
        id="coaching_program",
        name="Coaching / Group Program",
        domain="business",
        level=3,
        description=(
            "Sell transformation to a specific ICP. "
            "One core offer, one channel, "
            "one repeating transaction."
        ),
        primitive_ids=_BUSINESS_PRIMITIVE_BASE + ["feedback", "signal"],
        slots=_common_business_slots()
        + [
            TemplateSlot(
                id="transformation_promise",
                name="Transformation Promise",
                description="The identity shift the client undergoes",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="program_duration_days",
                name="Program Duration (days)",
                description="Length of the program in days",
                required=False,
                slot_type="number",
                default=90,
            ),
            TemplateSlot(
                id="cohort_size",
                name="Cohort Size",
                description="Max number of clients per cohort",
                required=False,
                slot_type="number",
                default=10,
            ),
        ],
        execution_logic=(
            "Identify ICP, open conversations via direct outreach, "
            "sell the transformation, deliver through group or 1:1 coaching, "
            "collect proof of result."
        ),
        adaptation_rules=[
            "If conversion rate < 5% after 100 conversations, refine ICP or offer positioning.",
            "If client completion rate < 60%, shorten program or add accountability checkpoints.",
            "When 10 clients complete, extract testimonials and shift from outreach to content leverage.",
        ],
    ),
    "agency": Template(
        id="agency",
        name="Service Agency",
        domain="business",
        level=3,
        description=(
            "Sell done-for-you services to businesses. Revenue from retainers or projects."
        ),
        primitive_ids=_BUSINESS_PRIMITIVE_BASE + ["feedback", "time"],
        slots=_common_business_slots()
        + [
            TemplateSlot(
                id="service_scope",
                name="Service Scope",
                description="What the agency delivers for the client",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="retainer_length_months",
                name="Retainer Length (months)",
                description="Minimum retainer commitment in months",
                required=False,
                slot_type="number",
                default=3,
            ),
            TemplateSlot(
                id="client_result",
                name="Client Result",
                description="The measurable business result delivered to clients",
                required=True,
                slot_type="text",
            ),
        ],
        execution_logic=(
            "Generate leads via cold outreach and referrals, run discovery calls, "
            "send proposals, onboard and deliver the service, report results, "
            "renew or upsell."
        ),
        adaptation_rules=[
            "If close rate < 20% after 20 proposals, refine offer scope or pricing.",
            "If client churn > 30% quarterly, add reporting cadence and proactive communication.",
            "After 3 retained clients, hire junior executor to free founder for sales.",
        ],
    ),
    "digital_product": Template(
        id="digital_product",
        name="Digital Product / Course",
        domain="business",
        level=3,
        description=("Create once, sell many times. Leveraged income model."),
        primitive_ids=_BUSINESS_PRIMITIVE_BASE + ["signal", "feedback"],
        slots=_common_business_slots()
        + [
            TemplateSlot(
                id="product_format",
                name="Product Format",
                description="Format of the digital product (course, ebook, template, etc.)",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="audience_size_target",
                name="Audience Size Target",
                description="Minimum audience size before first launch",
                required=False,
                slot_type="number",
                default=500,
            ),
            TemplateSlot(
                id="launch_strategy",
                name="Launch Strategy",
                description="How the product will be launched (live cohort, evergreen, etc.)",
                required=False,
                slot_type="text",
                default="Live cohort first, then evergreen",
            ),
        ],
        execution_logic=(
            "Build audience, validate the idea with a live cohort, "
            "teach it live before recording, launch, collect testimonials, "
            "then move to evergreen sales."
        ),
        adaptation_rules=[
            "If first cohort conversion < 3%, test new positioning or audience segment.",
            "If completion rate < 40%, restructure content into shorter actionable modules.",
            "After 3 successful launches, automate the funnel and shift to paid acquisition.",
        ],
    ),
    "ecommerce": Template(
        id="ecommerce",
        name="Ecommerce / Physical Products",
        domain="business",
        level=3,
        description=("Sell physical or digital products online. Revenue from transactions."),
        primitive_ids=_BUSINESS_PRIMITIVE_BASE + ["resource", "signal"],
        slots=_common_business_slots()
        + [
            TemplateSlot(
                id="product_type",
                name="Product Type",
                description="Type of product (physical, digital download, print-on-demand, etc.)",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="unit_cost",
                name="Unit Cost",
                description="Cost to produce or source one unit in USD",
                required=True,
                slot_type="number",
            ),
            TemplateSlot(
                id="fulfillment_method",
                name="Fulfillment Method",
                description="How orders are fulfilled (self-ship, 3PL, dropship, digital)",
                required=False,
                slot_type="text",
                default="Self-ship",
            ),
        ],
        execution_logic=(
            "Source or create product, set up store, drive organic traffic, "
            "fulfill orders, collect reviews, prove unit economics before scaling."
        ),
        adaptation_rules=[
            "If cost per acquisition > 50% of price, cut channel and test organic alternatives.",
            "If return rate > 10%, investigate product quality or listing accuracy.",
            "After 10 profitable orders, test paid ads with proven creative.",
        ],
    ),
    "saas": Template(
        id="saas",
        name="SaaS / Software Product",
        domain="business",
        level=3,
        description=("Build software, sell subscriptions. Revenue compounds with retention."),
        primitive_ids=_BUSINESS_PRIMITIVE_BASE + ["feedback", "signal", "time"],
        slots=_common_business_slots()
        + [
            TemplateSlot(
                id="core_problem",
                name="Core Problem",
                description="The recurring pain the software solves",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="platform",
                name="Platform",
                description="Where the product lives (web, mobile, desktop, API)",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="retention_target_days",
                name="Retention Target (days)",
                description="Minimum days a customer should stay subscribed to prove PMF",
                required=False,
                slot_type="number",
                default=60,
            ),
        ],
        execution_logic=(
            "Find 10 people with the problem, build the minimum that solves it, "
            "charge before it is perfect, iterate on feedback, "
            "prove retention before scaling acquisition."
        ),
        adaptation_rules=[
            "If day-30 retention < 40%, pivot feature set based on usage data before adding users.",
            "If activation rate < 25%, simplify onboarding or add guided setup.",
            "After 3 paying customers retained 60+ days, begin content and outbound acquisition.",
        ],
    ),
    "incubator_studio": Template(
        id="incubator_studio",
        name="Internal Incubator + B2B Studio",
        domain="business",
        level=3,
        description=(
            "Validate products internally, package proven systems as B2B offers. "
            "Revenue from project fees + recurring licenses."
        ),
        primitive_ids=_BUSINESS_PRIMITIVE_BASE + ["feedback", "signal", "time"],
        slots=_common_business_slots()
        + [
            TemplateSlot(
                id="internal_product",
                name="Internal Product",
                description="The product or system being incubated internally",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="b2b_offer_type",
                name="B2B Offer Type",
                description="Type of B2B offer (consulting, license, done-for-you)",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="spinoff_threshold",
                name="Spinoff Threshold",
                description="Revenue threshold that triggers spinoff to standalone entity",
                required=False,
                slot_type="text",
                default="$10K/month net profit",
            ),
        ],
        execution_logic=(
            "Build and validate internally \u2192 prove with own companies \u2192 "
            "package as B2B offer \u2192 sell project fees \u2192 build recurring."
        ),
        adaptation_rules=[
            "If internal validation takes > 6 months, reduce scope to minimum viable system.",
            "If first B2B client doesn't close within 30 outreach conversations, refine offer packaging.",
            "After 3 B2B clients, standardize delivery and hire junior executor.",
        ],
    ),
    "real_estate_development": Template(
        id="real_estate_development",
        name="Real Estate Development",
        domain="business",
        level=3,
        description=(
            "Buy, develop, sell or hold real estate. "
            "Revenue from appreciation, rental, or project fees."
        ),
        primitive_ids=_BUSINESS_PRIMITIVE_BASE + ["resource", "time"],
        slots=_common_business_slots()
        + [
            TemplateSlot(
                id="property_type",
                name="Property Type",
                description="Type of property (residential, commercial, land)",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="strategy",
                name="Strategy",
                description="Investment strategy (flip, hold, develop, wholesale)",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="market_area",
                name="Market Area",
                description="Geographic market being targeted",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="capital_source",
                name="Capital Source",
                description="How acquisitions are funded",
                required=False,
                slot_type="text",
                default="Self-funded",
            ),
        ],
        execution_logic=(
            "Identify market \u2192 source deals \u2192 analyze unit economics \u2192 "
            "acquire \u2192 develop/improve \u2192 exit or hold."
        ),
        adaptation_rules=[
            "If deal flow < 3 viable properties per quarter, expand market or adjust criteria.",
            "If renovation costs exceed estimate by > 20%, build stricter due diligence checklist.",
            "After 3 successful exits, begin raising outside capital for larger projects.",
        ],
    ),
    "personal_brand": Template(
        id="personal_brand",
        name="Personal Brand / Creator",
        domain="business",
        level=3,
        description=(
            "Build audience through content. Monetize through products, services, "
            "or sponsorships. Brand IS the advertising for other ventures."
        ),
        primitive_ids=_BUSINESS_PRIMITIVE_BASE + ["signal", "feedback"],
        slots=_common_business_slots()
        + [
            TemplateSlot(
                id="content_platform",
                name="Content Platform",
                description="Primary platform for content distribution",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="brand_archetype",
                name="Brand Archetype",
                description="Brand archetype (mentor, rebel, builder, etc.)",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="monetization_path",
                name="Monetization Path",
                description="How the brand generates revenue (product placement, affiliate, direct sales, sponsorship)",
                required=True,
                slot_type="text",
            ),
            TemplateSlot(
                id="content_cadence",
                name="Content Cadence",
                description="How often content is published",
                required=False,
                slot_type="text",
                default="Daily",
            ),
        ],
        execution_logic=(
            "Define positioning \u2192 post consistently \u2192 grow audience \u2192 "
            "monetize through owned ventures first, then sponsorships."
        ),
        adaptation_rules=[
            "If engagement rate drops below 3% for 2 weeks, audit content angles and test new formats.",
            "If audience growth stalls, collaborate with 3 creators in adjacent niches.",
            "After 10K engaged followers, begin direct product placement for owned ventures.",
        ],
    ),
}


# ─── TemplateRegistry ────────────────────────────────────────────────────────


class TemplateRegistry:
    """Registry for composable template blueprints."""

    def __init__(self) -> None:
        self._templates: dict[str, Template] = dict(_TEMPLATES)

    def register(self, template: Template) -> None:
        """Add or overwrite a template in the registry."""
        self._templates[template.id] = template

    def get(self, template_id: str) -> Template | None:
        """Retrieve a template by id."""
        return self._templates.get(template_id)

    def list_by_domain(self, domain: str) -> list[Template]:
        """Return all templates in a given domain."""
        return [t for t in self._templates.values() if t.domain == domain]

    def instantiate(self, template_id: str, context: dict) -> TemplateInstance | None:
        """Create a TemplateInstance by filling slots from context dict."""
        template = self._templates.get(template_id)
        if not template:
            return None
        valid, missing = self.validate_slots(template_id, context)
        filled: dict[str, Any] = {}
        for slot in template.slots:
            if slot.id in context:
                filled[slot.id] = context[slot.id]
            elif slot.default is not None:
                filled[slot.id] = slot.default
        return TemplateInstance(
            template_id=template_id,
            filled_slots=filled,
            declared_context=context,
            org_id=context.get("org_id", ""),
        )

    def validate_slots(self, template_id: str, context: dict) -> tuple[bool, list[str]]:
        """Check which required slots are missing from context."""
        template = self._templates.get(template_id)
        if not template:
            return False, ["template not found"]
        missing: list[str] = []
        for slot in template.slots:
            if slot.required and slot.id not in context and slot.default is None:
                missing.append(slot.id)
        return len(missing) == 0, missing


# ─── Standalone test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    registry = TemplateRegistry()
    print(f"Total templates: {len(registry._templates)}")
    for t in registry.list_by_domain("business"):
        valid, missing = registry.validate_slots(t.id, {})
        print(f"  {t.id}: {len(t.slots)} slots, {len(missing)} required missing")
    # Test instantiation
    instance = registry.instantiate(
        "coaching_program",
        {
            "offer_name": "Example Product",
            "icp_description": "Men 18-25 who want discipline",
            "primary_channel": "Instagram DMs",
            "price_point": 750,
            "delivery_method": "Group coaching + community",
            "success_metric": "Client completes 90 days",
        },
    )
    if instance:
        print(f"\nInstance created: {instance.instance_id[:8]}...")
        print(f"  Filled slots: {len(instance.filled_slots)}")
        print(f"  Status: {instance.status}")
