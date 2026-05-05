"""
KnowledgeLayerEngine — behavioral and strategic knowledge injection.

Foundation-level knowledge across 17 domains injected into the
CognitiveLoop PERCEIVE step based on task context signals.

Complements KnowledgeDomainRegistry (which handles domain state) —
knowledge_layers handles timeless behavioral principles.

Usage:
    from eos_ai.knowledge_layers import KnowledgeLayerEngine
    kle = KnowledgeLayerEngine()
    context = kle.get_relevant_layer('outreach', 'closing a DM conversation')
    # Returns: "BEHAVIORAL CONTEXT:\n• The real objection is never the stated one..."
"""

# ─── Foundation dicts ─────────────────────────────────────────────────────────

PSYCHOLOGICAL_FOUNDATIONS: dict[str, list[str]] = {
    'buyer_psychology': [
        'The real objection is never the stated one — find the fear beneath the words',
        'Cannot afford = fear of wasting money on something that wont work',
        'Need to think about it = not enough certainty or trust yet',
        'Identity drives buying decisions more than logic or price',
        'People buy transformation not features — before/after not specifications',
        'Loss aversion: losses hurt 2x more than equivalent gains feel good',
        'Anchoring: first number sets the psychological frame for all subsequent judgment',
        'Social proof: people follow what others do, especially peers',
        'Specificity creates believability — 34% more effective beats significantly more effective',
    ],
    'persuasion': [
        'Reciprocity: give first genuinely — the obligation to return is powerful',
        'Commitment and consistency: small commitments lead to larger ones',
        'Scarcity: limited availability increases desire — only works when real',
        'Authority: expertise and credentials reduce decision friction',
        'Liking: people say yes to those they like — similarity, genuine connection',
        'Unity: shared identity creates influence — we language, common mission',
    ],
}

NEGOTIATION_FOUNDATIONS: dict[str, list[str]] = {
    'core_concepts': [
        'BATNA determines your true power — strengthen it before negotiating',
        'Never negotiate with one option — create alternatives first',
        'Anchoring: whoever gives first number often wins — anchor high',
        'Concede in diminishing amounts — each concession smaller than the last',
        'Never concede without getting something in return — always conditional',
        'Silence after the ask wins deals — stop talking, wait',
    ],
    'tactics': [
        'Mirror: repeat last 3 words as question — they elaborate, you gain info',
        'Labeling: "It seems like you are concerned about..." validates without agreeing',
        'Calibrated questions: "How am I supposed to do that?" makes them solve your problem',
        'Flinch on first offer: visible reaction often produces immediate concession',
        'Tactical empathy: understand their perspective deeply — does not mean agree',
    ],
    'business_specific': [
        'Never give your number first in salary negotiation',
        'Discount requests: only give if you get something — commitment, testimonial, referral',
        'Multi-year contracts: ask 20-30% reduction — gives them certainty',
        'Payment terms are often easier to negotiate than price',
    ],
}

CRISIS_FOUNDATIONS: dict[str, list[str]] = {
    'response_principles': [
        'First 6 hours of PR crisis are critical — silence is interpreted as guilt',
        'Acknowledge immediately even without answers — we are investigating',
        'Delete nothing — screenshots exist, deletion amplifies suspicion',
        'One spokesperson only — centralize all communication',
        'Never say no comment — it implies hiding something',
        'Own it, explain it, fix it — blame never works',
    ],
    'financial_crisis': [
        'Sub-3-months runway: hiring freeze and spend review first day',
        'Accelerate receivables before cutting costs — fastest cash source',
        'Communicate proactively with investors before they ask',
        'Bridge financing order: insider bridge, venture debt, revenue financing, founder loan',
    ],
    'operational_crisis': [
        'Incident commander pattern: one person owns coordination, one technical, one comms',
        'Status page updated every 15 minutes during outage — silence breeds panic',
        'Blameless post-mortem: timeline, what worked, what failed, action items with owners',
        'Proactively offer SLA credits before customers ask',
    ],
}

