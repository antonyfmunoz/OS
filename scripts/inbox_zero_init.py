"""
Inbox Zero Initialization — run ONCE on first DEX setup.

Four-phase protocol:
  Phase 1 — AUDIT    Read-only. Map current inbox state.
  Phase 2 — PLAN     Show what will change. Confirm before proceeding.
  Phase 3 — EXECUTE  Apply GPS labels. Achieve Inbox Zero.
  Phase 4 — VERIFY   Post-init anomaly check. Auto-runs after Phase 3.

Run:
    python3 /opt/OS/scripts/inbox_zero_init.py
"""

import sys
import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

from collections import Counter
from pathlib import Path

from runtime.email_gps import EmailGPS, EmailFolder, ProcessedEmail
from runtime.gws_connector import GWSConnector
from runtime.context import load_context_from_env

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

# GPS labels we manage — keep these, delete everything else
GPS_LABELS = [
    'Antony', 'To Respond', 'Review',
    'Responded', 'Waiting On',
    'Receipts-Financials', 'Newsletters',
]

# Gmail built-in labels — never touch
SYSTEM_LABELS = [
    'INBOX', 'SENT', 'DRAFT', 'SPAM',
    'TRASH', 'STARRED', 'IMPORTANT',
    'UNREAD', 'CHAT',
    'CATEGORY_PERSONAL', 'CATEGORY_SOCIAL',
    'CATEGORY_UPDATES', 'CATEGORY_FORUMS',
    'CATEGORY_PROMOTIONS',
]

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

# Create all 7 GPS labels immediately — don't wait for process_inbox
print()
print('Creating GPS labels (any missing)...')
existing_label_names = {l['name'] for l in audit['existing_labels']}
for label in GPS_LABELS:
    if label not in existing_label_names:
        gws.get_or_create_label(label)
        print(f'  Created: {label}')
    else:
        print(f'  Exists:  {label}')

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

# Legacy labels with numbered prefixes
legacy_patterns = ['1 - ', '2 - ', '3 - ', '4 - ', '5 - ', '6 - ', '! - ']
legacy_labels = [l for l in user_labels if any(l['name'].startswith(p) for p in legacy_patterns)]
if legacy_labels:
    print()
    print(f'Legacy labels to remove ({len(legacy_labels)}):')
    for l in legacy_labels:
        count = audit['label_counts'].get(l['name'], 0)
        print(f'  ✗ {l["name"]}  ({count} emails)')

# Pre-classify sample senders by rules only — no AI cost
print()
print('Sample sender pre-classification (rules only, no AI):')
rule_counts: Counter = Counter()
sample_senders = audit.get('sample_senders', [])
for sender_raw in sample_senders:
    from_addr = sender_raw.split('<')[-1].rstrip('>') if '<' in sender_raw else sender_raw
    test = ProcessedEmail(
        id='sample', from_address=from_addr, from_name='',
        subject='', preview='', received_at='', folder=EmailFolder.REVIEW,
    )
    result = gps._classify_by_rules(test)
    label = result.value if result else 'needs AI'
    rule_counts[label] += 1
    print(f'  {from_addr[:42]:42} → {label}')

total = audit['total_inbox']
n_samples = max(len(sample_senders), 1)
ai_pct = rule_counts.get('needs AI', 0) / n_samples
est_ai   = int(total * ai_pct)
est_auto = total - est_ai

print()
print(f'Estimated breakdown for {total} emails:')
print(f'  Auto-classified by rules : ~{est_auto}  (no AI cost)')
print(f'  Needs AI classification  : ~{est_ai}')
print()

print('Execution order:')
print('  1. Remove old/legacy labels')
print('  2. Delete social notification noise')
print('  3+4. Classify all emails (rules first, AI for ~10%)')
print('  5. GPS labels applied (inside step 3+4)')
print('  6. Unsubscribe from newsletters')
print('  7. Inbox Zero')
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

