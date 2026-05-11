"""
Visible Drive UI inventory for Phase 95.0.

Extracts file/folder metadata from the visible Google Drive UI
using only computer-use methods (observation, mouse, keyboard, scroll).

No API. No Playwright. No CDP. No token/cookie access.
No document content reading.

This is the worst-case fallback when APIs are unavailable.
"""

from __future__ import annotations

import re
from typing import Any

from eos_ai.transport.local_gui_control_contracts import (
    GUIInventoryItem,
    GUIObservationMethod,
    GUIObservationResult,
)


DRIVE_FILE_TYPE_INDICATORS: dict[str, str] = {
    "Google Docs": "application/vnd.google-apps.document",
    "Google Sheets": "application/vnd.google-apps.spreadsheet",
    "Google Slides": "application/vnd.google-apps.presentation",
    "Google Forms": "application/vnd.google-apps.form",
    "Google Drawings": "application/vnd.google-apps.drawing",
    "PDF": "application/pdf",
    "Word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "Microsoft Word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "Excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "Microsoft Excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "PowerPoint": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "Microsoft PowerPoint": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "Image": "image/*",
    "Video": "video/*",
    "Audio": "audio/*",
    "Folder": "application/vnd.google-apps.folder",
    "Shortcut": "application/vnd.google-apps.shortcut",
}

DATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(\w+ \d{1,2}, \d{4})"),           # "May 4, 2026"
    re.compile(r"(\d{1,2}/\d{1,2}/\d{2,4})"),      # "5/4/2026"
    re.compile(r"(\d{4}-\d{2}-\d{2})"),             # "2026-05-04"
    re.compile(r"(today|yesterday)", re.IGNORECASE),
    re.compile(r"(\w+ \d{1,2})"),                   # "May 4" (current year implied)
]

BLOCKED_SCOPES: frozenset[str] = frozenset(
    {
        "gmail",
        "mail",
        "document_body",
        "document_content",
        "file_contents",
        "login_form",
        "credential_field",
        "settings",
        "admin_console",
    }
)


def validate_inventory_scope(scope: str) -> list[str]:
    """Validate that the inventory scope is within allowed bounds."""
    errors: list[str] = []
    lower_scope = scope.lower()

    for blocked in BLOCKED_SCOPES:
        if blocked in lower_scope:
            errors.append(f"Scope '{scope}' contains blocked target: {blocked}")

    if "drive" not in lower_scope and "my drive" not in lower_scope:
        errors.append(f"Scope '{scope}' does not appear to be Google Drive")

    return errors


def normalize_visible_drive_row(text: str) -> str:
    """Normalize whitespace and control characters from a visible Drive row."""
    cleaned = re.sub(r"\s+", " ", text.strip())
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", cleaned)
    return cleaned


def extract_file_name_from_visible_row(row_text: str) -> str:
    """Extract the file name from a visible Drive list row.

    Drive list view typically shows: [icon] Name [owner] [date] [size]
    The name is usually the first substantial text element.
    Splits on original separators (tabs, double spaces) before normalizing.
    """
    if not row_text or not row_text.strip():
        return ""

    stripped = row_text.strip()

    if "\t" in stripped:
        return stripped.split("\t")[0].strip()

    if "  " in stripped:
        return stripped.split("  ")[0].strip()

    if " — " in stripped:
        return stripped.split(" — ")[0].strip()

    return normalize_visible_drive_row(stripped)


def extract_modified_date_from_visible_row(row_text: str) -> str:
    """Extract modified date from a visible Drive list row."""
    for pattern in DATE_PATTERNS:
        match = pattern.search(row_text)
        if match:
            return match.group(1)
    return ""


