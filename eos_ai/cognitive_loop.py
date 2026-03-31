"""
CognitiveLoop — full Perceive → Understand → Plan → Execute
→ Verify → Reflect → Learn → Store cycle.

Wraps AgentRuntime with authority gating, prompt enhancement,
quality verification, and reflection logging. Every AI task
in the system should enter through here rather than calling
AgentRuntime directly.

Usage:
    from eos_ai.cognitive_loop import CognitiveLoop, CognitiveResult
    from eos_ai.agent_runtime import TaskType

    ctx  = load_context_from_env()
    loop = CognitiveLoop(ctx)
    result = loop.run(
        raw_prompt="Analyze this lead's signal",
        agent="sales_agent",
        task_type=TaskType.ANALYZE,
        venture_id="lyfe_institute",
    )
    print(result.output)
    print(result.iterations)
    print(result.was_enhanced)
"""

from dataclasses import dataclass, field
from pathlib import Path
import os, sys, uuid, tempfile, time as _time

# ─── Spend cache ──────────────────────────────────────────────────────────────
# Queried at most once per minute to avoid a DB round-trip on every response.

_spend_cache:    dict  = {}
_spend_cache_ts: float = 0.0
_SPEND_CACHE_TTL = 60  # seconds

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from eos_ai.context import EOSContext, load_context_from_env
from eos_ai.agent_runtime import AgentRuntime, TaskType
from eos_ai.memory import AgentMemory
from eos_ai.authority_engine import AuthorityEngine
from eos_ai.venture_knowledge import VentureKnowledgeBase


@dataclass
class MultimodalInput:
    text: str | None = None
    file_path: str | None = None
    file_bytes: bytes | None = None
    images: list[bytes] | None = None
    audio_path: str | None = None
    document_bytes: bytes | None = None
    document_mime: str | None = None
    video_path: str | None = None
    modality: str = 'text'
    user_prompt: str | None = None


@dataclass
class CognitiveResult:
    status: str                        # 'completed' | 'pending_approval'
    output: str | None
    model_used: str = ''
    tokens_used: dict = field(default_factory=dict)
    skill_used: str | None = None
    interaction_id: str | None = None
    approval_id: str | None = None
    iterations: int = 1
    was_enhanced: bool = False
    authority: dict | None = None
    response_audio_path: str | None = None
    response_modality: str = 'text'
    input_modality: str = 'text'


def _get_neon_spend(org_id: str) -> dict:
    """
    Return accumulated spend from the interactions table: today, this month,
    and all-time. Cost is calculated from stored token counts × model rates
    (cost_usd in tokens_json is 0 for legacy rows — we recalculate always).

    Results are cached for _SPEND_CACHE_TTL seconds so this is cheap to
    call on every response.
    """
    global _spend_cache, _spend_cache_ts

    now = _time.monotonic()
    if _spend_cache and (now - _spend_cache_ts) < _SPEND_CACHE_TTL:
        return _spend_cache

    from eos_ai.db import get_conn
    from eos_ai.agent_runtime import COST_PER_MILLION_TOKENS

    fallback = {'today': 0.0, 'month': 0.0, 'all_time': 0.0}
    try:
        with get_conn(org_id) as cur:
            cur.execute(
                """
                SELECT
                    model_used,
                    SUM(COALESCE((tokens_json->>'prompt')::int, 0))      AS input_tokens,
                    SUM(COALESCE((tokens_json->>'completion')::int, 0))  AS output_tokens,
                    CASE
                        WHEN created_at >= date_trunc('day',   NOW() AT TIME ZONE 'UTC')
                            THEN 'today'
                        WHEN created_at >= date_trunc('month', NOW() AT TIME ZONE 'UTC')
                            THEN 'month'
                        ELSE 'older'
                    END AS bucket
                FROM interactions
                WHERE org_id = %s
                GROUP BY model_used, bucket
                """,
                (org_id,),
            )
            rows = cur.fetchall()

        totals: dict[str, float] = {'today': 0.0, 'month': 0.0, 'all_time': 0.0}
        default_rates = {'input': 3.00, 'output': 15.00}

        for row in rows:
            model  = row['model_used'] or ''
            rates  = COST_PER_MILLION_TOKENS.get(model, default_rates)
            inp    = (row['input_tokens']  or 0)
            out    = (row['output_tokens'] or 0)
            cost   = inp / 1_000_000 * rates['input'] + out / 1_000_000 * rates['output']
            bucket = row['bucket']

            if bucket == 'today':
                totals['today']    += cost
                totals['month']    += cost
                totals['all_time'] += cost
            elif bucket == 'month':
                totals['month']    += cost
                totals['all_time'] += cost
            else:
                totals['all_time'] += cost

        _spend_cache    = totals
        _spend_cache_ts = now
        return totals

    except Exception as e:
        print(f'[CognitiveLoop] spend query failed: {e}')
        return fallback