NETWORK_EFFECTS_FOUNDATIONS: dict[str, list[str]] = {
    'core_principles': [
        'Value = n squared (Metcalfe) — every new user creates value for all existing users',
        'Network effects are the strongest moat — harder to replicate than technology or brand',
        'Two-sided platforms need both sides — the chicken-and-egg problem is the central challenge',
        'Tipping point: once critical mass is reached, growth becomes self-sustaining and cheap',
        'Winner-take-most dynamics emerge when multi-homing costs are high',
        'Platform beats pipeline — no inventory, scales exponentially, value created by users',
    ],
    'building_tactics': [
        'Solve chicken-and-egg: subsidize the harder side first, usually supply',
        'Single-player mode: build utility that works alone, add network layer second (Instagram)',
        'Start in one geography, achieve density, then expand (Uber started San Francisco only)',
        'Piggyback existing network: distribute through another platform to bootstrap (Airbnb on Craigslist)',
        'Come for the tool, stay for the network: utility first, community second',
        'Marquee users create social proof that pulls everyone else in',
    ],
    'defensive_tactics': [
        'Increase switching costs: data lock-in, integration depth, reputation systems',
        'Prevent multi-homing: exclusive supply, better experience on your platform only',
        'Disintermediation prevention: make platform more valuable than the transaction itself',
        'Platform governance: quality controls and trust systems protect the network from bad actors who destroy value for all',
    ],
}

ORGANIZATIONAL_DESIGN_FOUNDATIONS: dict[str, list[str]] = {
    'structure_principles': [
        'Structure follows strategy — org design should reflect how value is created',
        'Functional structure for single product, divisional for multiple products or markets',
        'Span of control: 5-7 direct reports optimal, wider for routine work, narrower for complex',
        'Add management layers when benefits of specialization exceed coordination costs',
        'Holacracy sounds good in theory, almost always reverts in practice',
        'Culture is not values on a wall — it is what behavior gets rewarded and tolerated',
    ],
    'decision_frameworks': [
        'Type 1 decisions (irreversible): deliberate, senior involvement, take time',
        'Type 2 decisions (reversible): fast, delegated, act on 70% info, reverse if wrong',
        'Amazon principle: most decisions are Type 2 — being slow is worse than occasionally wrong',
        'RACI: one Accountable per decision only — two accountables means no accountability',
        'Delegate everything doable at 70% quality — keep only vision, culture, key hiring, irreversible decisions',
        'Levels of delegation 1-6: told, research, recommend, act and report, act and update, act independently',
    ],
    'culture_building': [
        'Culture eats strategy for breakfast — Drucker was right',
        'What you tolerate is what you value — leaders define culture through what they allow, not just what they say',
        'Hire for values first, skills second — skills can be taught, values cannot',
        'Recognition programs that celebrate the right behaviors compound over time',
        'Psychological safety is the foundation of high-performing teams — Amy Edmondson research',
    ],
}

BUSINESS_MODEL_FOUNDATIONS: dict[str, list[str]] = {
    'model_patterns': [
        'Subscription beats transactional: predictable revenue, higher LTV, easier to plan',
        'Platform beats pipeline: others create value, you capture a percentage, scales without proportional cost',
        'Freemium only works if free users create value (viral loop) or convert at 2-5% or more',
        'Razor and blades: subsidize acquisition, profit on consumables — only works if you can lock in the consumable',
        'Marketplace take rate: start low for adoption, raise slowly post-tipping point, 25-30% is the proven ceiling',
        'Hidden revenue (Google, credit cards): free for users, monetize the other side — requires massive scale',
    ],
    'disruption_patterns': [
        'Low-end disruption: target over-served customers with good enough at much lower price, gradually move upmarket (Southwest)',
        'New-market disruption: serve non-consumers, make inaccessible accessible (PCs vs mainframes)',
        'Platform disruption: connect supply and demand, own no inventory, scale exponentially (Airbnb vs hotels)',
        'Subscription disruption: replace ownership with access, lower barrier, create recurring relationship (Adobe CC)',
        'Business Model Canvas: 9 blocks — always define all nine before building',
        'Pivot signal: poor unit economics plus low engagement plus no organic growth',
    ],
}

