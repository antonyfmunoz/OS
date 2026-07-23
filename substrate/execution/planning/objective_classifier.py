"""Deterministic objective classification, assessment, and revision parsing.

No LLM, no network — pure functions of the text (plus, for revision parsing,
the plan being revised). The planning rail runs this BEFORE the existing chat
intent rail; ordinary short imperatives ("fix this") deliberately do NOT
qualify as objectives and keep flowing to ``try_chat_intent_rail`` unchanged.

Calibration (asserted by tests):
- the nine-legacy-runtime-subsystems directive → SUFFICIENTLY_SPECIFIED
- "Fix the remaining runtime stuff." → CLARIFICATION_REQUIRED (material:
  scope and decomposition are undeterminable)
- secret/safety-system text → PROHIBITED
"""

from __future__ import annotations

import re
from typing import Any

from substrate.execution.intent.intent_spec import IntentSpec
from substrate.execution.planning.records import (
    IntentAssessment,
    IntentAssessmentState,
    ObjectivePlanRecord,
    RevisionEditSet,
)

# ── Objective detection ──────────────────────────────────────────────────────

_DIRECTIVE_VERBS = (
    "inspect",
    "audit",
    "migrate",
    "build",
    "implement",
    "converge",
    "ship",
    "fix",
    "refactor",
    "close",
    "wire",
    "replace",
    "consolidate",
    "determine",
    "produce",
    "create",
    "design",
    "establish",
    "eliminate",
    "harden",
    "qualify",
    "stabilize",
)

_EXPLICIT_PREFIXES = ("objective:", "plan:")

_IDENTIFIER_RE = re.compile(r"[A-Za-z0-9_]+(?:[_/.][A-Za-z0-9_]+)+|`[^`]+`|[a-z]+_[a-z_]+")
_NUMBER_WORDS = (
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
)
_LIST_RE = re.compile(r"\b\w+\b(?:\s*,\s*\b\w+\b){2,}")

# Vague referents that make scope undeterminable without clarification.
_VAGUE_REFERENTS = (
    "stuff",
    "things",
    "the rest",
    "remaining",
    "everything",
    "etc",
    "and so on",
    "whatever",
)

# Objectives targeting external actuation the planning slice does not support.
_UNSUPPORTED_SIGNALS = (
    "send an email",
    "send email",
    "email to",
    "post to twitter",
    "post to x ",
    "post to instagram",
    "post to linkedin",
    "buy ",
    "purchase ",
    "wire money",
    "transfer money",
    "call the",
    "phone the",
)

# Categories of ``check_blocked`` reasons that prohibit even PLANNING. The
# broader destructive-verb categories ("delete"/"remove"/"kill") are legal to
# PLAN — they surface as risk boundaries and owner decisions in the plan; only
# execution of them is gated (Wave 2+). Secret exposure and safety-system
# tampering are prohibited even as plan objectives.
_PROHIBITED_REASON_MARKERS = (
    "secret exposure",
    "credentials cannot be displayed",
    "safety system",
)


def _first_clause(text: str) -> str:
    stripped = text.strip().lower()
    for sep in (".", ";", "\n"):
        idx = stripped.find(sep)
        if idx > 0:
            return stripped[:idx]
    return stripped


def _has_directive_verb(text: str) -> bool:
    clause = _first_clause(text)
    words = re.findall(r"[a-z']+", clause)
    head = words[:6]
    return any(v in head for v in _DIRECTIVE_VERBS)


def _sentence_count(text: str) -> int:
    return len([s for s in re.split(r"[.!?\n]+", text) if s.strip()])


def _has_concreteness_signal(text: str) -> bool:
    lower = text.lower()
    if _IDENTIFIER_RE.search(text):
        return True
    if any(f" {w} " in f" {lower} " for w in _NUMBER_WORDS):
        return True
    if re.search(r"\b\d+\b", lower):
        return True
    if _LIST_RE.search(lower):
        return True
    if _sentence_count(text) >= 2 and len(lower.split()) >= 25:
        return True
    return False