def format_response_footer(
    result,
    iterations: int = 1,
    was_enhanced: bool = False,
    original_prompt: str = '',
    enhanced_prompt: str = '',
    org_id: str | None = None,
) -> str:
    """
    Build a stats footer for any AgentResult or CognitiveResult.

    Appended to the output string so every response surfaced through
    Telegram or the gateway carries model, cost, latency, and (when
    the prompt was enhanced) the optimized version.
    """
    from eos_ai.agent_runtime import calculate_cost

    model        = getattr(result, 'model_used', None) or 'unknown'
    cost         = getattr(result, 'cost_usd', 0.0) or calculate_cost(
                       model, getattr(result, 'tokens_used', None) or {}
                   )
    duration     = getattr(result, 'duration_ms', 0) or 0
    skill        = getattr(result, 'skill_used', None) or '—'
    tokens       = getattr(result, 'tokens_used', None) or {}
    total_tokens = tokens.get('total', 0)

    model_display = {
        'claude-haiku-4-5-20251001': 'Haiku',
        'claude-sonnet-4-6':         'Sonnet',
        'claude-opus-4-6':           'Opus',
        'sonar-pro':                 'Perplexity',
        'gemini-2.0-flash':          'Gemini Flash',
        'qwen2.5:14b':               'Qwen 14B (local)',
    }.get(model, model)

    if cost == 0.0:
        cost_str = 'free (local)'
    elif cost < 0.001:
        cost_str = '<$0.001'
    else:
        cost_str = f'${cost:.4f}'

    dur_str = (
        f'{duration}ms' if duration < 1000
        else f'{duration / 1000:.1f}s'
    )

    lines = [
        '',
        '─' * 33,
        f'⚙  {model_display}',
        f'🪙  {cost_str}  ⏱  {dur_str}  📊  {total_tokens:,} tokens',
    ]
    if skill and skill != '—':
        lines.append(f'🔧  Skill: {skill}')
    if iterations > 1:
        lines.append(f'🔄  {iterations} iterations')
    if (
        was_enhanced
        and enhanced_prompt
        and enhanced_prompt.strip() != original_prompt.strip()
    ):
        lines.append(f'✨  Optimized prompt:')
        lines.append(f'    Original: {original_prompt}')
        lines.append(f'    Enhanced: {enhanced_prompt}')

    # Show running spend totals for paid models only
    if cost > 0.0 and org_id:
        spend = _get_neon_spend(org_id)
        def _fmt(v: float) -> str:
            return f'${v:.2f}' if v >= 0.01 else (f'${v:.4f}' if v > 0 else '$0.00')
        lines.append(
            f'💰  Today {_fmt(spend["today"])}'
            f'  ·  Month {_fmt(spend["month"])}'
            f'  ·  All-time {_fmt(spend["all_time"])}'
        )

    lines.append('─' * 33)

    return '\n'.join(lines)


