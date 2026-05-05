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

import asyncio
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EmailFolder(Enum):
    ANTONY = "Antony"
    TO_RESPOND = "To Respond"
    REVIEW = "Review"
    RESPONDED = "Responded"
    WAITING_ON = "Waiting On"
    RECEIPTS = "Receipts-Financials"
    NEWSLETTERS = "Newsletters"


@dataclass
class ProcessedEmail:
    id: str
    from_address: str
    from_name: str
    subject: str
    preview: str
    received_at: str
    folder: EmailFolder
    draft_response: str = ""
    action_required: str = ""
    notes: str = ""
    _method: str = "rules"  # 'rules' | 'ai' | 'person_recognition'


class EmailGPS:
    DEX_TEMPLATE = (
        "Hi {name},\n\n"
        "This is DEX, Antony's assistant. "
        "I got to this email before him "
        "and thought you'd appreciate "
        "a speedy reply.\n\n"
        "{response}\n\n"
        "Best,\n"
        "DEX\n"
        "On behalf of Antony Munoz"
    )

    # Hard rule: financial keywords in subject → RECEIPTS (no reasoning needed)
    _FINANCIAL_SIGNALS = [
        "receipt",
        "invoice",
        "payment",
        "order confirmation",
        "charge",
        "refund",
        "transaction",
        "billing",
        "subscription renewed",
        "renewal",
        "your order",
        "order #",
    ]

    # Noise senders for bulk delete (social notification emails only)
    NOISE_SENDERS = [
        "reddit.com",
        "quora.com",
        "medium.com",
        "producthunt.com",
        "hackernews",
    ]

    # Noise subject patterns (paired with NOISE_SENDERS for deletion)
    NOISE_SUBJECTS = [
        "commented on",
        "replied to",
        "upvoted your",
        "followed you",
        "mentioned you",
        "liked your",
        "weekly digest",
        "daily digest",
        "top posts",
        "trending",
    ]

    def __init__(self, ctx):
        self.ctx = ctx

    def seed_folder_definitions(self) -> bool:
        """Seed default GPS folder definitions into Neon on first run.
        Safe to run multiple times — uses INSERT ... ON CONFLICT DO NOTHING."""
        try:
            from umh.storage.adapters.neon import get_conn

            defaults = [
                {
                    "name": "Antony",
                    "purpose": (
                        "Personal emails and important "
                        "contacts that need Antony's "
                        "direct attention. People he knows "
                        "personally. Opportunities requiring "
                        "his judgment. Anything DEX cannot "
                        "handle without his input."
                    ),
                    "examples": [
                        "Personal message from a contact",
                        "Investment opportunity from someone known",
                        "Message from a close collaborator",
                    ],
                    "auto_actions": ["notify immediately"],
                },
                {
                    "name": "To Respond",
                    "purpose": (
                        "Emails where someone is waiting "
                        "for a reply from Antony's team. "
                        "Business inquiries, client questions, "
                        "collaboration requests, partnership "
                        "proposals. DEX drafts a response "
                        "using the DEX template."
                    ),
                    "examples": [
                        "Business inquiry from unknown person",
                        "Question about coaching services",
                        "Partnership or collaboration request",
                    ],
                    "auto_actions": ["draft response"],
                },
                {
                    "name": "Review",
                    "purpose": (
                        "Emails needing Antony's input "
                        "or decision. Action required from "
                        "platforms, policy issues, account "
                        "restrictions, contracts, legal notices, "
                        "investment opportunities, anything "
                        "DEX cannot decide without him."
                    ),
                    "examples": [
                        "Meta ad account restricted",
                        "GitHub security alert",
                        "Contract requiring signature",
                        "Investment opportunity",
                    ],
                    "auto_actions": ["add to daily sync"],
                },
                {
                    "name": "Responded",
                    "purpose": (
                        "System notifications, platform "
                        "alerts, confirmations, security "
                        "emails, automated messages that "
                        "require no response. Already handled "
                        "or no action needed."
                    ),
                    "examples": [
                        "GitHub SSH key added notification",
                        "Login confirmation email",
                        "Automated system alert",
                    ],
                    "auto_actions": ["archive"],
                },
                {
                    "name": "Waiting On",
                    "purpose": (
                        "Emails where DEX has replied "
                        "on Antony's behalf and is waiting "
                        "for a response from the other person. "
                        "DEX will follow up if no reply "
                        "after 5 days."
                    ),
                    "examples": [
                        "Sent proposal, awaiting reply",
                        "Follow-up sent, no response yet",
                    ],
                    "auto_actions": ["follow up after 5 days"],
                },
                {
                    "name": "Receipts-Financials",
                    "purpose": (
                        "Financial emails only. Payment "
                        "confirmations, invoices, billing "
                        "statements, subscription charges, "
                        "refunds, bank statements. NOT "
                        "marketing from financial companies. "
                        "NOT product announcements from "
                        "paid tools."
                    ),
                    "examples": [
                        "Stripe payment confirmation",
                        "Invoice from a vendor",
                        "Subscription renewal charge",
                    ],
                    "auto_actions": ["log to expenses"],
                },
                {
                    "name": "Newsletters",
                    "purpose": (
                        "Marketing emails, product updates, "
                        "digests, social notifications, "
                        "anything with an unsubscribe link, "
                        "content from tools and platforms, "
                        "industry news, promotional offers."
                    ),
                    "examples": [
                        "Weekly product digest",
                        "Platform marketing email",
                        "Social media notification",
                        "Industry newsletter",
                    ],
                    "auto_actions": ["unsubscribe", "archive"],
                },
            ]

            with get_conn(self.ctx.org_id) as cur:
                for folder in defaults:
                    cur.execute(
                        """
                        INSERT INTO email_folders (
                            org_id, name, purpose,
                            examples, auto_actions)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (org_id, name)
                        DO NOTHING
                        """,
                        (
                            self.ctx.org_id,
                            folder["name"],
                            folder["purpose"],
                            folder["examples"],
                            folder["auto_actions"],
                        ),
                    )
                print("[EmailGPS] Folder definitions seeded")
            return True

        except Exception as e:
            print(f"[EmailGPS] Seed failed: {e}")
            return False

    def _load_folder_definitions(self) -> list:
        """Load folder definitions from Neon. Used to build AI classification prompt."""
        try:
            from umh.storage.adapters.neon import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT name, purpose, examples, auto_actions
                    FROM email_folders
                    WHERE org_id = %s
                    ORDER BY name
                    """,
                    (self.ctx.org_id,),
                )
                rows = cur.fetchall()
                if rows:
                    return [
                        {
                            "name": r["name"],
                            "purpose": r["purpose"],
                            "examples": r["examples"] or [],
                            "auto_actions": r["auto_actions"] or [],
                        }
                        for r in rows
                    ]
        except Exception:
            pass
        return []

    def update_folder_purpose(
        self,
        folder_name: str,
        instruction: str,
    ) -> str:
        """Update a folder's purpose in Neon based on founder instruction.
        Future classifications use the updated definition."""
        try:
            from umh.storage.adapters.neon import get_conn

            # Load current purpose
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT purpose FROM email_folders
                    WHERE org_id = %s AND name = %s
                    """,
                    (self.ctx.org_id, folder_name),
                )
                row = cur.fetchone()
                current_purpose = row["purpose"] if row else ""

            # Use AI to update purpose
            from umh.gateway.entry import utility_llm_call

            prompt = (
                f'Current folder "{folder_name}" purpose:\n'
                f"{current_purpose}\n\n"
                f"Founder instruction: {instruction}\n\n"
                f"Write an updated folder purpose that incorporates "
                f"this instruction. Keep it clear and concise. "
                f"2-3 sentences maximum."
            )
            new_purpose = utility_llm_call(prompt, operation="email_gps_purpose", max_tokens=100)

            if not new_purpose:
                return ""

            # Save to Neon
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    UPDATE email_folders
                    SET purpose = %s, updated_at = NOW()
                    WHERE org_id = %s AND name = %s
                    """,
                    (new_purpose, self.ctx.org_id, folder_name),
                )

            print(f'[EmailGPS] Updated "{folder_name}": {new_purpose[:60]}')
            return new_purpose

        except Exception as e:
            print(f"[EmailGPS] Update failed: {e}")
            return ""

    # Hard rule: action-required phrases in subject → REVIEW
    # These always require Antony's decision — no ambiguity
    _ACTION_REQUIRED_SIGNALS = [
        "action required",
        "action needed",
        "urgent:",
        "[urgent]",
        "your account has been restricted",
        "your account has been suspended",
        "your account has been disabled",
        "we restricted your",
        "we suspended your",
        "verify your identity",
        "verify your account",
    ]

    def _classify_by_rules(
        self,
        email: ProcessedEmail,
    ) -> Optional[EmailFolder]:
        """
        Hard rules for unambiguous cases — no AI reasoning needed.
        Returns folder if matched, None if AI should decide.
        """
        subject_lower = email.subject.lower()
        preview_lower = (email.preview or "").lower()

        # 1. Financial keyword in subject → RECEIPTS
        if any(s in subject_lower for s in self._FINANCIAL_SIGNALS):
            return EmailFolder.RECEIPTS

        # 2. Unsubscribe in body → NEWSLETTERS
        if "unsubscribe" in preview_lower:
            return EmailFolder.NEWSLETTERS

        # 3. Explicit action-required phrase → REVIEW
        if any(
            s in subject_lower or s in preview_lower[:100] for s in self._ACTION_REQUIRED_SIGNALS
        ):
            return EmailFolder.REVIEW

        return None  # AI decides

    # Sender address patterns that are never real people
    _PLATFORM_ADDRESS_INDICATORS = (
        "noreply",
        "no-reply",
        "donotreply",
        "do-not-reply",
        "notifications@",
        "alerts@",
        "updates@",
        "mailer@",
        "bounce@",
        "support@",
        "info@",
        "hello@",
        "team@",
        "news@",
        "billing@",
        "invoice@",
        "receipts@",
        "security@",
        "account@",
        "automated@",
        "system@",
    )

    # Domains that are platform senders — never a real person in Antony's network
    _PLATFORM_DOMAINS = frozenset(
        {
            "github.com",
            "google.com",
            "apple.com",
            "microsoft.com",
            "facebook.com",
            "facebookmail.com",
            "instagram.com",
            "twitter.com",
            "x.com",
            "linkedin.com",
            "reddit.com",
            "stripe.com",
            "shopify.com",
            "notion.so",
            "slack.com",
            "discord.com",
            "zoom.us",
            "calendly.com",
            "apify.com",
            "railway.app",
            "vercel.com",
            "anthropic.com",
            "openai.com",
            "hostinger.com",
            "supabase.com",
            "termius.com",
            "fireflies.ai",
            "canny.io",
            "replit.com",
            "cursor.sh",
            "netlify.com",
            "heroku.com",
            "digitalocean.com",
            "cloudflare.com",
            "namecheap.com",
            "godaddy.com",
            "canva.com",
            "figma.com",
            "framer.com",
            "webflow.io",
            "posthog.com",
            "mixpanel.com",
            "segment.io",
            "hubspot.com",
            "mailchimp.com",
            "sendgrid.com",
            "twilio.com",
            "typeform.com",
            "notion.com",
            "airtable.com",
            "neon.tech",
            "planetscale.com",
            "supabase.io",
            "whop.com",
            "gumroad.com",
            "kajabi.com",
            "teachable.com",
            "thinkific.com",
            "circle.so",
            "skool.com",
            "firebase.google.com",
            "accounts.google.com",
        }
    )

    def _check_person_recognition(
        self,
        email: ProcessedEmail,
    ) -> bool:
        """
        Check if this sender is a known person from Antony's pipeline or network.

        Only returns True for real humans with a tracked relationship.

        Approach:
          1. Block all platform senders immediately (address patterns + domains)
          2. Delegate to central person_recognition module (CRM + meetings + memory)
        """
        from_addr = email.from_address.lower()
        from_name = (email.from_name or "").lower()

        # 1. Platform address indicators — never a real person
        if any(p in from_addr for p in self._PLATFORM_ADDRESS_INDICATORS):
            return False

        # 2. Known platform domains — never a real person
        if "@" in from_addr:
            domain = from_addr.split("@")[-1]
            if domain in self._PLATFORM_DOMAINS:
                return False
            # Also catch subdomains like mail.shopify.com, em.stripe.com
            parts = domain.split(".")
            if len(parts) >= 2:
                root = ".".join(parts[-2:])
                if root in self._PLATFORM_DOMAINS:
                    return False

        # 3. Central person recognition — checks CRM, meetings, memory, Neon
        try:
            from umh.runtime_engine.person_recognition import recognize_person

            result = recognize_person(
                name=email.from_name or "",
                email=email.from_address,
                ctx=self.ctx,
            )
            if result.get("known"):
                print(
                    f"[EmailGPS] Known person ({result['confidence']}): "
                    f"{email.from_name or email.from_address} → ANTONY "
                    f"[sources: {', '.join(set(result.get('sources', [])))}]"
                )
                return True
        except Exception as e:
            print(f"[EmailGPS] Person recognition error: {e}")

        return False

    def classify_email(self, email: ProcessedEmail) -> EmailFolder:
        """Route email to correct GPS folder.

        Two hard rules handle the obvious cases (~40% of inbox):
          1. Financial keyword in subject → RECEIPTS
          2. Unsubscribe in body → NEWSLETTERS

        Everything else → AI with full context.
        Cost: ~$0.0001/email × 200 emails = $0.02/pass.
        """
        # Person recognition — check before rules or AI.
        # If this sender has been mentioned in recent conversations → ANTONY.
        if self._check_person_recognition(email):
            email._method = "person_recognition"
            return EmailFolder.ANTONY

        rule_result = self._classify_by_rules(email)
        if rule_result is not None:
            email._method = "rules"
            return rule_result

        email._method = "ai"
        return self._classify_with_ai(email)

    def _load_founder_context(self) -> str:
        """Load founder profile for AI classification context."""
        try:
            from pathlib import Path

            context_parts = []
            for path in (
                Path("/opt/OS/data/founder_profile.md"),
                Path("/opt/OS/data/brand_identity.md"),
            ):
                if path.exists():
                    context_parts.append(path.read_text()[:400])
            if context_parts:
                return "\n".join(context_parts)
        except Exception:
            pass
        return (
            "Antony Munoz — entrepreneur. "
            "Running Lyfe Institute (Initiate Arena coaching program, $750) "
            "and Empyrean Creative (AI agency). Portland, Oregon. "
            "Stage 1 — pre-revenue, building and running outreach."
        )

    def _default_folders(self) -> str:
        return (
            "Antony: Personal emails from real people Antony knows personally\n"
            "To Respond: Someone needs a reply from Antony or DEX\n"
            "Review: Antony needs to make a decision — action required\n"
            "Responded: DEX has already sent a reply on Antony's behalf\n"
            "Waiting On: Waiting for the other person's reply\n"
            "Receipts-Financials: Financial and billing emails only\n"
            "Newsletters: Everything else — marketing, updates, notifications, onboarding"
        )

    def _classify_with_ai(
        self,
        email: ProcessedEmail,
    ) -> EmailFolder:
        """AI classifies with full business context and judgment criteria."""
        try:
            from umh.gateway.entry import utility_llm_call

            definitions = self._load_folder_definitions()
            folder_context = (
                "\n".join(f"{d['name']}: {d['purpose']}" for d in definitions)
                if definitions
                else self._default_folders()
            )

            founder_context = self._load_founder_context()

            prompt = (
                f"You are DEX, world class EA to Antony Munoz.\n\n"
                f"ABOUT ANTONY:\n"
                f"{founder_context}\n\n"
                f"YOUR JOB:\n"
                f"Classify this email into exactly one folder. "
                f"Use judgment like a seasoned EA — not rules.\n\n"
                f"Ask yourself:\n"
                f"1. Is this from a real person Antony knows? → Antony\n"
                f"2. Does someone need a reply? → To Respond\n"
                f"3. Does Antony need to make a decision? → Review\n"
                f"4. Did DEX already respond? → Responded\n"
                f"5. Is it financial/billing? → Receipts-Financials\n"
                f"6. Is it anything else — marketing, updates, "
                f"notifications, onboarding, product emails, "
                f"automated alerts? → Newsletters\n\n"
                f"FOLDER DEFINITIONS:\n"
                f"{folder_context}\n\n"
                f"EMAIL TO CLASSIFY:\n"
                f"From: {email.from_address}\n"
                f"Subject: {email.subject}\n"
                f"Preview: {email.preview}\n\n"
                f"EXAMPLES:\n"
                f'Hostinger "We got your payment" → Receipts-Financials\n'
                f"Fireflies \"Here's what you're missing\" → Newsletters\n"
                f'Meta "Action required - ad account restricted" → Review\n'
                f'Termius "Welcome to Termius" → Newsletters\n'
                f'Canny "Daily Report" → Newsletters\n'
                f'Google AI Studio "Billing Update" → Receipts-Financials\n'
                f'Friend: "Hey can we talk?" → Antony\n'
                f'Stripe "Invoice #1234" → Receipts-Financials\n'
                f'GitHub "New SSH key added" → Newsletters\n\n'
                f"Reply with ONE folder name only."
            )
            result = utility_llm_call(prompt, operation="email_gps_classify", max_tokens=50)

            r = result.strip().upper()
            mapping = {
                "ANTONY": EmailFolder.ANTONY,
                "TO RESPOND": EmailFolder.TO_RESPOND,
                "TO_RESPOND": EmailFolder.TO_RESPOND,
                "REVIEW": EmailFolder.REVIEW,
                "RESPONDED": EmailFolder.RESPONDED,
                "WAITING ON": EmailFolder.WAITING_ON,
                "WAITING_ON": EmailFolder.WAITING_ON,
                "RECEIPTS": EmailFolder.RECEIPTS,
                "RECEIPTS-FINANCIALS": EmailFolder.RECEIPTS,
                "NEWSLETTERS": EmailFolder.NEWSLETTERS,
            }
            for key, folder in mapping.items():
                if key in r:
                    return folder

            return EmailFolder.NEWSLETTERS

        except Exception as e:
            print(f"[EmailGPS] AI classify error: {e}")
            return EmailFolder.NEWSLETTERS

    def draft_response(self, email: ProcessedEmail) -> str:
        """Generate DEX response draft for TO_RESPOND emails."""
        try:
            from umh.gateway.entry import utility_llm_call

            prompt = (
                f"Draft a brief response to this "
                f"email for DEX to send on behalf "
                f"of Antony Munoz.\n\n"
                f"From: {email.from_name}\n"
                f"Subject: {email.subject}\n"
                f"Email: {email.preview}\n\n"
                f"Antony's tone: direct, "
                f"professional, brief.\n"
                f"Write ONLY the response body.\n"
                f"No greeting, no signature."
            )
            body = utility_llm_call(prompt, operation="email_gps_draft", max_tokens=200)

            name = (email.from_name or "there").split()[0]
            return self.DEX_TEMPLATE.format(name=name, response=body)

        except Exception as e:
            print(f"[EmailGPS] Draft error: {e}")
            return ""

    def extract_action_items(
        self,
        subject: str,
        body: str,
        sender: str,
    ) -> list[str]:
        """Extract action items and commitments from email."""
        try:
            from umh.gateway.entry import utility_llm_call
            import json as _json

            prompt = (
                f"Extract action items and commitments from this email.\n"
                f"Only extract REAL tasks — things that require action.\n"
                f"Ignore pleasantries and FYI content.\n\n"
                f"From: {sender}\n"
                f"Subject: {subject}\n"
                f"Body: {body[:600]}\n\n"
                f"Return JSON only:\n"
                f'{{"action_items": ["list of specific tasks"],\n'
                f'  "has_deadline": false,\n'
                f'  "urgency": "high|medium|low|none"}}'
            )
            result = utility_llm_call(prompt, operation="email_gps_extract", max_tokens=200).strip()

            if "```" in result:
                result = result.split("```")[1].replace("json", "").strip()
            data = _json.loads(result)
            return data.get("action_items", [])
        except Exception:
            return []

    def capture_email_tasks(
        self,
        subject: str,
        body: str,
        sender: str,
        venture_id: str = None,
    ) -> int:
        """Extract and store action items from email as dex_tasks."""
        tasks = self.extract_action_items(subject, body, sender)
        if not tasks:
            return 0

        try:
            from umh.storage.adapters.neon import get_conn
            import json as _json

            stored = 0
            with get_conn(self.ctx.org_id) as cur:
                for task in tasks:
                    cur.execute(
                        """
                        INSERT INTO events
                        (org_id, event_type, payload_json, handled_by)
                        VALUES (%s, %s, %s, %s)
                    """,
                        (
                            str(self.ctx.org_id),
                            "dex_task",
                            _json.dumps(
                                {
                                    "task": task,
                                    "source": "email",
                                    "email_subject": subject,
                                    "from": sender,
                                    "status": "pending",
                                }
                            ),
                            "email_gps",
                        ),
                    )
                    stored += 1
            return stored
        except Exception as e:
            logger.warning(f"[EmailGPS] capture_email_tasks failed: {e}")
            return 0

    def process_inbox(
        self,
        limit: int = 50,
        process_all: bool = False,
        show_progress: bool = False,
    ) -> dict:
        """
        Fetch emails and route each to a GPS folder.

        process_all=True on first run to achieve immediate Inbox Zero
        across ALL existing emails (not just unread).
        """
        try:
            from umh.runtime_engine.gws_connector import GWSConnector

            gws = GWSConnector()

            fetch_limit = 500 if process_all else limit

            if process_all:
                raw_emails = gws.get_all_inbox_emails(
                    max_results=fetch_limit,
                )
                print(
                    f"[EmailGPS] First run — processing ALL "
                    f"{len(raw_emails)} emails for immediate Inbox Zero"
                )
            else:
                raw_emails = gws.get_recent_emails(
                    max_results=fetch_limit,
                    query="in:inbox is:unread",
                )

            processed: dict = {folder: [] for folder in EmailFolder}
            total = len(raw_emails)

            for i, raw in enumerate(raw_emails):
                from_raw = raw.get("from", "")
                from_name = ""
                from_addr = from_raw
                if "<" in from_raw and ">" in from_raw:
                    from_name = from_raw.split("<")[0].strip().strip('"')
                    from_addr = from_raw.split("<")[1].rstrip(">")

                email = ProcessedEmail(
                    id=raw.get("id", ""),
                    from_address=from_addr,
                    from_name=from_name,
                    subject=raw.get("subject", ""),
                    preview=raw.get("snippet", "")[:300],
                    received_at=raw.get("date", ""),
                    folder=EmailFolder.REVIEW,
                )
                email.folder = self.classify_email(email)

                if email.folder in (EmailFolder.TO_RESPOND, EmailFolder.REVIEW):
                    try:
                        self.capture_email_tasks(
                            subject=email.subject,
                            body=email.preview,
                            sender=email.from_address,
                        )
                    except Exception:
                        pass

                if email.folder == EmailFolder.TO_RESPOND:
                    email.draft_response = self.draft_response(email)

                    # Queue draft for approval — writes to orchestrator/approvals/pending/
                    if email.draft_response:
                        try:
                            from umh.runtime_engine.gateway import EOSGateway

                            gw = EOSGateway()
                            approval_id = gw.queue_for_approval(
                                {
                                    "type": "email_draft",
                                    "action": "send",
                                    "to": email.sender,
                                    "subject": f"Re: {email.subject}",
                                    "body": email.draft_response,
                                    "email_id": email.email_id,
                                    "venture_id": getattr(self.ctx, "venture_id", "lyfe_institute"),
                                    "folder": "To Respond",
                                }
                            )
                            print(f"[GPS] Draft queued for approval: {approval_id}")
                        except Exception as e:
                            print(f"[GPS] Failed to queue draft: {e}")

                processed[email.folder].append(email)

                if show_progress:
                    pct = int((i + 1) / total * 40)
                    bar = "█" * pct + "░" * (40 - pct)
                    print(
                        f"\r  [{bar}] {i + 1}/{total} "
                        f"— {email.folder.value}: "
                        f"{email.subject[:30]:<30}",
                        end="",
                        flush=True,
                    )
                else:
                    print(f"[EmailGPS] {email.folder.value}: {email.subject[:40]}")

                if email.id:
                    self.apply_label_to_email(
                        email.id,
                        email.folder,
                        method=getattr(email, "_method", "rules"),
                    )

                # Process attachments if present
                try:
                    _df_parts = raw.get("payload", {}).get("parts", [])
                    _df_attachments = [
                        p.get("filename")
                        for p in _df_parts
                        if p.get("filename") and "." in p.get("filename", "")
                    ]
                    if _df_attachments:
                        from umh.runtime_engine.document_filer import process_email_attachments

                        _df_results = process_email_attachments(
                            subject=email.subject,
                            sender=email.from_address,
                            attachment_names=_df_attachments,
                        )
                        _df_review = [r for r in _df_results if r.get("requires_review")]
                        if _df_review:
                            import requests as _df_req
                            import os as _df_os

                            _df_webhook = _df_os.getenv("DISCORD_BRIEF_WEBHOOK")
                            if _df_webhook:
                                _df_filenames = ", ".join(r["filename"] for r in _df_review)
                                _df_req.post(
                                    _df_webhook,
                                    json={
                                        "content": (
                                            f"📄 **Document review needed:**\n"
                                            f"{_df_filenames}\n"
                                            f"From: {email.from_address}"
                                        )
                                    },
                                    timeout=5,
                                )
                except Exception:
                    pass

            if show_progress:
                print()  # newline after progress bar

            total_processed = sum(len(v) for v in processed.values())
            print(f"[EmailGPS] Processed {total_processed} emails")
            return processed

        except Exception as e:
            print(f"[EmailGPS] Process inbox error: {e}")
            return {}

    def unsubscribe_via_gmail_api(self, email_id: str) -> bool:
        """
        Native Gmail unsubscribe using List-Unsubscribe header.
        Most reliable method — no browser needed.
        """
        try:
            from umh.runtime_engine.gws_connector import GWSConnector

            gws = GWSConnector()
            headers = gws.get_message_headers(
                email_id,
                ["List-Unsubscribe", "List-Unsubscribe-Post"],
            )
            unsub_header = headers.get("List-Unsubscribe", "")
            if not unsub_header:
                return False

            # Extract mailto or https URL from header
            mailto_match = re.search(r"<(mailto:[^>]+)>", unsub_header)
            url_match = re.search(r"<(https?://[^>]+)>", unsub_header)

            if url_match:
                url = url_match.group(1)
                # Try POST unsubscribe if List-Unsubscribe-Post header present
                if "List-Unsubscribe-Post" in headers:
                    import urllib.request

                    req = urllib.request.Request(
                        url,
                        data=b"List-Unsubscribe=One-Click",
                        method="POST",
                    )
                    req.add_header("Content-Type", "application/x-www-form-urlencoded")
                    try:
                        urllib.request.urlopen(req, timeout=10)
                        print(f"[EmailGPS] One-click POST unsub: {url[:60]}")
                        return True
                    except Exception:
                        pass
                # Fall through to browser with the extracted URL
                return self._browser_unsubscribe(url)

            if mailto_match:
                # mailto: unsubscribes — just treat as done (no send needed)
                print(f"[EmailGPS] Mailto unsub noted: {mailto_match.group(1)[:60]}")
                return True

            return False

        except Exception as e:
            print(f"[EmailGPS] Native unsub failed: {e}")
            return False

    def _browser_unsubscribe(self, url: str) -> bool:
        """Click unsubscribe link via headless browser."""
        try:
            from umh.runtime_engine.browser_agent import BrowserAgent

            async def do_unsub(u: str) -> bool:
                agent = BrowserAgent(headless=True)
                await agent.start()
                result = await agent.navigate(u)
                await agent.stop()
                return getattr(result, "success", False)

            asyncio.run(do_unsub(url))
            print(f"[EmailGPS] Browser unsubscribed: {url[:60]}")
            return True
        except Exception as e:
            print(f"[EmailGPS] Browser unsubscribe failed: {e}")
            return False

    def unsubscribe_and_delete(
        self,
        email_id: str,
        email_preview: str,
    ) -> bool:
        """
        Unsubscribe then delete. Priority order:
          1. Gmail native API (List-Unsubscribe header — most reliable)
          2. URL extracted from preview → browser agent
          3. Just delete if all fail
        """
        try:
            # 1. Gmail native unsubscribe (header-based)
            if self.unsubscribe_via_gmail_api(email_id):
                self._delete_email(email_id)
                return True

            # 2. Scrape URL from email body preview → browser agent
            urls = re.findall(
                r'https?://[^\s<>"\']+unsubscribe[^\s<>"\']*',
                email_preview.lower(),
            )
            if urls:
                self._browser_unsubscribe(urls[0])

            # 3. Always delete regardless
            self._delete_email(email_id)
            return True

        except Exception as e:
            print(f"[EmailGPS] Unsub error: {e}")
            return False

    def delete_obvious_noise(self, emails: list) -> int:
        """
        Delete social notification emails that have zero value.
        No approval needed — these are definitively noise.
        """
        deleted = 0
        for email in emails:
            sender = email.from_address.lower()
            subject = email.subject.lower()

            if any(n in sender for n in self.NOISE_SENDERS):
                if any(t in subject for t in self.NOISE_SUBJECTS):
                    self._delete_email(email.id)
                    deleted += 1

        print(f"[EmailGPS] Deleted noise: {deleted}")
        return deleted

    def _delete_email(self, email_id: str) -> None:
        """Move email to trash via Gmail API labels."""
        try:
            from umh.runtime_engine.gws_connector import GWSConnector

            gws = GWSConnector()
            gws.apply_label_to_message(
                email_id,
                add_label_ids=["TRASH"],
                remove_label_ids=["INBOX"],
            )
        except Exception as e:
            print(f"[EmailGPS] Delete error: {e}")

    def generate_inbox_report(self, processed: dict) -> str:
        """Format GPS results into a Discord-ready report for Antony."""
        total = sum(len(v) for v in processed.values())

        if total == 0:
            return "📬 **Inbox:** Clean ✅"

        lines = [f"📬 **Email GPS** ({total} emails)"]

        antony = processed.get(EmailFolder.ANTONY, [])
        review = processed.get(EmailFolder.REVIEW, [])
        to_respond = processed.get(EmailFolder.TO_RESPOND, [])
        waiting = processed.get(EmailFolder.WAITING_ON, [])

        if antony:
            lines.append(f"\n🔴 **For You** ({len(antony)}):")
            for e in antony[:5]:
                lines.append(f"  • {e.from_name or e.from_address}: {e.subject[:50]}")

        if review:
            lines.append(f"\n🟡 **Review in Sync** ({len(review)}):")
            for e in review[:5]:
                lines.append(f"  • {e.from_name or e.from_address}: {e.subject[:50]}")

        if to_respond:
            lines.append(f"\n🟢 **DEX Handling** ({len(to_respond)}):")
            drafts = sum(1 for e in to_respond if e.draft_response)
            if drafts:
                lines.append(f"  ↳ {drafts} drafts ready for your approval")

        if waiting:
            lines.append(f"\n⏳ **Waiting On Reply** ({len(waiting)}):")
            for e in waiting[:3]:
                lines.append(f"  • {e.subject[:50]}")

        receipts = processed.get(EmailFolder.RECEIPTS, [])
        newsletters = processed.get(EmailFolder.NEWSLETTERS, [])
        responded = processed.get(EmailFolder.RESPONDED, [])
        if receipts or newsletters or responded:
            lines.append(
                f"\n📁 Auto-filed: "
                f"{len(receipts)} receipts, "
                f"{len(newsletters)} newsletters, "
                f"{len(responded)} system"
            )

        return "\n".join(lines)

    def get_emails_to_respond(self, limit: int = 5) -> list[dict]:
        """Get emails currently in the TO_RESPOND Gmail label."""
        try:
            from umh.runtime_engine.gws_connector import GWSConnector

            gws = GWSConnector()
            label_id = gws.get_or_create_label("To Respond")
            if not label_id:
                return []
            messages = gws.get_messages_by_label(label_id, max_results=limit)
            emails = []
            for m in messages[:limit]:
                detail = gws._run(
                    "gmail",
                    "users",
                    "messages",
                    "get",
                    params={
                        "userId": "me",
                        "id": m["id"],
                        "format": "metadata",
                        "metadataHeaders": ["From", "Subject", "Date"],
                    },
                )
                if detail:
                    headers = {
                        h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])
                    }
                    emails.append(
                        {
                            "id": m["id"],
                            "from": headers.get("From", ""),
                            "subject": headers.get("Subject", ""),
                            "date": headers.get("Date", ""),
                        }
                    )
            return emails
        except Exception as e:
            print(f"[EmailGPS] get_emails_to_respond failed: {e}")
            return []

    def get_emails_for_review(self, limit: int = 5) -> list[dict]:
        """Get emails currently in the REVIEW Gmail label."""
        try:
            from umh.runtime_engine.gws_connector import GWSConnector

            gws = GWSConnector()
            label_id = gws.get_or_create_label("Review")
            if not label_id:
                return []
            messages = gws.get_messages_by_label(label_id, max_results=limit)
            emails = []
            for m in messages[:limit]:
                detail = gws._run(
                    "gmail",
                    "users",
                    "messages",
                    "get",
                    params={
                        "userId": "me",
                        "id": m["id"],
                        "format": "metadata",
                        "metadataHeaders": ["From", "Subject", "Date"],
                    },
                )
                if detail:
                    headers = {
                        h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])
                    }
                    emails.append(
                        {
                            "id": m["id"],
                            "from": headers.get("From", ""),
                            "subject": headers.get("Subject", ""),
                            "date": headers.get("Date", ""),
                        }
                    )
            return emails
        except Exception as e:
            print(f"[EmailGPS] get_emails_for_review failed: {e}")
            return []

    def sla_check(self) -> list[dict]:
        """
        Check TO_RESPOND emails older than 24h with no draft.
        Returns list of SLA breaches sorted by age descending.
        """
        try:
            from email.utils import parsedate_to_datetime
            from datetime import datetime, timezone

            emails = self.get_emails_to_respond(limit=20)
            now = datetime.now(timezone.utc)
            breaches = []

            for e in emails:
                date_str = e.get("date", "")
                if not date_str:
                    continue
                try:
                    email_dt = parsedate_to_datetime(date_str)
                    age = now - email_dt.astimezone(timezone.utc)
                    if age.total_seconds() > 24 * 3600:
                        e["age_hours"] = int(age.total_seconds() / 3600)
                        breaches.append(e)
                except Exception:
                    continue

            return sorted(breaches, key=lambda x: x.get("age_hours", 0), reverse=True)
        except Exception as e:
            logger.warning(f"[EmailGPS] sla_check failed: {e}")
            return []

    def get_drafts_pending(self, processed: dict) -> list[ProcessedEmail]:
        """Return emails in TO_RESPOND that have a draft ready."""
        return [e for e in processed.get(EmailFolder.TO_RESPOND, []) if e.draft_response]

    def get_review_folder(self, processed: dict) -> list[ProcessedEmail]:
        """Return emails in REVIEW folder."""
        return processed.get(EmailFolder.REVIEW, [])

    def apply_label_to_email(
        self,
        email_id: str,
        folder: EmailFolder,
        method: str = "rules",
    ) -> bool:
        """
        Apply Gmail label to actually move email in the real inbox.
        Creates the label if it doesn't exist, then removes INBOX label.
        Logs an email_classified event to Neon for the nightly reviewer.
        """
        try:
            from umh.runtime_engine.gws_connector import GWSConnector

            gws = GWSConnector()
            label_name = folder.value
            label_id = gws.get_or_create_label(label_name)
            if not label_id:
                print(f"[EmailGPS] Could not get/create label: {label_name}")
                return False
            ok = gws.apply_label_to_message(
                email_id,
                add_label_ids=[label_id],
                remove_label_ids=["INBOX"],
            )
            if ok:
                print(f"[EmailGPS] Labeled {email_id} → {label_name}")
                self._log_classification_event(email_id, folder, method)
            else:
                print(f"[EmailGPS] Label apply failed: {email_id}")
            return ok
        except Exception as e:
            print(f"[EmailGPS] Apply label error: {e}")
            return False

    def _log_classification_event(
        self,
        email_id: str,
        folder: EmailFolder,
        method: str,
    ) -> None:
        """Write email_classified event to Neon for nightly review."""
        try:
            import uuid
            import json
            from umh.storage.adapters.neon import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO events (
                        id, org_id, event_type,
                        payload_json, created_at
                    ) VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (
                        str(uuid.uuid4()),
                        self.ctx.org_id,
                        "email_classified",
                        json.dumps(
                            {
                                "email_id": email_id,
                                "folder": folder.value,
                                "method": method,
                            }
                        ),
                    ),
                )
        except Exception as e:
            print(f"[EmailGPS] Event log error: {e}")

    def reclassify_folder(
        self,
        source_folder: "EmailFolder",
        limit: int = 200,
    ) -> dict:
        """
        Pull emails from a folder, re-run classification, move if misclassified.
        Use this to fix the To Respond folder after rule updates.

        Returns: {moved: N, stayed: N, errors: N}
        """
        try:
            from umh.runtime_engine.gws_connector import GWSConnector

            gws = GWSConnector()

            label_name = source_folder.value
            label_id = gws.get_or_create_label(label_name)
            if not label_id:
                return {"error": f"Label not found: {label_name}"}

            messages = gws.get_messages_by_label(label_id, max_results=limit)
            moved = 0
            stayed = 0
            errors = 0

            print(f"[EmailGPS] Reclassifying {len(messages)} emails from {label_name}...")

            for msg_ref in messages:
                try:
                    # Single call: metadata + snippet together
                    detail = gws._run(
                        "gmail",
                        "users",
                        "messages",
                        "get",
                        params={
                            "userId": "me",
                            "id": msg_ref["id"],
                            "format": "metadata",
                            "metadataHeaders": ["From", "Subject", "Date"],
                        },
                    )
                    if not detail:
                        errors += 1
                        continue
                    headers = {
                        h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])
                    }
                    snippet = detail.get("snippet", "")[:300]
                    from_raw = headers.get("From", "")
                    from_name = ""
                    from_addr = from_raw
                    if "<" in from_raw and ">" in from_raw:
                        from_name = from_raw.split("<")[0].strip().strip('"')
                        from_addr = from_raw.split("<")[1].rstrip(">")

                    email = ProcessedEmail(
                        id=msg_ref["id"],
                        from_address=from_addr,
                        from_name=from_name,
                        subject=headers.get("Subject", ""),
                        preview=snippet,
                        received_at=headers.get("Date", ""),
                        folder=source_folder,
                    )
                    new_folder = self.classify_email(email)

                    if new_folder != source_folder:
                        self.apply_label_to_email(email.id, new_folder)
                        # Remove the source label
                        gws.apply_label_to_message(
                            email.id,
                            add_label_ids=[],
                            remove_label_ids=[label_id],
                        )
                        print(f"[EmailGPS] Moved {email.subject[:40]} → {new_folder.value}")
                        moved += 1
                    else:
                        stayed += 1

                except Exception as e:
                    print(f"[EmailGPS] Reclassify error on {msg_ref['id']}: {e}")
                    errors += 1

            print(
                f"[EmailGPS] Reclassify complete: {moved} moved, {stayed} stayed, {errors} errors"
            )
            return {"moved": moved, "stayed": stayed, "errors": errors}

        except Exception as e:
            return {"error": str(e)}

    def migrate_and_delete_old_labels(
        self,
        old_to_new_map: dict,
    ) -> dict:
        """
        Migrate emails from old labels to new GPS labels, then delete old labels.

        old_to_new_map: {'1 - To Respond': 'To Respond', ...}
        Uses GWSConnector CLI methods — no direct API access needed.

        Returns: {migrated: N, deleted: N, errors: []}
        """
        try:
            from umh.runtime_engine.gws_connector import GWSConnector

            gws = GWSConnector()

            # Build a map of label name → label id from Gmail
            all_labels = gws.list_all_labels()
            label_map: dict[str, str] = {l["name"]: l["id"] for l in all_labels}

            migrated = 0
            deleted = 0
            errors: list[str] = []

            for old_name, new_name in old_to_new_map.items():
                old_id = label_map.get(old_name)
                if not old_id:
                    print(f"[EmailGPS] Old label not found (already gone?): {old_name}")
                    continue

                # Get or create the target GPS label
                new_id = gws.get_or_create_label(new_name)
                if not new_id:
                    errors.append(f"Could not get/create label: {new_name}")
                    continue

                # Migrate all emails from old → new in batches of 500
                messages = gws.get_messages_by_label(old_id, max_results=2000)
                batch_size = 500
                email_count = 0

                for i in range(0, len(messages), batch_size):
                    batch_ids = [m["id"] for m in messages[i : i + batch_size]]
                    ok = gws.batch_modify_messages(
                        batch_ids,
                        add_label_ids=[new_id],
                        remove_label_ids=[old_id],
                    )
                    if ok:
                        email_count += len(batch_ids)
                    else:
                        errors.append(
                            f"Batch modify failed for batch {i // batch_size} of {old_name}"
                        )

                if email_count:
                    print(f"[EmailGPS] Migrated {email_count} emails: {old_name} → {new_name}")
                migrated += email_count

                # Delete the old label
                ok = gws.delete_label(old_id)
                if ok:
                    print(f"[EmailGPS] Deleted label: {old_name}")
                    deleted += 1
                else:
                    errors.append(f"Delete failed for {old_name}")

            return {
                "migrated": migrated,
                "deleted": deleted,
                "errors": errors,
            }

        except Exception as e:
            return {"error": str(e)}

    def get_waiting_on(self, processed: dict) -> list[ProcessedEmail]:
        """Return emails in WAITING_ON folder."""
        return processed.get(EmailFolder.WAITING_ON, [])

    def verify_existing_labels(self, sample: int = 5) -> str:
        """
        Sample emails from each GPS label already in Gmail.
        Used for spot-checking DEX's historical classifications.
        Triggered via !verify-inbox in Discord.
        """
        try:
            from umh.runtime_engine.gws_connector import GWSConnector

            gws = GWSConnector()

            # Build name → id map in one call
            all_labels = gws.list_all_labels()
            label_map: dict[str, str] = {l["name"]: l["id"] for l in all_labels}

            report_lines = [
                "━━━━━━━━━━━━━━━━━━━━━━━━",
                "EXISTING LABEL VERIFICATION",
                "━━━━━━━━━━━━━━━━━━━━━━━━",
            ]

            for folder in EmailFolder:
                label_id = label_map.get(folder.value)
                if not label_id:
                    report_lines.append(f"\n{folder.value}: label not found in Gmail")
                    continue

                messages = gws.get_messages_by_label(
                    label_id,
                    max_results=sample,
                )
                report_lines.append(f"\n{folder.value} ({len(messages)} sampled):")

                for msg_ref in messages[:sample]:
                    try:
                        detail = gws._run(
                            "gmail",
                            "users",
                            "messages",
                            "get",
                            params={
                                "userId": "me",
                                "id": msg_ref["id"],
                                "format": "metadata",
                                "metadataHeaders": ["From", "Subject"],
                            },
                        )
                        if not detail:
                            continue
                        headers = {
                            h["name"]: h["value"]
                            for h in detail.get("payload", {}).get("headers", [])
                        }
                        sender = headers.get("From", "")[:30]
                        subject = headers.get("Subject", "")[:40]
                        report_lines.append(f"  • {sender}: {subject}")
                    except Exception:
                        continue

            return "\n".join(report_lines)

        except Exception as e:
            return f"verify_existing_labels failed: {e}"
