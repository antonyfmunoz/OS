---
type: codebase-class
file: eos_ai/email_gps.py
line: 51
generated: 2026-04-12
---

# EmailGPS

**File:** [[eos_ai-email_gps-py]] | **Line:** 51

*No docstring.*

## Methods

- [[eos_ai-email_gps-py-EmailGPS-__init__]]`(ctx)` — 
- [[eos_ai-email_gps-py-EmailGPS-seed_folder_definitions]]`() → bool` — Seed default GPS folder definitions into Neon on first run.
- [[eos_ai-email_gps-py-EmailGPS-_load_folder_definitions]]`() → list` — Load folder definitions from Neon. Used to build AI classification prompt.
- [[eos_ai-email_gps-py-EmailGPS-update_folder_purpose]]`(folder_name, instruction) → str` — Update a folder's purpose in Neon based on founder instruction.
- [[eos_ai-email_gps-py-EmailGPS-_classify_by_rules]]`(email) → Optional[EmailFolder]` — Hard rules for unambiguous cases — no AI reasoning needed.
- [[eos_ai-email_gps-py-EmailGPS-_check_person_recognition]]`(email) → bool` — Check if this sender is a known person from Antony's pipeline or network.
- [[eos_ai-email_gps-py-EmailGPS-classify_email]]`(email) → EmailFolder` — Route email to correct GPS folder.
- [[eos_ai-email_gps-py-EmailGPS-_load_founder_context]]`() → str` — Load founder profile for AI classification context.
- [[eos_ai-email_gps-py-EmailGPS-_default_folders]]`() → str` — 
- [[eos_ai-email_gps-py-EmailGPS-_classify_with_ai]]`(email) → EmailFolder` — AI classifies with full business context and judgment criteria.
- [[eos_ai-email_gps-py-EmailGPS-draft_response]]`(email) → str` — Generate DEX response draft for TO_RESPOND emails.
- [[eos_ai-email_gps-py-EmailGPS-extract_action_items]]`(subject, body, sender) → list[str]` — Extract action items and commitments from email.
- [[eos_ai-email_gps-py-EmailGPS-capture_email_tasks]]`(subject, body, sender, venture_id) → int` — Extract and store action items from email as dex_tasks.
- [[eos_ai-email_gps-py-EmailGPS-process_inbox]]`(limit, process_all, show_progress) → dict` — Fetch emails and route each to a GPS folder.
- [[eos_ai-email_gps-py-EmailGPS-unsubscribe_via_gmail_api]]`(email_id) → bool` — Native Gmail unsubscribe using List-Unsubscribe header.
- [[eos_ai-email_gps-py-EmailGPS-_browser_unsubscribe]]`(url) → bool` — Click unsubscribe link via headless browser.
- [[eos_ai-email_gps-py-EmailGPS-unsubscribe_and_delete]]`(email_id, email_preview) → bool` — Unsubscribe then delete. Priority order:
- [[eos_ai-email_gps-py-EmailGPS-delete_obvious_noise]]`(emails) → int` — Delete social notification emails that have zero value.
- [[eos_ai-email_gps-py-EmailGPS-_delete_email]]`(email_id) → None` — Move email to trash via Gmail API labels.
- [[eos_ai-email_gps-py-EmailGPS-generate_inbox_report]]`(processed) → str` — Format GPS results into a Discord-ready report for Antony.
- [[eos_ai-email_gps-py-EmailGPS-get_emails_to_respond]]`(limit) → list[dict]` — Get emails currently in the TO_RESPOND Gmail label.
- [[eos_ai-email_gps-py-EmailGPS-get_emails_for_review]]`(limit) → list[dict]` — Get emails currently in the REVIEW Gmail label.
- [[eos_ai-email_gps-py-EmailGPS-sla_check]]`() → list[dict]` — Check TO_RESPOND emails older than 24h with no draft.
- [[eos_ai-email_gps-py-EmailGPS-get_drafts_pending]]`(processed) → list[ProcessedEmail]` — Return emails in TO_RESPOND that have a draft ready.
- [[eos_ai-email_gps-py-EmailGPS-get_review_folder]]`(processed) → list[ProcessedEmail]` — Return emails in REVIEW folder.
- [[eos_ai-email_gps-py-EmailGPS-apply_label_to_email]]`(email_id, folder, method) → bool` — Apply Gmail label to actually move email in the real inbox.
- [[eos_ai-email_gps-py-EmailGPS-_log_classification_event]]`(email_id, folder, method) → None` — Write email_classified event to Neon for nightly review.
- [[eos_ai-email_gps-py-EmailGPS-reclassify_folder]]`(source_folder, limit) → dict` — Pull emails from a folder, re-run classification, move if misclassified.
- [[eos_ai-email_gps-py-EmailGPS-migrate_and_delete_old_labels]]`(old_to_new_map) → dict` — Migrate emails from old labels to new GPS labels, then delete old labels.
- [[eos_ai-email_gps-py-EmailGPS-get_waiting_on]]`(processed) → list[ProcessedEmail]` — Return emails in WAITING_ON folder.
- [[eos_ai-email_gps-py-EmailGPS-verify_existing_labels]]`(sample) → str` — Sample emails from each GPS label already in Gmail.