def is_objective(text: str) -> bool:
    """True when the message reads as a plannable multi-step objective.

    Directive verb in the opening clause AND at least one concreteness signal
    (identifiers, enumerations, counts, or substantial multi-sentence shape).
    A bare short imperative ("fix this") is NOT an objective — it belongs to
    the existing intent-capture rail.

    Vague-but-directive messages ("Fix the remaining runtime stuff") ARE
    objectives — they enter planning and get assessed CLARIFICATION_REQUIRED
    rather than being silently routed to chat.
    """
    stripped = (text or "").strip()
    if not stripped:
        return False
    lower = stripped.lower()
    if any(lower.startswith(p) for p in _EXPLICIT_PREFIXES):
        return True
    if not _has_directive_verb(stripped):
        return False
    if _has_concreteness_signal(stripped):
        return True
    # Directive + vague referent → an objective needing clarification.
    if any(v in lower for v in _VAGUE_REFERENTS):
        return True
    return False


# ── Assessment ───────────────────────────────────────────────────────────────


def _vague_scope_questions(text: str) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    lower = text.lower()
    if any(v in lower for v in _VAGUE_REFERENTS):
        questions.append(
            {
                "question": (
                    "Which specific systems, files, or subsystems does this "
                    "objective cover? Name them or point to a document that does."
                ),
                "why_material": (
                    "The referent is vague — scope cannot be determined, so the "
                    "plan's packet decomposition would be a guess."
                ),
                "dimension": "scope",
            }
        )
        questions.append(
            {
                "question": (
                    "What should be true when this objective is done (the desired end state)?"
                ),
                "why_material": (
                    "Without a desired end state the gap model and completion "
                    "contract cannot be derived."
                ),
                "dimension": "desired_state",
            }
        )
    return questions


def assess(text: str, spec: IntentSpec) -> IntentAssessment:
    """Ordered deterministic assessment: prohibited → unsupported →
    clarification → sufficiently specified.

    Clarification triggers ONLY when ambiguity is material: a vague referent
    with no concreteness signal that resolves scope. FAILED is reserved for
    pipeline exceptions recorded by the loop — never produced here.
    """
    from substrate.workstation.vps_control_catalog import check_blocked

    lower = (text or "").lower()

    blocked_reason = check_blocked(text)
    if blocked_reason and any(m in blocked_reason.lower() for m in _PROHIBITED_REASON_MARKERS):
        return IntentAssessment(
            intent_id=spec.intent_id,
            state=IntentAssessmentState.PROHIBITED.value,
            reasons=[blocked_reason],
        )

    if any(s in lower for s in _UNSUPPORTED_SIGNALS):
        return IntentAssessment(
            intent_id=spec.intent_id,
            state=IntentAssessmentState.UNSUPPORTED.value,
            reasons=[
                "The objective targets external actuation outside the "
                "planning slice's supported scope (repository + runtime state)."
            ],
        )

    questions = _vague_scope_questions(text)
    if questions and not _has_concreteness_signal(text):
        return IntentAssessment(
            intent_id=spec.intent_id,
            state=IntentAssessmentState.CLARIFICATION_REQUIRED.value,
            clarification_questions=questions,
            reasons=["Scope and desired outcome are materially unclear."],
        )

    reasons = ["Targets are named or enumerable; desired state derivable."]
    if blocked_reason:
        reasons.append(f"Risk boundary noted (planning only, no execution): {blocked_reason}")
    return IntentAssessment(
        intent_id=spec.intent_id,
        state=IntentAssessmentState.SUFFICIENTLY_SPECIFIED.value,
        reasons=reasons,
    )


# ── Revision parsing ─────────────────────────────────────────────────────────

_REVISION_SHAPE_RE = re.compile(
    r"\b(graph|plan|packet|lane|node|wave\s*\d|reclassify|supersede)\b", re.IGNORECASE
)

_REMOVE_RE = re.compile(
    r"\b(?:move|take|pull)\s+(.+?)\s+out(?:\s+of\s+(?:this|the)\s+(?:graph|plan))?"
    r"|\b(?:remove|drop)\s+(.+?)(?:\s+from\s+(?:this|the)\s+(?:graph|plan))?$",
    re.IGNORECASE,
)
_MOVE_LANE_RE = re.compile(
    r"\b(?:classify|reclassify|move)\s+(.+?)\s+(?:as|to)\s+([\w\s\-]+?)\s*$",
    re.IGNORECASE,
)
_ADD_EDGE_RE = re.compile(
    r"\b(?:do\s+)?(.+?)\s+(?:before|after)\s+(.+?)$|\b(.+?)\s+depends\s+on\s+(.+?)$",
    re.IGNORECASE,
)
_RETITLE_RE = re.compile(r"\brename\s+(.+?)\s+to\s+(.+?)$", re.IGNORECASE)
_PROHIBIT_RE = re.compile(
    r"\bdo\s+not\s+(?:modify|touch|change)\s+(?:the\s+)?(.+?)(?:\.|$)", re.IGNORECASE
)


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


