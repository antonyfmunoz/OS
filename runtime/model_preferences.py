"""
Multi-model router with business context awareness and full human override.

Priority order (highest to lowest):
  1. forced_model   — per-call human override
  2. session_override — human session override
  3. per_task_overrides — human per-task override
  4. data_tier == 'confidential' — always local
  5. cost_mode resolution (auto → business stage, else explicit)
  6. cost_mode == 'free' / prefer_local → local
  7. cost_mode == 'economy' → Haiku (or Gemini for vision)
  8. cost_mode == 'performance' → best per task/modality

Human override always wins. Never crash. Always return a valid config.
"""

import os
from eos_ai.context import EOSContext
from eos_ai.db import get_conn


# ─── Provider configs ─────────────────────────────────────────────────────────

PROVIDER_CONFIGS: dict[str, dict] = {
    'claude-haiku': {
        'provider': 'anthropic',
        'model': 'claude-haiku-4-5-20251001',
        'best_for': ['classify', 'score', 'filter', 'extract', 'quick_analysis'],
        'cost_tier': 1,
        'min_revenue_usd': 0,
    },
    'claude-sonnet': {
        'provider': 'anthropic',
        'model': 'claude-sonnet-4-6',
        'best_for': ['generate', 'analyze', 'converse', 'outreach', 'content', 'research'],
        'cost_tier': 2,
        'min_revenue_usd': 0,
    },
    'claude-opus': {
        'provider': 'anthropic',
        'model': 'claude-opus-4-6',
        'best_for': ['strategy', 'architecture', 'high_stakes_decision', 'portfolio_advisory'],
        'cost_tier': 3,
        'min_revenue_usd': 0,
        # Opus allowed even at $0 for critical decisions — not blocked by revenue,
        # only by cost_mode
    },
    'perplexity-sonar': {
        'provider': 'perplexity',
        'model': 'sonar-pro',
        'best_for': ['market_research', 'competitor_intel', 'realtime_data', 'fact_check'],
        'cost_tier': 2,
        'capability': 'web_search',
        'api_key_env': 'PERPLEXITY_API_KEY',
        'min_revenue_usd': 0,
    },
    'gemini-flash': {
        'provider': 'gemini',
        'model': 'gemini-2.0-flash',
        'best_for': ['image_analysis', 'video_analysis', 'document_ocr', 'long_document'],
        'cost_tier': 1,
        'capability': 'vision',
        'api_key_env': 'GEMINI_API_KEY',
        'min_revenue_usd': 0,
    },
    'gemma-local': {
        'provider': 'ollama',
        'model': 'gemma3:4b',
        'best_for': ['voice_transcription', 'background_tasks', 'confidential_data',
                     'simple_classification'],
        'cost_tier': 0,
        'capability': 'local',
        'min_revenue_usd': 0,
    },
}

# ─── Business stage thresholds ────────────────────────────────────────────────
# These affect AUTO routing only — human overrides are unaffected.

BUSINESS_STAGES: dict[str, dict] = {
    'pre_revenue': {'max_revenue': 0,         'auto_cost_mode': 'economy'},
    'early':       {'max_revenue': 5000,       'auto_cost_mode': 'economy'},
    'growing':     {'max_revenue': 25000,      'auto_cost_mode': 'performance'},
    'scaling':     {'max_revenue': 100000,     'auto_cost_mode': 'performance'},
    'optimizing':  {'max_revenue': float('inf'), 'auto_cost_mode': 'performance'},
}

# Tasks that always deserve the best model regardless of business stage
ALWAYS_BEST = [
    'portfolio_advisory',
    'high_stakes_decision',
    'strategy',
    'architecture',
]

# Tasks that are fine on economy even in performance mode
ECONOMY_OK = [
    'classify', 'score', 'filter',
    'extract', 'background_tasks',
    'quick_analysis',
]


# ─── ModelPreferences ─────────────────────────────────────────────────────────

