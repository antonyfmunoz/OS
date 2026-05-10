"""
Email GPS — 3pm afternoon inbox pass.
Runs via cron at 15:00 daily.
Posts report to Discord if there's anything to surface.
"""

import sys
import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'eos_ai', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

from eos_ai.email_gps import EmailGPS
from eos_ai.context import load_context_from_env
from eos_ai.discord_utils import post_to_webhook

ctx       = load_context_from_env()
gps       = EmailGPS(ctx)
processed = gps.process_inbox(limit=50)
report    = gps.generate_inbox_report(processed)

print(report)

webhook = os.getenv('DISCORD_BRIEF_WEBHOOK', '')
has_content = any(len(v) > 0 for v in processed.values())
if webhook and has_content:
    post_to_webhook(report, username='DEX', webhook_url=webhook)
