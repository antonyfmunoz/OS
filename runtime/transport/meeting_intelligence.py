"""
Meeting Intelligence Layer v1 — bounded, additive, deterministic.

Sits on top of the existing meeting_transport pipeline:

    inject_transcript → voice_session → responder → SPEAK_TEXT

Three capabilities:
  1. Rolling meeting summary (stateful, bounded, model-backed with fallback)
  2. Deterministic intervention engine (decision gap / ambiguity + cooldown)
  3. Memory extraction (decisions → decision, open loops → task, points → insight)

Safety contract:
  - No new threads, no loops, no daemons.
  - Every public entry point is wrapped; NEVER raises.
  - All caps enforced on list lengths.
  - If model unavailable, summary degrades to "last 3 utterances as key_points".
"""

from __future__ import annotations

import json
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional


def _log(msg: str) -> None:
    print(f"[substrate.meeting_intelligence] {msg}", file=sys.stderr)


# ─── Caps ────────────────────────────────────────────────────────────────────

MAX_KEY_POINTS = 10
MAX_DECISIONS = 5
MAX_OPEN_LOOPS = 5
MAX_UTTERANCES_PER_UPDATE = 10
MAX_SUMMARIES = 100
MAX_MEMORIES_PER_RUN = 10
INTERVENTION_COOLDOWN_SECONDS = 30.0

# Decision-intelligence scoring bounds
MAX_PRESSURE_SCORE = 20
MAX_AMBIGUITY_SCORE = 20
MAX_REFINED_MESSAGE_CHARS = 240

# Execution-intelligence bounds (v1)
MAX_COMMITMENTS = 10
MAX_COMMITMENT_TEXT_CHARS = 300
COMMITMENT_STALE_SECONDS = 180.0  # considered stale/unresolved for follow-up

# ─── Temporal Intelligence Layer v1 ──────────────────────────────────────────
# All bounded, deterministic, additive. No timers, no background work — only
# evaluated when intelligence runs on the existing shared pipeline.
FOLLOW_UP_COOLDOWN_SECONDS = 60.0  # min gap between follow-up prompts per meeting
STALE_OPEN_LOOP_SECONDS = 240.0  # open-loops unresolved this long count as stale
COMMITMENT_FRESH_SECONDS = 60.0  # commitments newer than this are "fresh"
# Deterministic commitment-trigger phrases. Intentionally tiny/simple for v1.
_COMMITMENT_TRIGGERS = (
    "i will",
    "i'll",
    "we will",
    "we'll",
    "i'm going to",
    "going to send",
    "send you",
    "send it",
    "follow up",
    "follow-up",
    "circle back",
    "get back to you",
    "do that",
    "take care of",
    "handle that",
    "ping you",
)

# Resolution-intelligence v1 — deterministic phrases that signal a
# commitment has been fulfilled. Intentionally small and bounded.
_RESOLUTION_PHRASES = (
    "done",
    "finished",
    "sent",
    "completed",
    "took care of",
    "that's done",
    "thats done",
    "we did that",
    "already done",
    "handled it",
    "wrapped up",
    "shipped it",
)

# Minimum number of overlapping 4+ char tokens between a commitment and
# a resolution utterance before we consider it a match.
_RESOLUTION_MIN_TOKEN_OVERLAP = 2

# Bounded pressure decay per resolved commitment (applied on top of
# compute_scores, then re-clamped). Keeps effect deterministic and small.
RESOLUTION_PRESSURE_DECAY_PER_ITEM = 1
MAX_RECENTLY_RESOLVED_REPORTED = 5

# ─── Coordination Intelligence Layer v1 ─────────────────────────────────────
# Ownership awareness: WHO is responsible. Bounded, deterministic, additive.
# No identity system, no CRM, no org chart. Ownership is a string label only.
MAX_OWNERSHIP_DISTRIBUTION_ENTRIES = 10
GROUP_OWNER_LABEL = "group"
# Small bounded scoring nudges so ownership influence stays predictable.
OWNED_UNRESOLVED_PRESSURE_BONUS = 1
UNOWNED_UNRESOLVED_AMBIGUITY_BONUS = 1
# Deterministic name-phrase pattern: "Name will ..." / "Name is going to ..."
# Captures a single Capitalized token at the start of a clause.
import re as _re  # noqa: E402

_NAME_WILL_RE = _re.compile(
    r"\b([A-Z][a-z]{1,30})\s+(?:will|is going to|is gonna|'ll)\b"
)
_PRONOUN_EXCLUSIONS = frozenset(
    {"i", "we", "he", "she", "they", "you", "it", "the", "that", "this"}
)
_FIRST_PERSON_TRIGGERS = ("i will", "i'll", "i'm going to", "i am going to")
_GROUP_TRIGGERS = ("we will", "we'll", "we're going to", "we are going to")

# Role slugs recognized by the refinement helper. Keeping this tuple local
# avoids importing the roles module on the hot path.
_KNOWN_ROLE_SLUGS = ("ea_orchestrator", "ceo", "portfolio_advisor")

# ─── Execution Linkage Layer v1 ─────────────────────────────────────────────
# Additive, bounded, deterministic projection of intelligence state onto a
# structured "actionable item" shape. This is NOT a task execution engine —
# it only surfaces what IS actionable in a form downstream systems can
# consume. No stores, no side effects, no autonomy.
MAX_ACTIONABLE_ITEMS = 10
MIN_ACTIONABLE_TEXT_CHARS = 12  # anything shorter is "low context"
_DECISION_FOLLOWUP_HINTS = (
    "need to",
    "should",
    "next step",
    "follow up",
    "follow-up",
    "decide",
    "revisit",
    "action",
)
# Ambiguity markers used by readiness classification. Tiny, bounded.
_AMBIGUITY_MARKERS = (
    "maybe",
    "might",
    "not sure",
    "unclear",
    "figure out",
    "tbd",
    "someone",
    "somehow",
    "at some point",
)


# ─── Models ──────────────────────────────────────────────────────────────────


@dataclass
class Commitment:
    """Bounded execution-intelligence unit: an explicit or implicit promise."""

    text: str
    owner: Optional[str] = None
    created_at: float = 0.0
    resolved: bool = False
    resolved_at: Optional[float] = None
    source: str = "meeting"
    # Coordination Intelligence v1: bounded confidence tag for owner field.
    owner_confidence: str = "low"  # "high" | "low"

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "owner": self.owner,
            "created_at": self.created_at,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at,
            "source": self.source,
            "owner_confidence": self.owner_confidence,
        }


@dataclass
class ActionableItem:
    """
    Execution Linkage v1 projection unit.

    A structured, bounded, JSON-friendly shape surfacing something the
    intelligence layer believes is actionable. Deterministic only —
    no LLM, no autonomous execution, no side effects.
    """

    text: str
    kind: str  # "commitment" | "open_loop" | "decision_followup"
    owner: Optional[str] = None
    priority: str = "low"  # "low" | "medium" | "high"
    source: str = "meeting"
    execution_ready: bool = False
    readiness_state: str = "blocked_low_context"
    readiness_reason: str = ""
    owner_confidence: str = "low"  # inherited from commitment when applicable

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "kind": self.kind,
            "owner": self.owner,
            "priority": self.priority,
            "source": self.source,
            "execution_ready": self.execution_ready,
            "readiness_state": self.readiness_state,
            "readiness_reason": self.readiness_reason,
            "owner_confidence": self.owner_confidence,
        }


@dataclass
class MeetingSummary:
    node_id: str
    meeting_id: str
    last_updated_ts: float = 0.0
    key_points: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    participants: set[str] = field(default_factory=set)
    last_processed_event_id: Optional[str] = None
    last_intervention_ts: Optional[float] = None
    # Decision-intelligence scoring (bounded, deterministic, additive).
    decision_pressure_score: int = 0
    ambiguity_score: int = 0
    priority_level: str = "low"  # "low" | "medium" | "high"
    # Execution-intelligence v1 (bounded, deterministic, additive).
    commitments: list[dict] = field(default_factory=list)  # JSON-friendly
    escalation_level: str = "low"  # "low" | "medium" | "high"
    last_followup_ts: Optional[float] = None
    # Resolution-intelligence v1
    prev_decision_pressure_score: int = 0
    escalation_trend: str = "stable"  # "rising" | "stable" | "falling"
    # Temporal Intelligence v1 — additive, bounded, deterministic.
    # open_loops_since_ts: set when open_loops first appear with no decisions,
    # cleared when decisions catch up. Used to compute stale_open_loops_count.
    open_loops_since_ts: Optional[float] = None
    last_followup_prompt_ts: Optional[float] = (
        None  # last time detect_follow_up emitted
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "meeting_id": self.meeting_id,
            "last_updated_ts": self.last_updated_ts,
            "key_points": list(self.key_points),
            "decisions": list(self.decisions),
            "open_loops": list(self.open_loops),
            "participants": sorted(self.participants),
            "last_processed_event_id": self.last_processed_event_id,
            "last_intervention_ts": self.last_intervention_ts,
            "decision_pressure_score": self.decision_pressure_score,
            "ambiguity_score": self.ambiguity_score,
            "priority_level": self.priority_level,
            "commitments": [dict(c) for c in self.commitments],
            "escalation_level": self.escalation_level,
            "last_followup_ts": self.last_followup_ts,
            "prev_decision_pressure_score": self.prev_decision_pressure_score,
            "escalation_trend": self.escalation_trend,
            "open_loops_since_ts": self.open_loops_since_ts,
            "last_followup_prompt_ts": self.last_followup_prompt_ts,
        }


