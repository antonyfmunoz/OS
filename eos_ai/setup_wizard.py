"""
SetupWizard — onboarding flow for new EOS users.

Collects founder and venture info, creates a BusinessInstance,
and generates a personalised EA soul doc from the master template.

Usage (interactive):
    python3 -m eos_ai.setup_wizard

Usage (programmatic):
    from eos_ai.setup_wizard import generate_ea_soul_doc
    soul_doc = generate_ea_soul_doc(
        ai_name='ARIA',
        founder_name='Jane Smith',
        north_star='$50K/month',
        current_stage=1,
        offer_name='Growth Academy $997',
        primary_channel='LinkedIn',
    )
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ─── Stage focus map ──────────────────────────────────────────────────────────

_STAGE_FOCUS: dict[int, str] = {
    1: 'First sale as fast as possible',
    2: 'Scale what works — 10 consistent sales',
    3: 'Build repeatable systems',
    4: 'Hire and delegate',
    5: 'Optimize and expand',
    6: 'Portfolio plays',
}

_TEMPLATE_PATH = _REPO_ROOT / 'agents' / 'ea_template.md'


# ─── generate_ea_soul_doc ─────────────────────────────────────────────────────

def generate_ea_soul_doc(
    ai_name: str,
    founder_name: str,
    north_star: str,
    current_stage: int,
    offer_name: str,
    primary_channel: str,
) -> str:
    """
    Generate a personalised EA soul doc by filling the master template.

    Returns the completed soul doc string, or empty string if the
    template file is missing.
    """
    if not _TEMPLATE_PATH.exists():
        print(f'[SetupWizard] Template not found: {_TEMPLATE_PATH}')
        return ''

    template = _TEMPLATE_PATH.read_text(encoding='utf-8')

    stage_focus = _STAGE_FOCUS.get(current_stage, _STAGE_FOCUS[1])

    soul_doc = (
        template
        .replace('{{AI_NAME}}',         ai_name)
        .replace('{{FOUNDER_NAME}}',    founder_name)
        .replace('{{NORTH_STAR}}',      north_star)
        .replace('{{CURRENT_STAGE}}',   f'Stage {current_stage}')
        .replace('{{STAGE_FOCUS}}',     stage_focus)
        .replace('{{OFFER_NAME}}',      offer_name or 'your primary offer')
        .replace('{{PRIMARY_CHANNEL}}', primary_channel or 'direct outreach')
    )

    return soul_doc


# ─── run_setup ────────────────────────────────────────────────────────────────

def run_setup() -> None:
    """
    Interactive onboarding wizard. Collects inputs, creates BIS,
    and writes the user's personalised EA soul doc.
    """
    print('\n=== EOS Setup Wizard ===\n')

    def _ask(prompt: str, default: str = '') -> str:
        suffix = f' [{default}]' if default else ''
        val = input(f'{prompt}{suffix}: ').strip()
        return val if val else default

    # Collect inputs
    founder_name   = _ask('Your name')
    ai_name        = _ask('Name for your AI', 'DEX')
    north_star     = _ask('North star (revenue goal)', '$10K/month')
    venture_name   = _ask('Company name')
    industry       = _ask('Industry', 'coaching')
    offer_name     = _ask('Primary offer name')
    offer_price    = _ask('Offer price', '0')
    primary_channel = _ask('Primary acquisition channel', 'Instagram')

    venture_id = venture_name.lower().replace(' ', '_')

    # Generate soul doc
    soul_doc = generate_ea_soul_doc(
        ai_name=ai_name,
        founder_name=founder_name,
        north_star=north_star,
        current_stage=1,
        offer_name=offer_name,
        primary_channel=primary_channel,
    )

    if soul_doc:
        soul_doc_path = _REPO_ROOT / 'agents' / f'{ai_name.lower()}_ea.md'
        soul_doc_path.write_text(soul_doc, encoding='utf-8')
        print(f'\n✅ Soul doc: {soul_doc_path}')
    else:
        soul_doc_path = None
        print('\n⚠️  Soul doc generation failed — template missing')

    # Build and save BIS
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.business_instance import (
            BusinessInstance, BusinessInstanceManager, STAGE_NAMES
        )

        ctx = load_context_from_env()
        bim = BusinessInstanceManager(ctx)

        bis = BusinessInstance(
            org_id=ctx.org_id,
            venture_id=venture_id,
            name=venture_name,
            industry=industry,
            business_model='service',
            current_stage=1,
            stage_name=STAGE_NAMES[1],
            offer_name=offer_name,
            offer_price=float(offer_price) if offer_price.replace('.', '').isdigit() else 0.0,
            primary_channel=primary_channel,
            founder_name=founder_name,
            north_star=north_star,
            ai_name=ai_name,
            ai_soul_doc_path=str(soul_doc_path) if soul_doc_path else '',
        )
        bim.save_bis(bis)
        print(f'✅ BIS saved for venture: {venture_id}')

    except Exception as e:
        print(f'⚠️  BIS save failed: {e}')

    print('\nSetup complete. Restart services to activate.\n')


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    run_setup()