def _match_nodes(phrase: str, plan: ObjectivePlanRecord) -> list[str]:
    """Resolve a phrase to node ids by normalized-token containment over node
    titles, lanes, and gap ids. Returns ALL matches (ambiguity is the caller's
    decision)."""
    tokens = [t for t in _normalize(phrase).split() if len(t) > 2]
    if not tokens:
        return []
    matches: list[str] = []
    for node in plan.nodes:
        haystack = _normalize(
            " ".join(
                [
                    str(node.get("title", "")),
                    str(node.get("lane", "")),
                    str(node.get("gap_id", "")),
                ]
            )
        )
        if all(t in haystack for t in tokens):
            matches.append(str(node.get("node_id", "")))
    return matches


def is_revision_shaped(text: str) -> bool:
    return bool(_REVISION_SHAPE_RE.search(text or ""))


def classify_revision(text: str, plan: ObjectivePlanRecord) -> RevisionEditSet | None:
    """Deterministically parse a revision message against a specific plan.

    Returns None when the message has no revision shape at all. Ambiguous or
    unresolvable phrases go to ``unmatched_phrases`` (the rail replies with a
    bounded disambiguation question instead of guessing).
    """
    stripped = (text or "").strip()
    if not stripped or not is_revision_shaped(stripped):
        return None

    edits: list[dict[str, Any]] = []
    unmatched: list[str] = []
    notes: list[str] = []

    clauses = [c.strip() for c in re.split(r"[.;\n]+", stripped) if c.strip()]
    for clause in clauses:
        prohibit = _PROHIBIT_RE.search(clause)
        if prohibit:
            notes.append(f"prohibition: do not modify {prohibit.group(1).strip()}")
            continue

        remove = _REMOVE_RE.search(clause)
        if remove:
            phrase = (remove.group(1) or remove.group(2) or "").strip()
            # A phrase like "profile and audit" names several targets.
            parts = [p.strip() for p in re.split(r"\band\b|,", phrase) if p.strip()]
            for part in parts or [phrase]:
                node_ids = _match_nodes(part, plan)
                if len(node_ids) >= 1:
                    for node_id in node_ids:
                        edits.append({"op": "remove_node", "target_node_id": node_id})
                else:
                    unmatched.append(part)
            continue

        retitle = _RETITLE_RE.search(clause)
        if retitle:
            node_ids = _match_nodes(retitle.group(1), plan)
            if len(node_ids) == 1:
                edits.append(
                    {
                        "op": "retitle",
                        "target_node_id": node_ids[0],
                        "title": retitle.group(2).strip(),
                    }
                )
            else:
                unmatched.append(retitle.group(1).strip())
            continue

        move_lane = _MOVE_LANE_RE.search(clause)
        if move_lane:
            node_ids = _match_nodes(move_lane.group(1), plan)
            lane = move_lane.group(2).strip().lower()
            if node_ids:
                for node_id in node_ids:
                    edits.append({"op": "move_lane", "target_node_id": node_id, "lane": lane})
            else:
                unmatched.append(move_lane.group(1).strip())
            continue

        edge = _ADD_EDGE_RE.search(clause)
        if edge:
            a = (edge.group(1) or edge.group(3) or "").strip()
            b = (edge.group(2) or edge.group(4) or "").strip()
            a_ids = _match_nodes(a, plan)
            b_ids = _match_nodes(b, plan)
            if len(a_ids) == 1 and len(b_ids) == 1:
                lower = clause.lower()
                if " before " in lower:
                    edits.append({"op": "add_edge", "from": a_ids[0], "to": b_ids[0]})
                else:  # "after" / "depends on": a depends on b
                    edits.append({"op": "add_edge", "from": b_ids[0], "to": a_ids[0]})
            elif a or b:
                unmatched.append(clause)
            continue

    if not edits and not unmatched and not notes:
        return None
    return RevisionEditSet(edits=edits, unmatched_phrases=unmatched, notes=notes)


__all__ = [
    "assess",
    "classify_revision",
    "is_objective",
    "is_revision_shaped",
]