CULTURAL_INTELLIGENCE_FOUNDATIONS: dict[str, list[str]] = {
    'communication_styles': [
        'High-context cultures (Asia, Middle East, Latin America): meaning is implied, read between lines, relationship precedes business',
        'Low-context cultures (US, Germany, Scandinavia): explicit, direct, say what you mean, written contracts paramount',
        'Japan: "That will be difficult" = No. Silence = thinking not agreement. Never make anyone lose face publicly',
        'China: guanxi (relationship network) is essential infrastructure — build it before you need it',
        'Germany: punctuality is respect, data over opinion, thorough preparation expected, titles matter',
        'US: fast, transactional, relationship secondary to deal, first names immediately, contracts over relationship',
    ],
    'negotiation_by_culture': [
        'High power distance cultures (Malaysia, China, Mexico): always bring senior-to-senior, skip hierarchy at your peril',
        'Collectivist cultures: never put anyone on the spot, group saves face together, consensus required before agreement sticks',
        'Long-term oriented cultures (East Asia): first meeting is relationship only — expecting business is insulting',
        'Uncertainty avoidance cultures (Japan, France, Germany): bring complete data, detailed contracts, no ambiguity accepted',
        'Universal rule: do your research before entering any cross-cultural negotiation — ignorance is offensive not charming',
    ],
}

PARTNERSHIP_FOUNDATIONS: dict[str, list[str]] = {
    'principles': [
        'Strategic partnerships require win-win economics — if one side gains and one loses, the partnership will not survive',
        'Partner selection: complementary offerings, shared customers, no direct competition, compatible cultures',
        'Channel partnerships: resellers own the relationship, you own the product — never compete with your channel',
        'Technology integrations create switching costs for both sides — they are moat-building',
        'Partnership governance: executive sponsor, monthly steering, quarterly business review, clear decision rights documented',
        'Partnerships fail from: unequal commitment, misaligned incentives, unclear ownership, no dedicated resources',
    ],
    'storytelling': [
        'Customer is the hero, you are the guide — your product is Yoda not Luke Skywalker',
        'Origin story formula: personal problem → aha moment → struggle → breakthrough → mission born',
        'Problem-Agitation-Solution: state problem, make it visceral and real, then solve it',
        'Before-After-Bridge: where they are, where they could be, how to get there',
        'Specificity creates believability: 34% more effective beats significantly better',
        'Founder personal brand compounds: recruiting, fundraising, PR, sales, partnerships all become easier',
    ],
}

EXITS_INNOVATION_FOUNDATIONS: dict[str, list[str]] = {
    'exit_principles': [
        'Strategic buyers pay more than financial buyers — they pay for synergies you will never capture',
        'Build for acquisition 24 months out: clean financials, strong team not founder-dependent, no customer concentration above 15%',
        'Earnouts are a way to bridge valuation gap — but you must stay and perform to earn them',
        'IPO requires: $100M+ ARR, 30%+ growth, 70%+ gross margin, Rule of 40 above 40',
        'Secondary sale (selling shares while staying private) is underutilized liquidity option',
        'M&A due diligence will find everything — disclose issues proactively rather than have them discovered',
    ],
    'innovation_management': [
        'Three Horizons: 70% core H1, 20% adjacent H2, 10% transformational H3 — imbalance in either direction destroys value',
        'Stage-gate process prevents sunk cost investments in bad ideas — kill early and often',
        'Psychological safety is prerequisite for innovation — if failure is punished, only safe bets get proposed',
        'Most important metric: percent revenue from products launched in last 3 years — target 30-40%',
        'Innovation labs separate from core business often fail to integrate — structure matters',
        'Blameless post-mortems: timeline, what worked, what failed, action items with owners — never name individuals as causes',
    ],
}

