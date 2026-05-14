"""
SelfAwarenessEngine — EOS auto-reorganizes itself when anything changes.

Every state change has consequences across Discord, Notion, agents, and config.
This engine handles all of them automatically without being told.

From PHILOSOPHY.md: "The AI runs the business. The founder directs it."

Change types:
    stage_change, primitive_unlocked, primitive_locked, agent_added,
    agent_removed, hire_made, offer_changed, channel_changed, icp_changed,
    north_star_changed, company_added, revenue_milestone, first_sale,
    os_subscription

Usage:
    from runtime.self_awareness import SelfAwarenessEngine, SystemChange, ChangeType
    sae = SelfAwarenessEngine(ctx)
    change = sae.detect_change_from_text("I closed my first client today", "lyfe_institute")
    if change:
        import asyncio
        asyncio.run(sae.process_change(change))
"""

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


# ─── Change types ─────────────────────────────────────────────────────────────

class ChangeType(Enum):
    STAGE_CHANGE             = 'stage_change'
    PRIMITIVE_UNLOCKED       = 'primitive_unlocked'
    PRIMITIVE_LOCKED         = 'primitive_locked'
    AGENT_ADDED              = 'agent_added'
    AGENT_REMOVED            = 'agent_removed'
    HIRE_MADE                = 'hire_made'
    OFFER_CHANGED            = 'offer_changed'
    CHANNEL_CHANGED          = 'channel_changed'
    ICP_CHANGED              = 'icp_changed'
    NORTH_STAR_CHANGED       = 'north_star_changed'
    COMPANY_ADDED            = 'company_added'
    REVENUE_MILESTONE        = 'revenue_milestone'
    FIRST_SALE               = 'first_sale'
    OS_SUBSCRIPTION_CHANGED  = 'os_subscription'


@dataclass
class SystemChange:
    change_type:     ChangeType
    venture_id:      str
    previous_value:  Any
    new_value:       Any
    triggered_by:    str                          # 'founder' or 'system'
    timestamp:       datetime = field(default_factory=datetime.now)


# ─── Consequence map ───────────────────────────────────────────────────────────

CONSEQUENCE_MAP: dict[ChangeType, list[str]] = {

    ChangeType.STAGE_CHANGE: [
        'update_notion_stage_guidance',
        'unlock_primitives',
        'update_discord_channels',
        'update_kpi_dashboard',
        'notify_founder',
        'log_activity',
    ],

    ChangeType.PRIMITIVE_UNLOCKED: [
        'update_notion_stage_guidance',
        'notify_founder_primitive_unlocked',
        'log_activity',
    ],

    ChangeType.PRIMITIVE_LOCKED: [
        'update_notion_stage_guidance',
        'log_activity',
    ],

    ChangeType.AGENT_ADDED: [
        'register_agent_neon',
        'create_discord_channel',
        'create_notion_page',
        'update_empire_structure',
        'log_activity',
    ],

    ChangeType.HIRE_MADE: [
        'create_role_notion',
        'create_discord_channel',
        'update_org_chart',
        'update_kpi_dashboard',
        'notify_founder',
        'log_activity',
    ],

    ChangeType.OFFER_CHANGED: [
        'update_notion_company_profile',
        'update_icp_doc',
        'regenerate_messaging_doc',
        'update_bis',
        'notify_founder',
        'log_activity',
    ],

    ChangeType.CHANNEL_CHANGED: [
        'update_notion_company_profile',
        'update_bis',
        'create_discord_channel',
        'notify_founder',
        'log_activity',
    ],

    ChangeType.FIRST_SALE: [
        'advance_stage',
        'notify_founder_celebration',
        'update_notion_kpi',
        'log_activity',
    ],

    ChangeType.COMPANY_ADDED: [
        'create_bis',
        'create_notion_company_hub',
        'create_discord_category',
        'register_ceo_agent',
        'register_dev_agent',
        'update_empire_structure',
        'notify_founder',
        'log_activity',
    ],

    ChangeType.REVENUE_MILESTONE: [
        'update_notion_kpi',
        'notify_founder_celebration',
        'check_stage_transition',
        'log_activity',
    ],

    ChangeType.ICP_CHANGED: [
        'update_notion_company_profile',
        'regenerate_messaging_doc',
        'update_bis',
        'log_activity',
    ],

    ChangeType.NORTH_STAR_CHANGED: [
        'update_bis',
        'update_notion_portfolio',
        'regenerate_ea_soul_doc',
        'log_activity',
    ],
}