class ModelPreferences:

    def __init__(self, ctx: EOSContext) -> None:
        self.ctx = ctx
        self._prefs = self._load()
        self._business_context = self._load_business_context()

    # ─── Loaders ─────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        """Load model_preferences row for this org. INSERT default if missing."""
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "SELECT prefer_local, cost_mode, session_override, per_task_overrides "
                    "FROM model_preferences WHERE org_id = %s",
                    (self.ctx.org_id,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        'prefer_local':       bool(row['prefer_local']),
                        'cost_mode':          row['cost_mode'] or 'auto',
                        'session_override':   row['session_override'],
                        'per_task_overrides': dict(row['per_task_overrides'] or {}),
                    }
                # No row — insert defaults
                cur.execute(
                    "INSERT INTO model_preferences (org_id, cost_mode, prefer_local) "
                    "VALUES (%s, 'auto', false) "
                    "ON CONFLICT (org_id) DO NOTHING",
                    (self.ctx.org_id,),
                )
                return {
                    'prefer_local': False,
                    'cost_mode': 'auto',
                    'session_override': None,
                    'per_task_overrides': {},
                }
        except Exception as e:
            print(f"[ModelPreferences] _load failed: {e} — using defaults")
            return {
                'prefer_local': False,
                'cost_mode': 'auto',
                'session_override': None,
                'per_task_overrides': {},
            }

    def _load_business_context(self) -> dict:
        """Query ventures + org to determine business stage and auto cost mode."""
        total_revenue = 0.0
        venture_count = 0
        autonomy_stage = 'manual'

        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "SELECT SUM(monthly_revenue) as total_revenue, "
                    "AVG(monthly_revenue) as avg_revenue, "
                    "COUNT(*) as venture_count "
                    "FROM ventures WHERE org_id = %s",
                    (self.ctx.org_id,),
                )
                row = cur.fetchone()
                if row:
                    total_revenue = float(row['total_revenue'] or 0)
                    venture_count = int(row['venture_count'] or 0)

                # Try to get autonomy_stage from organizations
                try:
                    cur.execute(
                        "SELECT autonomy_stage FROM organizations WHERE id = %s",
                        (self.ctx.org_id,),
                    )
                    org_row = cur.fetchone()
                    if org_row and org_row.get('autonomy_stage'):
                        autonomy_stage = org_row['autonomy_stage']
                except Exception:
                    pass  # column may not exist yet — safe default

        except Exception as e:
            print(f"[ModelPreferences] _load_business_context failed: {e} — using defaults")

        # Map revenue → business stage
        if total_revenue <= 0:
            business_stage = 'pre_revenue'
        elif total_revenue <= 5000:
            business_stage = 'early'
        elif total_revenue <= 25000:
            business_stage = 'growing'
        elif total_revenue <= 100000:
            business_stage = 'scaling'
        else:
            business_stage = 'optimizing'

        auto_cost_mode = BUSINESS_STAGES[business_stage]['auto_cost_mode']

        return {
            'total_monthly_revenue': total_revenue,
            'business_stage':        business_stage,
            'auto_cost_mode':        auto_cost_mode,
            'venture_count':         venture_count,
            'autonomy_stage':        autonomy_stage,
        }

    # ─── Public accessors ────────────────────────────────────────────────────

    def get_business_context(self) -> dict:
        return self._business_context

    # ─── Core routing ────────────────────────────────────────────────────────

    def resolve_model(
        self,
        task_type: str,
        modality: str = 'text',
        data_tier: str = 'internal',
        require_realtime: bool = False,
        forced_model: str | None = None,
        task_criticality: str = 'normal',
    ) -> dict:
        """
        Return a provider config dict for the given task parameters.

        Priority order (highest wins):
          1. forced_model        — per-call human override
          2. session_override    — session-level human override
          3. per_task_overrides  — task-type human override
          4. confidential data   — always local
          5. cost mode resolution
          6. free / prefer_local — always local
          7. economy             — Haiku (or Gemini for vision)
          8. performance         — best per task/modality
        """
        # 1. forced_model — per-call human override
        if forced_model:
            config = self._find_config(forced_model)
            if config:
                return self._check_availability(config)
            # Not found in our configs — use it directly as anthropic model
            return {
                'provider': 'anthropic',
                'model': forced_model,
                'best_for': [],
                'cost_tier': 2,
            }

        # 2. session_override — human session override
        session = self._prefs.get('session_override')
        if session:
            config = self._find_config(session)
            if config:
                return self._check_availability(config)

        # 3. per_task_overrides — human per-task override
        task_override = self._prefs.get('per_task_overrides', {}).get(task_type)
        if task_override:
            config = self._find_config(task_override)
            if config:
                return self._check_availability(config)

        # 4a. No Anthropic key — everything goes local
        if not self._key_available('ANTHROPIC_API_KEY'):
            return PROVIDER_CONFIGS['gemma-local']

        # 4. Confidential data — always local
        if data_tier == 'confidential':
            return PROVIDER_CONFIGS['gemma-local']

        # 5. Determine effective cost mode
        cost_mode = self._prefs.get('cost_mode', 'auto')
        if cost_mode == 'auto':
            cost_mode = self._business_context['auto_cost_mode']
            # Critical tasks always get best, regardless of business stage
            if task_type in ALWAYS_BEST:
                cost_mode = 'performance'
            # Economy-ok tasks stay economy
            elif task_type in ECONOMY_OK and cost_mode == 'economy':
                cost_mode = 'economy'

        # 6. free / prefer_local — local only
        if cost_mode == 'free' or self._prefs.get('prefer_local'):
            return PROVIDER_CONFIGS['gemma-local']

        # 7. economy — Haiku or Gemini for vision
        if cost_mode == 'economy':
            if modality in ('image', 'video', 'document'):
                if self._key_available('GEMINI_API_KEY'):
                    return PROVIDER_CONFIGS['gemini-flash']
            return PROVIDER_CONFIGS['claude-haiku']

        # 8. performance — best per task/modality

        # Modality routing
        if modality in ('image', 'video', 'document'):
            if self._key_available('GEMINI_API_KEY'):
                return PROVIDER_CONFIGS['gemini-flash']
            return PROVIDER_CONFIGS['claude-sonnet']

        if modality == 'voice':
            return PROVIDER_CONFIGS['gemma-local']

        # Real-time research
        if require_realtime or task_type in (
            'market_research', 'competitor_intel', 'realtime_data', 'fact_check'
        ):
            if self._key_available('PERPLEXITY_API_KEY'):
                return PROVIDER_CONFIGS['perplexity-sonar']
            # Fallback: sonnet — real-time data not available
            return PROVIDER_CONFIGS['claude-sonnet']

        # Task-based routing
        if task_type in ALWAYS_BEST:
            return PROVIDER_CONFIGS['claude-opus']

        if task_type in ('generate', 'analyze', 'converse', 'outreach', 'content', 'research'):
            return PROVIDER_CONFIGS['claude-sonnet']

        # Default
        return PROVIDER_CONFIGS['claude-haiku']

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _find_config(self, model_name: str) -> dict | None:
        """Search PROVIDER_CONFIGS by key or by model field value."""
        if model_name in PROVIDER_CONFIGS:
            return PROVIDER_CONFIGS[model_name]
        for cfg in PROVIDER_CONFIGS.values():
            if cfg.get('model') == model_name:
                return cfg
        return None

    def _key_available(self, env_key: str) -> bool:
        return bool(os.getenv(env_key))

    def _check_availability(self, config: dict) -> dict:
        """If provider needs an API key and it's missing, fall back to gemma-local."""
        api_key_env = config.get('api_key_env')
        if api_key_env and not self._key_available(api_key_env):
            print(
                f"[ModelRouter] {config['model']} requires {api_key_env} "
                f"— falling back to gemma-local"
            )
            return PROVIDER_CONFIGS['gemma-local']
        # Anthropic models require ANTHROPIC_API_KEY
        if config.get('provider') == 'anthropic' and not self._key_available('ANTHROPIC_API_KEY'):
            print(
                f"[ModelRouter] {config['model']} requires ANTHROPIC_API_KEY "
                f"— falling back to gemma-local"
            )
            return PROVIDER_CONFIGS['gemma-local']
        return config

    # ─── Setters ─────────────────────────────────────────────────────────────

    def set_cost_mode(self, mode: str) -> None:
        valid = ('auto', 'free', 'economy', 'performance', 'manual')
        if mode not in valid:
            raise ValueError(f"cost_mode must be one of {valid}")
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "UPDATE model_preferences SET cost_mode = %s, updated_at = NOW() "
                    "WHERE org_id = %s",
                    (mode, self.ctx.org_id),
                )
        except Exception as e:
            print(f"[ModelPreferences] set_cost_mode DB write failed: {e}")
        self._prefs['cost_mode'] = mode

    def set_prefer_local(self, prefer: bool) -> None:
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "UPDATE model_preferences SET prefer_local = %s, updated_at = NOW() "
                    "WHERE org_id = %s",
                    (prefer, self.ctx.org_id),
                )
        except Exception as e:
            print(f"[ModelPreferences] set_prefer_local DB write failed: {e}")
        self._prefs['prefer_local'] = prefer

    def set_session_override(self, model: str | None) -> None:
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "UPDATE model_preferences SET session_override = %s, updated_at = NOW() "
                    "WHERE org_id = %s",
                    (model, self.ctx.org_id),
                )
        except Exception as e:
            print(f"[ModelPreferences] set_session_override DB write failed: {e}")
        self._prefs['session_override'] = model

    def set_task_override(self, task_type: str, model: str) -> None:
        overrides = dict(self._prefs.get('per_task_overrides', {}))
        overrides[task_type] = model
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "UPDATE model_preferences SET per_task_overrides = %s::jsonb, "
                    "updated_at = NOW() WHERE org_id = %s",
                    (str(overrides).replace("'", '"'), self.ctx.org_id),
                )
        except Exception as e:
            print(f"[ModelPreferences] set_task_override DB write failed: {e}")
        self._prefs['per_task_overrides'] = overrides

    def clear_task_override(self, task_type: str) -> None:
        overrides = dict(self._prefs.get('per_task_overrides', {}))
        overrides.pop(task_type, None)
        try:
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    "UPDATE model_preferences SET per_task_overrides = %s::jsonb, "
                    "updated_at = NOW() WHERE org_id = %s",
                    (str(overrides).replace("'", '"'), self.ctx.org_id),
                )
        except Exception as e:
            print(f"[ModelPreferences] clear_task_override DB write failed: {e}")
        self._prefs['per_task_overrides'] = overrides

    # ─── Summary ─────────────────────────────────────────────────────────────

    def get_current_summary(self) -> str:
        biz = self._business_context
        prefs = self._prefs
        cost_mode = prefs.get('cost_mode', 'auto')
        effective = cost_mode
        if cost_mode == 'auto':
            effective = (
                f"auto → {biz['auto_cost_mode']} "
                f"({biz['business_stage']}, "
                f"${biz['total_monthly_revenue']:,.0f}/mo)"
            )

        lines = [
            f"📊 Business stage: {biz['business_stage']}",
            f"💰 Monthly revenue: ${biz['total_monthly_revenue']:,.0f}",
            f"⚙️  Cost mode: {effective}",
            f"🏠 Prefer local: {prefs.get('prefer_local')}",
            f"🔄 Session override: {prefs.get('session_override') or 'None'}",
            "",
            "Model routing (current):",
        ]

        tasks_to_show = [
            ('strategy',  'text',  'internal',     False),
            ('generate',  'text',  'internal',     False),
            ('classify',  'text',  'internal',     False),
            ('research',  'text',  'internal',     True),
            ('analyze',   'image', 'internal',     False),
            ('generate',  'text',  'confidential', False),
        ]
        for task, mod, tier, rt in tasks_to_show:
            m = self.resolve_model(task, mod, tier, rt)
            flag = ''
            if mod != 'text':
                flag = f' ({mod})'
            if tier == 'confidential':
                flag = ' (confidential)'
            if rt:
                flag = ' (realtime)'
            lines.append(f"  {task}{flag} → {m['model']}")

        return '\n'.join(lines)