PERSONAL_PRODUCTIVITY_FOUNDATIONS: dict[str, list[str]] = {
    'attention_management': [
        'Deep work (Cal Newport): 4 hours of uninterrupted focused work beats 8 hours of fragmented work — protect the blocks',
        'Single-tasking beats multitasking every time — task switching costs 23 minutes to refocus',
        'Most important task first: identify the one thing that matters most today before touching anything else',
        'Energy management beats time management: peak cognitive hours (usually morning) for highest leverage work only',
        'Maker schedule vs manager schedule: makers need half-day blocks, managers run on 1-hour meetings — never mix',
    ],
    'decision_quality': [
        'Bezos decision rule: Type 1 vs Type 2 — most decisions are reversible, treat them fast',
        'Regret minimization: imagine yourself at 80, which choice leads to least regret?',
        'Second-order thinking: ask what happens after the immediate consequence — most people stop at first order',
        'Pre-mortem: imagine it failed, write down every reason why — surfaces blind spots before they become real problems',
        'Kill your darlings: attachment to decisions already made is the enemy of good decisions going forward — sunk costs are sunk',
    ],
    'founder_specific': [
        'Founder mode (Chesky): stay connected to details that matter, skip layers when needed, do not delegate your way into irrelevance',
        'The constraint is always one thing — find it, fix it, find the next one (Theory of Constraints)',
        'Revenue solves most problems — when in doubt, focus on the thing closest to money',
        'Your calendar is your values made visible — what gets scheduled gets done',
        'Hire for trust first, competence second — incompetent trusted people can be trained, competent untrustworthy will destroy',
    ],
}

ESG_FOUNDATIONS: dict[str, list[str]] = {
    'business_case': [
        'ESG is not charity — it is risk management, talent attraction, customer loyalty, and increasingly, access to capital',
        'Greenwashing is worse than silence — specific and substantiated beats vague and aspirational every time',
        'Scope 3 emissions (value chain) are typically 70-90% of total footprint — you cannot hit net zero without addressing them',
        'DEI is a business advantage: diverse teams make better decisions — McKinsey data across 1000+ companies confirms',
        'Governance failures (Enron, WeWork, FTX) destroy more value faster than any other ESG category — governance is not optional',
    ],
    'practical_actions': [
        'Quick wins: LED lighting, recycling, digital over paper, renewable energy credits, pay equity audit — all take under 90 days',
        'Science-based targets (SBTi) are the credible standard — anything weaker is marketing not commitment',
        'Board diversity is not box-checking — cognitively diverse boards make fewer catastrophic decisions',
        'Whistleblower protection signals culture: anonymous reporting channel plus no retaliation policy means people will tell you what is wrong',
    ],
}


# ─── Engine ───────────────────────────────────────────────────────────────────