def infer_file_type_from_visible_row(row_text: str) -> str:
    """Infer file type from visible row text or type indicator."""
    lower = row_text.lower()

    if "folder" in lower:
        return "application/vnd.google-apps.folder"

    for indicator, mime in DRIVE_FILE_TYPE_INDICATORS.items():
        if indicator.lower() in lower:
            return mime

    if row_text.strip().endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if row_text.strip().endswith(".xlsx"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if row_text.strip().endswith(".pdf"):
        return "application/pdf"

    return "application/vnd.google-apps.document"


def dedupe_inventory_items(items: list[GUIInventoryItem]) -> list[GUIInventoryItem]:
    """Remove duplicate items by name."""
    seen: set[str] = set()
    unique: list[GUIInventoryItem] = []
    for item in items:
        key = item.name.strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def detect_end_of_drive_list(
    observation_history: list[list[str]],
    min_stable_rounds: int = 2,
) -> bool:
    """Detect when we've reached the end of the Drive file list.

    Returns True if the last N observations returned the same items,
    meaning scrolling is no longer revealing new content.
    """
    if len(observation_history) < min_stable_rounds + 1:
        return False

    recent = observation_history[-min_stable_rounds:]
    first_set = set(recent[0])

    for obs in recent[1:]:
        if set(obs) != first_set:
            return False

    return True


def build_scroll_plan(
    max_scrolls: int = 10,
    scroll_delay_ms: int = 1000,
    observe_after_scroll: bool = True,
) -> list[dict[str, Any]]:
    """Build a scroll plan for inventorying Drive contents."""
    plan: list[dict[str, Any]] = []

    plan.append({
        "step": 0,
        "action": "observe",
        "description": "Initial observation of visible Drive rows",
    })

    for i in range(1, max_scrolls + 1):
        plan.append({
            "step": i * 2 - 1,
            "action": "scroll_down",
            "delay_ms": scroll_delay_ms,
            "description": f"Scroll down #{i}",
        })
        if observe_after_scroll:
            plan.append({
                "step": i * 2,
                "action": "observe",
                "description": f"Observe after scroll #{i}",
            })

    return plan


def build_inventory_result(
    items: list[GUIInventoryItem],
    observation_method: GUIObservationMethod,
    scroll_count: int = 0,
    end_of_list_reached: bool = False,
) -> dict[str, Any]:
    """Build the final inventory result from observed items."""
    unique_items = dedupe_inventory_items(items)

    type_counts: dict[str, int] = {}
    for item in unique_items:
        t = item.item_type or "unknown"
        type_counts[t] = type_counts.get(t, 0) + 1

    return {
        "work_order": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
        "method": "COMPUTER_USE_ONLY",
        "observation_method": observation_method.value,
        "total_items": len(unique_items),
        "type_distribution": type_counts,
        "scroll_count": scroll_count,
        "end_of_list_reached": end_of_list_reached,
        "items": [item.to_dict() for item in unique_items],
        "api_used": False,
        "playwright_used": False,
        "cdp_used": False,
        "document_content_read": False,
        "credentials_captured": False,
    }


def parse_ui_automation_output(raw_output: str) -> list[GUIInventoryItem]:
    """Parse Windows UI Automation output into inventory items.

    Expected format from PowerShell UI Automation:
    One line per data item, tab-separated or structured.
    """
    items: list[GUIInventoryItem] = []
    lines = raw_output.strip().split("\n")

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        name = extract_file_name_from_visible_row(line)
        if not name:
            continue

        modified = extract_modified_date_from_visible_row(line)
        file_type = infer_file_type_from_visible_row(line)

        items.append(GUIInventoryItem(
            name=name,
            item_type=file_type,
            modified_date=modified,
            row_index=i,
            observation_method=GUIObservationMethod.WINDOWS_UI_AUTOMATION,
        ))

    return items


DRIVE_ACCESSIBILITY_ROW_PATTERN = re.compile(
    r"^(?:FILE:\s*)?(.+?)\s+(Google Docs|Google Sheets|Google Slides|Microsoft Word|PDF)"
    r"\s+Modified\s+(.+?)\s+me(?:\s+More actions.*)?$"
)


def capture_visible_drive_rows_from_accessibility_tree(raw_tree_text: str) -> list[dict[str, str]]:
    """Parse raw accessibility tree output into structured rows.

    Expected input format (from PowerShell UIAutomation DataItem names):
    FILE: FileName FileType Modified DateStr me More actions (Alt+A)
    """
    rows: list[dict[str, str]] = []
    for line in raw_tree_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Remove FILE: prefix if present
        if line.startswith("FILE: "):
            line = line[6:]
        elif line.startswith("FILE:"):
            line = line[5:].strip()

        match = DRIVE_ACCESSIBILITY_ROW_PATTERN.match(line)
        if match:
            rows.append({
                "name": match.group(1).strip(),
                "type_label": match.group(2).strip(),
                "modified": match.group(3).strip(),
            })
            continue

        # Fallback: try to extract from unstructured line
        clean = re.sub(r"\s*More actions \(Alt\+A\)\s*$", "", line)
        if not clean:
            continue

        date_match = re.search(r"Modified (.+?)\s+me$", clean)
        modified = date_match.group(1) if date_match else ""
        if date_match:
            name_type = clean[:date_match.start()].strip()
        else:
            name_type = clean

        # Determine type and extract name
        type_label = ""
        name = name_type
        for indicator in ["Google Docs", "Google Sheets", "Google Slides", "Microsoft Word", "PDF"]:
            if indicator in name_type:
                type_label = indicator
                name = name_type.replace(indicator, "").strip()
                break

        if name:
            rows.append({
                "name": name,
                "type_label": type_label,
                "modified": modified,
            })

    return rows


def extract_drive_item_from_row(row: dict[str, str]) -> GUIInventoryItem:
    """Convert a parsed row dict into a GUIInventoryItem."""
    type_label = row.get("type_label", "")
    mime = DRIVE_FILE_TYPE_INDICATORS.get(type_label, "application/vnd.google-apps.document")

    return GUIInventoryItem(
        name=row.get("name", ""),
        item_type=mime,
        modified_date=row.get("modified", ""),
        owner="me",
        observation_method=GUIObservationMethod.WINDOWS_UI_AUTOMATION,
        confidence=0.95,
    )


def detect_new_items(
    previous_items: list[GUIInventoryItem],
    current_items: list[GUIInventoryItem],
) -> list[GUIInventoryItem]:
    """Find items in current that are not in previous (by name+date key)."""
    prev_keys = {f"{i.name.lower()}|{i.modified_date}" for i in previous_items}
    return [i for i in current_items if f"{i.name.lower()}|{i.modified_date}" not in prev_keys]


def should_continue_scrolling(
    history: list[int],
    max_scrolls: int = 10,
    no_new_item_limit: int = 3,
) -> bool:
    """Determine whether to continue scrolling.

    Args:
        history: list of new-item counts after each scroll (0 means no new items found)
        max_scrolls: maximum scroll attempts
        no_new_item_limit: stop after this many consecutive scrolls with no new items
    """
    if len(history) >= max_scrolls:
        return False

    # Check if last N scrolls found no new items
    if len(history) >= no_new_item_limit:
        recent = history[-no_new_item_limit:]
        if all(count == 0 for count in recent):
            return False

    return True


def build_scroll_action(direction: str = "down", amount: str = "page") -> dict[str, str]:
    """Build a scroll action descriptor."""
    return {
        "action": "scroll",
        "direction": direction,
        "amount": amount,
    }


def build_complete_cu_inventory(
    items: list[GUIInventoryItem],
    method: GUIObservationMethod,
    scroll_count: int,
    baseline_count: int = 29,
) -> dict[str, Any]:
    """Build the complete CU inventory result with completeness metadata."""
    result = build_inventory_result(items, method, scroll_count, end_of_list_reached=True)

    unique_count = result["total_items"]
    result["baseline_count"] = baseline_count
    result["completeness"] = "COMPLETE" if unique_count >= baseline_count else "PARTIAL"
    result["recall_vs_baseline"] = round(unique_count / baseline_count, 3) if baseline_count > 0 else 0.0

    return result


def mark_inventory_incomplete(
    current_count: int,
    baseline_count: int,
    reason: str,
) -> dict[str, Any]:
    """Mark an inventory as incomplete with reason."""
    return {
        "status": "INCOMPLETE",
        "current_count": current_count,
        "baseline_count": baseline_count,
        "recall": round(current_count / baseline_count, 3) if baseline_count > 0 else 0.0,
        "reason": reason,
    }