# ── PHASE 4 helpers ───────────────────────────────────────────────────────────

def run_post_init_verification(processed: dict) -> str:
    """
    Analyze what was just classified to catch systematic errors.
    Runs automatically after Phase 3 — no user prompt needed.
    """
    flags = []
    total = sum(len(v) for v in processed.values())

    if total == 0:
        return 'No emails processed.'

    # Flag 1: TO_RESPOND > 20% of total → likely misclassifications
    to_respond_emails = processed.get(EmailFolder.TO_RESPOND, [])
    to_respond = len(to_respond_emails)
    if to_respond > total * 0.2:
        flags.append(
            f'⚠️ TO_RESPOND is {to_respond} '
            f'({to_respond / total:.0%}) — '
            f'likely misclassifications. '
            f'Run !reclassify after init.'
        )

    # Flag 2: REVIEW > 50% of total → AI likely offline, emails defaulted to safe fallback
    review = len(processed.get(EmailFolder.REVIEW, []))
    if review > total * 0.5:
        flags.append(
            f'⚠️ REVIEW is {review} '
            f'({review / total:.0%}) — '
            f'AI may be offline. '
            f'Emails defaulted to safe fallback.'
        )

    # Flag 3: Newsletters with no unsub record
    newsletters = processed.get(EmailFolder.NEWSLETTERS, [])
    unsub_failed = [
        e for e in newsletters
        if not e.notes or 'unsubscribed' not in e.notes
    ]
    if unsub_failed:
        flags.append(
            f'⚠️ {len(unsub_failed)} newsletters '
            f'could not be unsubscribed. '
            f'Manual review recommended.'
        )

    # Flag 4: Sample of TO_RESPOND for human verification
    if to_respond_emails:
        flags.append(
            f'\n📋 TO_RESPOND sample '
            f'(verify these need responses):'
        )
        for e in to_respond_emails[:5]:
            flags.append(
                f'  • {e.from_name or e.from_address}'
                f': {e.subject[:50]}'
            )

    # Flag 5: Receipts sanity check
    receipts = processed.get(EmailFolder.RECEIPTS, [])
    if receipts:
        flags.append(f'\n💳 RECEIPTS ({len(receipts)}):')
        for e in receipts[:3]:
            flags.append(f'  • {e.subject[:50]}')

    # Build report
    lines = [
        '',
        '━━━━━━━━━━━━━━━━━━━━━━━━',
        'PHASE 4 — VERIFICATION REPORT',
        '━━━━━━━━━━━━━━━━━━━━━━━━',
        f'Total processed: {total}',
        '',
        'Folder breakdown:',
    ]

    for folder, emails in processed.items():
        if emails:
            pct = len(emails) / total * 100
            lines.append(
                f'  {folder.value:20} '
                f'{len(emails):3} ({pct:.0f}%)'
            )

    if flags:
        lines.append('')
        lines.append('Flags:')
        for flag in flags:
            lines.append(f'  {flag}')
    else:
        lines.append('')
        lines.append('✅ All classifications look correct.')

    lines.append('')
    lines.append('To re-classify any folder: !reclassify')
    lines.append('Nightly review runs at 11pm.')

    return '\n'.join(lines)


def verify_existing_labels() -> str:
    """Delegates to EmailGPS.verify_existing_labels() — uses GWSConnector."""
    return gps.verify_existing_labels(sample=5)


# ── Step 1: Migrate legacy labels → GPS labels, then delete old labels ─────────
print('Step 1 — Migrating and deleting legacy labels...')

OLD_TO_NEW_MAP = {
    '! - Antony F Munoz': 'Antony',
    '1 - To Respond':     'To Respond',
    '2 - To Review':      'Review',
    '3 - Responded':      'Responded',
    '4 - Waiting On':     'Waiting On',
    '5 - Financials':     'Receipts-Financials',
    '6 - Newsletters':    'Newsletters',
}