@dataclass
class ExtractedMemory:
    type: str  # "decision" | "task" | "insight"
    content: str
    timestamp: float
    source: str = "meeting"

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "content": self.content,
            "timestamp": self.timestamp,
            "source": self.source,
        }


# ─── Bounded stores ──────────────────────────────────────────────────────────


class _MeetingSummaryStore:
    def __init__(self, cap: int = MAX_SUMMARIES) -> None:
        self._lock = threading.RLock()
        self._rows: dict[str, MeetingSummary] = {}
        self._recent_interventions: list[dict] = []
        self._memories: dict[str, list[ExtractedMemory]] = {}
        self._cap = cap

    @staticmethod
    def _key(node_id: str, meeting_id: str) -> str:
        return f"meeting_summary:{node_id}:{meeting_id}"

    def get(self, node_id: str, meeting_id: str) -> Optional[MeetingSummary]:
        with self._lock:
            return self._rows.get(self._key(node_id, meeting_id))

    def put(self, summary: MeetingSummary) -> MeetingSummary:
        with self._lock:
            key = self._key(summary.node_id, summary.meeting_id)
            self._rows[key] = summary
            if len(self._rows) > self._cap:
                # drop oldest by last_updated_ts
                ordered = sorted(
                    self._rows.items(), key=lambda kv: kv[1].last_updated_ts
                )
                for k, _ in ordered[: len(self._rows) - self._cap]:
                    self._rows.pop(k, None)
        return summary

    def record_intervention(self, entry: dict) -> None:
        with self._lock:
            self._recent_interventions.append(entry)
            if len(self._recent_interventions) > 20:
                self._recent_interventions = self._recent_interventions[-20:]

    def recent_interventions(self, limit: int = 10) -> list[dict]:
        with self._lock:
            return list(self._recent_interventions[-max(0, int(limit)) :])

    def put_memories(self, node_id: str, memories: list[ExtractedMemory]) -> None:
        with self._lock:
            key = f"meeting_memory:{node_id}"
            bucket = self._memories.setdefault(key, [])
            bucket.extend(memories)
            if len(bucket) > 200:
                self._memories[key] = bucket[-200:]

    def memories(self, node_id: str) -> list[ExtractedMemory]:
        with self._lock:
            return list(self._memories.get(f"meeting_memory:{node_id}", []))

    def memory_count(self, node_id: Optional[str] = None) -> int:
        with self._lock:
            if node_id is None:
                return sum(len(v) for v in self._memories.values())
            return len(self._memories.get(f"meeting_memory:{node_id}", []))

    def clear(self) -> None:
        with self._lock:
            self._rows.clear()
            self._recent_interventions.clear()
            self._memories.clear()


_store_singleton: Optional[_MeetingSummaryStore] = None
_store_singleton_lock = threading.Lock()


def get_meeting_summary_store() -> _MeetingSummaryStore:
    global _store_singleton
    if _store_singleton is None:
        with _store_singleton_lock:
            if _store_singleton is None:
                _store_singleton = _MeetingSummaryStore()
    return _store_singleton


def reset_meeting_summary_store_for_tests() -> None:
    global _store_singleton
    with _store_singleton_lock:
        _store_singleton = None


# ─── Utilities ───────────────────────────────────────────────────────────────


def _cap_list(items: Any, cap: int) -> list[str]:
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for x in items:
        if isinstance(x, str):
            s = x.strip()
            if s:
                out.append(s[:500])
        if len(out) >= cap:
            break
    return out


def _extract_json_block(text: str) -> Optional[dict]:
    """Best-effort: pull the first {...} JSON object from a model reply."""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        pass
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
    except Exception:  # noqa: BLE001
        return None
    return None


# ─── Summary update ──────────────────────────────────────────────────────────


def _fallback_summary(
    previous: Optional[MeetingSummary],
    utterances: list[dict],
) -> dict[str, list[str]]:
    """Deterministic fallback when the model is unavailable or returns garbage."""
    prev_points = list(previous.key_points) if previous else []
    tail = [
        (u.get("text") or "").strip()
        for u in utterances[-3:]
        if isinstance(u, dict) and (u.get("text") or "").strip()
    ]
    merged_points = _cap_list(prev_points + tail, MAX_KEY_POINTS)
    return {
        "key_points": merged_points,
        "decisions": list(previous.decisions) if previous else [],
        "open_loops": list(previous.open_loops) if previous else [],
    }


def _build_prompt(
    previous: Optional[MeetingSummary],
    utterances: list[dict],
) -> tuple[str, str]:
    system = (
        "You maintain a rolling structured summary of a live meeting. "
        "Return STRICT JSON only, with exactly these keys: "
        '"key_points" (<=10), "decisions" (<=5), "open_loops" (<=5). '
        "Each value is a list of short strings. No prose outside JSON."
    )
    prev_block = {
        "key_points": list(previous.key_points) if previous else [],
        "decisions": list(previous.decisions) if previous else [],
        "open_loops": list(previous.open_loops) if previous else [],
    }
    lines = []
    for u in utterances:
        if not isinstance(u, dict):
            continue
        speaker = u.get("participant_name") or u.get("user_id") or "speaker"
        text = (u.get("text") or "").strip()
        if text:
            lines.append(f"- {speaker}: {text[:400]}")
    prompt = (
        "PREVIOUS_SUMMARY_JSON:\n"
        + json.dumps(prev_block, ensure_ascii=False)
        + "\n\nNEW_UTTERANCES:\n"
        + ("\n".join(lines) if lines else "(none)")
        + "\n\nReturn updated JSON only."
    )
    return system, prompt


def update_meeting_summary(
    node_id: str,
    meeting_id: str,
    utterances: list[dict],
) -> dict[str, Any]:
    """Update (or create) the rolling meeting summary. Never raises."""
    try:
        store = get_meeting_summary_store()
        previous = store.get(node_id, meeting_id)
        if previous is None:
            previous = MeetingSummary(node_id=node_id, meeting_id=meeting_id)

        # bound incoming utterances
        recent = [u for u in (utterances or []) if isinstance(u, dict)][
            -MAX_UTTERANCES_PER_UPDATE:
        ]

        # track participants
        for u in recent:
            name = u.get("participant_name") or u.get("user_id")
            if isinstance(name, str) and name.strip():
                previous.participants.add(name.strip()[:80])
                if len(previous.participants) > 50:
                    # keep set bounded
                    trimmed = set(list(previous.participants)[:50])
                    previous.participants = trimmed

        parsed: Optional[dict] = None
        try:
            from execution.runtime.model_router import call_with_fallback

            system, prompt = _build_prompt(previous, recent)
            result = call_with_fallback(
                prompt=prompt,
                system=system,
                task_type="summarize",
                trigger_source="meeting_intelligence",
            )
            text = getattr(result, "output", None) or ""
            parsed = _extract_json_block(text)
        except Exception as e:  # noqa: BLE001
            _log(f"model call failed: {e}")
            parsed = None

        if not isinstance(parsed, dict):
            parsed = _fallback_summary(previous, recent)

        previous.key_points = _cap_list(parsed.get("key_points"), MAX_KEY_POINTS)
        previous.decisions = _cap_list(parsed.get("decisions"), MAX_DECISIONS)
        previous.open_loops = _cap_list(parsed.get("open_loops"), MAX_OPEN_LOOPS)
        previous.last_updated_ts = time.time()

        # Temporal Intelligence v1: mark when open_loops first appeared without
        # enough decisions to resolve them. Clear when decisions catch up.
        try:
            if previous.open_loops and len(previous.decisions) < len(
                previous.open_loops
            ):
                if not previous.open_loops_since_ts:
                    previous.open_loops_since_ts = previous.last_updated_ts
            else:
                previous.open_loops_since_ts = None
        except Exception as e:  # noqa: BLE001
            _log(f"open_loops_since_ts tracking failed: {e}")

        # Execution-intelligence: extract + merge commitments from new utterances
        try:
            new_commitments = extract_commitments(recent)
            if new_commitments or previous.commitments:
                previous.commitments = _merge_commitments(
                    previous.commitments, new_commitments
                )
        except Exception as e:  # noqa: BLE001
            _log(f"commitment merge failed: {e}")

        compute_scores(previous)

        # Resolution-intelligence: detect fulfilled commitments, decay pressure.
        try:
            updates = resolve_commitments(previous, recent)
            if updates:
                _apply_pressure_decay(previous, len(updates))
        except Exception as e:  # noqa: BLE001
            _log(f"resolve_commitments failed: {e}")

        compute_escalation_level(previous)
        _update_escalation_trend(previous)

        # track last processed event id if present on the tail utterance
        if recent:
            tail = recent[-1]
            eid = tail.get("event_id") or (tail.get("metadata") or {}).get("event_id")
            if isinstance(eid, str) and eid:
                previous.last_processed_event_id = eid[:120]

        store.put(previous)
        return previous.as_dict()
    except Exception as e:  # noqa: BLE001
        _log(f"update_meeting_summary failed: {e}")
        return {
            "node_id": node_id,
            "meeting_id": meeting_id,
            "last_updated_ts": time.time(),
            "key_points": [],
            "decisions": [],
            "open_loops": [],
            "participants": [],
            "last_processed_event_id": None,
            "last_intervention_ts": None,
            "error": str(e)[:200],
        }


