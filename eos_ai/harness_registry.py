"""
HarnessRegistry — every tool, model, and agent that EOS can use.

Provides a single inventory of all integration points with their
status, required context layers, and env key for availability checks.

Usage:
    from eos_ai.harness_registry import HarnessRegistryManager, HarnessType
    hrm = HarnessRegistryManager()
    print(hrm.format_status())
    models = hrm.get_active_models()
"""

import os
from dataclasses import dataclass, field
from enum import Enum


class HarnessType(Enum):
    MODEL = 'model'         # LLMs
    TOOL = 'tool'           # external tools
    AGENT = 'agent'         # AI agents
    INTERFACE = 'interface' # user interfaces


@dataclass
class HarnessEntry:
    id: str
    name: str
    harness_type: HarnessType
    description: str
    status: str                             # active, inactive, coming
    requires_context: list = field(default_factory=list)
    provides: list = field(default_factory=list)
    config_key: str = ''


HARNESS_REGISTRY: dict[str, HarnessEntry] = {

    # ── MODELS ────────────────────────────────────────────────────────────────

    'claude': HarnessEntry(
        id='claude',
        name='Anthropic Claude',
        harness_type=HarnessType.MODEL,
        description='Available via CC subprocess (Max subscription). SDK key needs refresh.',
        status='degraded',
        requires_context=['all_layers'],
        provides=['world_class_reasoning'],
        config_key='ANTHROPIC_API_KEY',
    ),

    'gemini': HarnessEntry(
        id='gemini',
        name='Google Gemini 2.5 Flash',
        harness_type=HarnessType.MODEL,
        description='Primary fallback model via google.genai SDK',
        status='active',
        requires_context=['all_layers'],
        provides=['fast_reasoning', 'primary_fallback'],
        config_key='GOOGLE_API_KEY',
    ),

    'qwen_local': HarnessEntry(
        id='qwen_local',
        name='Qwen2.5:3b (Ollama)',
        harness_type=HarnessType.MODEL,
        description='Free local last-resort fallback model',
        status='active',
        requires_context=['all_layers'],
        provides=['local_reasoning'],
        config_key='OLLAMA_BASE_URL',
    ),

    # ── INTERFACES ────────────────────────────────────────────────────────────

    'discord': HarnessEntry(
        id='discord',
        name='Discord Bot',
        harness_type=HarnessType.INTERFACE,
        description='Primary voice + text interface',
        status='active',
        requires_context=['instance_layer'],
        provides=['voice_interface', 'text_interface', 'meeting_facilitation'],
        config_key='DISCORD_BOT_TOKEN',
    ),

    'telegram': HarnessEntry(
        id='telegram',
        name='Telegram Bot',
        harness_type=HarnessType.INTERFACE,
        description='Mobile text interface',
        status='active',
        requires_context=['instance_layer'],
        provides=['mobile_interface'],
        config_key='TELEGRAM_BOT_TOKEN',
    ),

    # ── TOOLS ─────────────────────────────────────────────────────────────────

    'groq_whisper': HarnessEntry(
        id='groq_whisper',
        name='Groq Whisper STT',
        harness_type=HarnessType.TOOL,
        description='Voice-to-text transcription',
        status='active',
        requires_context=[],
        provides=['speech_to_text'],
        config_key='GROQ_API_KEY',
    ),

    'scrapling': HarnessEntry(
        id='scrapling',
        name='Scrapling',
        harness_type=HarnessType.TOOL,
        description='Web research and scraping',
        status='active',
        requires_context=['instance_layer'],
        provides=['web_research'],
        config_key='',
    ),

    'apify': HarnessEntry(
        id='apify',
        name='Apify',
        harness_type=HarnessType.TOOL,
        description='Instagram DM monitor',
        status='active',
        requires_context=['instance_layer'],
        provides=['instagram_monitoring'],
        config_key='APIFY_API_TOKEN',
    ),

    'neon': HarnessEntry(
        id='neon',
        name='Neon PostgreSQL',
        harness_type=HarnessType.TOOL,
        description='Multi-tenant database',
        status='active',
        requires_context=[],
        provides=['persistent_memory', 'multi_tenant_isolation', 'knowledge_storage'],
        config_key='DATABASE_URL',
    ),

    # ── AGENTS ────────────────────────────────────────────────────────────────

    'claude_code': HarnessEntry(
        id='claude_code',
        name='Claude Code',
        harness_type=HarnessType.AGENT,
        description='Developer agent — builds EOS',
        status='active',
        requires_context=['platform_layer'],
        provides=['code_generation', 'system_building', 'debugging', 'deployment'],
        config_key='',
    ),

    'perplexity': HarnessEntry(
        id='perplexity',
        name='Perplexity Sonar',
        harness_type=HarnessType.MODEL,
        description='Real-time web search + synthesis. Used for world pulse market intel.',
        status='active',
        requires_context=[],
        provides=['web_search', 'market_intel'],
        config_key='PERPLEXITY_API_KEY',
    ),

    'groq_llm': HarnessEntry(
        id='groq_llm',
        name='Groq LLaMA 70B',
        harness_type=HarnessType.MODEL,
        description='Ultra-fast inference. Used for quick responses.',
        status='active',
        requires_context=[],
        provides=['fast_inference'],
        config_key='GROQ_API_KEY',
    ),

    'notebooklm': HarnessEntry(
        id='notebooklm',
        name='NotebookLM (Google)',
        harness_type=HarnessType.TOOL,
        description=(
            'Zero-hallucination knowledge base. '
            'Query uploaded documents with '
            'citation-backed answers from Gemini. '
            'Use for research and competitor intel.'
        ),
        status='active',
        requires_context=[],
        provides=[
            'grounded_research',
            'citation_backed_answers',
            'document_synthesis',
            'audio_overview_generation',
        ],
        config_key='',
    ),

    # ── PLANNED ───────────────────────────────────────────────────────────────

    'manus': HarnessEntry(
        id='manus',
        name='Manus Agent (Meta)',
        harness_type=HarnessType.AGENT,
        description=(
            'Fully autonomous agent acquired by Meta '
            'Dec 2025 for $2B+. Can browse web, '
            'analyze data, write code, execute '
            'complex multi-step tasks end-to-end. '
            'API access TBD post-acquisition. '
            'Monitor developers.facebook.com '
            'and manus.im for updates.'
        ),
        status='planned',
        requires_context=[],
        provides=['autonomous_execution'],
        config_key='MANUS_API_KEY',
    ),

    # ── COMING ────────────────────────────────────────────────────────────────

    'browser_agent': HarnessEntry(
        id='browser_agent',
        name='Browser Agent (Playwright)',
        harness_type=HarnessType.TOOL,
        description=(
            'Universal browser control. '
            'Operates any web tool without API. '
            'Powers Manus, Instagram, LinkedIn, '
            'and any web interface.'
        ),
        status='active',
        requires_context=[],
        provides=[
            'browser_control',
            'web_automation',
            'manus_access',
            'instagram_dm',
            'linkedin_outreach',
        ],
        config_key='',
    ),

    'twilio': HarnessEntry(
        id='twilio',
        name='Twilio Phone',
        harness_type=HarnessType.INTERFACE,
        description='Phone call interface',
        status='coming',
        requires_context=['instance_layer'],
        provides=['phone_interface'],
        config_key='TWILIO_API_KEY',
    ),
}