# Also delete any other non-GPS, non-system user labels
existing_label_names_phase3 = {l['name'] for l in audit['existing_labels']}
extra_old = {
    name: name  # map to itself (will be deleted without migration)
    for name in existing_label_names_phase3
    if name not in SYSTEM_LABELS
    and not name.startswith('CATEGORY_')
    and name not in GPS_LABELS
    and name not in OLD_TO_NEW_MAP  # already covered
}

# Run migration for legacy numbered labels
migrate_result = gps.migrate_and_delete_old_labels(OLD_TO_NEW_MAP)
removed_labels = migrate_result.get('deleted', 0)
migrated_emails = migrate_result.get('migrated', 0)
if migrate_result.get('errors'):
    for err in migrate_result['errors']:
        print(f'  ⚠️ {err}')
print(f'  Migrated {migrated_emails} emails, deleted {removed_labels} legacy labels')

# Delete any remaining unknown user labels (no migration needed)
extra_deleted = 0
if extra_old:
    extra_result = gps.migrate_and_delete_old_labels(extra_old)
    extra_deleted = extra_result.get('deleted', 0)
    print(f'  Deleted {extra_deleted} other old labels')

removed_labels += extra_deleted
print()

# ── Step 2: Delete obvious noise emails ───────────────────────────────────────
print('Step 2 — Deleting social notification noise...')
noise_emails_raw = gws.get_all_inbox_emails(max_results=500)
noise_candidates = []
for raw in noise_emails_raw:
    from_raw  = raw.get('from', '')
    from_addr = from_raw.split('<')[-1].rstrip('>') if '<' in from_raw else from_raw
    noise_candidates.append(ProcessedEmail(
        id=raw.get('id', ''),
        from_address=from_addr,
        from_name='',
        subject=raw.get('subject', ''),
        preview=raw.get('snippet', '')[:300],
        received_at=raw.get('date', ''),
        folder=EmailFolder.REVIEW,
    ))
noise_deleted = gps.delete_obvious_noise(noise_candidates)
print(f'  Done — {noise_deleted} noise emails deleted')
print()

# ── Steps 3 & 4: Auto-classify (rules first, then AI for ~10%) ────────────────
print('Steps 3 & 4 — Classifying inbox (rules → AI for remainder)...')
processed = gps.process_inbox(
    limit=500,
    process_all=True,
    show_progress=True,
)
total_processed = sum(len(v) for v in processed.values())
print(f'  Done — {total_processed} emails classified')
print()

# ── Step 5: GPS labels already applied inside process_inbox ───────────────────

# ── Step 6: Unsubscribe from newsletters via browser agent ────────────────────
print('Step 6 — Unsubscribing from newsletters...')
newsletters = processed.get(EmailFolder.NEWSLETTERS, [])
unsub_count = 0
for email in newsletters:
    if gps.unsubscribe_and_delete(email.id, email.preview):
        unsub_count += 1
print(f'  Done — {unsub_count}/{len(newsletters)} unsubscribed')
print()

# ── Step 7: Final report ──────────────────────────────────────────────────────
print()
print('━━━━━━━━━━━━━━━━━━━━━━━━')
print('INBOX ZERO COMPLETE')
print('━━━━━━━━━━━━━━━━━━━━━━━━')
for folder, emails in processed.items():
    if emails:
        print(f'  {folder.value}: {len(emails)}')
print(f'Noise deleted:   {noise_deleted}')
print(f'Labels cleaned:  {removed_labels}')
print(f'Unsubscribed:    {unsub_count}')
print(f'Total processed: {total_processed}')
print()
print(gps.generate_inbox_report(processed))

# ── PHASE 4: POST-INIT VERIFICATION ──────────────────────────────────────────
print()
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print('PHASE 4 — POST-INIT VERIFICATION')
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print()
print('Running post-init verification...')
verification = run_post_init_verification(processed)
print(verification)