# ─── Engine ────────────────────────────────────────────────────────────────────

class SelfAwarenessEngine:

    def __init__(self, ctx, discord_guild=None):
        self.ctx   = ctx
        self.guild = discord_guild

    # ─── Public ───────────────────────────────────────────────────────────────

    async def process_change(self, change: SystemChange) -> dict:
        """
        Central change processor.
        Executes all consequences for the change type automatically.
        """
        consequences = CONSEQUENCE_MAP.get(change.change_type, [])

        print(f'[SelfAwareness] Processing: {change.change_type.value} for {change.venture_id}')
        print(f'[SelfAwareness] Consequences: {len(consequences)}')

        results: dict = {}
        for consequence in consequences:
            try:
                result = await self._execute(consequence, change)
                results[consequence] = result
                print(f'[SelfAwareness] ✅ {consequence}')
            except Exception as e:
                results[consequence] = f'error: {e}'
                print(f'[SelfAwareness] ❌ {consequence}: {e}')

            # Validate any Discord-bound content for notify consequences
            if 'notify' in consequence or 'discord' in consequence:
                try:
                    from runtime.output_validator import get_validator
                    validator = get_validator(self.ctx)
                    val_result = validator.validate_discord_message(
                        str(change.new_value),
                        context=consequence,
                    )
                    if not val_result.passed:
                        validator.log_violation(val_result, consequence)
                except Exception:
                    pass

        return results

    def detect_change_from_text(
        self,
        text: str,
        venture_id: str = 'lyfe_institute',
    ) -> Optional[SystemChange]:
        """
        Detect what changed from natural language input.
        Returns SystemChange if a business-significant event is detected, else None.
        """
        text_lower = text.lower()

        # First sale
        if any(s in text_lower for s in [
            'closed my first client', 'first client paid',
            'got my first sale', 'first paying customer',
            'they paid me', 'first sale',
        ]):
            return SystemChange(
                change_type=ChangeType.FIRST_SALE,
                venture_id=venture_id,
                previous_value=0,
                new_value=1,
                triggered_by='founder',
            )

        # Hire
        if any(s in text_lower for s in [
            'hired', 'just hired', 'new employee',
            'brought on', 'added to the team',
        ]):
            return SystemChange(
                change_type=ChangeType.HIRE_MADE,
                venture_id=venture_id,
                previous_value=None,
                new_value=text,
                triggered_by='founder',
            )

        # Offer change
        if any(s in text_lower for s in [
            'changing my offer', 'new offer',
            'updated the offer', 'offer is now',
        ]):
            return SystemChange(
                change_type=ChangeType.OFFER_CHANGED,
                venture_id=venture_id,
                previous_value=None,
                new_value=text,
                triggered_by='founder',
            )

        # Channel change
        if any(s in text_lower for s in [
            'switching to', 'new channel', 'moving to linkedin',
            'moving to instagram', 'trying cold email',
        ]):
            return SystemChange(
                change_type=ChangeType.CHANNEL_CHANGED,
                venture_id=venture_id,
                previous_value=None,
                new_value=text,
                triggered_by='founder',
            )

        # North star change
        if any(s in text_lower for s in [
            'north star is now', 'new goal', 'changing my goal',
            'my focus is now',
        ]):
            return SystemChange(
                change_type=ChangeType.NORTH_STAR_CHANGED,
                venture_id=venture_id,
                previous_value=None,
                new_value=text,
                triggered_by='founder',
            )

        # ICP change
        if any(s in text_lower for s in [
            'new icp', 'changing my target', 'targeting',
            'audience is now', 'ideal customer is',
        ]):
            return SystemChange(
                change_type=ChangeType.ICP_CHANGED,
                venture_id=venture_id,
                previous_value=None,
                new_value=text,
                triggered_by='founder',
            )

        return None

    # ─── Consequence executor ─────────────────────────────────────────────────

    async def _execute(self, consequence: str, change: SystemChange) -> bool:

        # ── NOTION UPDATES ────────────────────────────────────────────────────

        if consequence == 'update_notion_stage_guidance':
            from understanding.ontology.primitives import PRIMITIVE_LIBRARY

            stage = (
                change.new_value
                if change.change_type == ChangeType.STAGE_CHANGE
                else None
            )
            if not stage:
                return True

            active = [
                pid for pid, p in PRIMITIVE_LIBRARY.items()
                if p.stage_applicability.get(stage, True)
            ]
            locked = [
                pid for pid, p in PRIMITIVE_LIBRARY.items()
                if not p.stage_applicability.get(stage, True)
            ]

            stage_page_map = {
                'lyfe_institute':    os.getenv('NOTION_LYFE_STAGE_ID', ''),
                'empyrean_creative': os.getenv('NOTION_EMPYREAN_STAGE_ID', ''),
                'personal_brand':    os.getenv('NOTION_PERSONAL_BRAND_ID', ''),
            }
            page_id = stage_page_map.get(change.venture_id, '')
            notion_key = os.getenv('NOTION_API_KEY')

            if page_id and notion_key:
                from notion_client import Client
                client = Client(auth=notion_key)
                date_str = datetime.now().strftime('%Y-%m-%d')
                client.blocks.children.append(
                    block_id=page_id,
                    children=[{
                        'object': 'block',
                        'type': 'callout',
                        'callout': {
                            'rich_text': [{'type': 'text', 'text': {'content': (
                                f'🎯 Stage {stage} activated — {date_str}\n'
                                f'Active: {", ".join(active)}\n'
                                f'Locked: {", ".join(locked)}'
                            )[:2000]}}],
                            'icon': {'type': 'emoji', 'emoji': '🎯'},
                        },
                    }]
                )
            return True

        elif consequence == 'update_notion_company_profile':
            self._log_to_neon(
                change.venture_id,
                f'{change.change_type.value}: {change.previous_value} → {change.new_value}',
            )
            return True

        elif consequence == 'update_notion_portfolio':
            notion_key = os.getenv('NOTION_API_KEY')
            page_id    = os.getenv('NOTION_PORTFOLIO_ID', '')
            if page_id and notion_key:
                from notion_client import Client
                client = Client(auth=notion_key)
                date_str = datetime.now().strftime('%Y-%m-%d')
                client.blocks.children.append(
                    block_id=page_id,
                    children=[{
                        'object': 'block',
                        'type': 'paragraph',
                        'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': (
                            f'📊 Portfolio update — {date_str}\n'
                            f'{change.change_type.value}: {change.new_value}'
                        )[:2000]}}]},
                    }]
                )
            return True

        elif consequence == 'update_notion_kpi':
            kpi_map = {
                'lyfe_institute':    os.getenv('NOTION_LYFE_INSTITUTE_ID', ''),
                'empyrean_creative': os.getenv('NOTION_EMPYREAN_CREATIVE_ID', ''),
            }
            page_id   = kpi_map.get(change.venture_id, '')
            notion_key = os.getenv('NOTION_API_KEY')
            if page_id and notion_key:
                from notion_client import Client
                client = Client(auth=notion_key)
                client.blocks.children.append(
                    block_id=page_id,
                    children=[{
                        'object': 'block',
                        'type': 'paragraph',
                        'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': (
                            f'📈 KPI update: {change.change_type.value} — {change.new_value}'
                        )[:2000]}}]},
                    }]
                )
            return True

        elif consequence == 'update_empire_structure':
            page_id   = os.getenv('NOTION_EMPIRE_ID', '')
            notion_key = os.getenv('NOTION_API_KEY')
            if page_id and notion_key:
                from notion_client import Client
                client = Client(auth=notion_key)
                date_str = datetime.now().strftime('%Y-%m-%d')
                client.blocks.children.append(
                    block_id=page_id,
                    children=[{
                        'object': 'block',
                        'type': 'paragraph',
                        'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': (
                            f'🏛️ Empire updated — {date_str}\n'
                            f'{change.change_type.value}: {change.new_value}'
                        )[:2000]}}]},
                    }]
                )
            return True

        elif consequence in ('create_role_notion', 'create_notion_page',
                              'create_notion_company_hub', 'update_org_chart',
                              'update_icp_doc', 'regenerate_messaging_doc',
                              'update_kpi_dashboard'):
            # Log to Neon — Notion page IDs not yet configured for these
            self._log_to_neon(
                change.venture_id,
                f'{consequence}: {change.change_type.value} — {change.new_value}',
            )
            return True

        # ── DISCORD UPDATES ────────────────────────────────────────────────────

        elif consequence == 'update_discord_channels':
            if self.guild:
                # Import DiscordServerManager from discord_bot at runtime to
                # avoid circular import — discord_bot imports gateway
                import importlib
                try:
                    discord_bot = importlib.import_module('discord_bot')
                    mgr = discord_bot.DiscordServerManager(self.guild)
                    await mgr.create_stage_channels(
                        change.venture_id,
                        change.new_value,
                    )
                except Exception as e:
                    print(f'[SelfAwareness] Discord channel update failed: {e}')
            return True

        elif consequence == 'create_discord_channel':
            if self.guild and change.new_value:
                import importlib
                try:
                    discord_bot = importlib.import_module('discord_bot')
                    mgr = discord_bot.DiscordServerManager(self.guild)
                    company_cat = change.venture_id.replace('_', ' ').title()
                    await mgr.ensure_channel(
                        name=str(change.new_value).lower().replace(' ', '-'),
                        category_name=company_cat,
                        topic=f'Auto-created: {change.change_type.value}',
                    )
                except Exception as e:
                    print(f'[SelfAwareness] Discord channel create failed: {e}')
            return True

        elif consequence == 'create_discord_category':
            if self.guild and change.new_value:
                try:
                    import discord as _discord
                    existing = _discord.utils.get(
                        self.guild.categories,
                        name=str(change.new_value),
                    )
                    if not existing:
                        await self.guild.create_category(str(change.new_value))
                except Exception as e:
                    print(f'[SelfAwareness] Category create failed: {e}')
            return True

        # ── SYSTEM UPDATES ─────────────────────────────────────────────────────

        elif consequence == 'advance_stage':
            from runtime.stage_manager import StageManager
            from runtime.evolution_engine import EvolutionEngine
            sm      = StageManager(self.ctx)
            ee      = EvolutionEngine(self.ctx)
            current = ee.get_current_stage(change.venture_id)
            # advance_stage is sync — call directly
            sm.advance_stage(
                venture_id=change.venture_id,
                new_stage=current + 1,
            )
            return True

        elif consequence == 'unlock_primitives':
            # Primitives are gated by stage in EvolutionEngine — nothing
            # to do here beyond logging; the stage update already unlocks them
            self._log_to_neon(
                change.venture_id,
                f'unlock_primitives: stage {change.new_value}',
            )
            return True

        elif consequence == 'check_stage_transition':
            from runtime.stage_manager import StageManager, detect_stage_transition
            stage_hint = f'advance to stage based on revenue milestone {change.new_value}'
            detected   = detect_stage_transition(stage_hint)
            if detected.get('detected'):
                sm = StageManager(self.ctx)
                sm.advance_stage(
                    venture_id=change.venture_id,
                    new_stage=detected['new_stage'],
                )
            return True

        elif consequence == 'update_bis':
            from runtime.business_instance import BusinessInstanceManager
            bim = BusinessInstanceManager(self.ctx)
            bis = bim.get_bis(change.venture_id)
            if not bis:
                return True

            field_map = {
                ChangeType.OFFER_CHANGED:    'offer_name',
                ChangeType.CHANNEL_CHANGED:  'primary_channel',
                ChangeType.ICP_CHANGED:      'icp_description',
                ChangeType.NORTH_STAR_CHANGED: 'north_star',
            }
            field_name = field_map.get(change.change_type)
            if field_name and hasattr(bis, field_name):
                setattr(bis, field_name, str(change.new_value))
                bim.save_bis(bis)
            return True

        elif consequence == 'create_bis':
            from runtime.business_instance import (
                BusinessInstance, BusinessInstanceManager,
            )
            bim = BusinessInstanceManager(self.ctx)
            # Only create if not already present
            existing = bim.get_bis(change.venture_id)
            if not existing:
                bis = BusinessInstance(
                    org_id=self.ctx.org_id,
                    venture_id=change.venture_id,
                    name=str(change.new_value),
                    industry='unknown',
                    business_model='unknown',
                )
                bim.save_bis(bis)
            return True

        elif consequence == 'register_agent_neon':
            from state.stores.agent_registry_store import AgentRegistryStore
            AgentRegistryStore().register_agent(
                org_id=self.ctx.org_id,
                name=str(change.new_value),
                agent_type='ai_agent',
                department=change.venture_id,
            )
            return True

        elif consequence in ('register_ceo_agent', 'register_dev_agent'):
            from state.stores.agent_registry_store import AgentRegistryStore
            agent_name = (
                f'{change.venture_id}_ceo'
                if consequence == 'register_ceo_agent'
                else f'{change.venture_id}_dev'
            )
            AgentRegistryStore().register_agent(
                org_id=self.ctx.org_id,
                name=agent_name,
                agent_type='ai_agent',
                department=change.venture_id,
            )
            return True

        elif consequence == 'regenerate_ea_soul_doc':
            try:
                from runtime.setup_wizard import generate_ea_soul_doc
                from runtime.business_instance import BusinessInstanceManager
                from pathlib import Path

                bim = BusinessInstanceManager(self.ctx)
                bis = bim.get_bis(change.venture_id) or bim.get_bis('lyfe_institute')
                if bis:
                    soul_doc = generate_ea_soul_doc(
                        ai_name=getattr(bis, 'ai_name', 'DEX'),
                        founder_name=getattr(bis, 'founder_name', 'Founder'),
                        north_star=change.new_value,
                        current_stage=getattr(bis, 'current_stage', 1),
                        offer_name=getattr(bis, 'offer_name', ''),
                        primary_channel=getattr(bis, 'primary_channel', ''),
                    )
                    if soul_doc:
                        ai_name = getattr(bis, 'ai_name', 'dex').lower()
                        path = Path(f'{_REPO_ROOT}/agents/{ai_name}_ea.md')
                        path.write_text(soul_doc)
            except Exception as e:
                print(f'[SelfAwareness] regenerate_ea_soul_doc failed: {e}')
            return True

        # ── NOTIFICATIONS ──────────────────────────────────────────────────────

        elif consequence == 'notify_founder':
            self._log_to_neon(
                change.venture_id,
                f'System update: {change.change_type.value} — {change.new_value}',
            )
            return True

        elif consequence == 'notify_founder_celebration':
            self._log_to_neon(
                change.venture_id,
                f'🎉 {change.change_type.value}: {change.new_value}',
            )
            return True

        elif consequence == 'notify_founder_primitive_unlocked':
            from understanding.ontology.primitives import PRIMITIVE_LIBRARY
            primitive = PRIMITIVE_LIBRARY.get(str(change.new_value))
            msg = (
                f'✅ Primitive unlocked: {change.new_value}'
                + (f'\n{primitive.principle[:100]}' if primitive else '')
            )
            self._log_to_neon(change.venture_id, msg)
            return True

        elif consequence == 'log_activity':
            self._log_to_neon(
                change.venture_id,
                f'{change.change_type.value}: {change.venture_id} | '
                f'{change.previous_value} → {change.new_value}',
            )
            return True

        # Unknown consequence — log and continue
        print(f'[SelfAwareness] Unknown consequence: {consequence}')
        return False

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _log_to_neon(self, venture_id: str, message: str) -> None:
        """Write activity event to Neon events table."""
        import json
        try:
            from state.memory.memory import AgentMemory
            AgentMemory().log_event(
                org_id=self.ctx.org_id,
                event_type='self_awareness_event',
                payload={
                    'venture_id': venture_id,
                    'message':    message[:500],
                },
                handled_by=json.dumps(['SelfAwarenessEngine']),
            )
        except Exception as e:
            print(f'[SelfAwareness] _log_to_neon failed: {e}')