# ─── Intervention engine ─────────────────────────────────────────────────────


def _count_ambiguity_overlaps(key_points: list[str]) -> int:
    """Bounded count of overlapping key-point pairs (≥2 shared 4+ char tokens)."""
    norm = []
    for p in key_points:
        toks = {w.lower() for w in p.split() if len(w) >= 4}
        norm.append(toks)
    overlaps = 0
    for i in range(len(norm)):
        for j in range(i + 1, len(norm)):
            if len(norm[i] & norm[j]) >= 2:
                overlaps += 1
                if overlaps >= MAX_AMBIGUITY_SCORE:
                    return MAX_AMBIGUITY_SCORE
    return overlaps


def compute_scores(summary: MeetingSummary) -> None:
    """
    Deterministically compute decision_pressure_score, ambiguity_score,
    priority_level on a MeetingSummary in-place. Never raises.
    """
    try:
        pressure = max(0, len(summary.open_loops) - len(summary.decisions))
        ambiguity = _count_ambiguity_overlaps(summary.key_points)

        # Coordination Intelligence v1: bounded ownership-aware nudges.
        # Owned unresolved commitments raise pressure (accountability exists).
        # Unowned unresolved commitments raise ambiguity (who owns this?).
        owned_unresolved = 0
        unowned_unresolved = 0
        for c in unresolved_commitments(summary):
            if (c.get("owner") or "").strip():
                owned_unresolved += 1
            else:
                unowned_unresolved += 1
        if owned_unresolved > 0:
            pressure += OWNED_UNRESOLVED_PRESSURE_BONUS
        if unowned_unresolved > 0:
            ambiguity += UNOWNED_UNRESOLVED_AMBIGUITY_BONUS

        pressure = min(pressure, MAX_PRESSURE_SCORE)
        ambiguity = min(ambiguity, MAX_AMBIGUITY_SCORE)

        if pressure >= 3:
            level = "high"
        elif pressure >= 1 or ambiguity >= 1:
            level = "medium"
        else:
            level = "low"

        summary.decision_pressure_score = pressure
        summary.ambiguity_score = ambiguity
        summary.priority_level = level
    except Exception as e:  # noqa: BLE001
        _log(f"compute_scores failed: {e}")
        summary.decision_pressure_score = 0
        summary.ambiguity_score = 0
        summary.priority_level = "low"


# ─── Execution intelligence: commitments + follow-up + escalation ───────────


def _infer_ownership(
    low_text: str,
    raw_text: str,
    speaker: Optional[str],
) -> tuple[Optional[str], str]:
    """
    Deterministic ownership heuristic for Coordination Intelligence v1.

    Priority (bounded, no NLP):
      1. "Name will ..." capitalized name → (Name, "high")
      2. "I will ..." with speaker metadata → (speaker, "high")
      3. "I will ..." without speaker → (None, "low")
      4. "We will ..." → ("group", "high")
      5. fallback to speaker if present → (speaker, "low")
      6. otherwise → (None, "low")
    """
    try:
        # 1. Explicit third-party: "John will send it"
        m = _NAME_WILL_RE.search(raw_text or "")
        if m:
            name = m.group(1).strip()[:80]
            if name and name.lower() not in _PRONOUN_EXCLUSIONS:
                return (name, "high")
        # 2/3. First person
        if any(t in low_text for t in _FIRST_PERSON_TRIGGERS):
            if speaker:
                return (speaker, "high")
            return (None, "low")
        # 4. Group
        if any(t in low_text for t in _GROUP_TRIGGERS):
            return (GROUP_OWNER_LABEL, "high")
        # 5. Fallback to speaker
        if speaker:
            return (speaker, "low")
    except Exception as e:  # noqa: BLE001
        _log(f"_infer_ownership failed: {e}")
    return (None, "low")


def extract_commitments(utterances: list[dict]) -> list[Commitment]:
    """
    Deterministic v1 commitment extraction.

    Scans utterances for simple trigger phrases ("I will", "follow up", etc.)
    and emits Commitment objects. Never raises; returns bounded list.
    """
    out: list[Commitment] = []
    try:
        if not isinstance(utterances, list):
            return out
        now = time.time()
        for u in utterances:
            if not isinstance(u, dict):
                continue
            text = (u.get("text") or "").strip()
            if not text:
                continue
            low = text.lower()
            # Coordination Intelligence v1: "Name will ..." is also a valid
            # commitment trigger even without the first-person phrases.
            has_name_will = bool(_NAME_WILL_RE.search(text))
            if not has_name_will and not any(
                trig in low for trig in _COMMITMENT_TRIGGERS
            ):
                continue
            speaker = u.get("participant_name") or u.get("user_id")
            speaker_str = (
                speaker.strip()[:80]
                if isinstance(speaker, str) and speaker.strip()
                else None
            )
            owner_str, owner_conf = _infer_ownership(low, text, speaker_str)
            out.append(
                Commitment(
                    text=text[:MAX_COMMITMENT_TEXT_CHARS],
                    owner=owner_str,
                    created_at=now,
                    resolved=False,
                    source="meeting",
                    owner_confidence=owner_conf,
                )
            )
            if len(out) >= MAX_COMMITMENTS:
                break
    except Exception as e:  # noqa: BLE001
        _log(f"extract_commitments failed: {e}")
    return out


