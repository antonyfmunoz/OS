"""
Inbox Zero Initialization — run ONCE on first DEX setup.

Three-phase protocol:
  Phase 1 — AUDIT    Read-only. Map current inbox state.
  Phase 2 — PLAN     Show what will change. Confirm before proceeding.
  Phase 3 — EXECUTE  Apply GPS labels. Achieve Inbox Zero.

Run:
    python3 /opt/OS/scripts/inbox_zero_init.py
"""

import sys
sys.path.insert(0, '/opt/OS')

from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
load_dotenv('/opt/OS/13_Scripts/.env')

from pathlib import Path

from eos_ai.email_gps import EmailGPS, EmailFolder
from eos_ai.gws_connector import GWSConnector
from eos_ai.context import load_context_from_env

ctx = load_context_from_env()
gps = EmailGPS(ctx)
gws = GWSConnector()

# Resolve relative to repo root so path works in container (/app) and on host
AUDIT_PATH = str(Path(__file__).resolve().parent.parent / 'data' / 'gmail_audit.json')

# ── PHASE 1: AUDIT ────────────────────────────────────────────────────────────
print()
print('━━━━━━━━━━━━━━━━━━━━━━━━')
print('PHASE 1 — AUDIT (read only, no changes)')
print('━━━━━━━━━━━━━━━━━━━━━━━━')
print()

audit = gws.audit_inbox(save_path=AUDIT_PATH)

user_labels = [l for l in audit['existing_labels'] if l['type'] == 'user']
system_labels = [l for l in audit['existing_labels'] if l['type'] == 'system']

print()
print(f'System labels ({len(system_labels)}):')
for l in system_labels:
    print(f'  {l["name"]}')

print()
if user_labels:
    print(f'User labels ({len(user_labels)}):')
    for l in user_labels:
        count = audit['label_counts'].get(l['name'], '?')
        print(f'  • {l["name"]}  ({count} emails)')
else:
    print('User labels: none')

print()
if audit['sample_senders']:
    print('Sample senders in inbox:')
    for sender in sorted(audit['sample_senders'])[:15]:
        print(f'  • {sender}')

print()
print(f'Total inbox:  {audit["total_inbox"]} emails')
print(f'Full audit:   {AUDIT_PATH}')

# ── PHASE 2: PLAN ─────────────────────────────────────────────────────────────
print()
print('━━━━━━━━━━━━━━━━━━━━━━━━')
print('PHASE 2 — PLAN')
print('━━━━━━━━━━━━━━━━━━━━━━━━')
print()

# Show which GPS labels will be created vs already exist
existing_names = {l['name'] for l in audit['existing_labels']}
gps_labels = [f.value for f in EmailFolder]

to_create = [l for l in gps_labels if l not in existing_names]
already   = [l for l in gps_labels if l in existing_names]

if already:
    print('GPS labels already in Gmail:')
    for l in already:
        print(f'  ✓ {l}')
if to_create:
    print('GPS labels to be created:')
    for l in to_create:
        print(f'  + {l}')

print()
print('What will happen:')
print(f'  • Each of {audit["total_inbox"]} inbox emails will be classified by DEX')
print(f'  • A GPS label will be applied to each email')
print(f'  • The INBOX label will be removed from each email')
print(f'  • Emails matching financial keywords → Receipts-Financials')
print(f'  • Emails with unsubscribe links → Newsletters')
print(f'  • Everything else → classified by AI (Antony / To Respond / Review)')
print()

answer = input(
    f'Found {audit["total_inbox"]} emails'
    f' across {len(audit["existing_labels"])} existing labels.\n'
    f'Ready to apply GPS structure? (y/n): '
).strip().lower()

if answer != 'y':
    print()
    print('Aborted. No changes made.')
    sys.exit(0)

# ── PHASE 3: EXECUTE ──────────────────────────────────────────────────────────
print()
print('━━━━━━━━━━━━━━━━━━━━━━━━')
print('PHASE 3 — EXECUTE')
print('━━━━━━━━━━━━━━━━━━━━━━━━')
print()

processed = gps.process_inbox(
    limit=500,
    process_all=True,
)

total_processed = sum(len(v) for v in processed.values())

print()
print('━━━━━━━━━━━━━━━━━━━━━━━━')
print('INBOX ZERO COMPLETE')
print('━━━━━━━━━━━━━━━━━━━━━━━━')
for folder, emails in processed.items():
    if emails:
        print(f'  {folder.value}: {len(emails)}')
print(f'Total processed: {total_processed}')
print()
print(gps.generate_inbox_report(processed))
