"""Knowledge Layer Engine — behavioral distillation layers 6-17.

Layers 1-5 are domain knowledge (in knowledge_domains.py).
Layers 6-17 are behavioral: how to think, decide, and act in specific
contexts. Each layer is a set of principles that get injected into
agent context when the situation matches.

Injection point: CognitiveLoop PERCEIVE step (1c: behavioral context).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeLayer:
    """A behavioral knowledge layer with principles and trigger conditions."""

    layer_id: int
    name: str
    key: str
    principles: list[str]
    triggers: list[str]
    applies_to: list[str] = field(default_factory=list)


LAYERS: dict[str, KnowledgeLayer] = {
    "PSYCHOLOGICAL": KnowledgeLayer(
        layer_id=6,
        name="Psychological Foundations",
        key="PSYCHOLOGICAL",
        principles=[
            "People buy emotionally and justify rationally",
            "Social proof is the strongest persuasion lever — show others like them succeeding",
            "Loss aversion outweighs gain motivation 2:1 — frame around what they'll lose by not acting",
            "Cognitive load kills conversion — reduce decisions to binary choices",
            "Reciprocity drives engagement — give value before asking",
            "Status drives male behavior more than money — frame offers around identity and respect",
            "Commitment consistency: small yeses compound into big ones",
            "Scarcity increases perceived value — limit access genuinely, not artificially",
            "People remember how you made them feel, not what you said",
            "Mirror their language — use their words, not yours",
        ],
        triggers=[
            "persuade",
            "outreach",
            "sell",
            "close",
            "pitch",
            "convince",
            "influence",
            "negotiate",
            "message",
            "dm",
            "psychology",
        ],
        applies_to=["sales", "marketing", "customer_success"],
    ),
    "REAL_TIME_INTELLIGENCE": KnowledgeLayer(
        layer_id=7,
        name="Real-Time Intelligence",
        key="REAL_TIME_INTELLIGENCE",
        principles=[
            "Current data beats historical patterns when they conflict",
            "Signal decay: information loses value exponentially — act on fresh intel fast",
            "Verify before acting — single-source intelligence is hypothesis, not fact",
            "Market sentiment shifts faster than fundamentals — watch both",
            "Competitive intelligence is only useful if it changes your action",
            "Leading indicators predict, lagging indicators confirm — track both, act on leading",
            "Pattern interrupts signal regime change — escalate when established patterns break",
            "Real-time doesn't mean reactive — filter noise from signal before acting",
        ],
        triggers=[
            "trend",
            "market",
            "competitor",
            "news",
            "signal",
            "alert",
            "real-time",
            "current",
            "latest",
            "breaking",
        ],
        applies_to=["executive", "sales", "marketing", "operations"],
    ),
    "NEGOTIATION": KnowledgeLayer(
        layer_id=8,
        name="Negotiation Mastery",
        key="NEGOTIATION",
        principles=[
            "Never negotiate against yourself — let them make the first offer",
            "BATNA (Best Alternative To Negotiated Agreement) is your power — always know yours",
            "Anchor high — the first number shapes the entire negotiation",
            "Separate the person from the problem — be hard on issues, soft on people",
            "Ask open-ended questions to reveal their constraints",
            "Silence is a weapon — state your position and wait",
            "Create value before claiming it — expand the pie first",
            "Walk-away power is the strongest leverage — be willing to leave",
            "Multiple offers simultaneously reduce anchoring bias",
            "Document everything agreed — verbal agreements decay",
        ],
        triggers=[
            "negotiate",
            "deal",
            "contract",
            "pricing",
            "terms",
            "agreement",
            "partnership",
            "vendor",
            "discount",
            "counteroffer",
        ],
        applies_to=["executive", "sales", "legal", "hr"],
    ),
    "CRISIS": KnowledgeLayer(
        layer_id=9,
        name="Crisis Management",
        key="CRISIS",
        principles=[
            "First: stop the bleeding. Containment before investigation",
            "Communicate early and honestly — silence breeds speculation",
            "Assign one decision-maker per crisis — committees cause paralysis",
            "Document actions in real-time — memory degrades under stress",
            "Distinguish between urgent (time-sensitive) and important (impact-sensitive)",
            "Post-mortem without blame — learn from the system, not the person",
            "Every crisis has a window — act before it closes",
            "Preserve optionality — don't burn bridges in crisis mode",
            "Over-communicate internally, be measured externally",
            "The first narrative wins — control the story or someone else will",
        ],
        triggers=[
            "crisis",
            "emergency",
            "urgent",
            "fire",
            "outage",
            "incident",
            "breach",
            "critical",
            "failure",
            "disaster",
            "escalat",
        ],
        applies_to=["executive", "operations", "engineering", "customer_success"],
    ),
    "NETWORK_EFFECTS": KnowledgeLayer(
        layer_id=10,
        name="Network Effects",
        key="NETWORK_EFFECTS",
        principles=[
            "Value = n² — each new user increases value for all existing users",
            "Critical mass precedes virality — invest in seeding before expecting organic",
            "Two-sided networks need the hard side first (suppliers, creators, experts)",
            "Local network effects beat global ones — dominate a niche before expanding",
            "Switching costs compound over time — increase them through data lock-in and habit",
            "Network effects have a dark side — negative experiences also amplify",
            "Community is a network effect multiplier — invest in belonging",
            "Referral loops must be effortless — reduce friction to zero",
            "Cross-side effects: more buyers attract more sellers and vice versa",
        ],
        triggers=[
            "network",
            "viral",
            "referral",
            "community",
            "growth",
            "scale",
            "flywheel",
            "platform",
            "marketplace",
            "loop",
        ],
        applies_to=["product", "marketing", "executive"],
    ),
    "ORGANIZATIONAL_DESIGN": KnowledgeLayer(
        layer_id=11,
        name="Organizational Design",
        key="ORGANIZATIONAL_DESIGN",
        principles=[
            "Structure follows strategy — reorganize when strategy changes, not before",
            "Conway's Law: system design mirrors org structure — design both intentionally",
            "Span of control: 5-8 direct reports max per manager",
            "Every role needs clear authority, accountability, and metrics",
            "Hire for the role's future needs, not just current ones",
            "Culture is what you tolerate, not what you declare",
            "Information flow determines decision quality — reduce bottlenecks",
            "Cross-functional teams outperform functional silos for most work",
            "The first 10 hires define the culture for the next 100",
            "Remote-first requires 10x more written communication discipline",
        ],
        triggers=[
            "hiring",
            "team",
            "org",
            "structure",
            "department",
            "role",
            "management",
            "culture",
            "scale",
            "headcount",
        ],
        applies_to=["hr", "executive", "operations"],
    ),
    "BUSINESS_MODEL": KnowledgeLayer(
        layer_id=12,
        name="Business Model Innovation",
        key="BUSINESS_MODEL",
        principles=[
            "Revenue model determines company DNA — choose before building",
            "Subscription beats one-time: LTV compounds, churn is the enemy",
            "Monetize the thing customers value most — not the thing that's easiest to charge for",
            "Unit economics must work at unit scale before spending on growth",
            "Freemium conversion rate: 2-5% is standard — plan for it",
            "Price anchoring: offer 3 tiers, make the middle one the target",
            "Revenue diversification reduces risk but increases complexity — single until stable",
            "The best business model is the one your ICP expects",
            "Cohort analysis > aggregate metrics — new vs retained tell different stories",
        ],
        triggers=[
            "pricing",
            "revenue",
            "model",
            "subscription",
            "freemium",
            "monetize",
            "tier",
            "plan",
            "unit economics",
            "ltv",
            "cac",
        ],
        applies_to=["finance", "product", "executive"],
    ),
    "CULTURAL_INTELLIGENCE": KnowledgeLayer(
        layer_id=13,
        name="Cultural Intelligence",
        key="CULTURAL_INTELLIGENCE",
        principles=[
            "Cultural context determines communication effectiveness — adapt, don't assume",
            "High-context cultures communicate implicitly; low-context explicitly — match the receiver",
            "Time orientation varies: monochronic (linear, scheduled) vs polychronic (fluid, relational)",
            "Power distance shapes how feedback and disagreement are expressed",
            "Individualist vs collectivist cultures have different motivation frameworks",
            "Humor, formality, and directness are cultural variables, not universals",
            "Gen Z and Millennial communication norms differ from Gen X/Boomer defaults",
            "Digital-native audiences expect visual-first, text-second communication",
        ],
        triggers=[
            "culture",
            "demographic",
            "audience",
            "international",
            "diverse",
            "generation",
            "gen z",
            "millennial",
            "communication style",
        ],
        applies_to=["marketing", "customer_success", "hr", "sales"],
    ),
    "ESG": KnowledgeLayer(
        layer_id=14,
        name="ESG & Sustainability",
        key="ESG",
        principles=[
            "Sustainability is a business advantage, not a cost center",
            "Greenwashing destroys trust faster than no ESG at all",
            "Measure and report what matters — vanity metrics undermine credibility",
            "Supply chain accountability extends to every tier",
            "Stakeholder capitalism: employees, community, and environment are stakeholders too",
            "Regulatory compliance is the floor, not the ceiling",
            "Social impact creates differentiation in commoditized markets",
        ],
        triggers=[
            "sustainability",
            "esg",
            "social impact",
            "environment",
            "ethics",
            "responsible",
            "carbon",
            "diversity",
            "equity",
            "inclusion",
        ],
        applies_to=["executive", "operations", "legal"],
    ),
    "PERSONAL_PRODUCTIVITY": KnowledgeLayer(
        layer_id=15,
        name="Personal Productivity",
        key="PERSONAL_PRODUCTIVITY",
        principles=[
            "Structure over discipline — systems outperform willpower every time",
            "Context switching is the silent killer — batch similar tasks",
            "Energy management > time management — work with your biology",
            "The constraint is never time, it's attention — protect deep work blocks",
            "Decision fatigue is real — systemize routine decisions",
            "Weekly review is non-negotiable — reflection drives improvement",
            "Delegate everything below your hourly rate threshold",
            "Input quality determines output quality — garbage in, garbage out",
            "Accountability structures outperform solo discipline 3:1",
            "Progress is the ultimate motivator — track visible wins",
            "Two-minute rule: if it takes less than 2 minutes, do it now",
        ],
        triggers=[
            "productivity",
            "focus",
            "time management",
            "routine",
            "habit",
            "workflow",
            "efficiency",
            "schedule",
            "deep work",
            "overwhelm",
        ],
        applies_to=["executive", "operations", "hr"],
    ),
    "PARTNERSHIP": KnowledgeLayer(
        layer_id=16,
        name="Partnerships & Storytelling",
        key="PARTNERSHIP",
        principles=[
            "Strategic partnerships multiply reach — find complementary, not competitive partners",
            "Co-creation > co-marketing — build something together for stronger bonds",
            "Stories sell, features tell — lead with narrative, follow with proof",
            "Origin stories build trust — share the real why, not the polished version",
            "Storytelling structure: situation → tension → resolution → lesson",
            "User stories are more powerful than brand stories — amplify testimonials",
            "Every partnership needs clear value exchange — asymmetry breeds resentment",
            "Joint ventures require exit clauses written before entry",
            "Brand partnerships must share values, not just audiences",
        ],
        triggers=[
            "partnership",
            "collaborate",
            "story",
            "narrative",
            "brand story",
            "testimonial",
            "case study",
            "joint venture",
            "co-create",
        ],
        applies_to=["marketing", "sales", "executive"],
    ),
    "EXITS_INNOVATION": KnowledgeLayer(
        layer_id=17,
        name="Exits & Innovation Management",
        key="EXITS_INNOVATION",
        principles=[
            "Build to sell even if you never will — it forces operational excellence",
            "Innovation has three horizons: core (70%), adjacent (20%), transformational (10%)",
            "Exit multiples are driven by growth rate, retention, and market size — optimize all three",
            "Acquirers buy growth trajectories, not current revenue",
            "Innovation requires protected budgets — don't raid R&D for operations",
            "The Innovator's Dilemma: incumbents optimize existing, disruptors build new",
            "Strategic acquisitions: buy talent, technology, or market access — never just revenue",
            "Clean books, clean code, clean contracts — mess reduces exit valuation",
            "Dual-track: run the business and innovate simultaneously, with separate teams",
        ],
        triggers=[
            "exit",
            "acquisition",
            "sell",
            "innovation",
            "r&d",
            "valuation",
            "multiple",
            "growth rate",
            "horizon",
            "disrupt",
        ],
        applies_to=["executive", "finance", "product"],
    ),
}


class KnowledgeLayerEngine:
    """Behavioral distillation engine — selects and injects layers 6-17.

    Called from CognitiveLoop PERCEIVE step (1c: behavioral context).
    """

    def __init__(self) -> None:
        self._layers = LAYERS
        self._trigger_patterns: dict[str, re.Pattern[str]] = {}
        for key, layer in self._layers.items():
            pattern = "|".join(re.escape(t) for t in layer.triggers)
            self._trigger_patterns[key] = re.compile(pattern, re.IGNORECASE)

    def get_relevant_layers(
        self,
        context: str,
        department: str = "",
        top_n: int = 3,
    ) -> list[KnowledgeLayer]:
        """Find the most relevant behavioral layers for a context string."""
        scored: list[tuple[float, str]] = []

        for key, layer in self._layers.items():
            score = 0.0
            pattern = self._trigger_patterns[key]
            matches = pattern.findall(context)
            score += len(matches) * 10.0

            if department and department in layer.applies_to:
                score += 5.0

            if score > 0:
                scored.append((score, key))

        scored.sort(reverse=True)
        return [self._layers[key] for _, key in scored[:top_n]]

    def get_relevant_layer(
        self,
        context: str,
        department: str = "",
    ) -> KnowledgeLayer | None:
        """Return the single most relevant layer, or None."""
        layers = self.get_relevant_layers(context, department, top_n=1)
        return layers[0] if layers else None

    def format_for_injection(self, layers: list[KnowledgeLayer]) -> str:
        """Format selected layers for system prompt injection."""
        if not layers:
            return ""

        parts = []
        for layer in layers:
            principles = "\n".join(f"  - {p}" for p in layer.principles[:5])
            parts.append(f"[{layer.name}]\n{principles}")

        return "\n\n".join(parts)

    def inject(
        self,
        context: str,
        department: str = "",
        top_n: int = 2,
    ) -> str:
        """One-call method: find relevant layers and return injection string."""
        layers = self.get_relevant_layers(context, department, top_n=top_n)
        return self.format_for_injection(layers)

    def get_layer(self, key: str) -> KnowledgeLayer | None:
        """Get a specific layer by key."""
        return self._layers.get(key)

    def all_layers(self) -> list[dict[str, Any]]:
        """Return all layers as dicts for API/dashboard use."""
        return [
            {
                "layer_id": layer.layer_id,
                "name": layer.name,
                "key": layer.key,
                "principle_count": len(layer.principles),
                "trigger_count": len(layer.triggers),
                "applies_to": layer.applies_to,
            }
            for layer in self._layers.values()
        ]

    @property
    def layer_count(self) -> int:
        return len(self._layers)

    @property
    def principle_count(self) -> int:
        return sum(len(l.principles) for l in self._layers.values())
