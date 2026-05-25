"""Philosophy Lens Engine — codified lenses from PHILOSOPHY.md Section VII.

Lenses are optimization tools. Not rules. Not mandates.
Applied when they produce signal. Set aside when they don't.

Each lens encodes a thinking pattern that can be matched against
input text and injected into agent context as a guiding question.

Injection point: CognitiveLoop PERCEIVE step (1b: philosophical context).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class PhilosophyLens:
    """A single philosophy lens with trigger keywords and an application question."""

    id: int
    name: str
    description: str
    trigger_keywords: list[str] = field(default_factory=list)
    application_question: str = ""


LENSES: list[PhilosophyLens] = [
    PhilosophyLens(
        id=1,
        name="First principles",
        description="Reason from atomic truth.",
        trigger_keywords=[
            "why",
            "root cause",
            "fundamental",
            "assumption",
            "axiom",
            "first principles",
            "from scratch",
            "ground up",
            "basic",
            "foundation",
        ],
        application_question="What is the atomic truth here — the irreducible fact that everything else builds on?",
    ),
    PhilosophyLens(
        id=2,
        name="Systems thinking",
        description="See second and third order effects.",
        trigger_keywords=[
            "system",
            "ripple",
            "downstream",
            "side effect",
            "consequence",
            "cascade",
            "second order",
            "third order",
            "feedback loop",
            "interconnected",
        ],
        application_question="What are the second and third order effects of this action?",
    ),
    PhilosophyLens(
        id=3,
        name="Nature and reality mapping",
        description="Find patterns that already solved this problem.",
        trigger_keywords=[
            "nature",
            "pattern",
            "analogy",
            "precedent",
            "history",
            "biology",
            "evolution",
            "ecosystem",
            "natural",
            "organic",
        ],
        application_question="Where has nature or history already solved this exact problem?",
    ),
    PhilosophyLens(
        id=4,
        name="Leverage",
        description="Find the force that moves everything.",
        trigger_keywords=[
            "leverage",
            "multiplier",
            "force",
            "bottleneck",
            "constraint",
            "unlock",
            "keystone",
            "linchpin",
            "catalyst",
            "domino",
        ],
        application_question="What is the single force that, if applied here, moves everything else?",
    ),
    PhilosophyLens(
        id=5,
        name="Minimum effective dose",
        description="Smallest intervention, maximum result.",
        trigger_keywords=[
            "minimum",
            "simplest",
            "smallest",
            "efficient",
            "lean",
            "mvp",
            "essential",
            "pareto",
            "80/20",
            "less is more",
        ],
        application_question="What is the smallest possible intervention that produces the maximum result?",
    ),
    PhilosophyLens(
        id=6,
        name="Asymmetric returns",
        description="Find 10x upside, 1x downside.",
        trigger_keywords=[
            "asymmetric",
            "upside",
            "downside",
            "risk",
            "reward",
            "bet",
            "optionality",
            "convex",
            "antifragile",
            "tail risk",
        ],
        application_question="Where is the 10x upside with only 1x downside?",
    ),
    PhilosophyLens(
        id=7,
        name="Timing",
        description="Right knowledge at the right moment.",
        trigger_keywords=[
            "timing",
            "when",
            "moment",
            "window",
            "premature",
            "too late",
            "too early",
            "ripe",
            "ready",
            "season",
        ],
        application_question="Is this the right moment for this action, or is the timing wrong?",
    ),
    PhilosophyLens(
        id=8,
        name="Subtraction",
        description="Removal is often the highest leverage action.",
        trigger_keywords=[
            "remove",
            "subtract",
            "eliminate",
            "simplify",
            "cut",
            "prune",
            "reduce",
            "declutter",
            "excess",
            "bloat",
        ],
        application_question="What can be removed here to produce a better outcome than adding anything?",
    ),
    PhilosophyLens(
        id=9,
        name="Constraint as creative force",
        description="Limitations create direction and speed.",
        trigger_keywords=[
            "constraint",
            "limitation",
            "restricted",
            "scarce",
            "budget",
            "deadline",
            "boundary",
            "narrow",
            "focused",
            "creative constraint",
        ],
        application_question="How can the current constraints be used as a creative force rather than fought against?",
    ),
    PhilosophyLens(
        id=10,
        name="Lag",
        description="Effects follow causes with delay. Read signals with time awareness.",
        trigger_keywords=[
            "lag",
            "delay",
            "latency",
            "leading indicator",
            "lagging indicator",
            "patience",
            "compound",
            "accumulate",
            "long term",
            "delayed",
        ],
        application_question="Is there a time lag between the cause and the visible effect that needs to be accounted for?",
    ),
    PhilosophyLens(
        id=11,
        name="Resonance",
        description="Force in the direction of natural wiring compounds faster.",
        trigger_keywords=[
            "resonance",
            "strength",
            "natural",
            "talent",
            "wiring",
            "flow",
            "alignment",
            "passion",
            "energy",
            "zone of genius",
        ],
        application_question="Is this action aligned with natural wiring, or is it fighting against it?",
    ),
    PhilosophyLens(
        id=12,
        name="Emergence",
        description="Multiple lenses simultaneously produce something none would alone.",
        trigger_keywords=[
            "emergence",
            "synergy",
            "combination",
            "compound",
            "intersection",
            "convergence",
            "synthesis",
            "holistic",
            "gestalt",
            "more than the sum",
        ],
        application_question="What new possibility emerges when multiple forces are combined here?",
    ),
    PhilosophyLens(
        id=13,
        name="Adjacent possible",
        description="What is one step away that opens the most new moves?",
        trigger_keywords=[
            "adjacent",
            "next step",
            "unlock",
            "possibility",
            "opportunity",
            "expand",
            "open",
            "horizon",
            "bridge",
            "gateway",
        ],
        application_question="What is the one step away from here that opens the most new possibilities?",
    ),
    PhilosophyLens(
        id=14,
        name="Signal vs noise",
        description="The discipline of ignoring noise is as important as responding to signal.",
        trigger_keywords=[
            "signal",
            "noise",
            "distraction",
            "focus",
            "filter",
            "relevant",
            "irrelevant",
            "attention",
            "priority",
            "ignore",
        ],
        application_question="Is this signal or noise — and do I have the discipline to ignore it if it is noise?",
    ),
    PhilosophyLens(
        id=15,
        name="The gap as fuel",
        description="Distance between where you are and where you want to be is the engine.",
        trigger_keywords=[
            "gap",
            "distance",
            "ambition",
            "dissatisfaction",
            "hunger",
            "drive",
            "vision",
            "current state",
            "desired state",
            "motivation",
        ],
        application_question="How can the gap between current reality and the goal be used as fuel rather than frustration?",
    ),
    PhilosophyLens(
        id=16,
        name="Readiness",
        description="Stage is about the business. Readiness is about the person.",
        trigger_keywords=[
            "readiness",
            "prepared",
            "capable",
            "capacity",
            "maturity",
            "growth",
            "personal",
            "mindset",
            "skill gap",
            "development",
        ],
        application_question="Is the person ready for this — not just the business?",
    ),
]


class LensEngine:
    """Philosophy lens engine — matches and injects lenses from PHILOSOPHY.md.

    Called from CognitiveLoop PERCEIVE step (1b: philosophical context).
    """

    def __init__(self) -> None:
        self._lenses = LENSES
        self._patterns: list[tuple[PhilosophyLens, re.Pattern[str]]] = []
        for lens in self._lenses:
            pattern = "|".join(re.escape(kw) for kw in lens.trigger_keywords)
            self._patterns.append((lens, re.compile(pattern, re.IGNORECASE)))

    def match(self, text: str, top_n: int = 3) -> list[PhilosophyLens]:
        """Keyword-match which lenses apply to input text, ranked by hit count."""
        scored: list[tuple[float, int, PhilosophyLens]] = []

        for lens, pattern in self._patterns:
            hits = pattern.findall(text)
            if hits:
                scored.append((len(hits), lens.id, lens))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [lens for _, _, lens in scored[:top_n]]

    def apply(self, lens: PhilosophyLens) -> str:
        """Return the lens's application question as a prompt injection."""
        return f"[{lens.name}] {lens.application_question}"

    def inject(self, text: str, top_n: int = 2) -> str:
        """Match top-N lenses and format them as injectable context."""
        matched = self.match(text, top_n=top_n)
        if not matched:
            return ""

        parts: list[str] = []
        for lens in matched:
            parts.append(f"[{lens.name}] {lens.description}\n  -> {lens.application_question}")
        return "\n\n".join(parts)

    def get_lens(self, lens_id: int) -> PhilosophyLens | None:
        """Get a specific lens by ID."""
        for lens in self._lenses:
            if lens.id == lens_id:
                return lens
        return None

    def get_lens_by_name(self, name: str) -> PhilosophyLens | None:
        """Get a specific lens by name (case-insensitive)."""
        lower = name.lower()
        for lens in self._lenses:
            if lens.name.lower() == lower:
                return lens
        return None

    def all_lenses(self) -> list[PhilosophyLens]:
        """Return all lenses."""
        return list(self._lenses)

    @property
    def lens_count(self) -> int:
        return len(self._lenses)