class KnowledgeLayerEngine:
    """
    Selects and formats behavioral principles relevant to the current task.
    Returns a compact injection string for the CognitiveLoop PERCEIVE step.
    """

    def __init__(self) -> None:
        self.psych            = PSYCHOLOGICAL_FOUNDATIONS
        self.negotiation      = NEGOTIATION_FOUNDATIONS
        self.crisis           = CRISIS_FOUNDATIONS
        self.network_effects  = NETWORK_EFFECTS_FOUNDATIONS
        self.org_design       = ORGANIZATIONAL_DESIGN_FOUNDATIONS
        self.business_model   = BUSINESS_MODEL_FOUNDATIONS
        self.cultural         = CULTURAL_INTELLIGENCE_FOUNDATIONS
        self.partnerships     = PARTNERSHIP_FOUNDATIONS
        self.exits_innovation = EXITS_INNOVATION_FOUNDATIONS
        self.personal         = PERSONAL_PRODUCTIVITY_FOUNDATIONS
        self.esg              = ESG_FOUNDATIONS

    def get_relevant_layer(
        self,
        task_type: str,
        context: str = '',
    ) -> str:
        """
        Return a formatted string of behavioral principles relevant to the
        given task_type and context. Empty string if nothing applies.

        Args:
            task_type: TaskType value string — 'analyze', 'generate', etc.
            context:   The prompt text — used for keyword matching.

        Returns:
            Multi-line string starting with 'BEHAVIORAL CONTEXT:' or ''.
        """
        ctx_lower = context.lower()
        relevant: list[str] = []

        # Sales / outreach / closing
        if any(w in ctx_lower for w in (
            'outreach', 'close', 'sell', 'objection', 'prospect',
            'lead', 'dm', 'convince', 'pitch', 'offer', 'buy',
        )):
            relevant.extend(self.psych['buyer_psychology'][:4])
            relevant.extend(self.negotiation['tactics'][:3])

        # Negotiation / pricing / deals
        if any(w in ctx_lower for w in (
            'negotiate', 'price', 'discount', 'contract',
            'vendor', 'salary', 'deal', 'terms',
        )):
            relevant.extend(self.negotiation['core_concepts'][:4])
            relevant.extend(self.negotiation['business_specific'][:2])

        # Crisis / problems
        if any(w in ctx_lower for w in (
            'crisis', 'issue', 'problem', 'emergency',
            'breach', 'complaint', 'outage', 'failing', 'broke',
        )):
            relevant.extend(self.crisis['response_principles'][:4])

        # Platform / network / marketplace
        if any(w in ctx_lower for w in (
            'platform', 'marketplace', 'network', 'viral',
            'two-sided', 'community', 'ecosystem',
        )):
            relevant.extend(self.network_effects['core_principles'][:3])
            relevant.extend(self.network_effects['building_tactics'][:2])

        # Team / org / management
        if any(w in ctx_lower for w in (
            'team', 'hire', 'delegate', 'structure',
            'management', 'culture', 'org', 'department',
        )):
            relevant.extend(self.org_design['structure_principles'][:2])
            relevant.extend(self.org_design['decision_frameworks'][:2])
            relevant.extend(self.org_design['culture_building'][:1])

        # Business model / revenue / pricing
        if any(w in ctx_lower for w in (
            'model', 'pricing', 'subscription',
            'marketplace', 'disrupt', 'pivot', 'freemium',
        )):
            relevant.extend(self.business_model['model_patterns'][:3])

        # Cultural / international
        if any(w in ctx_lower for w in (
            'international', 'global', 'japan', 'china', 'germany',
            'culture', 'cross-cultural', 'foreign', 'partnership abroad',
        )):
            relevant.extend(self.cultural['communication_styles'][:3])
            relevant.extend(self.cultural['negotiation_by_culture'][:2])

        # Partnership decisions
        if any(w in ctx_lower for w in (
            'partner', 'partnership', 'channel', 'reseller',
            'integration', 'alliance', 'collaborate',
        )):
            relevant.extend(self.partnerships['principles'][:3])

        # Storytelling / content / brand / pitch
        if any(w in ctx_lower for w in (
            'story', 'narrative', 'brand', 'founder',
            'content', 'message', 'pitch', 'explain',
        )):
            relevant.extend(self.partnerships['storytelling'][:3])

        # Exit / acquisition decisions
        if any(w in ctx_lower for w in (
            'exit', 'acquire', 'ipo', 'investor',
            'valuation', 'acquisition', 'm&a',
        )):
            relevant.extend(self.exits_innovation['exit_principles'][:3])

        # Innovation / product decisions
        if any(w in ctx_lower for w in (
            'innovate', 'new product', 'r&d', 'research',
            'experiment', 'launch', 'build', 'develop',
        )):
            relevant.extend(self.exits_innovation['innovation_management'][:3])

        # Focus / productivity / founder decisions
        if any(w in ctx_lower for w in (
            'focus', 'productivity', 'time', 'energy',
            'overwhelm', 'priority', 'schedule', 'constraint',
        )):
            relevant.extend(self.personal['attention_management'][:2])
            relevant.extend(self.personal['founder_specific'][:2])

        # Decision-making quality
        if any(w in ctx_lower for w in (
            'decision', 'choose', 'choice', 'should i',
            'tradeoff', 'option', 'risk', 'uncertain',
        )):
            relevant.extend(self.personal['decision_quality'][:3])

        # ESG / sustainability / governance
        if any(w in ctx_lower for w in (
            'esg', 'sustainability', 'diversity', 'governance',
            'ethics', 'compliance', 'emissions', 'dei',
        )):
            relevant.extend(self.esg['business_case'][:2])
            relevant.extend(self.esg['practical_actions'][:2])

        if not relevant:
            return ''

        lines = ['BEHAVIORAL CONTEXT:']
        seen: set[str] = set()
        for item in relevant:
            if item not in seen:
                lines.append(f'• {item}')
                seen.add(item)
            if len(lines) > 9:   # cap at 8 bullets
                break

        return '\n'.join(lines)
