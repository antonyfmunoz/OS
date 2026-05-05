"""UMH Objective Reconstruction — convert messy intent into structured PlanObjective.

Pure function: no LLM calls, no I/O, no execution. Uses keyword matching
and pattern extraction to infer intent category, extract known variables,
and flag uncertainty.
"""

from __future__ import annotations

import re

from umh.planning.models import PlanObjective

_INTENT_PATTERNS: list[tuple[str, re.Pattern, dict]] = [
    (
        "system_health",
        re.compile(
            r"\b(system\s+health|status|uptime|check\s+system|system\s+check|health\s+check)\b",
            re.I,
        ),
        {"template_hint": "inspect_system_status"},
    ),
    (
        "file_inspect",
        re.compile(r"\b(inspect|read|view|show|cat|open)\b.*\b(file|path)\b", re.I),
        {"template_hint": "inspect_file"},
    ),
    (
        "file_inspect",
        re.compile(r"\b(inspect|read|view|show|cat|open)\s+(/[\w./\-]+)", re.I),
        {"template_hint": "inspect_file"},
    ),
    (
        "directory_list",
        re.compile(r"\b(list|ls|dir|directory|folder|files\s+in)\b", re.I),
        {"template_hint": "list_directory"},
    ),
    (
        "summarize",
        re.compile(r"\b(summarize|summary|tldr|brief|condense)\b", re.I),
        {"template_hint": "summarize_text"},
    ),
    (
        "screenshot",
        re.compile(r"\b(screenshot|screen\s*shot|screen\s+capture|capture\s+screen)\b", re.I),
        {"template_hint": "computer_screenshot_review"},
    ),
    (
        "shell_health",
        re.compile(r"\b(load|cpu|memory|ram|disk|health)\b.*\b(check|status|usage)\b", re.I),
        {"template_hint": "shell_health_check"},
    ),
    (
        "computer_action",
        re.compile(r"\b(click|type|scroll|drag|key\s*press)\b", re.I),
        {},
    ),
    (
        "metrics",
        re.compile(r"\b(metrics|stats|statistics|dashboard|monitor)\b", re.I),
        {"template_hint": "inspect_system_status"},
    ),
]

_PATH_RE = re.compile(r"(?:^|\s)(/[\w./\-]+)")
_MAX_STEPS_RE = re.compile(r"\bmax[\s_-]*steps?\s*[:=]?\s*(\d+)\b", re.I)
_DRY_RUN_RE = re.compile(r"\b(dry[\s_-]*run|simulate|preview)\b", re.I)
_SANDBOX_RE = re.compile(r"\b(sandbox|sandboxed|isolated)\b", re.I)


def reconstruct_objective(raw_input: str) -> PlanObjective:
    """Convert a raw string into a structured PlanObjective.

    Pure function — no I/O, no LLM, no execution.
    """
    if not raw_input or not raw_input.strip():
        return PlanObjective(
            title="",
            description="",
            raw_input=raw_input or "",
            intent_category="unknown",
            uncertainty=("Empty input — cannot determine intent",),
        )

    cleaned = raw_input.strip()

    intent_category = "unknown"
    template_hint = ""
    inferred_constraints: dict[str, str | bool] = {}

    for category, pattern, meta in _INTENT_PATTERNS:
        if pattern.search(cleaned):
            intent_category = category
            template_hint = meta.get("template_hint", "")
            break

    path_match = _PATH_RE.search(cleaned)
    extracted_path = path_match.group(1) if path_match else ""

    max_steps = 10
    ms_match = _MAX_STEPS_RE.search(cleaned)
    if ms_match:
        max_steps = min(int(ms_match.group(1)), 10)

    dry_run = bool(_DRY_RUN_RE.search(cleaned))
    sandbox = bool(_SANDBOX_RE.search(cleaned))

    if dry_run:
        inferred_constraints["dry_run"] = True
    if sandbox:
        inferred_constraints["sandbox"] = True

    title = template_hint if template_hint else _derive_title(cleaned, intent_category)
    description = cleaned

    context: dict = {}
    if extracted_path:
        context["path"] = extracted_path
    if intent_category == "summarize":
        text = _extract_summarize_text(cleaned)
        if text:
            context["text"] = text

    uncertainty: list[str] = []
    assumptions: list[str] = []

    if intent_category == "unknown":
        uncertainty.append("Could not determine intent category")
    if intent_category == "file_inspect" and not extracted_path:
        uncertainty.append("File inspect intent detected but no path found")
    if intent_category == "computer_action":
        uncertainty.append("Computer action detected — will require approval")
        assumptions.append("Computer use adapter is available")
    if not template_hint and intent_category != "unknown":
        uncertainty.append("No template directly matches — may require LLM planning")

    if template_hint:
        assumptions.append(f"Template '{template_hint}' matches intent")

    return PlanObjective(
        title=title,
        description=description,
        constraints=list(inferred_constraints.keys()),
        context=context,
        max_steps=max_steps,
        dry_run=dry_run,
        raw_input=raw_input,
        intent_category=intent_category,
        inferred_constraints=inferred_constraints,
        uncertainty=tuple(uncertainty),
        assumptions=tuple(assumptions),
    )


def _derive_title(text: str, intent_category: str) -> str:
    """Produce a short title from raw text when no template matches."""
    words = text.split()
    if len(words) <= 5:
        return text.lower().strip()
    return " ".join(words[:5]).lower().strip()


def _extract_summarize_text(raw: str) -> str:
    """Extract the text to summarize from a raw input string."""
    lower = raw.lower()
    for prefix in ("summarize ", "summary of ", "tldr ", "summarize: "):
        idx = lower.find(prefix)
        if idx >= 0:
            return raw[idx + len(prefix) :].strip()
    return raw