class CognitiveLoop:
    """
    Full cognitive loop. Wraps AgentRuntime with:
      - PERCEIVE:  load venture context and recent memory
      - UNDERSTAND: prompt enhancement for vague inputs
      - PLAN:      authority check before any execution
      - EXECUTE:   agent runtime call
      - VERIFY:    quality loop (up to max_iterations)
      - REFLECT:   extract and log learnings
      - LEARN:     memory already handled by runtime
      - STORE:     Neon event for reflections
    """

    def __init__(self, ctx: EOSContext):
        self.ctx       = ctx
        self.runtime   = AgentRuntime()
        self.memory    = AgentMemory()
        self.authority = AuthorityEngine(ctx)
        # Session tracking for context compaction
        self.session_id: str        = str(uuid.uuid4())
        self._messages:  list[dict] = []
        self._last_transcript: str  = ''
        # Ordering — monotonic turn counter for in-order processing
        self._turn_counter: int = 0

    # ─── Public: run ─────────────────────────────────────────────────────────

    def run(
        self,
        input: str | MultimodalInput,
        session_id: str = None,
        cm=None,
        agent: str = 'executive_assistant',
        task_type: TaskType = None,
        venture_id: str | None = None,
        skill_name: str | None = None,
        workflow_id: str | None = None,
        channel: str = '',
        max_iterations: int = 3,
    ) -> CognitiveResult:

        # 0. PERCEIVE — resolve multimodal input to text
        self._last_transcript = ''

        if isinstance(input, MultimodalInput):
            modality = input.modality
            user_prompt_override = input.user_prompt

            if modality != 'text' and (
                input.file_path or input.audio_path
                or input.images or input.document_bytes
                or input.video_path
            ):
                from eos_ai.media_processor import MediaProcessor

                # write bytes to temp file if no path given
                tmp_path = None
                process_path = (
                    input.file_path or input.audio_path or input.video_path
                )

                if not process_path:
                    suffix_map = {
                        'image': '.jpg', 'document': '.pdf',
                        'video': '.mp4', 'audio': '.wav',
                    }
                    suffix = suffix_map.get(modality, '.bin')
                    raw = (
                        input.file_bytes
                        or (input.images[0] if input.images else None)
                        or input.document_bytes
                    )
                    if raw:
                        with tempfile.NamedTemporaryFile(
                            suffix=suffix, delete=False
                        ) as f:
                            f.write(raw)
                            tmp_path = f.name
                        process_path = tmp_path

                if process_path:
                    # get venture context for business-aware framing
                    biz_ctx = ''
                    if venture_id:
                        try:
                            biz_ctx = VentureKnowledgeBase.to_agent_context(
                                venture_id, detail='brief'
                            )
                        except Exception:
                            pass

                    mp = MediaProcessor()
                    text = mp.process(
                        file_path=process_path,
                        modality=modality,
                        user_prompt=user_prompt_override or '',
                        business_context=biz_ctx,
                    )

                    # preserve transcript for voice messages
                    if modality in ('voice', 'audio'):
                        self._last_transcript = text

                    # clean up temp file
                    if tmp_path:
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass
                else:
                    text = input.text or ''
            else:
                text = input.text or ''
        else:
            text = input
            modality = 'text'
            user_prompt_override = None

        # COMPACT — check if context window approaching limit before proceeding
        self._messages.append({"role": "user", "content": text})
        self._maybe_compact()

        # 1. PERCEIVE + 2. UNDERSTAND — compact system context
        # Model reasons from its intelligence + these anchoring facts.
        # Context shapes HOW it responds, not WHAT it says.
        _system_parts: list[str] = []
        _classified_signal: dict = {}

        # Layer 0: AI identity — universal, non-negotiable
        try:
            from eos_ai.ai_identity import AIIdentityEngine
            _system_parts.append(AIIdentityEngine().get_foundation_prompt())
        except Exception as _e:
            print(f'[AIIdentity] Load failed: {_e}')

        # Layer 0a: EA best practices — DEX operating standards
        try:
            from eos_ai.ea_best_practices import get_all_standards
            _standards = get_all_standards()
            _system_parts.append(f'## Operating Standards\n{_standards}')
        except Exception:
            pass

        # Layer 0b: Signal classification — higher signal gates lower signal
        try:
            from eos_ai.signal_hierarchy import SignalHierarchyEngine
            _she = SignalHierarchyEngine(ctx=self.ctx)
            _classified_signal = _she.classify_input(text or '', channel='unknown')
            _signal_ctx = _she.format_for_prompt(_classified_signal)
            if _signal_ctx:
                _system_parts.append(_signal_ctx)
        except Exception as _she_err:
            print(f'[CognitiveLoop] Signal classification skipped: {_she_err}')

        # Layer 0c: Quality requirements — pre-flight before generation
        try:
            from eos_ai.quality_gate import QualityTransformationGate, TransformationResult
            _qtg = QualityTransformationGate(self.ctx)
            _pre_result = TransformationResult(
                original='', transformed='',
                reality_score=0.5, intelligence_score=0.5,
                personalization_score=0.5, execution_score=0.5,
                overall_score=0.5, transformations_applied=[],
                is_world_class=False,
            )
            _quality_enhancement = _qtg.get_enhancement_prompt(
                _pre_result, _classified_signal
            )
            if _quality_enhancement:
                _system_parts.append(_quality_enhancement)
        except Exception as _qg_pre_err:
            print(f'[CognitiveLoop] Quality gate pre-flight skipped: {_qg_pre_err}')

        # Layer 1d: Instance context — tight founder summary (~50 tokens)
        # Stage, offer, channel, north star. Nothing else.
        try:
            from eos_ai.business_instance import get_ai_name
            from eos_ai.tenant import TenantManager
            _ai_name_ctx = get_ai_name(self.ctx)
            _tm = TenantManager(self.ctx)
            _bis_raw = _tm.format_for_prompt()
            _stage_line = next(
                (l.strip() for l in (_bis_raw or '').splitlines()
                 if 'stage' in l.lower()),
                'STAGE: 1 — zero sales, zero revenue',
            )
            _bis_tight = (
                f'FOUNDER: Antony  AI: {_ai_name_ctx}\n'
                f'COMPANIES: Lyfe Institute (coaching $750, Instagram DMs), '
                f'Empyrean Creative (AI services), Personal Brand\n'
                f'{_stage_line}\n'
                f'FOCUS: First sale, Lyfe Institute, Initiate Arena, Instagram DMs\n'
                f'NORTH STAR: $100K/month'
            )
            _system_parts.append(_bis_tight)
        except Exception:
            _system_parts.append(
                'FOUNDER: Antony  AI: DEX\n'
                'COMPANIES: Lyfe Institute (coaching $750, Instagram DMs), '
                'Empyrean Creative (AI services), Personal Brand\n'
                'STAGE: 1 — zero sales, zero revenue\n'
                'FOCUS: First sale, Lyfe Institute, Initiate Arena, Instagram DMs\n'
                'NORTH STAR: $100K/month'
            )

        # Layer 1e: GWS document context — founder's own written business docs
        try:
            _gws_path = Path('/opt/OS/data/gws_context.md')
            if _gws_path.exists():
                _gws_raw = _gws_path.read_text()
                # Inject a compact summary — first 600 chars covers all ventures
                _gws_preview = _gws_raw[:600].strip()
                if _gws_preview:
                    _system_parts.append(
                        f'FOUNDER DOCS (Google Drive):\n{_gws_preview}'
                    )
        except Exception:
            pass

        # Layer 1e-ii: Founder profile — synthesized from GWS docs
        try:
            _profile_path = Path('/opt/OS/data/founder_profile.md')
            if _profile_path.exists():
                _profile_raw = _profile_path.read_text()
                _profile_preview = _profile_raw[:300].strip()
                if _profile_preview:
                    _system_parts.append(
                        f'FOUNDER PROFILE:\n{_profile_preview}'
                    )
        except Exception:
            pass

        # Layer 1e-iii: Brand identity — who Antony is, what the brand is NOT
        try:
            _brand_path = Path('/opt/OS/data/brand_identity.md')
            if _brand_path.exists():
                _brand = _brand_path.read_text()
                _brand_preview = _brand[:500].strip()
                if _brand_preview:
                    _system_parts.append(
                        f'BRAND IDENTITY:\n{_brand_preview}'
                    )
        except Exception:
            pass

        # Layer 1e-iv: Funnel strategy — current state of each acquisition channel
        try:
            _funnel_path = Path('/opt/OS/data/funnel_strategy.md')
            if _funnel_path.exists():
                _funnel = _funnel_path.read_text()
                _funnel_preview = _funnel[:400].strip()
                if _funnel_preview:
                    _system_parts.append(
                        f'FUNNEL STRATEGY:\n{_funnel_preview}'
                    )
        except Exception:
            pass

        # Layer 1e-v: Workbook framework — design philosophy, not a built product
        try:
            _wb_path = Path('/opt/OS/data/workbook_framework.md')
            if _wb_path.exists():
                _wb = _wb_path.read_text()
                _wb_preview = _wb[:300].strip()
                if _wb_preview:
                    _system_parts.append(
                        f'WORKBOOK FRAMEWORK:\n{_wb_preview}'
                    )
        except Exception:
            pass

        # Layer 1e-vi: Cross-session behavioral patterns
        try:
            from eos_ai.pattern_engine import PatternEngine
            _pe = PatternEngine(self.ctx)
            _patterns = _pe.analyze(days_back=14)
            if _patterns:
                _system_parts.append(_pe.inject_to_context(_patterns))
        except Exception:
            pass

        # Layer 1e-vii: Key decisions (permanent record)
        try:
            from eos_ai.decision_log import DecisionLog
            _dl = DecisionLog(self.ctx)
            _decisions = _dl.get_recent_decisions(
                venture_id=venture_id or '',
                limit=5,
            )
            if _decisions:
                _system_parts.append(_dl.format_for_context(_decisions))
        except Exception:
            pass

        # Layer 1e-vii-b: DEX learnings — what Antony has taught DEX (cloning loop)
        try:
            from eos_ai.db import get_conn
            import json as _lrn_json
            with get_conn(ctx.org_id) as _lrn_cur:
                _lrn_cur.execute('''
                    SELECT payload_json FROM events
                    WHERE org_id = %s
                    AND event_type = 'dex_learning'
                    ORDER BY created_at DESC
                    LIMIT 10
                ''', (str(ctx.org_id),))
                _learnings = _lrn_cur.fetchall()
            if _learnings:
                _learning_lines = []
                for _lr in _learnings:
                    _lp = _lr['payload_json']
                    if isinstance(_lp, str):
                        _lp = _lrn_json.loads(_lp)
                    _lq = _lp.get('question', '')
                    _la = _lp.get('answer', '')
                    if _lq and _la:
                        _learning_lines.append(f'Q: {_lq} → A: {_la}')
                if _learning_lines:
                    _system_parts.append(
                        '## What Antony Has Taught DEX\n' +
                        '\n'.join(_learning_lines[:10])
                    )
        except Exception:
            pass

        # Layer 1e-viii: Recent NotebookLM insights — grounded research context
        try:
            from eos_ai.notebooklm_sync import NotebookLMSync
            _nls = NotebookLMSync(self.ctx)
            _nlm_insights = _nls.get_recent_insights(
                venture_id=venture_id or '',
                limit=3,
            )
            if _nlm_insights:
                _nlm_lines = [
                    f'NLM: {i.get("answer", "")[:100]}'
                    for i in _nlm_insights
                    if i.get('answer')
                ]
                if _nlm_lines:
                    _system_parts.append(
                        'NOTEBOOKLM INSIGHTS:\n' + '\n'.join(_nlm_lines)
                    )
        except Exception:
            pass

        # Layer 1f: Full stage primitives — rules, focus, not_yet (~300 tokens)
        try:
            from eos_ai.primitives import PrimitiveRegistry
            _pr = PrimitiveRegistry(self.ctx)
            _prim_ctx = _pr.compose_business_context(venture_id or 'lyfe_institute')
            _prim_block = _prim_ctx.strip()[:800] if _prim_ctx else ''
            if _prim_block:
                _system_parts.append(_prim_block)
        except Exception:
            pass

        # Layer 1d: North star + stage from BIS
        try:
            from eos_ai.business_instance import BusinessInstanceManager
            _bim = BusinessInstanceManager(self.ctx)
            _bis = _bim.get_bis(venture_id or 'lyfe_institute')
            if _bis and _bis.north_star:
                _bis_block = f'North star: {_bis.north_star}'
                if _bis.stage_name:
                    _bis_block += f' | Stage: {_bis.current_stage} ({_bis.stage_name})'
                _system_parts.append(_bis_block)
        except Exception:
            pass

        # Layer 1h: Hierarchy — role only, not full org chart
        try:
            from eos_ai.agent_hierarchy import AgentHierarchy
            _ah = AgentHierarchy()
            if agent and agent not in (
                'default', 'gateway.direct', 'prompt_engine', 'quality_checker'
            ):
                _h_full = _ah.format_for_prompt(agent)
                if _h_full:
                    _h_lines = [l for l in _h_full.splitlines() if l.strip()][:2]
                    _system_parts.append('\n'.join(_h_lines))
        except Exception:
            pass

        # Calendar context — today's schedule (injected last, highest recency)
        try:
            from eos_ai.gws_connector import GWSConnector
            gws = GWSConnector()
            events = gws.get_today_events()
            if events:
                cal_text = "TODAY'S SCHEDULE:\n"
                for e in events[:3]:
                    title = e.get('title', '')
                    start = e.get('start', 'all day')
                    if start and 'T' in str(start):
                        start = str(start).split('T')[1][:5]
                    cal_text += f'  {start} {title}\n'
                _system_parts.append(cal_text)
        except Exception:
            pass

        # Layer 1i: Human intelligence — relationship brief for any known person
        # mentioned in this message. Injected last so it's highest recency.
        try:
            from eos_ai.human_intelligence import HumanIntelligenceEngine
            _hi = HumanIntelligenceEngine(self.ctx)
            _text_lower = (text or '').lower()
            # Pull all usernames from human_profiles for this org
            from eos_ai.db import get_conn as _get_conn
            with _get_conn(self.ctx.org_id) as _hi_cur:
                _hi_cur.execute(
                    'SELECT username FROM human_profiles WHERE org_id = %s',
                    (self.ctx.org_id,),
                )
                _known = [r['username'] for r in _hi_cur.fetchall()]
            for _uname in _known:
                if _uname and _uname.lower() in _text_lower:
                    _rel_brief = _hi.get_relationship_context(_uname)
                    if _rel_brief:
                        _system_parts.append(_rel_brief)
                    break  # one person per message is enough
        except Exception:
            pass

        # Cross-session semantic memory — surface relevant past context
        try:
            _semantic_query = text or input or ''
            if _semantic_query and len(_semantic_query.split()) >= 3:
                _semantic_hits = self.memory.semantic_search(
                    query=_semantic_query,
                    limit=3,
                    min_similarity=0.60,
                    venture_id=venture_id,
                )
                if _semantic_hits:
                    _sem_block = "## Relevant Past Context (semantic memory)\n"
                    for _hit in _semantic_hits:
                        _sim = _hit.get('similarity', 0)
                        _date = (_hit.get('created_at') or '')[:10]
                        _input = str(_hit.get('input_summary') or '')[:150]
                        _output = str(_hit.get('output_summary') or '')[:200]
                        _sem_block += f"\n[{_date} | similarity: {_sim}]\n"
                        if _input:
                            _sem_block += f"Input: {_input}\n"
                        if _output:
                            _sem_block += f"Output: {_output}\n"
                    _system_parts.append(_sem_block)
        except Exception as _sem_err:
            pass  # Never let semantic memory break execution

        # Conversation history injection — what was said earlier this session
        try:
            if session_id and cm:
                _input_text = text if isinstance(text, str) else (input if isinstance(input, str) else '')
                _history = (
                        cm.format_channel_history_for_prompt(channel, query=_input_text)
                        if channel else cm.format_session_for_prompt(session_id)
                    )
                if _history and _history.strip():
                    _system_parts.append(
                        f"## Conversation History (this session)\n{_history}"
                    )
        except Exception as _hist_err:
            pass  # Never let history injection break execution

        # Martell pattern detection — behavioral alerts injected into system context
        try:
            from eos_ai.martell_patterns import detect_leverage_killer, check_solution_standard
            _assassin = detect_leverage_killer(text)
            if _assassin and _assassin.get('intervention'):
                _system_parts.append(
                    f'## Behavioral Alert\n{_assassin["intervention"]}\n'
                    f'Note: Surface this observation to the founder in your response.'
                )
            if check_solution_standard(text):
                _system_parts.append(
                    '## Solution Standard Alert\n'
                    'The founder is presenting a problem without options. '
                    'Apply the Solution Standard: acknowledge the problem, then ask '
                    'for or present 3 options with a clear recommendation.'
                )
        except Exception:
            pass

        # No List enforcement — flag anything Antony has committed to never doing
        try:
            from eos_ai.founder_rate import check_against_no_list
            _no_list_violations = check_against_no_list(text)
            if _no_list_violations:
                _system_parts.append(
                    f'## No List Alert\n'
                    f'The following items are on Antony\'s No List and appear '
                    f'in this message: {", ".join(_no_list_violations)}\n'
                    f'Flag this to Antony — he has committed to never doing these.'
                )
        except Exception:
            pass

        original_prompt = text
        enhanced = self._enhance_prompt(text)
        enhanced_prompt = enhanced
        system_extra = '\n\n'.join(_system_parts) if _system_parts else None

        # 3. PLAN — authority check before committing
        action_type = self._infer_action_type(task_type)
        authority_check = self.authority.check_can_execute(
            action_type, workflow_id
        )
        if not authority_check['can_execute'] and authority_check['requires_approval']:
            approval_id = self.authority.queue_for_approval(
                action_type,
                {'prompt': enhanced, 'agent': agent},
                agent,
            )
            return CognitiveResult(
                status='pending_approval',
                output=None,
                approval_id=approval_id,
                authority=authority_check,
            )

        # 4. EXECUTE — initial run through agent runtime
        result = self.runtime.run(
            task_type=task_type,
            prompt=enhanced,
            venture_id=venture_id,
            skill_name=skill_name,
            agent=agent,
            ctx=self.ctx,
            system_extra=system_extra,
        )

        # 5. VERIFY — quality loop
        iteration = 0
        while iteration < max_iterations:
            quality = self._verify_output(
                result.output, text, task_type
            )
            if quality['passes']:
                break
            result = self.runtime.run(
                task_type=task_type,
                prompt=(
                    f"{enhanced}\n\nPrior attempt:\n"
                    f"{result.output}\n\nIssues found:\n"
                    f"{quality['issues']}\n\nImprove:"
                ),
                venture_id=venture_id,
                skill_name=skill_name,
                agent=agent,
                ctx=self.ctx,
                system_extra=system_extra,
            )
            iteration += 1

        # 5b. STAGE FILTER — prepend stage-appropriate correction if needed
        _output_str = result.output or ''
        try:
            from eos_ai.primitives import ContextualReasoningEngine
            _cre       = ContextualReasoningEngine(self.ctx)
            _stage_ctx = _cre.get_current_context(venture_id or 'lyfe_institute')
            _advice_triggers = [
                'hire', 'build a team', 'outsource', 'automate outreach',
                'run paid', 'launch ads', 'paid ads', 'scale', 'raise',
                'invest', 'expand',
            ]
            _resp_lower  = _output_str.lower()
            _premature   = [t for t in _advice_triggers if t in _resp_lower]
            if _premature and _stage_ctx.get('stage') == 1:
                _eval = _cre.evaluate_principle(
                    f"Advice about: {', '.join(_premature)}", _stage_ctx
                )
                if not _eval.get('applies', True):
                    _warning = (
                        f"⚠️ Stage check: {_eval.get('warning', '')}\n"
                        f"What applies now: "
                        f"{_eval.get('what_applies_instead', '')}\n\n"
                    )
                    _output_str = _warning + _output_str
        except Exception:
            pass  # stage filter is enhancement — never block result

        # 5c. QUALITY GATE — score output through the four values and log
        try:
            from eos_ai.quality_gate import QualityTransformationGate
            _qtg_post = QualityTransformationGate(self.ctx)
            _transformation = _qtg_post.transform(
                output=_output_str,
                input_text=text,
                classified_signal=_classified_signal,
                bis_context={'current_stage': 1},
            )
            _output_str = _transformation.transformed
            print(
                f'[QualityGate] '
                f'R:{_transformation.reality_score:.2f} '
                f'I:{_transformation.intelligence_score:.2f} '
                f'P:{_transformation.personalization_score:.2f} '
                f'E:{_transformation.execution_score:.2f} '
                f'→ {_transformation.overall_score:.2f} '
                f'| WC:{_transformation.is_world_class}'
            )
        except Exception as _qg_post_err:
            pass  # quality gate is enhancement — never block result

        # 6. REFLECT — extract learnings from iteration count
        reflection = self._reflect(text, result.output, iteration)

        # 7. LEARN — log reflection to Neon if there's a real insight
        if reflection.get('insight'):
            try:
                self.memory.log_event(
                    org_id=self.ctx.org_id,
                    event_type='cognitive_reflection',
                    payload={
                        'prompt': text[:200],
                        'insight': reflection['insight'],
                        'iterations': iteration,
                        'agent': agent,
                    },
                )
            except Exception:
                pass  # reflection logging is enhancement — never block result

        # 7b. LEARN — permanently integrate conversation into knowledge base
        try:
            from eos_ai.knowledge_integrator import KnowledgeIntegrator
            from datetime import datetime, timezone as _tz
            _ki = KnowledgeIntegrator(self.ctx)
            if text and result.output:
                _ki.integrate(
                    content=(
                        f'Conversation:\n'
                        f'Founder: {text[:500]}\n'
                        f'System: {(result.output or "")[:500]}'
                    ),
                    source='telegram_conversation',
                    category='conversation',
                    metadata={
                        'task_type': str(task_type),
                        'agent':     agent or 'system',
                        'timestamp': datetime.now(_tz.utc).isoformat(),
                    },
                )
        except Exception:
            pass  # knowledge integration is enhancement — never block result

        # 8. STORE — handled by memory.log() inside runtime.run()

        was_enhanced = enhanced != text
        footer = format_response_footer(
            result=result,
            iterations=iteration + 1,
            was_enhanced=was_enhanced,
            original_prompt=original_prompt,
            enhanced_prompt=enhanced_prompt,
            org_id=self.ctx.org_id,
        )
        output_with_footer = _output_str + footer

        cognitive_result = CognitiveResult(
            status='completed',
            output=output_with_footer,
            model_used=result.model_used,
            tokens_used=result.tokens_used,
            skill_used=result.skill_used,
            interaction_id=result.interaction_id,
            iterations=iteration + 1,
            was_enhanced=was_enhanced,
            authority=result.authority,
        )

        # Append assistant response to session messages (without footer)
        if _output_str:
            self._messages.append({"role": "assistant", "content": _output_str})

        return cognitive_result

    # ─── Private helpers ─────────────────────────────────────────────────────

    def _maybe_compact(self) -> None:
        """
        Check if the session message list is approaching the token limit.
        If so, compact into a brief, seed the next context, and reset messages.
        User never sees the reset — conversation continues seamlessly.
        """
        try:
            from eos_ai.context_compaction import ContextCompactor
            compactor = ContextCompactor(self.ctx)
            if compactor.should_compact(self._messages):
                brief       = compactor.compact(self._messages, self.session_id)
                seed        = compactor.build_seeded_context(brief)
                # Reset messages with the seeded context as the first entry
                self._messages = [{"role": "system", "content": seed}]
                print(
                    f"[CognitiveLoop] Context compacted for session "
                    f"{self.session_id[:8]}..."
                )
        except Exception as e:
            print(f"[CognitiveLoop] Context compaction skipped: {e}")

    def _enhance_prompt(self, prompt: str) -> str:
        """
        Expand prompts shorter than the trust-adjusted threshold into precise,
        actionable form.

        Threshold shrinks as trust grows (system knows the user better):
          trust 1-2: expand if < 15 words (default — user is new)
          trust 3:   expand if < 11 words
          trust 4:   expand if <  7 words
          trust 5:   expand if <  5 words (minimal friction — shorthand mastered)

        Priority order:
          1. UserModel.get_intent_expansion() — uses founder's communication
             profile. Only active at trust_level >= 3. Takes priority because
             it understands domain-specific shorthand.
          2. Generic Haiku enhancement — fires when user model can't expand
             or trust_level is too low.
        """
        # Greeting guard — never enhance casual greetings or status checks
        # Must be first — before threshold check and before any expansion path
        _greeting_signals = [
            'hey', 'hi', 'hello', 'morning', 'good morning', 'gm',
            'what\'s up', 'whats up', 'sup', 'yo', 'how are',
            'how\'s it', 'hows it', 'what\'s going on', 'wassup',
            'good evening', 'good afternoon', 'evening', 'night',
        ]
        _p = prompt.lower().strip().rstrip('?!.')
        if any(_p == g or _p.startswith(g + ' ') or _p.startswith(g + ',') for g in _greeting_signals):
            return prompt  # Never enhance greetings

        try:
            from eos_ai.user_model import UserModel
            _um = UserModel(self.ctx)
            _trust = _um.get_trust_level()
            # trust 1→15, trust 2→13, trust 3→11, trust 4→9, trust 5→5
            threshold = max(5, 15 - (_trust * 2))
        except Exception:
            threshold = 15

        if len(prompt.split()) >= threshold:
            return prompt

        # Guard: never enhance greetings or casual messages
        _greeting_signals = [
            'hey', 'hi', 'hello', 'morning', 'good morning',
            'what\'s up', 'whats up', 'sup', 'yo', 'how are',
            'how\'s it', 'hows it', 'what\'s going on',
        ]
        _prompt_lower = prompt.lower().strip()
        if any(
            _prompt_lower.startswith(g) or _prompt_lower == g
            for g in _greeting_signals
        ):
            return prompt  # Never enhance greetings

        # 1. User model expansion (profile-aware, higher fidelity)
        try:
            from eos_ai.user_model import UserModel
            um       = UserModel(self.ctx)
            expanded = um.get_intent_expansion(prompt)
            if expanded != prompt:
                return expanded
        except Exception:
            pass  # user model is enhancement — never block execution

        # 2. Generic Haiku enhancement fallback
        try:
            # Build context-aware enhancement prompt
            _ctx_hint = ""
            try:
                _ctx_hint = (
                    f"Business context: Lyfe Institute (Initiate Arena, $750, "
                    f"90-day program, men 18-25). "
                    f"Empyrean Creative (AI infrastructure, creative studio). "
                    f"DEX is the name of the AI Executive Assistant — "
                    f"never expand DEX as decentralized exchange. "
                    f"Founder: Antony Munoz. North star: $10K/month. Stage 1 validation.\n\n"
                )
            except Exception:
                pass

            # Detect greetings and casual messages — never enhance these
            _greeting_signals = [
                'hey', 'hi', 'hello', 'morning', 'good morning',
                'what\'s up', 'whats up', 'sup', 'yo', 'how are',
                'how\'s it', 'hows it', 'what\'s going on',
            ]
            _prompt_lower = prompt.lower().strip()
            _is_greeting = any(
                _prompt_lower.startswith(g) or _prompt_lower == g
                for g in _greeting_signals
            )
            if _is_greeting:
                return prompt  # Never enhance greetings

            enhancement = self.runtime.run(
                task_type=TaskType.CLASSIFY,
                prompt=(
                    _ctx_hint +
                    "You are expanding a founder's shorthand message into a "
                    "precise, actionable execution prompt for their AI EA. "
                    "Preserve the original intent exactly. Do not add unrelated "
                    "context. Return ONLY the expanded prompt, nothing else:\n\n"
                    + prompt
                ),
                agent='prompt_engine',
            )
            expanded = enhancement.output.strip()
            return expanded if expanded else prompt
        except Exception:
            return prompt

    def _verify_output(
        self,
        output: str,
        original_prompt: str,
        task_type: TaskType,
    ) -> dict:
        """
        Quick quality check. Returns {'passes': bool, 'issues': str|None}.
        Scoring and classification tasks always pass — they are structured
        by design. Generation tasks get a Haiku PASS/FAIL review.
        """
        if len(output) < 50:
            return {'passes': False, 'issues': 'Output too short'}

        if task_type in (TaskType.SCORE, TaskType.CLASSIFY):
            return {'passes': True, 'issues': None}

        try:
            check = self.runtime.run(
                task_type=TaskType.CLASSIFY,
                prompt=(
                    "Does this output adequately address the request? "
                    "Reply with PASS or FAIL and one sentence why.\n\n"
                    f"Request: {original_prompt[:200]}\n\n"
                    f"Output: {output[:500]}"
                ),
                agent='quality_checker',
            )
            passes = 'PASS' in check.output.upper()
            return {
                'passes': passes,
                'issues': check.output if not passes else None,
            }
        except Exception:
            return {'passes': True, 'issues': None}  # never block on checker failure

    def _reflect(
        self,
        prompt: str,
        output: str,
        iterations: int,
    ) -> dict:
        """
        Extract insight from the run. Only meaningful when iterations > 0
        (i.e., first attempt failed quality check).
        """
        if iterations == 0:
            return {'insight': None}
        return {
            'insight': (
                f'Required {iterations + 1} iterations. '
                'Prompt may benefit from more specificity.'
            )
        }

    def process_in_order(
        self,
        input: 'str | MultimodalInput',
        agent: str,
        task_type: TaskType,
        venture_id: str | None = None,
        **kwargs,
    ) -> 'CognitiveResult':
        """
        Process a message and attach a monotonic turn number to the result.

        Callers that need strict ordering (e.g. the Telegram handler after
        the per-chat lock is acquired) should use this instead of run() so
        the result carries a turn_number they can use for logging / ordering
        assertions.

        turn N+1 is never assigned until turn N's run() returns, because
        this method is synchronous — the real sequencing guarantee comes from
        the asyncio per-chat lock in the Telegram handler.
        """
        turn = self._turn_counter
        self._turn_counter += 1
        result = self.run(
            input=input,
            agent=agent,
            task_type=task_type,
            venture_id=venture_id,
            **kwargs,
        )
        result.turn_number = turn  # type: ignore[attr-defined]
        return result

    def _infer_action_type(self, task_type: TaskType) -> str:
        """Map TaskType to authority engine action type string."""
        mapping = {
            'SCORE':    'analyze',
            'CLASSIFY': 'classify',
            'SUMMARIZE':'analyze',
            'ANALYZE':  'analyze',
            'GENERATE': 'draft_message',
        }
        key = task_type.value.upper() if hasattr(task_type, 'value') else str(task_type).upper()
        return mapping.get(key, 'analyze')

    def _map_task_to_domain(
        self,
        task_type: TaskType,
        context: str = '',
    ) -> str | None:
        """
        Map a TaskType + context to the most relevant knowledge domain key.
        Returns None when no strong mapping exists.

        GENERATE → business_sales (outreach/close context) or business_marketing (content)
        ANALYZE  → business_sales (lead/dm context) or business_strategy (general)
        CLASSIFY → human_psychology (default — classifying behavior/intent)
        SCORE    → human_psychology (lead scoring = reading human signals)
        SUMMARIZE → None (pure distillation, no domain enrichment needed)
        """
        ctx_lower = context.lower()
        task_val  = task_type.value if hasattr(task_type, 'value') else str(task_type)

        if task_val == 'generate':
            sales_words = ('outreach', 'dm', 'close', 'follow', 'prospect', 'lead', 'pitch')
            if any(w in ctx_lower for w in sales_words):
                return 'business_sales'
            return 'business_marketing'

        if task_val == 'analyze':
            sales_words = ('lead', 'dm', 'conversation', 'objection', 'close', 'pipeline')
            finance_words = ('revenue', 'cash', 'profit', 'unit economics', 'burn', 'cost')
            ops_words = ('process', 'workflow', 'bottleneck', 'automate', 'system')
            if any(w in ctx_lower for w in sales_words):
                return 'business_sales'
            if any(w in ctx_lower for w in finance_words):
                return 'business_finance'
            if any(w in ctx_lower for w in ops_words):
                return 'business_operations'
            return 'business_strategy'

        if task_val == 'classify':
            return 'human_psychology'

        if task_val == 'score':
            return 'human_psychology'

        return None
