---
type: codebase-class
file: eos_ai/gws_connector.py
line: 49
generated: 2026-05-07
---

# GWSConnector

**File:** [[eos_ai-gws_connector-py]] | **Line:** 49

*No docstring.*

## Methods

- [[eos_ai-gws_connector-py-GWSConnector-_run]]`() → dict | None` — Run a gws CLI command and return parsed JSON, or None on error.
- [[eos_ai-gws_connector-py-GWSConnector-get_today_events]]`() → list[dict]` — 
- [[eos_ai-gws_connector-py-GWSConnector-get_upcoming_events]]`(days) → list[dict]` — 
- [[eos_ai-gws_connector-py-GWSConnector-create_calendar_event]]`(title, start_iso, duration_minutes, attendee_email, description) → dict | None` — Create a Google Calendar event with a Google Meet link.
- [[eos_ai-gws_connector-py-GWSConnector-update_calendar_event]]`(event_id, title, start_iso, duration_minutes, description) → dict | None` — Update an existing calendar event.
- [[eos_ai-gws_connector-py-GWSConnector-delete_calendar_event]]`(event_id) → bool` — Delete a calendar event.
- [[eos_ai-gws_connector-py-GWSConnector-list_calendar_events]]`(days, query) → list[dict]` — List events with optional search query.
- [[eos_ai-gws_connector-py-GWSConnector-check_conflicts]]`(start_iso, duration_minutes, buffer_minutes) → list[dict]` — Check for calendar conflicts including buffer time.
- [[eos_ai-gws_connector-py-GWSConnector-block_travel_time]]`(event_id, location, travel_minutes) → dict` — Block travel time before and after an event
- [[eos_ai-gws_connector-py-GWSConnector-detect_timezone_from_email]]`(email) → str` — Detect likely timezone from email domain.
- [[eos_ai-gws_connector-py-GWSConnector-format_time_for_attendee]]`(dt_iso, attendee_email) → str` — Format a datetime in both Antony's timezone and
- [[eos_ai-gws_connector-py-GWSConnector-get_tasks]]`() → list[dict]` — 
- [[eos_ai-gws_connector-py-GWSConnector-create_task]]`(title, notes, due) → dict | None` — 
- [[eos_ai-gws_connector-py-GWSConnector-complete_task]]`(task_id) → bool` — 
- [[eos_ai-gws_connector-py-GWSConnector-search_drive]]`(query, max_results) → list[dict]` — 
- [[eos_ai-gws_connector-py-GWSConnector-read_document]]`(file_id) → str` — Export a Google Doc as plain text (first 5000 chars).
- [[eos_ai-gws_connector-py-GWSConnector-create_folder]]`(name, parent_id) → dict` — Create a folder in Google Drive.
- [[eos_ai-gws_connector-py-GWSConnector-move_file]]`(file_id, new_parent_id) → bool` — Move a file to a different folder.
- [[eos_ai-gws_connector-py-GWSConnector-list_files]]`(folder_id, query, max_results) → list[dict]` — List files in Drive, optionally filtered by folder or query.
- [[eos_ai-gws_connector-py-GWSConnector-rename_file]]`(file_id, new_name) → bool` — Rename a file or folder.
- [[eos_ai-gws_connector-py-GWSConnector-create_document]]`(title, content, folder_id) → dict` — Create a new Google Doc.
- [[eos_ai-gws_connector-py-GWSConnector-get_drive_structure]]`(max_folders) → list[dict]` — Get the top-level folder structure of Drive.
- [[eos_ai-gws_connector-py-GWSConnector-audit_drive]]`() → dict` — Audit Drive for organization issues:
- [[eos_ai-gws_connector-py-GWSConnector-get_recent_emails]]`(max_results, query) → list[dict]` — 
- [[eos_ai-gws_connector-py-GWSConnector-search_emails_from]]`(sender, max_results) → list[dict]` — 
- [[eos_ai-gws_connector-py-GWSConnector-audit_inbox]]`(save_path) → dict` — Read-only audit of current Gmail state.
- [[eos_ai-gws_connector-py-GWSConnector-get_all_inbox_emails]]`(max_results) → list[dict]` — Get ALL inbox emails (read + unread) for Inbox Zero processing.
- [[eos_ai-gws_connector-py-GWSConnector-get_or_create_label]]`(label_name) → str | None` — Return Gmail label ID for label_name, creating it if needed.
- [[eos_ai-gws_connector-py-GWSConnector-apply_label_to_message]]`(message_id, add_label_ids, remove_label_ids) → bool` — Add/remove labels on a message. Returns True on success.
- [[eos_ai-gws_connector-py-GWSConnector-delete_label]]`(label_id) → bool` — Permanently delete a Gmail label by ID.
- [[eos_ai-gws_connector-py-GWSConnector-get_messages_by_label]]`(label_id, max_results) → list[dict]` — List message IDs for a given label.
- [[eos_ai-gws_connector-py-GWSConnector-batch_modify_messages]]`(message_ids, add_label_ids, remove_label_ids) → bool` — Apply label changes to multiple messages in one call.
- [[eos_ai-gws_connector-py-GWSConnector-get_message_headers]]`(message_id, headers) → dict` — Fetch specific headers from a message. Returns {header_name: value}.
- [[eos_ai-gws_connector-py-GWSConnector-list_all_labels]]`() → list[dict]` — Return all Gmail labels with id, name, type.
- [[eos_ai-gws_connector-py-GWSConnector-send_email]]`(to_email, subject, body, cc, reply_to) → dict` — Send an email via Gmail API.
