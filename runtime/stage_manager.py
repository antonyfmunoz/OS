"""
StageManager — auto-updates Notion, Discord, and primitives when stage advances.

When the founder says "I closed my first client" or "advance to stage 2",
gateway.py detects it and calls StageManager.advance_stage().

Everything that needs to change on a stage transition happens here:
  - BIS stage updated in Neon
  - Notion Stage Guidance page updated
  - Notion Morning Brief notified
  - Event fired for Discord bot to create new channels + announce

Usage:
    from runtime.stage_manager import StageManager, detect_stage_transition
    ctx = load_context_from_env()
    sm = StageManager(ctx)
    result = sm.advance_stage('lyfe_institute', 2)
    print(result.message)
"""

import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

from runtime.context import EOSContext


# ─── Stage transition detection ───────────────────────────────────────────────

_STAGE_SIGNALS: dict[str, list[str]] = {
    'first_sale': [
        'closed my first client',
        'first client paid',
        'got my first sale',
        'first paying customer',
        'they paid',
        'someone paid',
        'advance to stage 2',
        'move to stage 2',
    ],
    'consistent_sales': [
        '10 clients',
        'consistent sales',
        'advance to stage 3',
        'move to stage 3',
        'scaling now',
        'reliably closing',
    ],
}

_STAGE_MAP: dict[str, int] = {
    'first_sale': 2,
    'consistent_sales': 3,
}


def detect_stage_transition(text: str) -> dict:
    """
    Detect if founder's message signals a stage transition.
    Returns {'detected': bool, 'transition': str, 'new_stage': int}.
    Called by gateway.py before routing.
    """
    text_lower = text.lower()
    for transition, keywords in _STAGE_SIGNALS.items():
        if any(kw in text_lower for kw in keywords):
            return {
                'detected': True,
                'transition': transition,
                'new_stage': _STAGE_MAP[transition],
            }
    return {'detected': False, 'transition': '', 'new_stage': 0}


# ─── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class StageTransitionResult:
    previous_stage: int
    new_stage: int
    venture_id: str
    notion_updated: bool
    primitives_unlocked: list[str]
    discord_event_fired: bool
    message: str
    error: str = ''


# ─── StageManager ─────────────────────────────────────────────────────────────