def _merge_commitments(existing: list[dict], new_items: list[Commitment]) -> list[dict]:
    """Append new commitments onto existing, dedupe by text, cap enforced."""
    merged: list[dict] = []
    seen: set[str] = set()
    for c in existing or []:
        if not isinstance(c, dict):
            continue
        key = (c.get("text") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(c)
    for nc in new_items:
        key = (nc.text or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(nc.as_dict())
        if len(merged) >= MAX_COMMITMENTS:
            break
    return merged[:MAX_COMMITMENTS]


def _tokens(text: str) -> set[str]:
    if not isinstance(text, str):
        return set()
    return {w.lower().strip(".,!?;:") for w in text.split() if len(w) >= 4}


def resolve_commitments(
    summary: MeetingSummary,
    utterances: list[dict],
) -> list[dict]:
    """
    Deterministic v1 resolution detection.

    Scans new utterances for simple resolution phrases and matches them
    against unresolved commitments via keyword overlap. On match the
    commitment dict is mutated in-place (resolved=True, resolved_at=now)
    and a bounded list of updates is returned.

    Never raises.
    """
    updates: list[dict] = []
    try:
        if not isinstance(utterances, list):
            return updates
        commitments = summary.commitments or []
        if not commitments:
            return updates

        now = time.time()
        for u in utterances:
            if not isinstance(u, dict):
                continue
            text = (u.get("text") or "").strip()
            if not text:
                continue
            low = text.lower()
            if not any(p in low for p in _RESOLUTION_PHRASES):
                continue
            u_tokens = _tokens(text)
            if not u_tokens:
                continue

            for c in commitments:
                if not isinstance(c, dict) or c.get("resolved"):
                    continue
                c_tokens = _tokens(c.get("text") or "")
                if not c_tokens:
                    continue
                overlap = len(u_tokens & c_tokens)
                if overlap >= _RESOLUTION_MIN_TOKEN_OVERLAP:
                    c["resolved"] = True
                    c["resolved_at"] = now
                    updates.append(
                        {
                            "text": (c.get("text") or "")[:MAX_COMMITMENT_TEXT_CHARS],
                            "owner": c.get("owner"),
                            "resolved_at": now,
                        }
                    )
                    if len(updates) >= MAX_COMMITMENTS:
                        return updates
                    # one utterance can close multiple commitments, but
                    # don't break — allow chained matches.
    except Exception as e:  # noqa: BLE001
        _log(f"resolve_commitments failed: {e}")
    return updates


def _apply_pressure_decay(summary: MeetingSummary, resolved_delta: int) -> None:
    """Bounded, deterministic downward adjustment of pressure score."""
    try:
        if resolved_delta <= 0:
            return
        decay = resolved_delta * RESOLUTION_PRESSURE_DECAY_PER_ITEM
        new_pressure = max(0, int(summary.decision_pressure_score or 0) - decay)
        summary.decision_pressure_score = min(new_pressure, MAX_PRESSURE_SCORE)
        # Re-derive priority_level downward if pressure dropped to 0 and
        # no ambiguity remains. Keep the existing tiered thresholds.
        if summary.decision_pressure_score >= 3:
            summary.priority_level = "high"
        elif (
            summary.decision_pressure_score >= 1 or (summary.ambiguity_score or 0) >= 1
        ):
            summary.priority_level = "medium"
        else:
            summary.priority_level = "low"
    except Exception as e:  # noqa: BLE001
        _log(f"_apply_pressure_decay failed: {e}")


def _update_escalation_trend(summary: MeetingSummary) -> None:
    """Compare current pressure against prev snapshot; bounded trend tag."""
    try:
        prev = int(summary.prev_decision_pressure_score or 0)
        cur = int(summary.decision_pressure_score or 0)
        if cur > prev:
            summary.escalation_trend = "rising"
        elif cur < prev:
            summary.escalation_trend = "falling"
        else:
            summary.escalation_trend = "stable"
        summary.prev_decision_pressure_score = cur
    except Exception as e:  # noqa: BLE001
        _log(f"_update_escalation_trend failed: {e}")
        summary.escalation_trend = "stable"


def unresolved_commitments(summary: MeetingSummary) -> list[dict]:
    try:
        return [
            c
            for c in (summary.commitments or [])
            if isinstance(c, dict) and not c.get("resolved", False)
        ]
    except Exception:  # noqa: BLE001
        return []


def ownership_distribution(summary: MeetingSummary) -> dict[str, int]:
    """
    Bounded count of commitments per owner label. Unowned commitments are
    NOT included here (use unassigned_commitments_count). Cap enforced.
    """
    counts: dict[str, int] = {}
    try:
        for c in summary.commitments or []:
            if not isinstance(c, dict):
                continue
            owner = (c.get("owner") or "").strip()
            if not owner:
                continue
            counts[owner] = counts.get(owner, 0) + 1
            if len(counts) >= MAX_OWNERSHIP_DISTRIBUTION_ENTRIES:
                break
    except Exception as e:  # noqa: BLE001
        _log(f"ownership_distribution failed: {e}")
    return counts


def unassigned_commitments_count(summary: MeetingSummary) -> int:
    try:
        return sum(
            1
            for c in (summary.commitments or [])
            if isinstance(c, dict) and not (c.get("owner") or "").strip()
        )
    except Exception:  # noqa: BLE001
        return 0


def ownership_pressure_hint(summary: MeetingSummary) -> str:
    """
    Single bounded label describing ownership health of unresolved commitments.
      - "clear"    → unresolved items all have owners
      - "diffused" → mix of owned + unowned
      - "missing"  → all unresolved items are unowned
      - "clear"    → no unresolved items (default calm state)
    """
    try:
        unresolved = unresolved_commitments(summary)
        if not unresolved:
            return "clear"
        owned = sum(1 for c in unresolved if (c.get("owner") or "").strip())
        unowned = len(unresolved) - owned
        if unowned == 0:
            return "clear"
        if owned == 0:
            return "missing"
        return "diffused"
    except Exception:  # noqa: BLE001
        return "clear"


def compute_escalation_level(summary: MeetingSummary) -> str:
    """
    Derive escalation from existing scores + unresolved commitment count.
    Deterministic. Never raises. Writes to summary.escalation_level and returns it.
    """
    try:
        unresolved = len(unresolved_commitments(summary))
        pressure = int(summary.decision_pressure_score or 0)
        ambiguity = int(summary.ambiguity_score or 0)
        priority = summary.priority_level or "low"

        if priority == "high" or pressure >= 3 or unresolved >= 3:
            level = "high"
        elif priority == "medium" or pressure >= 1 or ambiguity >= 1 or unresolved >= 1:
            level = "medium"
        else:
            level = "low"
        summary.escalation_level = level
        return level
    except Exception as e:  # noqa: BLE001
        _log(f"compute_escalation_level failed: {e}")
        summary.escalation_level = "low"
        return "low"


# ─── Temporal Intelligence v1 helpers ────────────────────────────────────────


def commitment_age_seconds(commitment: dict, now: Optional[float] = None) -> float:
    """Age in seconds of a commitment dict. Safe on bad input."""
    try:
        created = float((commitment or {}).get("created_at") or 0.0)
        if created <= 0.0:
            return 0.0
        ref = float(now) if now is not None else time.time()
        return max(0.0, ref - created)
    except Exception:  # noqa: BLE001
        return 0.0


def oldest_unresolved_commitment_age_seconds(
    summary: MeetingSummary, now: Optional[float] = None
) -> float:
    """Age of the oldest unresolved commitment. 0.0 if none."""
    try:
        unresolved = unresolved_commitments(summary)
        if not unresolved:
            return 0.0
        ref = float(now) if now is not None else time.time()
        return max(commitment_age_seconds(c, ref) for c in unresolved)
    except Exception:  # noqa: BLE001
        return 0.0


def stale_commitments_count(
    summary: MeetingSummary, now: Optional[float] = None
) -> int:
    """Count of unresolved commitments older than COMMITMENT_STALE_SECONDS."""
    try:
        ref = float(now) if now is not None else time.time()
        return sum(
            1
            for c in unresolved_commitments(summary)
            if commitment_age_seconds(c, ref) >= COMMITMENT_STALE_SECONDS
        )
    except Exception:  # noqa: BLE001
        return 0


def stale_open_loops_count(summary: MeetingSummary, now: Optional[float] = None) -> int:
    """
    Stale open loops: open_loops exist, have aged past STALE_OPEN_LOOP_SECONDS
    since first appearing without decisions catching up. Bounded by MAX_OPEN_LOOPS.
    """
    try:
        if not summary.open_loops:
            return 0
        since = float(summary.open_loops_since_ts or 0.0)
        if since <= 0.0:
            return 0
        ref = float(now) if now is not None else time.time()
        if (ref - since) < STALE_OPEN_LOOP_SECONDS:
            return 0
        return min(len(summary.open_loops), MAX_OPEN_LOOPS)
    except Exception:  # noqa: BLE001
        return 0


def next_followup_eligible_ts(summary: MeetingSummary) -> Optional[float]:
    """
    Earliest wall-clock timestamp a new follow-up prompt may be emitted.
    Uses last_followup_prompt_ts (or last_followup_ts as fallback) + cooldown.
    Returns None if no follow-up has ever been emitted.
    """
    try:
        anchor = summary.last_followup_prompt_ts or summary.last_followup_ts or None
        if not anchor:
            return None
        return float(anchor) + FOLLOW_UP_COOLDOWN_SECONDS
    except Exception:  # noqa: BLE001
        return None


def is_followup_in_cooldown(
    summary: MeetingSummary, now: Optional[float] = None
) -> bool:
    """True if a follow-up was emitted within FOLLOW_UP_COOLDOWN_SECONDS."""
    try:
        eligible = next_followup_eligible_ts(summary)
        if eligible is None:
            return False
        ref = float(now) if now is not None else time.time()
        return ref < eligible
    except Exception:  # noqa: BLE001
        return False


def temporal_health(summary: MeetingSummary, now: Optional[float] = None) -> str:
    """
    Deterministic temporal quality signal for operator reporting.
    Returns one of: "fresh" | "aging" | "stale".
    """
    try:
        ref = float(now) if now is not None else time.time()
        if stale_commitments_count(summary, ref) > 0:
            return "stale"
        if stale_open_loops_count(summary, ref) > 0:
            return "stale"
        oldest = oldest_unresolved_commitment_age_seconds(summary, ref)
        if oldest == 0.0 and not summary.open_loops:
            return "fresh"
        if oldest >= COMMITMENT_FRESH_SECONDS:
            return "aging"
        return "fresh"
    except Exception:  # noqa: BLE001
        return "fresh"


def detect_follow_up(summary: MeetingSummary) -> Optional[dict]:
    """
    Deterministic follow-up detector. If there's at least one unresolved
    commitment, return a bounded intervention candidate dict. Prefer stale ones.
    Returns None otherwise (caller falls back to existing decision/ambiguity logic).

    Temporal v1: gated by FOLLOW_UP_COOLDOWN_SECONDS — suppresses repeat prompts
    for the same meeting within the cooldown window.
    """
    try:
        unresolved = unresolved_commitments(summary)
        if not unresolved:
            return None

        now = time.time()
        # Cooldown: suppress repeat follow-up prompts within the window.
        if is_followup_in_cooldown(summary, now):
            return None

        # Prioritize oldest unresolved deterministically.
        unresolved_sorted = sorted(
            unresolved, key=lambda c: float(c.get("created_at") or 0.0)
        )
        stale = [
            c
            for c in unresolved_sorted
            if (now - float(c.get("created_at") or 0.0)) >= COMMITMENT_STALE_SECONDS
        ]
        target = stale[0] if stale else unresolved_sorted[0]
        text = (target.get("text") or "").strip()[:MAX_COMMITMENT_TEXT_CHARS]
        if not text:
            return None
        owner = target.get("owner")
        level = (summary.escalation_level or "low").lower()
        # Coordination Intelligence v1: owner-targeted + escalation-aware phrasing.
        if owner and owner != GROUP_OWNER_LABEL:
            if level == "high":
                msg = f"{owner} — you committed to: {text}. Status now?"
            else:
                msg = (
                    f"{owner}, you mentioned you'd handle: {text}. Has that been done?"
                )
        elif owner == GROUP_OWNER_LABEL:
            if level == "high":
                msg = f"The group committed to: {text}. Who is driving it?"
            else:
                msg = f"We said we'd handle: {text}. Who is taking point?"
        else:
            if level == "high":
                msg = (
                    f"This item has no clear owner and is unresolved: {text}. "
                    f"Who will take it?"
                )
            else:
                msg = (
                    f"This item doesn't have a clear owner yet: {text}. "
                    f"Who should take it?"
                )
        return {
            "type": "follow_up",
            "message": msg[: MAX_REFINED_MESSAGE_CHARS * 2],
            "stale": bool(stale),
            "commitment_text": text,
            "owner": owner,
            "owner_confidence": target.get("owner_confidence", "low"),
            "ownership_pressure_hint": ownership_pressure_hint(summary),
        }
    except Exception as e:  # noqa: BLE001
        _log(f"detect_follow_up failed: {e}")
        return None


def _has_repeated_topic(key_points: list[str]) -> bool:
    """Cheap overlap check: two key points share ≥2 tokens of 4+ chars."""
    norm = []
    for p in key_points:
        toks = {w.lower() for w in p.split() if len(w) >= 4}
        norm.append(toks)
    for i in range(len(norm)):
        for j in range(i + 1, len(norm)):
            if len(norm[i] & norm[j]) >= 2:
                return True
    return False


def detect_intervention(summary: MeetingSummary) -> Optional[dict]:
    """Deterministic rule-based trigger. Returns intervention dict or None."""
    try:
        now = time.time()
        last = summary.last_intervention_ts or 0.0
        if now - last < INTERVENTION_COOLDOWN_SECONDS:
            return None

        level = compute_escalation_level(summary)

        # Execution-intelligence: unresolved commitments take precedence.
        follow_up = detect_follow_up(summary)
        if follow_up is not None:
            follow_up["escalation_level"] = level
            return follow_up

        if len(summary.open_loops) >= 3 and len(summary.decisions) == 0:
            return {
                "type": "decision_prompt",
                "message": "Do you want to finalize a decision on: "
                + summary.open_loops[0],
                "escalation_level": level,
            }

        if len(summary.key_points) >= 2 and _has_repeated_topic(summary.key_points):
            return {
                "type": "clarification",
                "message": "There seems to be ambiguity around: "
                + summary.key_points[0],
                "escalation_level": level,
            }

        # At high escalation with no other trigger, still nudge on top open loop.
        if level == "high" and summary.open_loops:
            return {
                "type": "decision_prompt",
                "message": "High priority — resolve: " + summary.open_loops[0],
                "escalation_level": level,
            }
    except Exception as e:  # noqa: BLE001
        _log(f"detect_intervention failed: {e}")
    return None


_ROLE_STYLE_HINT = {
    "ceo": "Strategic framing: crisp, decisive, owner-tone.",
    "ea_orchestrator": "Operational clarity: next-step, scheduling-friendly.",
    "portfolio_advisor": "Risk/analysis framing: surface tradeoffs, no command.",
}

_ROLE_STATIC_PREFIX = {
    "ceo": "Decision needed — ",
    "ea_orchestrator": "Next step — ",
    "portfolio_advisor": "Risk check — ",
}


def _normalize_role(role_slug: Optional[str]) -> Optional[str]:
    if not isinstance(role_slug, str):
        return None
    slug = role_slug.strip().lower()
    return slug if slug in _KNOWN_ROLE_SLUGS else None


def derive_active_role(node_id: Optional[str] = None) -> Optional[str]:
    """
    Best-effort: derive the currently speaking role from the active voice
    session, if one is attached to the node. Always safe; returns None on
    any failure so the caller can fall back to role-agnostic phrasing.
    """
    try:
        from runtime.substrate import voice_session as vs  # noqa: F401

        getter = getattr(vs, "get_active_role_slug", None)
        if callable(getter):
            return _normalize_role(getter(node_id))
    except Exception:  # noqa: BLE001
        pass
    return None


def refine_intervention_message(
    raw_message: str,
    role_slug: Optional[str],
    summary: Optional[MeetingSummary] = None,
) -> str:
    """
    Bounded, fallback-safe refinement of an intervention message.

    Contract:
      - Trigger logic is NOT moved here; caller already decided to intervene.
      - If role is unknown → return raw_message untouched (capped).
      - Tries model_router.call_with_fallback for phrasing; on ANY failure,
        returns a deterministic role-prefixed static phrasing.
      - Output is always <= MAX_REFINED_MESSAGE_CHARS and single-line.
    """
    raw = (raw_message or "").strip()
    if not raw:
        return ""
    role = _normalize_role(role_slug)
    if role is None:
        return raw[:MAX_REFINED_MESSAGE_CHARS]

    static = (_ROLE_STATIC_PREFIX.get(role, "") + raw)[:MAX_REFINED_MESSAGE_CHARS]

    try:
        from execution.runtime.model_router import call_with_fallback

        style = _ROLE_STYLE_HINT.get(role, "")
        pressure = getattr(summary, "decision_pressure_score", 0) if summary else 0
        ambiguity = getattr(summary, "ambiguity_score", 0) if summary else 0
        priority = getattr(summary, "priority_level", "low") if summary else "low"

        system = (
            "You rephrase a SHORT meeting intervention for a specific agent role. "
            "Rules: ONE sentence, <=200 chars, no preamble, no quotes, no emojis, "
            "preserve meaning, match the role style. Return ONLY the sentence."
        )
        prompt = (
            f"ROLE: {role}\nSTYLE: {style}\n"
            f"PRIORITY: {priority} (pressure={pressure}, ambiguity={ambiguity})\n"
            f"ORIGINAL: {raw}\n\nRephrased:"
        )
        result = call_with_fallback(
            prompt=prompt,
            system=system,
            task_type="summarize",
            trigger_source="meeting_intelligence.refine",
        )
        text = (getattr(result, "output", None) or "").strip()
        # Strip quotes / leading markers; keep one line.
        if text:
            text = text.splitlines()[0].strip().strip('"').strip("'")
            if text:
                return text[:MAX_REFINED_MESSAGE_CHARS]
    except Exception as e:  # noqa: BLE001
        _log(f"refine_intervention_message model path failed: {e}")

    return static


def maybe_emit_intervention(
    node_id: str,
    meeting_id: str,
    summary: Any,
) -> Optional[dict]:
    """Detect + emit SPEAK_TEXT intervention. Never raises."""
    try:
        store = get_meeting_summary_store()
        live = store.get(node_id, meeting_id)
        if live is None:
            return None

        interv = detect_intervention(live)
        if interv is None:
            return None

        role = derive_active_role(node_id)
        refined = refine_intervention_message(interv["message"], role, live)
        if refined:
            interv["message"] = refined
        interv["role"] = role
        interv["priority_level"] = live.priority_level
        interv.setdefault("escalation_level", live.escalation_level)
        if interv.get("type") == "follow_up":
            _now = time.time()
            live.last_followup_ts = _now
            live.last_followup_prompt_ts = _now

        try:
            from runtime.transport.station_helpers import propose_speak_text

            propose_speak_text(
                node_id=node_id,
                text=interv["message"],
                issued_by="meeting_intelligence",
            )
        except Exception as e:  # noqa: BLE001
            _log(f"propose_speak_text failed: {e}")

        live.last_intervention_ts = time.time()
        store.put(live)
        store.record_intervention(
            {
                "node_id": node_id,
                "meeting_id": meeting_id,
                "ts": live.last_intervention_ts,
                "type": interv["type"],
                "role": role,
                "priority_level": live.priority_level,
                "escalation_level": live.escalation_level,
                "message": interv["message"][:240],
            }
        )
        return interv
    except Exception as e:  # noqa: BLE001
        _log(f"maybe_emit_intervention failed: {e}")
        return None


# ─── Memory extraction ───────────────────────────────────────────────────────


def extract_memory(summary: Any) -> list[ExtractedMemory]:
    """Turn summary fields into ExtractedMemory objects. Never raises."""
    out: list[ExtractedMemory] = []
    try:
        if summary is None:
            return out
        node_id = getattr(summary, "node_id", None)
        now = time.time()
        decisions = list(getattr(summary, "decisions", []) or [])
        open_loops = list(getattr(summary, "open_loops", []) or [])
        key_points = list(getattr(summary, "key_points", []) or [])

        for d in decisions:
            if len(out) >= MAX_MEMORIES_PER_RUN:
                break
            out.append(ExtractedMemory(type="decision", content=str(d), timestamp=now))
        for t in open_loops:
            if len(out) >= MAX_MEMORIES_PER_RUN:
                break
            out.append(ExtractedMemory(type="task", content=str(t), timestamp=now))
        for p in key_points:
            if len(out) >= MAX_MEMORIES_PER_RUN:
                break
            out.append(ExtractedMemory(type="insight", content=str(p), timestamp=now))

        if node_id and out:
            get_meeting_summary_store().put_memories(str(node_id), out)
    except Exception as e:  # noqa: BLE001
        _log(f"extract_memory failed: {e}")
    return out


# ─── Hot-path hook (called by meeting_transport.pump_attached_sources) ──────


def on_utterance_injected(
    node_id: str,
    meeting_id: Optional[str],
    recent_utterances: list[dict],
) -> None:
    """Wrapper the transport calls after each inject_utterance. Never raises."""
    try:
        if not meeting_id:
            meeting_id = "default"
        summary_dict = update_meeting_summary(node_id, meeting_id, recent_utterances)  # noqa: F841
        live = get_meeting_summary_store().get(node_id, meeting_id)
        if live is not None:
            maybe_emit_intervention(node_id, meeting_id, live)
            extract_memory(live)
    except Exception as e:  # noqa: BLE001
        _log(f"on_utterance_injected failed: {e}")


# ─── Reporting helper ────────────────────────────────────────────────────────


def _memory_counts_by_type(
    memories: list[ExtractedMemory],
) -> dict[str, int]:
    counts = {"decision": 0, "task": 0, "insight": 0}
    for m in memories:
        if m.type in counts:
            counts[m.type] += 1
    return counts


# ─── Execution Linkage Layer v1 — projection + classification ──────────────


def classify_execution_readiness(item: "ActionableItem") -> dict[str, Any]:
    """
    Deterministic readiness classifier for an ActionableItem.

    States:
      - ready
      - blocked_missing_owner
      - blocked_ambiguous
      - blocked_low_context

    Bounded heuristics only. Never raises. Mutates the item fields
    `readiness_state`, `readiness_reason`, `execution_ready` and returns
    a small JSON-friendly dict snapshot.
    """
    state = "ready"
    reason = "owner + context present"
    try:
        text = (item.text or "").strip()
        low = text.lower()
        # 1. Low context beats everything (can't act on vague text).
        if len(text) < MIN_ACTIONABLE_TEXT_CHARS:
            state = "blocked_low_context"
            reason = f"text under {MIN_ACTIONABLE_TEXT_CHARS} chars"
        # 2. Missing owner — for commitment / open_loop / decision followups.
        elif not (item.owner or "").strip():
            state = "blocked_missing_owner"
            reason = "no owner identified"
        # 3. Ambiguous: low owner confidence, vague markers, or group without detail.
        elif item.owner_confidence == "low" or any(
            m in low for m in _AMBIGUITY_MARKERS
        ):
            state = "blocked_ambiguous"
            reason = "ambiguous owner or wording"
        else:
            state = "ready"
            reason = "owner + clear phrasing"
    except Exception as e:  # noqa: BLE001
        _log(f"classify_execution_readiness failed: {e}")
        state = "blocked_low_context"
        reason = "classifier error"

    item.readiness_state = state
    item.readiness_reason = reason
    item.execution_ready = state == "ready"
    return {
        "readiness_state": state,
        "execution_readiness_reason": reason,
        "execution_ready": item.execution_ready,
    }


def _decision_implies_followup(decision_text: str) -> bool:
    if not isinstance(decision_text, str):
        return False
    low = decision_text.lower()
    return any(h in low for h in _DECISION_FOLLOWUP_HINTS)


def project_actionable_items(summary: "MeetingSummary") -> list[ActionableItem]:
    """
    Turn an existing MeetingSummary into a bounded list of ActionableItem
    projections. Pure function; never mutates the summary. Never raises.

    Sources (in order, bounded by MAX_ACTIONABLE_ITEMS):
      1. Unresolved commitments     → kind="commitment"
      2. Stale open loops           → kind="open_loop"
      3. Decisions implying followup→ kind="decision_followup"
    """
    out: list[ActionableItem] = []
    try:
        if summary is None:
            return out
        priority = (summary.priority_level or "low").strip() or "low"
        if priority not in ("low", "medium", "high"):
            priority = "low"

        # 1. Unresolved commitments.
        for c in unresolved_commitments(summary):
            if len(out) >= MAX_ACTIONABLE_ITEMS:
                break
            if not isinstance(c, dict):
                continue
            text = (c.get("text") or "").strip()
            if not text:
                continue
            owner_raw = (c.get("owner") or "").strip() or None
            conf = c.get("owner_confidence") or "low"
            item = ActionableItem(
                text=text[:MAX_COMMITMENT_TEXT_CHARS],
                kind="commitment",
                owner=owner_raw,
                priority=priority,
                source=c.get("source") or "meeting",
                owner_confidence=conf if conf in ("high", "low") else "low",
            )
            classify_execution_readiness(item)
            out.append(item)

        # 2. Stale open loops — only when actually stale per temporal layer.
        try:
            stale_count = stale_open_loops_count(summary)
        except Exception:  # noqa: BLE001
            stale_count = 0
        if stale_count > 0:
            for loop_text in (summary.open_loops or [])[:MAX_OPEN_LOOPS]:
                if len(out) >= MAX_ACTIONABLE_ITEMS:
                    break
                if not isinstance(loop_text, str):
                    continue
                text = loop_text.strip()
                if not text:
                    continue
                item = ActionableItem(
                    text=text[:MAX_COMMITMENT_TEXT_CHARS],
                    kind="open_loop",
                    owner=None,
                    priority=priority,
                    source="meeting",
                    owner_confidence="low",
                )
                classify_execution_readiness(item)
                out.append(item)

        # 3. Decisions implying follow-up (only if deterministic hint present).
        for dec in (summary.decisions or [])[:MAX_DECISIONS]:
            if len(out) >= MAX_ACTIONABLE_ITEMS:
                break
            if not isinstance(dec, str):
                continue
            text = dec.strip()
            if not text or not _decision_implies_followup(text):
                continue
            item = ActionableItem(
                text=text[:MAX_COMMITMENT_TEXT_CHARS],
                kind="decision_followup",
                owner=None,
                priority=priority,
                source="meeting",
                owner_confidence="low",
            )
            classify_execution_readiness(item)
            out.append(item)
    except Exception as e:  # noqa: BLE001
        _log(f"project_actionable_items failed: {e}")
    return out[:MAX_ACTIONABLE_ITEMS]


def execution_linkage_block(summary: "MeetingSummary") -> dict[str, Any]:
    """
    Bounded report-shape for Execution Linkage v1. JSON-friendly.
    Safe on any input. Always returns a fully-populated dict.
    """
    ready = blocked_owner = blocked_amb = blocked_ctx = 0
    items_dicts: list[dict[str, Any]] = []
    top_owner: Optional[str] = None
    highest_priority: Optional[dict[str, Any]] = None
    _PRIO_RANK = {"low": 0, "medium": 1, "high": 2}
    try:
        items = project_actionable_items(summary) if summary is not None else []
        owner_counts: dict[str, int] = {}
        for it in items:
            d = it.as_dict()
            items_dicts.append(d)
            st = it.readiness_state
            if st == "ready":
                ready += 1
            elif st == "blocked_missing_owner":
                blocked_owner += 1
            elif st == "blocked_ambiguous":
                blocked_amb += 1
            else:
                blocked_ctx += 1
            if it.owner:
                owner_counts[it.owner] = owner_counts.get(it.owner, 0) + 1
            if highest_priority is None or _PRIO_RANK.get(
                it.priority, 0
            ) > _PRIO_RANK.get(highest_priority.get("priority", "low"), 0):
                highest_priority = d
        if owner_counts:
            top_owner = max(owner_counts.items(), key=lambda kv: kv[1])[0]
    except Exception as e:  # noqa: BLE001
        _log(f"execution_linkage_block failed: {e}")

    total = len(items_dicts)
    return {
        "actionable_items_count": total,
        "actionable_items_ready_count": ready,
        "actionable_items_blocked_count": total - ready,
        "actionable_items": items_dicts,
        "execution_readiness_summary": {
            "ready": ready,
            "blocked_missing_owner": blocked_owner,
            "blocked_ambiguous": blocked_amb,
            "blocked_low_context": blocked_ctx,
        },
        "top_actionable_owner": top_owner,
        "highest_priority_actionable": highest_priority,
    }


def intelligence_report_block(
    node_id: Optional[str] = None,
    meeting_id: Optional[str] = None,
) -> dict[str, Any]:
    """Bounded snapshot used by transport_report. Never raises."""
    try:
        store = get_meeting_summary_store()
        summary_dict: Optional[dict] = None
        high_priority_open_loops: list[str] = []
        scoring: dict[str, Any] = {
            "decision_pressure_score": 0,
            "ambiguity_score": 0,
            "priority_level": "low",
        }
        actionable_tasks: list[dict[str, Any]] = []
        commitments_count = 0
        unresolved_commitments_count = 0
        resolved_commitments_count = 0
        completion_rate = 0.0
        follow_up_candidates: list[dict[str, Any]] = []
        intervention_escalation_level = "low"
        escalation_trend = "stable"
        recent_commitments: list[dict[str, Any]] = []
        recently_resolved_commitments: list[dict[str, Any]] = []
        # Temporal Intelligence v1 report defaults
        stale_commitments_count_val = 0
        oldest_unresolved_age_val = 0.0
        stale_open_loops_count_val = 0
        next_followup_eligible_ts_val: Optional[float] = None
        followup_cooldown_active = False
        temporal_health_val = "fresh"
        # Coordination Intelligence v1 defaults
        ownership_distribution_val: dict[str, int] = {}
        unassigned_commitments_count_val = 0
        commitments_by_owner: dict[str, list[dict]] = {}
        top_owner_val: Optional[str] = None
        ownership_pressure_hint_val = "clear"
        if node_id and meeting_id:
            live = store.get(node_id, meeting_id)
            if live is not None:
                summary_dict = live.as_dict()
                scoring = {
                    "decision_pressure_score": live.decision_pressure_score,
                    "ambiguity_score": live.ambiguity_score,
                    "priority_level": live.priority_level,
                }
                if live.priority_level in ("medium", "high"):
                    high_priority_open_loops = list(live.open_loops[:5])
                actionable_tasks = [
                    {
                        "content": t[:240],
                        "actionable": True,
                        "priority": live.priority_level,
                    }
                    for t in live.open_loops[:5]
                ]
                # Execution-intelligence fields
                commitments_count = len(live.commitments or [])
                unresolved = unresolved_commitments(live)
                unresolved_commitments_count = len(unresolved)
                resolved_commitments_count = max(
                    0, commitments_count - unresolved_commitments_count
                )
                completion_rate = (
                    round(resolved_commitments_count / commitments_count, 3)
                    if commitments_count > 0
                    else 0.0
                )
                intervention_escalation_level = live.escalation_level or "low"
                escalation_trend = live.escalation_trend or "stable"
                recent_commitments = [
                    {
                        "text": (c.get("text") or "")[:240],
                        "owner": c.get("owner"),
                        "resolved": bool(c.get("resolved", False)),
                        "resolved_at": c.get("resolved_at"),
                    }
                    for c in (live.commitments or [])[-5:]
                ]
                resolved_sorted = sorted(
                    [
                        c
                        for c in (live.commitments or [])
                        if isinstance(c, dict) and c.get("resolved")
                    ],
                    key=lambda c: float(c.get("resolved_at") or 0.0),
                    reverse=True,
                )
                recently_resolved_commitments = [
                    {
                        "text": (c.get("text") or "")[:240],
                        "owner": c.get("owner"),
                        "resolved_at": c.get("resolved_at"),
                    }
                    for c in resolved_sorted[:MAX_RECENTLY_RESOLVED_REPORTED]
                ]
                # Temporal Intelligence v1: bounded snapshots
                _now_rep = time.time()
                stale_commitments_count_val = stale_commitments_count(live, _now_rep)
                oldest_unresolved_age_val = round(
                    oldest_unresolved_commitment_age_seconds(live, _now_rep), 3
                )
                stale_open_loops_count_val = stale_open_loops_count(live, _now_rep)
                next_followup_eligible_ts_val = next_followup_eligible_ts(live)
                followup_cooldown_active = is_followup_in_cooldown(live, _now_rep)
                temporal_health_val = temporal_health(live, _now_rep)
                # Coordination Intelligence v1 snapshots
                ownership_distribution_val = ownership_distribution(live)
                unassigned_commitments_count_val = unassigned_commitments_count(live)
                ownership_pressure_hint_val = ownership_pressure_hint(live)
                # Bounded commitments_by_owner (<= MAX_OWNERSHIP_DISTRIBUTION_ENTRIES,
                # each owner's list capped at 5 items for report size).
                for _c in live.commitments or []:
                    if not isinstance(_c, dict):
                        continue
                    _own = (_c.get("owner") or "").strip()
                    if not _own:
                        continue
                    bucket = commitments_by_owner.setdefault(_own, [])
                    if len(bucket) >= 5:
                        continue
                    bucket.append(
                        {
                            "text": (_c.get("text") or "")[:240],
                            "resolved": bool(_c.get("resolved", False)),
                            "owner_confidence": _c.get("owner_confidence", "low"),
                        }
                    )
                    if len(commitments_by_owner) >= MAX_OWNERSHIP_DISTRIBUTION_ENTRIES:
                        break
                if ownership_distribution_val:
                    top_owner_val = max(
                        ownership_distribution_val.items(), key=lambda kv: kv[1]
                    )[0]
                fu = detect_follow_up(live)
                if fu is not None:
                    follow_up_candidates.append(
                        {
                            "text": fu.get("commitment_text"),
                            "owner": fu.get("owner"),
                            "stale": fu.get("stale", False),
                            "message": fu.get("message", "")[:240],
                        }
                    )

        # Execution Linkage v1 — bounded projection of current live summary.
        if node_id and meeting_id:
            _live_for_linkage = store.get(node_id, meeting_id)
        else:
            _live_for_linkage = None
        linkage_block = execution_linkage_block(_live_for_linkage)

        memories = store.memories(node_id) if node_id else []
        memory_counts = _memory_counts_by_type(memories)

        recent = store.recent_interventions(limit=10)
        recent_reasons = [
            {"type": r.get("type"), "role": r.get("role")}
            for r in recent
            if isinstance(r, dict)
        ]

        return {
            "summary": summary_dict,
            "scoring": scoring,
            "high_priority_open_loops": high_priority_open_loops,
            "actionable_tasks": actionable_tasks,
            "recent_interventions": recent,
            "recent_intervention_reasons": recent_reasons,
            "memory_extracted_count": store.memory_count(node_id=node_id),
            "memory_counts_by_type": memory_counts,
            "commitments_count": commitments_count,
            "unresolved_commitments_count": unresolved_commitments_count,
            "resolved_commitments_count": resolved_commitments_count,
            "completion_rate": completion_rate,
            "follow_up_candidates": follow_up_candidates,
            "intervention_escalation_level": intervention_escalation_level,
            "escalation_trend": escalation_trend,
            "recent_commitments": recent_commitments,
            "recently_resolved_commitments": recently_resolved_commitments,
            # Temporal Intelligence v1 — bounded, additive temporal fields.
            "stale_commitments_count": stale_commitments_count_val,
            "oldest_unresolved_commitment_age_seconds": oldest_unresolved_age_val,
            "stale_open_loops_count": stale_open_loops_count_val,
            "next_followup_eligible_ts": next_followup_eligible_ts_val,
            "followup_cooldown_active": followup_cooldown_active,
            "temporal_health": temporal_health_val,
            # Coordination Intelligence v1 — ownership awareness (WHO).
            "ownership_distribution": ownership_distribution_val,
            "unassigned_commitments_count": unassigned_commitments_count_val,
            "commitments_by_owner": commitments_by_owner,
            "top_owner": top_owner_val,
            "ownership_pressure_hint": ownership_pressure_hint_val,
            # Execution Linkage v1 — additive, bounded, deterministic.
            **linkage_block,
        }
    except Exception as e:  # noqa: BLE001
        _log(f"intelligence_report_block failed: {e}")
        return {
            "summary": None,
            "scoring": {
                "decision_pressure_score": 0,
                "ambiguity_score": 0,
                "priority_level": "low",
            },
            "high_priority_open_loops": [],
            "actionable_tasks": [],
            "recent_interventions": [],
            "recent_intervention_reasons": [],
            "memory_extracted_count": 0,
            "memory_counts_by_type": {"decision": 0, "task": 0, "insight": 0},
            "commitments_count": 0,
            "unresolved_commitments_count": 0,
            "resolved_commitments_count": 0,
            "completion_rate": 0.0,
            "follow_up_candidates": [],
            "intervention_escalation_level": "low",
            "escalation_trend": "stable",
            "recent_commitments": [],
            "recently_resolved_commitments": [],
            "stale_commitments_count": 0,
            "oldest_unresolved_commitment_age_seconds": 0.0,
            "stale_open_loops_count": 0,
            "next_followup_eligible_ts": None,
            "followup_cooldown_active": False,
            "temporal_health": "fresh",
            "ownership_distribution": {},
            "unassigned_commitments_count": 0,
            "commitments_by_owner": {},
            "top_owner": None,
            "ownership_pressure_hint": "clear",
            "actionable_items_count": 0,
            "actionable_items_ready_count": 0,
            "actionable_items_blocked_count": 0,
            "actionable_items": [],
            "execution_readiness_summary": {
                "ready": 0,
                "blocked_missing_owner": 0,
                "blocked_ambiguous": 0,
                "blocked_low_context": 0,
            },
            "top_actionable_owner": None,
            "highest_priority_actionable": None,
        }


# ============================================================================
# Product Linkage Layer v1
# ----------------------------------------------------------------------------
# Stable, versioned, product-facing contract over the intelligence layers.
#
# Purpose:
#   Turn the existing intelligence/report output into a bounded, normalized
#   snapshot that future products (EntrepreneurOS, CreatorOS, ...) can consume
#   without coupling to internal meeting_intelligence field churn.
#
# Properties:
#   - Additive: reuses intelligence_report_block + execution_linkage_block
#   - Deterministic: pure transform over current summary state
#   - Bounded: inherits all existing caps; adds none of its own
#   - Report-only: zero side effects, zero new stores, zero background work
#   - Backward compatible: does not alter any existing report key
#   - Degrades safely: every failure path returns a well-formed empty snapshot
# ============================================================================

LINKAGE_SCHEMA_VERSION = "v1"
LINKAGE_CONTRACT_NAME = "product_linkage"
LINKAGE_SOURCE = "meeting_intelligence"


def _empty_linkage_snapshot(
    node_id: Optional[str],
    meeting_id: Optional[str],
) -> dict[str, Any]:
    """Well-formed empty snapshot used as a safe-degrade fallback."""
    return {
        "schema_version": LINKAGE_SCHEMA_VERSION,
        "contract": LINKAGE_CONTRACT_NAME,
        "source": LINKAGE_SOURCE,
        "node_id": node_id or "",
        "meeting_id": meeting_id,
        "generated_at": time.time(),
        "summary": {
            "priority_level": "low",
            "decision_pressure_score": 0,
            "ambiguity_score": 0,
            "escalation_level": "low",
            "escalation_trend": "stable",
            "participants_count": 0,
            "open_loops_count": 0,
            "decisions_count": 0,
        },
        "execution": {
            "commitments_count": 0,
            "unresolved_commitments_count": 0,
            "resolved_commitments_count": 0,
            "completion_rate": 0.0,
            "stale_commitments_count": 0,
        },
        "temporal": {
            "temporal_health": "fresh",
            "oldest_unresolved_commitment_age_seconds": 0.0,
            "stale_open_loops_count": 0,
            "followup_cooldown_active": False,
            "next_followup_eligible_ts": None,
        },
        "coordination": {
            "ownership_distribution": {},
            "unassigned_commitments_count": 0,
            "top_owner": None,
            "ownership_pressure_hint": "clear",
        },
        "actionable": {
            "items": [],
            "count": 0,
            "ready_count": 0,
            "blocked_count": 0,
            "readiness_summary": {
                "ready": 0,
                "blocked_missing_owner": 0,
                "blocked_ambiguous": 0,
                "blocked_low_context": 0,
            },
            "top_actionable_owner": None,
            "highest_priority_actionable": None,
        },
    }


def _normalize_actionable_item(raw: Any) -> Optional[dict[str, Any]]:
    """Project a raw ActionableItem dict into a stable, product-facing shape."""
    if not isinstance(raw, dict):
        return None
    text = str(raw.get("text") or "")[:240]
    if not text:
        return None
    return {
        "text": text,
        "kind": str(raw.get("kind") or "open_loop"),
        "owner": raw.get("owner"),
        "owner_confidence": str(raw.get("owner_confidence") or "low"),
        "priority": str(raw.get("priority") or "low"),
        "readiness_state": str(raw.get("readiness_state") or "blocked_low_context"),
        "readiness_reason": str(raw.get("readiness_reason") or "")[:240],
        "execution_ready": bool(raw.get("execution_ready", False)),
        "source": str(raw.get("source") or "meeting"),
    }


def build_linkage_snapshot(
    summary: Optional["MeetingSummary"],
    *,
    node_id: str,
    meeting_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build a stable, versioned Product Linkage snapshot for the given summary.

    Pure transform. Side-effect free. Always returns a fully-populated dict
    conforming to LINKAGE_SCHEMA_VERSION. Degrades safely on any failure.
    """
    try:
        snap = _empty_linkage_snapshot(node_id, meeting_id)
        if summary is None:
            return snap

        snap["generated_at"] = time.time()
        snap["node_id"] = getattr(summary, "node_id", node_id) or node_id or ""
        snap["meeting_id"] = getattr(summary, "meeting_id", meeting_id)

        # --- summary block --------------------------------------------------
        participants = getattr(summary, "participants", None) or set()
        open_loops = getattr(summary, "open_loops", None) or []
        decisions = getattr(summary, "decisions", None) or []
        snap["summary"] = {
            "priority_level": getattr(summary, "priority_level", "low") or "low",
            "decision_pressure_score": int(
                getattr(summary, "decision_pressure_score", 0) or 0
            ),
            "ambiguity_score": int(getattr(summary, "ambiguity_score", 0) or 0),
            "escalation_level": getattr(summary, "escalation_level", "low") or "low",
            "escalation_trend": getattr(summary, "escalation_trend", "stable")
            or "stable",
            "participants_count": len(participants),
            "open_loops_count": len(open_loops),
            "decisions_count": len(decisions),
        }

        # --- execution block ------------------------------------------------
        commitments = getattr(summary, "commitments", None) or []
        unresolved = unresolved_commitments(summary)
        commitments_count = len(commitments)
        unresolved_count = len(unresolved)
        resolved_count = max(0, commitments_count - unresolved_count)
        completion_rate = (
            round(resolved_count / commitments_count, 3)
            if commitments_count > 0
            else 0.0
        )
        now_ts = time.time()
        snap["execution"] = {
            "commitments_count": commitments_count,
            "unresolved_commitments_count": unresolved_count,
            "resolved_commitments_count": resolved_count,
            "completion_rate": completion_rate,
            "stale_commitments_count": stale_commitments_count(summary, now_ts),
        }

        # --- temporal block -------------------------------------------------
        snap["temporal"] = {
            "temporal_health": temporal_health(summary, now_ts),
            "oldest_unresolved_commitment_age_seconds": round(
                oldest_unresolved_commitment_age_seconds(summary, now_ts), 3
            ),
            "stale_open_loops_count": stale_open_loops_count(summary, now_ts),
            "followup_cooldown_active": is_followup_in_cooldown(summary, now_ts),
            "next_followup_eligible_ts": next_followup_eligible_ts(summary),
        }

        # --- coordination block ---------------------------------------------
        own_dist = ownership_distribution(summary)
        top_owner = (
            max(own_dist.items(), key=lambda kv: kv[1])[0] if own_dist else None
        )
        snap["coordination"] = {
            "ownership_distribution": own_dist,
            "unassigned_commitments_count": unassigned_commitments_count(summary),
            "top_owner": top_owner,
            "ownership_pressure_hint": ownership_pressure_hint(summary),
        }

        # --- actionable block ----------------------------------------------
        linkage = execution_linkage_block(summary)
        raw_items = linkage.get("actionable_items") or []
        normalized_items: list[dict[str, Any]] = []
        for raw in raw_items[:MAX_ACTIONABLE_ITEMS]:
            norm = _normalize_actionable_item(raw)
            if norm is not None:
                normalized_items.append(norm)

        highest = linkage.get("highest_priority_actionable")
        highest_norm = _normalize_actionable_item(highest) if highest else None

        snap["actionable"] = {
            "items": normalized_items,
            "count": len(normalized_items),
            "ready_count": int(linkage.get("actionable_items_ready_count", 0) or 0),
            "blocked_count": int(
                linkage.get("actionable_items_blocked_count", 0) or 0
            ),
            "readiness_summary": dict(
                linkage.get("execution_readiness_summary")
                or {
                    "ready": 0,
                    "blocked_missing_owner": 0,
                    "blocked_ambiguous": 0,
                    "blocked_low_context": 0,
                }
            ),
            "top_actionable_owner": linkage.get("top_actionable_owner"),
            "highest_priority_actionable": highest_norm,
        }

        return snap
    except Exception as e:  # noqa: BLE001
        _log(f"build_linkage_snapshot failed: {e}")
        return _empty_linkage_snapshot(node_id, meeting_id)


def linkage_snapshot(
    node_id: str,
    meeting_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Product-facing entry point: fetch the live summary and return a stable,
    versioned Product Linkage snapshot. Never raises; degrades safely.
    """
    try:
        if not node_id:
            return _empty_linkage_snapshot(node_id, meeting_id)
        store = get_meeting_summary_store()
        live = store.get(node_id, meeting_id) if meeting_id else None
        return build_linkage_snapshot(
            live, node_id=node_id, meeting_id=meeting_id
        )
    except Exception as e:  # noqa: BLE001
        _log(f"linkage_snapshot failed: {e}")
        return _empty_linkage_snapshot(node_id, meeting_id)


def product_linkage_block(
    node_id: Optional[str] = None,
    meeting_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Report-shaped wrapper over linkage_snapshot, suitable for merging into
    transport_report or any other report surface.
    """
    return linkage_snapshot(node_id or "", meeting_id)


__all__ = [
    "MeetingSummary",
    "ExtractedMemory",
    "Commitment",
    "get_meeting_summary_store",
    "reset_meeting_summary_store_for_tests",
    "update_meeting_summary",
    "compute_scores",
    "compute_escalation_level",
    "extract_commitments",
    "resolve_commitments",
    "unresolved_commitments",
    "detect_follow_up",
    "detect_intervention",
    "derive_active_role",
    "refine_intervention_message",
    "maybe_emit_intervention",
    "extract_memory",
    "on_utterance_injected",
    "intelligence_report_block",
    # Temporal Intelligence v1
    "commitment_age_seconds",
    "oldest_unresolved_commitment_age_seconds",
    "stale_commitments_count",
    "stale_open_loops_count",
    "next_followup_eligible_ts",
    "is_followup_in_cooldown",
    "temporal_health",
    "FOLLOW_UP_COOLDOWN_SECONDS",
    "STALE_OPEN_LOOP_SECONDS",
    "COMMITMENT_STALE_SECONDS",
    # Coordination Intelligence v1
    "ownership_distribution",
    "unassigned_commitments_count",
    "ownership_pressure_hint",
    "GROUP_OWNER_LABEL",
    "MAX_OWNERSHIP_DISTRIBUTION_ENTRIES",
    # Execution Linkage v1
    "ActionableItem",
    "project_actionable_items",
    "classify_execution_readiness",
    "execution_linkage_block",
    "MAX_ACTIONABLE_ITEMS",
    # Product Linkage v1
    "LINKAGE_SCHEMA_VERSION",
    "LINKAGE_CONTRACT_NAME",
    "LINKAGE_SOURCE",
    "build_linkage_snapshot",
    "linkage_snapshot",
    "product_linkage_block",
]