class HarnessRegistryManager:

    def __init__(self) -> None:
        self.registry = HARNESS_REGISTRY

    def get_active(self) -> list[HarnessEntry]:
        return [e for e in self.registry.values() if e.status == 'active']

    def get_by_type(self, harness_type: HarnessType) -> list[HarnessEntry]:
        return [e for e in self.registry.values() if e.harness_type == harness_type]

    def get_active_models(self) -> list[str]:
        return [
            e.id for e in self.get_by_type(HarnessType.MODEL)
            if e.status == 'active'
        ]

    def is_available(self, entry_id: str) -> bool:
        """Check if a harness entry is available based on env var and status."""
        entry = self.registry.get(entry_id)
        if not entry:
            return False
        if entry.config_key:
            return bool(os.getenv(entry.config_key))
        return entry.status == 'active'

    def get_available(self) -> list[HarnessEntry]:
        return [e for e in self.registry.values() if self.is_available(e.id)]

    def format_status(self) -> str:
        lines = ['EOS HARNESS STATUS:']
        for htype in HarnessType:
            entries = self.get_by_type(htype)
            if not entries:
                continue
            lines.append(f'\n{htype.value.upper()}:')
            for e in entries:
                available = self.is_available(e.id)
                status = '✅' if available else (
                    '⏳' if e.status == 'coming' else '❌'
                )
                lines.append(
                    f'  {status} {e.name}: {", ".join(e.provides[:2])}'
                )
        return '\n'.join(lines)