class StageManager:

    def __init__(self, ctx: EOSContext):
        self.ctx = ctx

    def advance_stage(
        self,
        venture_id: str,
        new_stage: int,
    ) -> StageTransitionResult:
        """
        Handle full stage transition. Updates BIS, Notion, fires Discord event.
        Synchronous — safe to call from gateway.py.
        """
        from runtime.business_instance import BusinessInstanceManager
        from understanding.ontology.primitives import PRIMITIVE_LIBRARY

        bim = BusinessInstanceManager(self.ctx)
        bis = bim.get_bis(venture_id)
        previous_stage = bis.current_stage

        if new_stage <= previous_stage:
            return StageTransitionResult(
                previous_stage=previous_stage,
                new_stage=new_stage,
                venture_id=venture_id,
                notion_updated=False,
                primitives_unlocked=[],
                discord_event_fired=False,
                message=f'Already at Stage {previous_stage} — no change.',
            )

        # Update BIS
        bis.current_stage = new_stage
        bim.save_bis(bis)
        print(f'[StageManager] {venture_id}: Stage {previous_stage} → {new_stage}')

        # Determine newly unlocked primitives
        unlocked = [
            pid for pid, p in PRIMITIVE_LIBRARY.items()
            if (
                p.stage_applicability.get(new_stage, True)
                and not p.stage_applicability.get(previous_stage, True)
            )
        ]

        # Update Notion
        notion_updated = False
        try:
            notion_key = os.getenv('NOTION_API_KEY')
            if notion_key:
                self._update_notion(venture_id, new_stage, unlocked, previous_stage)
                notion_updated = True
        except Exception as e:
            print(f'[StageManager] Notion update failed: {e}')

        # Fire event for Discord bot to pick up
        discord_event_fired = False
        try:
            self._fire_discord_event(venture_id, new_stage, unlocked)
            discord_event_fired = True
        except Exception as e:
            print(f'[StageManager] Discord event failed: {e}')

        message = (
            f'🎯 Stage {new_stage} unlocked for {venture_id}.\n\n'
            f'Primitives unlocked: {", ".join(unlocked) if unlocked else "none"}\n'
            f'Notion updated: {notion_updated}\n'
            f'Discord notified: {discord_event_fired}'
        )

        return StageTransitionResult(
            previous_stage=previous_stage,
            new_stage=new_stage,
            venture_id=venture_id,
            notion_updated=notion_updated,
            primitives_unlocked=unlocked,
            discord_event_fired=discord_event_fired,
            message=message,
        )

    def _update_notion(
        self,
        venture_id: str,
        new_stage: int,
        unlocked: list[str],
        previous_stage: int,
    ) -> None:
        """Update Notion Stage Guidance and Morning Brief pages."""
        from notion_client import Client
        from understanding.ontology.primitives import PRIMITIVE_LIBRARY

        client = Client(auth=os.getenv('NOTION_API_KEY'))
        date = datetime.now().strftime('%Y-%m-%d %H:%M')

        # Direct stage page lookup — no child search needed
        stage_page_map = {
            'lyfe_institute':    os.getenv('NOTION_LYFE_STAGE_ID', ''),
            'empyrean_creative': os.getenv('NOTION_EMPYREAN_STAGE_ID', ''),
            'personal_brand':    os.getenv('NOTION_BRAND_STAGE_ID', ''),
        }
        stage_page_id = stage_page_map.get(venture_id, '')

        if stage_page_id:
            try:
                active = [
                    pid for pid, p in PRIMITIVE_LIBRARY.items()
                    if p.stage_applicability.get(new_stage, True)
                ]
                locked = [
                    pid for pid, p in PRIMITIVE_LIBRARY.items()
                    if not p.stage_applicability.get(new_stage, True)
                ]
                client.blocks.children.append(
                    block_id=stage_page_id,
                    children=[
                        {'object': 'block', 'type': 'divider', 'divider': {}},
                        {
                            'object': 'block',
                            'type': 'callout',
                            'callout': {
                                'rich_text': [{'type': 'text', 'text': {
                                    'content': (
                                        f'Stage {new_stage} Activated — {date}\n\n'
                                        f'NEWLY UNLOCKED:\n' +
                                        '\n'.join(f'  ✅ {p}' for p in unlocked) +
                                        f'\n\nALL ACTIVE:\n' +
                                        '\n'.join(f'  ✅ {p}' for p in active) +
                                        f'\n\nSTILL LOCKED:\n' +
                                        '\n'.join(f'  ❌ {p}' for p in locked)
                                    )[:2000]
                                }}],
                                'icon': {'type': 'emoji', 'emoji': '🎯'},
                            },
                        },
                    ]
                )
                print(f'[StageManager] Stage Guidance updated in Notion')
            except Exception as e:
                print(f'[StageManager] Stage Guidance update failed: {e}')

        # Append to Morning Brief
        brief_id = os.getenv('NOTION_MORNING_BRIEF_ID')
        if brief_id:
            try:
                client.blocks.children.append(
                    block_id=brief_id,
                    children=[{
                        'object': 'block',
                        'type': 'callout',
                        'callout': {
                            'rich_text': [{'type': 'text', 'text': {
                                'content': (
                                    f'🎯 STAGE TRANSITION — {date}\n'
                                    f'{venture_id} advanced: Stage {previous_stage} → Stage {new_stage}\n'
                                    f'New primitives: {", ".join(unlocked) if unlocked else "none"}'
                                )
                            }}],
                            'icon': {'type': 'emoji', 'emoji': '🎯'},
                        },
                    }]
                )
                print(f'[StageManager] Morning Brief updated in Notion')
            except Exception as e:
                print(f'[StageManager] Morning Brief update failed: {e}')

    def _fire_discord_event(
        self,
        venture_id: str,
        new_stage: int,
        unlocked: list[str],
    ) -> None:
        """
        Log stage transition event to Neon for Discord bot to surface.
        Discord bot picks this up on next interaction.
        """
        from state.storage.db import get_conn
        import json

        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                '''
                INSERT INTO events (id, org_id, type, payload, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ''',
                (
                    str(uuid.uuid4()),
                    self.ctx.org_id,
                    'stage_transition',
                    json.dumps({
                        'venture_id': venture_id,
                        'new_stage': new_stage,
                        'unlocked_primitives': unlocked,
                    }),
                )
            )
        print(f'[StageManager] Stage transition event fired to Neon')
