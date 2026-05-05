"""Attachment fallback for oversized Discord outputs.

When a reply exceeds safe Discord chunking limits (>9000 chars or >6 chunks),
this module prepares a short summary + .md file attachment instead of dumping
many broken chunks into the channel.

Pure preparation — no discord.py or LLM imports. Only stdlib.
"""

import re
import time
from pathlib import Path
from typing import Optional


def generate_summary(full_text: str, max_summary_chars: int = 800) -> str:
    """Generate a concise summary of the full text for Discord display.

    Extracts the first heading as title, takes opening paragraphs,
    lists section headings as bullets, and appends an attachment note.
    Always stays under max_summary_chars.
    """
    tail = "\n\n📎 *Full report attached below.*"
    budget = max_summary_chars - len(tail)
    if budget < 50:
        return full_text[:max_summary_chars]

    parts: list[str] = []

    # Extract first heading
    heading_match = re.search(r"^(#{1,3})\s+(.+)$", full_text, re.MULTILINE)
    if heading_match:
        title_line = f"**{heading_match.group(2).strip()}**"
        parts.append(title_line)

    # Grab first 2-3 paragraphs (split on double newline)
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", full_text) if p.strip()]
    # Skip the heading paragraph if we already captured it
    body_paragraphs: list[str] = []
    for p in paragraphs:
        if heading_match and p.strip() == heading_match.group(0).strip():
            continue
        # Skip lines that are just headings — we list those separately
        if re.match(r"^#{1,3}\s+", p):
            continue
        body_paragraphs.append(p)
        if len(body_paragraphs) >= 3:
            break

    if body_paragraphs:
        parts.append("\n\n".join(body_paragraphs))

    # Collect section headings as bullet list
    all_headings = re.findall(r"^#{1,3}\s+(.+)$", full_text, re.MULTILINE)
    if len(all_headings) > 1:
        section_list = "\n\n**Sections:**\n" + "\n".join(
            f"• {h.strip()}" for h in all_headings
        )
        parts.append(section_list)

    raw = "\n\n".join(parts) if parts else full_text[:budget]

    # Trim to budget
    if len(raw) > budget:
        raw = raw[: budget - 3].rstrip() + "..."

    return raw + tail


def prepare_attachment(full_text: str, reply_id: str, role: str = "") -> dict:
    """Prepare a file attachment dict for Discord.

    Writes full_text to a temp .md file and returns metadata
    needed by the transport layer to attach the file.
    """
    file_path = f"/tmp/eos_report_{reply_id}.md"
    Path(file_path).write_text(full_text, encoding="utf-8")

    short_id = reply_id[:4] if len(reply_id) >= 4 else reply_id
    filename = f"report_{short_id}.md"

    return {
        "file_path": file_path,
        "filename": filename,
        "reply_id": reply_id,
        "content_length": len(full_text),
        "created_at": time.time(),
    }


def build_fallback_message(full_text: str, reply_id: str, role: str = "") -> dict:
    """Build everything needed for an attachment-fallback delivery.

    Returns a dict with the summary, attachment metadata, delivery mode,
    reply_id, and total character count.
    """
    summary = generate_summary(full_text)
    attachment = prepare_attachment(full_text, reply_id, role)

    return {
        "summary": summary,
        "attachment": attachment,
        "delivery_mode": "attachment_fallback",
        "reply_id": reply_id,
        "total_chars": len(full_text),
    }


def build_canonical_final_message(
    full_text: str,
    result_id: str,
    *,
    title: str = "",
    summary_bullets: list[str] | None = None,
    run_id: str = "",
    task_id: str = "",
    role: str = "",
) -> dict:
    """Build everything needed for canonical final artifact delivery.

    This is the preferred delivery path for medium/long canonical final
    reports. Returns:
      - visible_message: short Builder completion message
      - attachment: file metadata for the full report
      - delivery_mode: "canonical_attachment"

    Visible message shape:
      ✓ [Title]
      • bullet 1
      • bullet 2
      ref result_id | run_id
      📎 Full report attached below.

    The attachment contains the complete exact text as a .md file.
    """
    short_id = result_id[:8] if len(result_id) >= 8 else result_id

    # Build visible summary
    parts: list[str] = []

    # Success marker + title
    display_title = title or "Task Complete"
    parts.append(f"✓ **{display_title}**")

    # Summary bullets
    if summary_bullets:
        for bullet in summary_bullets[:3]:
            parts.append(f"• {bullet}")
    else:
        # Auto-extract from full text
        auto_summary = _extract_summary_bullets(full_text)
        for bullet in auto_summary:
            parts.append(f"• {bullet}")

    # Reference line
    ref_parts = [f"ref {short_id}"]
    if run_id:
        ref_parts.append(f"run {run_id[:8]}")
    if task_id:
        ref_parts.append(f"task {task_id[:8]}")
    parts.append(" | ".join(ref_parts))

    # Attachment note
    parts.append("\n📎 *Full report attached below.*")

    visible_message = "\n".join(parts)

    # Build attachment
    filename = f"final_report_{short_id}.md"
    file_path = f"/tmp/eos_final_{result_id}.md"
    Path(file_path).write_text(full_text, encoding="utf-8")

    return {
        "visible_message": visible_message,
        "attachment": {
            "file_path": file_path,
            "filename": filename,
            "result_id": result_id,
            "content_length": len(full_text),
            "created_at": time.time(),
        },
        "delivery_mode": "canonical_attachment",
        "result_id": result_id,
        "total_chars": len(full_text),
    }


def _extract_summary_bullets(text: str, max_bullets: int = 3) -> list[str]:
    """Auto-extract summary bullets from report text.

    Takes first few meaningful paragraphs and truncates to one line each.
    """
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    bullets: list[str] = []
    for p in paragraphs:
        # Skip headings
        if re.match(r"^#{1,3}\s+", p):
            continue
        # Skip very short lines
        if len(p) < 10:
            continue
        # Truncate to reasonable bullet length
        line = p.split("\n")[0][:120]
        if len(line) > 117:
            line = line[:117] + "..."
        bullets.append(line)
        if len(bullets) >= max_bullets:
            break
    return bullets


def validate_artifact_file(file_path: str, filename: str = "") -> dict:
    """Preflight validation for an artifact file before Discord send.

    Checks:
      1. File exists on disk
      2. File size > 0
      3. File is readable (open succeeds)

    Returns dict with 'valid' bool and diagnostic fields.
    """
    result: dict = {
        "valid": False,
        "file_path": file_path,
        "filename": filename,
        "size_bytes": 0,
        "error": "",
    }

    p = Path(file_path)
    if not p.exists():
        result["error"] = "artifact_file_missing"
        return result

    size = p.stat().st_size
    result["size_bytes"] = size
    if size == 0:
        result["error"] = "artifact_file_empty"
        return result

    try:
        with open(file_path, "rb") as f:
            f.read(1)
    except Exception as exc:
        result["error"] = f"artifact_file_unreadable: {exc}"
        return result

    result["valid"] = True
    return result


def cleanup_attachment(file_path: str) -> bool:
    """Remove a temp attachment file after Discord upload.

    Returns True if the file was removed, False if it was not found.
    """
    p = Path(file_path)
    existed = p.exists()
    p.unlink(missing_ok=True)
    return existed
