"""
EmailGPS — Dan Martell's 7-folder email management system for DEX.

Antony never touches email until DEX has processed it first. Ever.
"I am no longer ever, ever allowed to touch an email that wasn't first
checked by my assistant." — Dan Martell, Buy Back Your Time

Folders:
  ANTONY        → his eyes only, needs direct attention
  TO_RESPOND    → DEX drafts response, Antony approves
  REVIEW        → discussed in daily sync
  RESPONDED     → DEX handled completely
  WAITING_ON    → replied, waiting on someone
  RECEIPTS      → all financial emails
  NEWSLETTERS   → anything with unsubscribe link
"""

from dataclasses import dataclass, field
from enum import Enum


class EmailFolder(Enum):
    ANTONY      = 'Antony'
    TO_RESPOND  = 'To Respond'
    REVIEW      = 'Review'
    RESPONDED   = 'Responded'
    WAITING_ON  = 'Waiting On'
    RECEIPTS    = 'Receipts-Financials'
    NEWSLETTERS = 'Newsletters'


@dataclass
class ProcessedEmail:
    id: str
    from_address: str
    from_name: str
    subject: str
    preview: str
    received_at: str
    folder: EmailFolder
    draft_response: str = ''
    action_required: str = ''
    notes: str = ''


class EmailGPS:

    DEX_TEMPLATE = (
        'Hi {name},\n\n'
        'This is DEX, Antony\'s assistant. '
        'I got to this email before him '
        'and thought you\'d appreciate '
        'a speedy reply.\n\n'
        '{response}\n\n'
        'Best,\n'
        'DEX\n'
        'On behalf of Antony Munoz'
    )

    # Financial signal keywords → RECEIPTS
    _FINANCIAL_SIGNALS = [
        'receipt', 'invoice', 'payment',
        'order', 'charge', 'billing',
        'subscription', 'refund', 'stripe',
        'paypal', 'transaction',
    ]

    def __init__(self, ctx):
        self.ctx = ctx

    def classify_email(self, email: ProcessedEmail) -> EmailFolder:
        """Route email to correct GPS folder."""
        subject_lower  = email.subject.lower()
        from_lower     = email.from_address.lower()
        preview_lower  = email.preview.lower()

        # Financial signals → RECEIPTS
        if any(
            s in subject_lower or s in from_lower
            for s in self._FINANCIAL_SIGNALS
        ):
            return EmailFolder.RECEIPTS

        # Unsubscribe link → NEWSLETTERS
        if 'unsubscribe' in preview_lower:
            return EmailFolder.NEWSLETTERS

        # Use AI for everything else
        try:
            from eos_ai.model_router import get_router, TaskType
            router = get_router(self.ctx)
            model  = router.route(TaskType.FAST_RESPONSE, prefer_fast=True)

            if not model:
                return EmailFolder.REVIEW

            result = router.call(
                model,
                prompt=(
                    f'Classify this email for '
                    f'Antony Munoz\'s EA system.\n\n'
                    f'From: {email.from_address}\n'
                    f'Subject: {email.subject}\n'
                    f'Preview: {email.preview}\n\n'
                    f'Folders:\n'
                    f'ANTONY = personal/important, '
                    f'needs his direct attention\n'
                    f'TO_RESPOND = DEX can draft '
                    f'a response\n'
                    f'REVIEW = needs his input '
                    f'or decision, discuss in sync\n'
                    f'RESPONDED = already handled\n'
                    f'WAITING_ON = awaiting reply '
                    f'from someone\n\n'
                    f'Reply with ONE word only:\n'
                    f'ANTONY, TO_RESPOND, REVIEW, '
                    f'RESPONDED, or WAITING_ON'
                ),
                max_tokens=10,
            )

            r = result.strip().upper()
            if 'ANTONY' in r:
                return EmailFolder.ANTONY
            elif 'TO_RESPOND' in r or 'RESPOND' in r:
                return EmailFolder.TO_RESPOND
            elif 'REVIEW' in r:
                return EmailFolder.REVIEW
            elif 'WAITING' in r:
                return EmailFolder.WAITING_ON
            return EmailFolder.TO_RESPOND

        except Exception as e:
            print(f'[EmailGPS] Classify error: {e}')
            return EmailFolder.REVIEW

    def draft_response(self, email: ProcessedEmail) -> str:
        """Generate DEX response draft for TO_RESPOND emails."""
        try:
            from eos_ai.model_router import get_router, TaskType
            router = get_router(self.ctx)
            model  = router.route(TaskType.CONVERSATION)

            if not model:
                return ''

            body = router.call(
                model,
                prompt=(
                    f'Draft a brief response to this '
                    f'email for DEX to send on behalf '
                    f'of Antony Munoz.\n\n'
                    f'From: {email.from_name}\n'
                    f'Subject: {email.subject}\n'
                    f'Email: {email.preview}\n\n'
                    f'Antony\'s tone: direct, '
                    f'professional, brief.\n'
                    f'Write ONLY the response body.\n'
                    f'No greeting, no signature.'
                ),
                max_tokens=200,
            )

            name = (email.from_name or 'there').split()[0]
            return self.DEX_TEMPLATE.format(name=name, response=body)

        except Exception as e:
            print(f'[EmailGPS] Draft error: {e}')
            return ''

    def process_inbox(
        self,
        limit: int = 50,
        process_all: bool = False,
    ) -> dict:
        """
        Fetch emails and route each to a GPS folder.

        process_all=True on first run to achieve immediate Inbox Zero
        across ALL existing emails (not just unread).
        """
        try:
            from eos_ai.gws_connector import GWSConnector
            gws = GWSConnector()

            fetch_limit = 500 if process_all else limit

            if process_all:
                # First run: get ALL inbox emails (read + unread)
                raw_emails = gws.get_all_inbox_emails(
                    max_results=fetch_limit,
                )
                print(
                    f'[EmailGPS] First run — processing ALL '
                    f'{len(raw_emails)} emails for immediate Inbox Zero'
                )
            else:
                raw_emails = gws.get_recent_emails(
                    max_results=fetch_limit,
                    query='in:inbox is:unread',
                )

            processed: dict = {folder: [] for folder in EmailFolder}

            for raw in raw_emails:
                # Parse from field: "Name <email>" or just email
                from_raw  = raw.get('from', '')
                from_name = ''
                from_addr = from_raw
                if '<' in from_raw and '>' in from_raw:
                    from_name = from_raw.split('<')[0].strip().strip('"')
                    from_addr = from_raw.split('<')[1].rstrip('>')

                email = ProcessedEmail(
                    id=raw.get('id', ''),
                    from_address=from_addr,
                    from_name=from_name,
                    subject=raw.get('subject', ''),
                    preview=raw.get('snippet', '')[:300],
                    received_at=raw.get('date', ''),
                    folder=EmailFolder.REVIEW,
                )
                email.folder = self.classify_email(email)

                if email.folder == EmailFolder.TO_RESPOND:
                    email.draft_response = self.draft_response(email)

                processed[email.folder].append(email)
                print(
                    f'[EmailGPS] {email.folder.value}: '
                    f'{email.subject[:40]}'
                )

                # Apply Gmail label to actually move email in inbox
                if email.id:
                    self.apply_label_to_email(email.id, email.folder)

            total = sum(len(v) for v in processed.values())
            print(f'[EmailGPS] Processed {total} emails')
            return processed

        except Exception as e:
            print(f'[EmailGPS] Process inbox error: {e}')
            return {}

    def generate_inbox_report(self, processed: dict) -> str:
        """Format GPS results into a Discord-ready report for Antony."""
        total = sum(len(v) for v in processed.values())

        if total == 0:
            return '📬 **Inbox:** Clean ✅'

        lines = [f'📬 **Email GPS** ({total} emails)']

        antony     = processed.get(EmailFolder.ANTONY, [])
        review     = processed.get(EmailFolder.REVIEW, [])
        to_respond = processed.get(EmailFolder.TO_RESPOND, [])
        waiting    = processed.get(EmailFolder.WAITING_ON, [])

        if antony:
            lines.append(f'\n🔴 **For You** ({len(antony)}):')
            for e in antony[:5]:
                lines.append(
                    f'  • {e.from_name or e.from_address}'
                    f': {e.subject[:50]}'
                )

        if review:
            lines.append(f'\n🟡 **Review in Sync** ({len(review)}):')
            for e in review[:5]:
                lines.append(
                    f'  • {e.from_name or e.from_address}'
                    f': {e.subject[:50]}'
                )

        if to_respond:
            lines.append(f'\n🟢 **DEX Handling** ({len(to_respond)}):')
            drafts = sum(1 for e in to_respond if e.draft_response)
            if drafts:
                lines.append(f'  ↳ {drafts} drafts ready for your approval')

        if waiting:
            lines.append(f'\n⏳ **Waiting On Reply** ({len(waiting)}):')
            for e in waiting[:3]:
                lines.append(f'  • {e.subject[:50]}')

        receipts    = processed.get(EmailFolder.RECEIPTS, [])
        newsletters = processed.get(EmailFolder.NEWSLETTERS, [])
        if receipts or newsletters:
            lines.append(
                f'\n📁 Auto-filed: '
                f'{len(receipts)} receipts, '
                f'{len(newsletters)} newsletters'
            )

        return '\n'.join(lines)

    def get_drafts_pending(self, processed: dict) -> list[ProcessedEmail]:
        """Return emails in TO_RESPOND that have a draft ready."""
        return [
            e for e in processed.get(EmailFolder.TO_RESPOND, [])
            if e.draft_response
        ]

    def get_review_folder(self, processed: dict) -> list[ProcessedEmail]:
        """Return emails in REVIEW folder."""
        return processed.get(EmailFolder.REVIEW, [])

    def apply_label_to_email(
        self,
        email_id: str,
        folder: EmailFolder,
    ) -> bool:
        """
        Apply Gmail label to actually move email in the real inbox.
        Creates the label if it doesn't exist, then removes INBOX label.
        """
        try:
            from eos_ai.gws_connector import GWSConnector
            gws = GWSConnector()
            label_name = folder.value
            label_id   = gws.get_or_create_label(label_name)
            if not label_id:
                print(
                    f'[EmailGPS] Could not get/create label: '
                    f'{label_name}'
                )
                return False
            ok = gws.apply_label_to_message(
                email_id,
                add_label_ids=[label_id],
                remove_label_ids=['INBOX'],
            )
            if ok:
                print(
                    f'[EmailGPS] Labeled {email_id} → {label_name}'
                )
            else:
                print(
                    f'[EmailGPS] Label apply failed: {email_id}'
                )
            return ok
        except Exception as e:
            print(f'[EmailGPS] Apply label error: {e}')
            return False

    def get_waiting_on(self, processed: dict) -> list[ProcessedEmail]:
        """Return emails in WAITING_ON folder."""
        return processed.get(EmailFolder.WAITING_ON, [])
