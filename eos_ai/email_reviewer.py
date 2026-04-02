"""
EmailReviewer — nightly self-review of Email GPS classification.

Runs at 11pm daily. Pulls all email events from the last 24 hours,
checks for anomalies, builds a report, and posts to Discord.

Cron:
    0 23 * * * python3 -c "
    import sys; sys.path.insert(0, '/opt/OS')
    from dotenv import load_dotenv
    load_dotenv('/opt/OS/eos_ai/.env')
    load_dotenv('/opt/OS/services/.env')
    from eos_ai.email_reviewer import EmailReviewer
    from eos_ai.context import load_context_from_env
    from eos_ai.discord_utils import post_to_webhook
    import os
    ctx = load_context_from_env()
    er = EmailReviewer(ctx)
    report = er.run_nightly_review()
    webhook = os.getenv('DISCORD_BRIEF_WEBHOOK')
    if webhook:
        post_to_webhook(report, webhook=webhook)
    print(report)
    " >> /opt/OS/logs/email_review.log 2>&1
"""

import json
import uuid
from collections import Counter
from datetime import datetime, timedelta


class EmailReviewer:

    def __init__(self, ctx):
        self.ctx = ctx

    def run_nightly_review(self) -> str:
        try:
            from eos_ai.db import get_conn

            since = (datetime.now() - timedelta(hours=24)).isoformat()

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    '''
                    SELECT payload_json
                    FROM events
                    WHERE org_id = %s
                      AND event_type = 'email_classified'
                      AND created_at > %s
                    ORDER BY created_at DESC
                    ''',
                    (self.ctx.org_id, since),
                )
                rows = cur.fetchall()

            if not rows:
                report = (
                    '📊 **Email GPS Nightly Review**\n'
                    'No emails processed in the last 24 hours.\n'
                    '_Check that the Email GPS cron is running._'
                )
                self._store_report(report)
                return report

            folders: Counter = Counter()
            methods: Counter = Counter()

            for row in rows:
                data = row[0]
                if isinstance(data, str):
                    data = json.loads(data)
                folders[data.get('folder', 'unknown')] += 1
                methods[data.get('method', 'unknown')] += 1

            total = sum(folders.values())
            flags: list[str] = []

            # Flag: Review folder too high (AI offline or rules broken)
            review_count = folders.get('Review', 0)
            if total > 0 and review_count / total > 0.4:
                flags.append(
                    f'⚠️ Review folder is '
                    f'{review_count / total:.0%} of processed emails '
                    f'— AI may be offline or classifier needs tuning'
                )

            # Flag: To Respond suspiciously high (misclassification)
            to_respond = folders.get('To Respond', 0)
            if to_respond > 20:
                flags.append(
                    f'⚠️ {to_respond} emails in To Respond '
                    f'— verify these actually need DEX responses. '
                    f'Run !reclassify to fix.'
                )

            # Flag: No system/newsletter emails (rules may have broken)
            auto_routed = (
                folders.get('Responded', 0)
                + folders.get('Newsletters', 0)
                + folders.get('Receipts-Financials', 0)
            )
            if total > 10 and auto_routed == 0:
                flags.append(
                    '⚠️ Zero auto-routed emails today '
                    '— system sender rules may be broken'
                )

            lines = [
                '📊 **Email GPS Nightly Review**',
                f'Processed: {total} emails',
                '',
                '**Folder breakdown:**',
            ]
            for folder, count in folders.most_common():
                pct = int(count / total * 100) if total else 0
                lines.append(f'  {folder}: {count} ({pct}%)')

            lines.append('')
            lines.append('**Classification method:**')
            for method, count in methods.most_common():
                lines.append(f'  {method}: {count}')

            if flags:
                lines.append('')
                lines.append('**Flags:**')
                for flag in flags:
                    lines.append(f'  {flag}')
            else:
                lines.append('')
                lines.append('✅ No anomalies detected')

            lines.append('')
            lines.append('_Reported in tomorrow\'s sync_')

            report = '\n'.join(lines)
            self._store_report(report)
            return report

        except Exception as e:
            return f'Email review failed: {e}'

    def _store_report(self, report: str) -> None:
        """Persist report to Neon so morning sync can include it."""
        try:
            from eos_ai.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    '''
                    INSERT INTO events (
                        id, org_id, event_type,
                        payload_json, created_at
                    ) VALUES (%s, %s, %s, %s, NOW())
                    ''',
                    (
                        str(uuid.uuid4()),
                        self.ctx.org_id,
                        'email_review_report',
                        json.dumps({'report': report}),
                    ),
                )
        except Exception as e:
            print(f'[EmailReviewer] Store report failed: {e}')
