"""
KnowledgeDomainRegistry — base equilibrium awareness layer.

Structured awareness of every domain the system operates in.
Uses horizontal-then-vertical methodology: scan all domains first
at low cost, go deep only on highest signal.

Domain knowledge is injected into the CognitiveLoop PERCEIVE step
when the input text triggers domain-specific keywords.

Domain state (current research) is persisted to the Neon skills table
under the naming convention: domain_{key}.

Usage:
    from runtime.knowledge_domains import KnowledgeDomainRegistry

    registry = KnowledgeDomainRegistry()

    # Find relevant domains for a given context
    relevant = registry.get_relevant_domains(
        context="should I run paid ads or organic outreach",
        task_type="analyze",
        top_n=3,
    )

    # Format for system prompt injection
    domain_context = registry.format_for_injection(relevant)

    # Check what needs updating
    due = registry.get_update_schedule()
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# ─── Domain catalog ───────────────────────────────────────────────────────────

DOMAINS: dict[str, dict] = {

    # REALITY
    'reality_physics': {
        'category': 'reality',
        'core_principles': [
            'Everything operates within physical laws',
            'Energy is conserved and transformed not created',
            'Systems tend toward entropy without input',
            'Cause and effect are universal',
        ],
        'current_focus': [
            'quantum computing implications for AI',
            'energy constraints on compute scaling',
        ],
        'connected_to': ['technology_ai', 'systems_thinking'],
        'injection_triggers': [
            'impossible', 'laws of nature', 'physical limit',
            'energy', 'compute', 'hardware',
        ],
        'update_frequency': 'quarterly',
    },

    'reality_mathematics': {
        'category': 'reality',
        'core_principles': [
            'Logic and proof are the foundation of truth',
            'Patterns repeat across scales and domains',
            'Probability governs uncertain outcomes',
            'Optimization requires defining the objective',
        ],
        'current_focus': [
            'statistical reasoning in AI outputs',
            'optimization theory in business systems',
        ],
        'connected_to': ['technology_ai', 'business_finance'],
        'injection_triggers': [
            'probability', 'statistics', 'optimize',
            'calculate', 'measure', 'formula', 'model',
        ],
        'update_frequency': 'quarterly',
    },

    'reality_biology': {
        'category': 'reality',
        'core_principles': [
            'Systems that adapt survive, rigid ones die',
            'Evolution selects for fitness to environment',
            'Feedback loops regulate living systems',
            'Cooperation and competition coexist',
        ],
        'current_focus': [
            'biomimicry in organizational design',
            'adaptation patterns in market evolution',
        ],
        'connected_to': ['systems_thinking', 'business_strategy'],
        'injection_triggers': [
            'adapt', 'evolve', 'survive', 'ecosystem',
            'organism', 'growth', 'decay', 'lifecycle',
        ],
        'update_frequency': 'quarterly',
    },

    # HUMAN
    'human_psychology': {
        'category': 'human',
        'core_principles': [
            'Behavior is driven by emotion first, logic second',
            'Identity drives decisions more than logic',
            'Pain avoidance outweighs pleasure seeking',
            'Social proof and belonging are primal needs',
            'People buy outcomes not features',
        ],
        'current_focus': [
            'identity-based behavior change',
            'psychological triggers for male 18-25 ICP',
            'shame vs aspiration in conversion',
        ],
        'connected_to': [
            'business_sales', 'business_marketing',
            'human_communication', 'personal_development',
        ],
        'injection_triggers': [
            'why do people', 'motivation', 'behavior',
            'belief', 'emotion', 'fear', 'desire',
            'identity', 'self-image', 'persuade',
        ],
        'update_frequency': 'monthly',
        'layers': {
            'timeless': [
                'Emotion drives decision, logic justifies it after',
                'Identity is the strongest motivator — people die for their self-image',
                'Pain avoidance outweighs pleasure-seeking by roughly 2:1',
                'Consistency bias: people act in alignment with public commitments',
            ],
            'historical': [
                'Cialdini: 7 influence principles — reciprocity, scarcity, authority, consistency, liking, social proof, unity',
                'Kahneman: System 1 (fast, emotional) dominates System 2 (slow, rational)',
                'Festinger: cognitive dissonance drives rationalization, not reason',
            ],
            'functional_expertise': [
                'Motivational interviewing: evoke change talk — do not argue for change',
                'Prochaska stages of change: precontemplation → contemplation → preparation → action → maintenance',
                'Identity change precedes behavior change — must shift the label first',
            ],
            'tactical': [
                'For 18-25 male ICP: activate shame of wasted potential, then offer identity upgrade',
                'Mirror their language exactly — "I know what I need to do, I just can\'t stay consistent"',
                'Reframe the buying decision as identity alignment, not a purchase',
            ],
            'psychological': [
                'The gap between current self and ideal self creates purchase motivation',
                'Belonging to a tribe of executors is more motivating than discipline itself',
                'Fear of missing out on who they could become beats fear of losing money',
            ],
            'current_state': '',
            'update_frequency': 'monthly',
        },
    },

    'human_physiology': {
        'category': 'human',
        'core_principles': [
            'Sleep is the foundation of all performance',
            'Physical state determines cognitive capacity',
            'Stress hormones impair long-term decision making',
            'Energy management matters more than time management',
        ],
        'current_focus': [
            'founder performance optimization',
            'decision fatigue prevention',
        ],
        'connected_to': ['personal_development', 'personal_mastery'],
        'injection_triggers': [
            'energy', 'tired', 'focus', 'health', 'sleep',
            'performance', 'stress', 'burnout',
        ],
        'update_frequency': 'monthly',
    },

    'human_communication': {
        'category': 'human',
        'core_principles': [
            'People hear what they expect not what is said',
            'Specificity builds trust, vagueness destroys it',
            'Questions are more powerful than statements',
            'Silence creates space for truth',
            'Stories transfer meaning better than facts',
        ],
        'current_focus': [
            'DM conversation patterns that book calls',
            'voice and tone for 18-25 male ICP',
            'objection handling language patterns',
        ],
        'connected_to': [
            'business_sales', 'human_psychology',
            'business_marketing',
        ],
        'injection_triggers': [
            'how to say', 'message', 'reply', 'tone',
            'communicate', 'explain', 'convince', 'frame',
        ],
        'update_frequency': 'weekly',
        'layers': {
            'timeless': [
                'Ask before you tell — earn the right to offer advice',
                'Specificity builds trust, vagueness destroys it',
                'The question you ask reveals what you actually think',
                'Silence is not awkward — it is pressure; let it work',
            ],
            'historical': [
                'Carnegie: genuine interest in the other person wins every conversation',
                'Rosenberg NVC: observations → feelings → needs → requests',
                'Epictetus: say what you mean, mean what you say, do not use words to impress',
            ],
            'functional_expertise': [
                'DM sequence: observation → question → bridge → offer',
                'Objection reframe: acknowledge → isolate → reframe to identity → close',
                'Active listening: reflect back exact words, not paraphrase — precision matters',
            ],
            'tactical': [
                'For 18-25 male: direct, no hedging, no fluff — respect their intelligence',
                'Open with a specific observation about their content or profile — no templates',
                'Never justify or defend the price — just state it and ask a question',
            ],
            'psychological': [
                'People feel heard when you reflect their exact words back',
                'Directness signals confidence — confidence triggers trust',
                'Asking for permission before advice increases compliance dramatically',
            ],
            'current_state': '',
            'update_frequency': 'weekly',
        },
    },

    # CIVILIZATION
    'civilization_history': {
        'category': 'civilization',
        'core_principles': [
            'Power concentrates then disrupts cyclically',
            'Technology shifts always create new winners',
            'Most innovations fail, some change everything',
            'Human nature is constant, context changes',
        ],
        'current_focus': [
            'AI as a technology shift comparable to internet',
            'creator economy historical patterns',
        ],
        'connected_to': ['technology_ai', 'business_strategy'],
        'injection_triggers': [
            'historically', 'precedent', 'pattern',
            'before', 'how did', 'what happened when',
        ],
        'update_frequency': 'quarterly',
    },

    'civilization_philosophy': {
        'category': 'civilization',
        'core_principles': [
            'First principles: question every assumption',
            'Reason from facts not from analogy',
            'The map is not the territory',
            'What cannot be measured cannot be managed',
            "Occam's razor: simplest explanation wins",
        ],
        'current_focus': [
            'first principles applied to business building',
            'stoicism for founder resilience',
        ],
        'connected_to': ['business_strategy', 'personal_mastery'],
        'injection_triggers': [
            'why', 'first principles', 'assumption',
            'logic', 'reason', 'truth', 'meaning', 'ethics',
        ],
        'update_frequency': 'quarterly',
    },

    'civilization_economics': {
        'category': 'civilization',
        'core_principles': [
            'Incentives drive all human behavior at scale',
            'Markets aggregate information imperfectly',
            'Scarcity determines value',
            'Compounding is the most powerful force in finance',
            'Second order effects dominate long term outcomes',
        ],
        'current_focus': [
            'creator economy monetization patterns',
            'AI impact on labor markets',
            'attention economy dynamics',
        ],
        'connected_to': [
            'business_finance', 'business_strategy',
            'technology_ai',
        ],
        'injection_triggers': [
            'market', 'price', 'value', 'incentive',
            'economy', 'monetize', 'revenue', 'profit',
        ],
        'update_frequency': 'monthly',
    },

    # BUSINESS
    'business_strategy': {
        'category': 'business',
        'core_principles': [
            'Strategy is what you say no to',
            'Competitive advantage must be defensible',
            'Focus beats diversification at early stage',
            'Distribution beats product in most markets',
            'The best strategy is clear enough to execute',
        ],
        'current_focus': [
            'OS Trinity differentiation strategy',
            'creator economy competitive positioning',
            'AI-native business model patterns',
        ],
        'connected_to': [
            'business_marketing', 'business_finance',
            'civilization_economics',
        ],
        'injection_triggers': [
            'strategy', 'compete', 'position', 'advantage',
            'market', 'differentiate', 'focus', 'priority',
        ],
        'update_frequency': 'weekly',
        'layers': {
            'timeless': [
                'Strategy is the art of deciding what not to do',
                'Competitive advantage must be defensible — not just different',
                'The constraint is always singular — find it, break it',
                'Optionality is valuable but inaction is expensive',
            ],
            'historical': [
                'Porter: competitive advantage comes from cost leadership, differentiation, or focus',
                'Christensen: disruption comes from below — build for the underserved',
                'Thiel: competition is for losers — build monopolies through unique insight',
            ],
            'functional_expertise': [
                'Theory of constraints: identify binding constraint, subordinate everything else to it',
                'Jobs to be done: people hire products to make progress in their lives',
                'Blue ocean: create uncontested market space rather than compete in red ocean',
            ],
            'tactical': [
                'For early stage: one channel, one offer, one ICP until $1M ARR',
                'Positioning statement: For [ICP] who [problem], [product] is [category] that [differentiator]',
                'Strategic priority stack: revenue → retention → referral → reach',
            ],
            'psychological': [
                'Founders fail strategy by chasing shiny objects — boredom masquerades as strategy',
                'The best moat is distribution, not product — people protect access',
                'Commitment creates strategy — ambiguity destroys it',
            ],
            'current_state': '',
            'update_frequency': 'weekly',
        },
    },

    'business_marketing': {
        'category': 'business',
        'core_principles': [
            'Marketing is making people aware of a solution',
            'The message must match the awareness level',
            'Attention is the scarce resource',
            'Specificity converts, vagueness repels',
            'Content that makes people feel seen converts',
        ],
        'current_focus': [
            'Instagram organic for male self-improvement',
            'hook formulas for 18-25 frustrated drifter',
            'content-to-DM pipeline optimization',
        ],
        'connected_to': [
            'business_sales', 'human_psychology',
            'human_communication', 'creative_content',
        ],
        'injection_triggers': [
            'marketing', 'content', 'hook', 'post',
            'audience', 'reach', 'awareness', 'brand',
            'instagram', 'social', 'copy', 'ads', 'paid',
        ],
        'update_frequency': 'weekly',
        'layers': {
            'timeless': [
                'Match message to awareness level — cold audiences need education, warm need offers',
                'Specificity converts, vagueness repels',
                'The hook determines whether the content gets consumed at all',
                'Great marketing makes the prospect feel understood before they know you',
            ],
            'historical': [
                'Ogilvy: the headline is 80 cents of every dollar spent',
                'Hormozi: $100M Offers — irresistible offers beat ad spend every time',
                'Gary Halbert: find a starving crowd, then serve them',
            ],
            'functional_expertise': [
                'Stages of awareness: Unaware → Problem aware → Solution aware → Product aware → Ready to buy',
                'Hook formula: pattern interrupt + identity challenge + promise',
                'Content-to-DM pipeline: hook creates comment, comment triggers DM, DM opens conversation',
            ],
            'tactical': [
                'Instagram hook: first 2 seconds must stop the scroll — use contrast or controversy',
                'Caption: hook → story → lesson → CTA in comment',
                'Post timing: 7am-9am and 6pm-9pm target timezone for max reach',
            ],
            'psychological': [
                'Identity-based content performs better than advice content for 18-25 male ICP',
                'Us vs them framing creates tribe and enemies — both are magnetic',
                'Aspiration + shame together create the strongest scroll-stop hooks',
                'Social proof de-risks the decision — show transformation not features',
            ],
            'current_state': '',
            'update_frequency': 'weekly',
        },
    },

    'business_sales': {
        'category': 'business',
        'core_principles': [
            'Sales is helping people make decisions',
            'Qualify hard, close easy',
            'The best salespeople talk less, listen more',
            'Objections are requests for more information',
            'Follow up is where deals are won',
        ],
        'current_focus': [
            'DM to call conversion patterns',
            'Initiate Arena objection handling',
            'pricing conversation for $750 offer',
        ],
        'connected_to': [
            'human_psychology', 'human_communication',
            'business_marketing',
        ],
        'injection_triggers': [
            'close', 'sell', 'prospect', 'lead', 'pipeline',
            'objection', 'follow up', 'dm', 'outreach',
            'conversion', 'book', 'call',
        ],
        'update_frequency': 'weekly',
        'layers': {
            'timeless': [
                'Qualify hard, close easy',
                'The real objection is never the stated one',
                'Silence after the ask wins deals',
                'Distribution beats product',
            ],
            'historical': [
                'Challenger Sale: best reps teach, tailor, take control',
                'Sandler: create no-pressure environment, let prospect sell themselves',
                'Hormozi: diagnose before prescribing — pain first, solution second',
            ],
            'functional_expertise': [
                'SPIN: Situation→Problem→Implication→Need-payoff questions',
                'MEDDIC: Metrics, Economic buyer, Decision criteria, Decision process, Identify pain, Champion',
                'Outbound: 5-7 touch sequence, change angle not just frequency',
            ],
            'tactical': [
                'Cold DM opener: specific observation about their content + genuine question',
                'Follow-up: 5 touches, each different angle — never just checking in',
                'Close: make direct ask, then shut up — whoever speaks first loses',
            ],
            'psychological': [
                'Identity drives decisions more than logic',
                'Pain avoidance outweighs pleasure seeking 2:1',
                'People buy transformation not features',
                'Social proof reduces decision friction',
            ],
            'current_state': '',
            'update_frequency': 'weekly',
        },
    },

    'business_finance': {
        'category': 'business',
        'core_principles': [
            'Revenue is vanity, profit is sanity, cash is king',
            'Unit economics must work before scaling',
            'Every expense is a bet on future return',
            'Financial discipline creates optionality',
        ],
        'current_focus': [
            'path to $10K/month Initiate Arena',
            'cost optimization for AI spend',
            'venture capital vs bootstrapping tradeoffs',
        ],
        'connected_to': ['business_strategy', 'civilization_economics'],
        'injection_triggers': [
            'cost', 'revenue', 'profit', 'cash', 'spend',
            'budget', 'invest', 'return', 'unit economics',
        ],
        'update_frequency': 'weekly',
        'layers': {
            'timeless': [
                'Revenue is vanity, profit is sanity, cash is king',
                'Unit economics must work before scaling — if the unit loses money, scale loses more',
                'Every expense is a bet on future return — demand the ROI case',
                'Compounding is the most powerful force — start early, reinvest consistently',
                'Cash flow timing kills more businesses than lack of profitability',
            ],
            'historical': [
                'Buffett: only invest in what you understand — circle of competence',
                'Graham: margin of safety — buy only when price is significantly below intrinsic value',
                'Dalio: diversification is the only free lunch — uncorrelated assets reduce risk without reducing return',
            ],
            'functional_expertise': [
                'Unit economics: LTV/CAC ratio must exceed 3:1 for sustainable growth',
                'Burn multiple: dollars burned per dollar of new ARR — below 1.5x is efficient',
                'Rule of 40: growth rate + profit margin should exceed 40% for healthy SaaS',
                'Working capital cycle: days receivable minus days payable determines cash requirements',
            ],
            'tactical': [
                'Early stage: weekly cash flow review, monthly P&L, quarterly projections',
                'Revenue recognition: only count cash in bank at early stage — never on invoiced',
                'Before raising prices: test 10-20% increase on next 5 sales — measure conversion delta',
                'Cost audit: every recurring expense justifies ROI every 90 days or gets cut',
            ],
            'psychological': [
                'Founders avoid looking at numbers when scared — force the weekly review regardless',
                'Revenue solves most psychological problems in a startup',
                'Sunk cost fallacy kills more businesses than bad strategy — kill what is not working',
            ],
            'current_state': '',
            'update_frequency': 'weekly',
        },
    },

    'business_operations': {
        'category': 'business',
        'core_principles': [
            'Systems beat willpower every time',
            'Automate the repeatable, humanize the unique',
            'Every bottleneck has a root cause',
            'Measure what matters, ignore what does not',
        ],
        'current_focus': [
            'AI automation patterns for solopreneurs',
            'workflow design for 2-hour work day',
            'delegation frameworks for small teams',
        ],
        'connected_to': ['technology_ai', 'business_strategy'],
        'injection_triggers': [
            'process', 'workflow', 'automate', 'system',
            'bottleneck', 'efficiency', 'operations',
            'delegate', 'scale',
        ],
        'update_frequency': 'weekly',
        'layers': {
            'timeless': [
                'Systems beat willpower — design for consistency not heroics',
                'The constraint determines throughput — fix it before anything else',
                'What gets measured gets managed, what gets managed gets improved',
                'Document before delegating — clarity is the currency of leverage',
            ],
            'historical': [
                'Toyota Production System: eliminate waste, create flow, pull not push',
                'EOS (Traction): vision + people + data + issues + process + traction',
                'Goldratt Theory of Constraints: find, exploit, subordinate, elevate, repeat',
            ],
            'functional_expertise': [
                'Process mapping: swimlane diagrams reveal handoff failures',
                'SOP structure: trigger → steps → owner → output → exceptions',
                'Automation decision: if it runs more than 3x/week and has fixed rules, automate it',
            ],
            'tactical': [
                'For solopreneur: identify the 3 tasks only you can do — delegate everything else',
                'Weekly ops rhythm: Sunday review → Monday priorities → Friday close-out',
                'First automation target: lead capture and follow-up (highest volume, most predictable)',
            ],
            'psychological': [
                'Founders resist SOPs because they feel like constraints on creativity',
                'Delegation anxiety = trust deficit = hire slow, fire fast',
                'The best operations are invisible — they only surface when they break',
            ],
            'current_state': '',
            'update_frequency': 'weekly',
        },
    },

    # TECHNOLOGY
    'technology_ai': {
        'category': 'technology',
        'core_principles': [
            'LLMs predict next tokens based on training data',
            'Context window is the working memory of the model',
            'Better prompts get better outputs consistently',
            'Models hallucinate when uncertain',
            'RAG solves the knowledge cutoff problem',
        ],
        'current_focus': [
            'frontier models: Claude Sonnet 4.6 Opus 4.6',
            'Gemini 2.0 Flash for vision and long context',
            'local models: Qwen 2.5 for cost-free tasks',
            'embedding models: Gemini embedding-001 768dim',
            'agent orchestration patterns',
            'MCP protocol for tool connections',
        ],
        'connected_to': [
            'technology_software', 'business_operations',
            'reality_mathematics',
        ],
        'injection_triggers': [
            'model', 'AI', 'LLM', 'claude', 'gemini', 'GPT',
            'agent', 'prompt', 'token', 'embedding', 'RAG',
            'fine-tune', 'training', 'inference',
        ],
        'update_frequency': 'weekly',
        'layers': {
            'timeless': [
                'Garbage in, garbage out — the quality of the prompt determines quality of output',
                'Context is memory — what the model knows at inference time is all it has',
                'Agents are LLMs + tools + memory + goals — each layer adds capability and complexity',
                'Intelligence is not in the model — it is in the system around the model',
            ],
            'historical': [
                'Attention is all you need (Vaswani 2017) — transformers replaced recurrence with attention',
                'GPT-3 (2020) proved scale creates emergent capabilities',
                'InstructGPT (2022) proved RLHF aligns models to intent better than raw pretraining',
            ],
            'functional_expertise': [
                'Prompt engineering: system prompt sets role, user prompt sets task, examples set format',
                'RAG pattern: embed query → retrieve top-k docs → inject into context → generate',
                'Agent loop: observe → plan → act → observe — each cycle is one reasoning step',
            ],
            'tactical': [
                'Use Haiku for classification/scoring, Sonnet for generation, Opus for complex reasoning',
                'Structured output via JSON mode reduces parsing failures by 80%+',
                'Few-shot examples in system prompt outperform instruction-only prompts for format compliance',
            ],
            'psychological': [
                'AI systems feel intelligent because they mirror — they reflect the quality of their context',
                'Trust in AI outputs requires understanding failure modes — hallucination, recency bias, sycophancy',
                'The best AI integrations are invisible — they extend human capability without replacing judgment',
            ],
            'current_state': '',
            'update_frequency': 'weekly',
        },
    },

    'technology_software': {
        'category': 'technology',
        'core_principles': [
            'Simple systems are more reliable than complex ones',
            'Premature optimization is the root of all evil',
            'Test what matters, skip what does not',
            'Code is read more than it is written',
            'The best architecture evolves, not is designed',
        ],
        'current_focus': [
            'Python async patterns for agent systems',
            'TypeScript for SaaS API layers',
            'PostgreSQL RLS for multi-tenant isolation',
            'Docker for operational script deployment',
        ],
        'connected_to': ['technology_ai', 'business_operations'],
        'injection_triggers': [
            'code', 'build', 'architecture', 'database',
            'API', 'deploy', 'debug', 'python', 'typescript',
        ],
        'update_frequency': 'weekly',
    },

    # CREATIVE
    'creative_storytelling': {
        'category': 'creative',
        'core_principles': [
            'Every story needs a hero with a problem',
            'Conflict creates engagement',
            'Show do not tell',
            'The best hooks make people feel seen',
            'Transformation is the ultimate story',
        ],
        'current_focus': [
            'short form video storytelling for Instagram',
            'Antony brand narrative: vigilante architect',
            'testimonial story structure for Initiate Arena',
        ],
        'connected_to': [
            'business_marketing', 'human_psychology',
            'creative_content',
        ],
        'injection_triggers': [
            'story', 'narrative', 'hook', 'angle', 'frame',
            'character', 'conflict', 'transformation',
        ],
        'update_frequency': 'weekly',
        'layers': {
            'timeless': [
                'The hero must want something — desire creates forward motion',
                'Conflict is story — remove it and nothing happens',
                'Show the transformation, not just the destination',
                'The villain makes the hero meaningful — create a worthy adversary',
            ],
            'historical': [
                "Campbell's Hero's Journey: call → threshold → trials → revelation → return",
                "Aristotle's Poetics: story = beginning + middle + end, plus reversal and recognition",
                'McKee: story is a metaphor for life — it must be true even if fictional',
            ],
            'functional_expertise': [
                'Short form structure: hook (1s) → setup (5s) → conflict (30s) → payoff (5s)',
                'Testimonial arc: before state → inciting moment → program → after state → call to action',
                'Brand narrative: origin wound → villain (societal lie) → hero methodology → promised land',
            ],
            'tactical': [
                'Instagram hook formula: identity statement + challenge + implicit promise in 3 words or less',
                'Comment-triggering content: ends on a question or provocation — never a conclusion',
                'Antony brand angle: the system builder vs the motivator — antihero of self-help',
            ],
            'psychological': [
                'Audiences self-insert into the hero — make the hero relatable, not admirable',
                'Tension creates dopamine — resolve it too fast and engagement drops',
                'The transformation the audience wants to see is the transformation they want for themselves',
            ],
            'current_state': '',
            'update_frequency': 'weekly',
        },
    },

    'creative_content': {
        'category': 'creative',
        'core_principles': [
            'Content that educates and entertains wins',
            'Consistency beats perfection',
            'Repurpose horizontally across platforms',
            'The best content makes people share',
        ],
        'current_focus': [
            'Instagram Reels for 18-25 male self-improvement',
            'Remotion for programmatic video production',
            'content-to-DM pipeline',
        ],
        'connected_to': ['business_marketing', 'creative_storytelling'],
        'injection_triggers': [
            'content', 'post', 'reel', 'video', 'caption',
            'copy', 'create', 'produce', 'publish',
        ],
        'update_frequency': 'weekly',
    },

    # PERSONAL
    'personal_development': {
        'category': 'personal',
        'core_principles': [
            'Identity change precedes behavior change',
            'Environment design beats willpower',
            'Skills compound over time like interest',
            'The obstacle is the way',
        ],
        'current_focus': [
            'self-mastery frameworks for LYFEOS',
            'habit architecture for founders',
            'masculine identity and purpose frameworks',
        ],
        'connected_to': [
            'human_psychology', 'personal_mastery',
            'human_physiology',
        ],
        'injection_triggers': [
            'grow', 'improve', 'develop', 'habit', 'discipline',
            'mastery', 'purpose', 'identity', 'become',
        ],
        'update_frequency': 'monthly',
    },

    'personal_mastery': {
        'category': 'personal',
        'core_principles': [
            'Mastery requires deliberate practice not repetition',
            'Feedback loops accelerate learning',
            'The plateau is where most people quit',
            'Excellence is a habit not an act',
        ],
        'current_focus': [
            'founder skill development priorities',
            'flow state for deep work',
        ],
        'connected_to': ['personal_development', 'human_psychology'],
        'injection_triggers': [
            'master', 'expert', 'skill', 'practice',
            'improve', 'level up', 'get better', 'elite',
        ],
        'update_frequency': 'monthly',
    },

    # SYSTEMS
    'systems_thinking': {
        'category': 'systems',
        'core_principles': [
            'Everything is a system with inputs and outputs',
            'Feedback loops determine system behavior',
            'Leverage points change systems dramatically',
            'Optimizing parts often degrades the whole',
            'Emergence: complex behavior from simple rules',
        ],
        'current_focus': [
            'EOS as a self-improving system',
            'compounding moat through data accumulation',
            'leverage points in the OS Trinity',
        ],
        'connected_to': [
            'reality_biology', 'business_strategy',
            'technology_ai',
        ],
        'injection_triggers': [
            'system', 'feedback', 'loop', 'leverage',
            'compound', 'emerge', 'optimize', 'whole',
        ],
        'update_frequency': 'monthly',
    },
}

# ─── Registry ─────────────────────────────────────────────────────────────────


class KnowledgeDomainRegistry:
    """
    Structured awareness of every domain the system operates in.

    On init, loads any previously saved domain state from the Neon skills
    table. On query, scores domains by trigger-word match and returns the
    top N most relevant domains with their core principles.
    """

    def __init__(self):
        self._domains = DOMAINS
        self._current_state: dict = self._load_state()

    # ─── State persistence ────────────────────────────────────────────────

    def _load_state(self) -> dict:
        """Load domain current_state from Neon skills table (domain_ prefix)."""
        try:
            from runtime.db import get_conn
            from runtime.context import load_context_from_env
            ctx = load_context_from_env()
            state: dict = {}
            with get_conn(ctx.org_id) as cur:
                cur.execute(
                    "SELECT name, content FROM skills WHERE name LIKE 'domain_%%' AND org_id = %s",
                    (ctx.org_id,),
                )
                for row in cur.fetchall():
                    key = row['name'].replace('domain_', '', 1)
                    try:
                        state[key] = json.loads(row['content'])
                    except Exception:
                        state[key] = {'content': row['content']}
            return state
        except Exception:
            return {}

    def save_domain_update(
        self,
        domain_key: str,
        current_state: str,
        ctx,
    ) -> bool:
        """
        Persist updated domain knowledge to the Neon skills table
        as a skill named domain_{key}. Returns True on success.
        """
        state_obj = {
            'content': current_state,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'domain_key': domain_key,
        }
        try:
            from runtime.db import get_conn
            with get_conn(ctx.org_id) as cur:
                cur.execute(
                    'SELECT id FROM skills WHERE org_id = %s AND name = %s',
                    (ctx.org_id, f'domain_{domain_key}'),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE skills
                        SET content = %s, version = version + 1
                        WHERE id = %s
                        """,
                        (json.dumps(state_obj), existing['id']),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO skills (org_id, name, content, version, created_at)
                        VALUES (%s, %s, %s, 1, NOW())
                        """,
                        (ctx.org_id, f'domain_{domain_key}', json.dumps(state_obj)),
                    )
            self._current_state[domain_key] = state_obj
            print(f'[KnowledgeDomains] Saved: domain_{domain_key}')
            return True
        except Exception as e:
            print(f'[KnowledgeDomains] save_domain_update failed: {e}')
            return False

    # ─── Query ────────────────────────────────────────────────────────────

    def get_domain(self, key: str) -> dict | None:
        """Return the static domain definition for a given key."""
        return self._domains.get(key)

    def all_domains(self) -> list[str]:
        """Return all registered domain keys."""
        return list(self._domains.keys())

    def get_relevant_domains(
        self,
        context: str,
        task_type: str = '',
        top_n: int = 3,
    ) -> list[dict]:
        """
        Score each domain by trigger-word matches against context and task_type.
        Returns top_n domains sorted by relevance score, each as:
            {key, category, core_principles, relevance_score, current_state?}
        """
        context_lower = context.lower()
        task_lower = task_type.lower()
        scored: list[tuple[int, str, dict]] = []

        for key, domain in self._domains.items():
            score = 0
            for trigger in domain['injection_triggers']:
                if trigger in context_lower:
                    score += 2
                if trigger in task_lower:
                    score += 1
            # Category name bonus
            if domain['category'] in context_lower:
                score += 1
            if score > 0:
                scored.append((score, key, domain))

        scored.sort(key=lambda x: x[0], reverse=True)

        result: list[dict] = []
        for score, key, domain in scored[:top_n]:
            entry: dict = {
                'key': key,
                'category': domain['category'],
                'core_principles': domain['core_principles'],
                'current_focus': domain['current_focus'],
                'relevance_score': score,
            }
            if key in self._current_state:
                entry['current_state'] = self._current_state[key]
            result.append(entry)

        return result

    def format_for_injection(self, domains: list[dict]) -> str:
        """
        Format domain knowledge for system prompt injection.
        Returns empty string when no domains are relevant.
        """
        if not domains:
            return ''
        lines = ['DOMAIN KNOWLEDGE:']
        for d in domains:
            lines.append(f"\n[{d['category'].upper()}: {d['key']}]")
            for p in d['core_principles']:
                lines.append(f'  \u2022 {p}')
            # Include current research state if available
            if d.get('current_state') and d['current_state'].get('content'):
                snippet = d['current_state']['content'][:300]
                lines.append(f'  Current: {snippet}')
        return '\n'.join(lines)

    # ─── Update scheduling ────────────────────────────────────────────────

    def get_update_schedule(self) -> list[str]:
        """
        Return domain keys that are due for an update based on
        update_frequency and the last_updated timestamp in current state.
        Domains with no recorded state are always due.
        """
        due: list[str] = []
        now = datetime.now(timezone.utc)
        thresholds = {'weekly': 7, 'monthly': 30, 'quarterly': 90}

        for key, domain in self._domains.items():
            freq = domain.get('update_frequency', 'monthly')
            state = self._current_state.get(key, {})
            last = state.get('last_updated')

            if not last:
                due.append(key)
                continue

            try:
                last_dt = datetime.fromisoformat(last)
                # Make naive datetimes timezone-aware
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                delta_days = (now - last_dt).days
                if delta_days >= thresholds.get(freq, 30):
                    due.append(key)
            except Exception:
                due.append(key)

        return due

    def get_layered_context(
        self,
        domain_key: str,
        layers_needed: list[str] | None = None,
    ) -> str:
        """
        Return formatted context from specified layers of a domain.
        Default: all layers.

        Layer keys: timeless, historical, functional_expertise,
                    tactical, psychological, current_state

        Format:
            TIMELESS: ...
            TACTICAL: ...
        """
        domain = self._domains.get(domain_key)
        if not domain:
            return ''
        layer_data: dict = domain.get('layers', {})
        if not layer_data:
            # Fallback: format core_principles as timeless layer
            principles = '\n'.join(f'  • {p}' for p in domain['core_principles'])
            return f'TIMELESS [{domain_key}]:\n{principles}'

        all_layers = ['timeless', 'historical', 'functional_expertise', 'tactical', 'psychological']
        selected   = layers_needed if layers_needed else all_layers

        lines = [f'KNOWLEDGE LAYERS — {domain_key}\n']
        labels = {
            'timeless':            'TIMELESS PRINCIPLES',
            'historical':          'PROVEN PATTERNS',
            'functional_expertise': 'DOMAIN EXPERTISE',
            'tactical':            'TACTICAL EXECUTION',
            'psychological':       'PSYCHOLOGICAL FOUNDATIONS',
        }
        for layer in selected:
            if layer == 'current_state':
                continue  # skip — injected separately
            items = layer_data.get(layer, [])
            if not items:
                continue
            label = labels.get(layer, layer.upper())
            lines.append(f'{label}:')
            for item in items:
                lines.append(f'  • {item}')
            lines.append('')

        # Current state at the end if present
        current = layer_data.get('current_state') or self._current_state.get(domain_key, {}).get('content', '')
        if current:
            lines.append(f'CURRENT INTEL:\n  {current[:300]}')

        return '\n'.join(lines).strip()

    def get_layered_injection(
        self,
        domain_key: str,
        task_type: str,
        context: str = '',
    ) -> str:
        """
        Select and format the most relevant layers for this task type.
        Returns a compact string for direct system-prompt injection.

        Always includes: timeless principles
        Adds tactical for: execute, outreach, close, generate
        Adds psychological for: persuade, outreach, close, content, analyze, classify, score
        Always appends: current_state if present
        """
        domain = self._domains.get(domain_key, {})
        layers = domain.get('layers', {})
        if not layers:
            return ''

        relevant: list[str] = []
        task_lower = task_type.lower()

        timeless = layers.get('timeless', [])
        if timeless:
            relevant.append(
                'TIMELESS:\n' + '\n'.join(f'• {p}' for p in timeless[:5])
            )

        if task_lower in ('execute', 'outreach', 'close', 'generate'):
            tactical = layers.get('tactical', [])
            if tactical:
                relevant.append(
                    'TACTICAL:\n' + '\n'.join(f'• {p}' for p in tactical[:5])
                )

        if task_lower in ('persuade', 'outreach', 'close', 'content',
                          'analyze', 'classify', 'score', 'generate'):
            psych = layers.get('psychological', [])
            if psych:
                relevant.append(
                    'PSYCHOLOGY:\n' + '\n'.join(f'• {p}' for p in psych[:3])
                )

        current = (
            layers.get('current_state')
            or self._current_state.get(domain_key, {}).get('content', '')
        )
        if current:
            relevant.append(f'CURRENT:\n{current[:300]}')

        return '\n\n'.join(relevant)

    def get_status_report(self) -> str:
        """
        Human-readable status of all domains — for /domains Telegram command.
        Shows update recency and current_focus per domain.
        """
        lines = [f'KNOWLEDGE DOMAINS ({len(self._domains)} registered)\n']
        by_category: dict[str, list[str]] = {}
        for key, domain in self._domains.items():
            cat = domain['category']
            by_category.setdefault(cat, []).append(key)

        for cat, keys in sorted(by_category.items()):
            lines.append(f'\n{cat.upper()}')
            for key in keys:
                domain = self._domains[key]
                state = self._current_state.get(key)
                if state and state.get('last_updated'):
                    last = state['last_updated'][:10]
                    status = f'updated {last}'
                else:
                    status = 'never updated'
                freq = domain.get('update_frequency', 'monthly')
                lines.append(f'  {key} [{freq}] — {status}')

        due = self.get_update_schedule()
        lines.append(f'\nDue for update: {len(due)}/{len(self._domains)}')
        return '\n'.join(lines)
