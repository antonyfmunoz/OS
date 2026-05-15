"""
Workflow Delegation Layer v1 — deterministic intent classification + policy.

Purpose
-------
Classifies incoming requests into bounded intent classes (conversation,
skill_tool, workflow) and resolves mode-safe workflow policy.  Pure,
bounded, deterministic — no LLM classification, no hot-path imports.

Architecture
------------
This module sits BETWEEN mode/target resolution and the responder call.
It enriches request metadata with workflow intent without altering the
request flow.  V1 is metadata/policy only — no autonomous execution.

  Discord message
    → mode resolved  (discord_mode_routing)
    → target resolved (target_policy)
    → **workflow classified** (this module)   ← NEW
    → inject_transcript / responder
    → reply

Design rules
------------
- Rule-based keyword matching only (no LLM, no fuzzy).
- Bounded intent classes: conversation | skill_tool | workflow.
- Bounded workflow kinds per mode.
- Mode boundary preserved: product never becomes builder.
- Additive metadata only — no side-effect execution.
- Imports NOTHING from the hot path (gateway, cognitive_loop,
  model_router, agent_runtime, primitives).

This module imports NOTHING from the hot path (gateway, cognitive_loop,
model_router, agent_runtime, primitives).
"""

from __future__ import annotations

import os
import re
from typing import Any, Optional

__all__ = [
    "DELEGATION_VERSION",
    "classify_workflow_intent",
    "resolve_workflow_policy",
    "enrich_metadata",
]

DELEGATION_VERSION = "v1"

# ── intent classes ──────────────────────────────────────────────────────────

INTENT_CONVERSATION = "conversation"
INTENT_SKILL_TOOL = "skill_tool"
INTENT_WORKFLOW = "workflow"

_VALID_INTENTS = frozenset({INTENT_CONVERSATION, INTENT_SKILL_TOOL, INTENT_WORKFLOW})

# ── workflow kinds ──────────────────────────────────────────────────────────

KIND_NONE = "none"
KIND_BUILDER_DEV = "builder_dev"
KIND_PRODUCT_RUNTIME = "product_runtime"
KIND_CONTENT_OPS = "content_ops"
KIND_ANALYSIS = "analysis"
KIND_SYSTEM_OPS = "system_ops"

_VALID_KINDS = frozenset(
    {
        KIND_NONE,
        KIND_BUILDER_DEV,
        KIND_PRODUCT_RUNTIME,
        KIND_CONTENT_OPS,
        KIND_ANALYSIS,
        KIND_SYSTEM_OPS,
    }
)

# ── keyword rules ───────────────────────────────────────────────────────────
# Each rule: (compiled_regex, intent, workflow_kind)
# Order matters: first match wins.  More specific patterns first.

_WORKFLOW_BUILDER_DEV_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:fix|patch|debug|hotfix)\b.*\b(?:bug|error|crash|issue|exception)\b",
        r"\b(?:update|change|modify|edit|refactor)\b.*\b(?:code|file|module|function|class|method|router|gateway|transport)\b",
        r"\b(?:add|create|build|implement|write)\b.*\b(?:feature|endpoint|route|handler|test|skill|agent|module)\b",
        r"\b(?:deploy|redeploy|restart|rebuild)\b",
        r"\b(?:run|execute)\b.*\b(?:tests?|smoke\s*tests?|migration|script)\b",
        r"\b(?:check|inspect|review)\b.*\b(?:logs?|errors?|imports?|deps?|dependencies)\b",
        r"\b(?:install|uninstall|upgrade|downgrade)\b.*\b(?:package|dependency|library|module)\b",
        r"\b(?:docker|container|compose|git|pip|npm)\b",
        r"\b(?:merge|rebase|branch|commit|push|pull)\b",
    )
]

_WORKFLOW_PRODUCT_RUNTIME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:run|execute|trigger|start|launch)\b.*\b(?:workflow|onboarding|pipeline|sequence|playbook)\b",
        r"\b(?:send|deliver|dispatch)\b.*\b(?:email|message|notification|alert|report|brief)\b",
        r"\b(?:schedule|automate|cron)\b.*\b(?:task|job|run|check)\b",
        r"\b(?:process|handle|route)\b.*\b(?:lead|prospect|customer|ticket|request)\b",
    )
]

_WORKFLOW_CONTENT_OPS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:create|write|draft|generate)\b.*\b(?:post|content|article|script|copy|caption|thread)\b",
        r"\b(?:publish|schedule|queue)\b.*\b(?:post|content|video|reel|story|draft)\b",
        r"\b(?:edit|revise|rewrite)\b.*\b(?:draft|copy|script|content)\b",
    )
]

_WORKFLOW_SYSTEM_OPS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:check|show|display)\b.*\b(?:status|health|uptime|metrics)\b",
        r"\b(?:clear|reset|flush)\b.*\b(?:cache|state|queue)\b",
        r"\bsystem\s+(?:status|health|check)\b",
    )
]

# ── planning-only exclusions ───────────────────────────────────────────────
# Messages that ASK for a plan/analysis without requesting execution should
# pass through to the CC session (conversation intent) rather than being
# intercepted as builder_dev workflows.  Checked BEFORE builder_dev patterns.

_PLANNING_ONLY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bplan\s+out\b",
        r"\boutline\s+(?:how|a\s+plan|the\s+plan|steps)\b",
        r"\bsketch\s+out\b",
        r"\bdraft\s+(?:a\s+)?plan\b",
        r"\bplan\s+(?:how|for)\b",
        r"\bdon'?t\s+execute\b",
        r"\bbut\s+don'?t\s+(?:do|execute|implement|build|run)\b",
        r"\bwithout\s+execut(?:ing|e)\b",
        r"\bjust\s+plan\b",
        r"\bplan\s+only\b",
        r"\bthink\s+through\b",
        r"\bhow\s+would\s+you\b",
        r"\bwhat\s+would\s+(?:it|the)\b.*\blook\s+like\b",
        r"\bwalk\s+me\s+through\b",
    )
]

_SKILL_TOOL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:use|load|run|apply)\b.*\b(?:skill|tool|plugin)\b",
        r"\b(?:search|look\s*up|find|query)\b.*\b(?:web|google|brave|perplexity)\b",
        r"\b(?:transcribe|translate|convert|render)\b",
        r"\b(?:scrape|crawl|fetch)\b.*\b(?:url|page|site|website)\b",
    )
]

_ANALYSIS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:analyze|analyse|audit|evaluate|assess)\b.*\b(?:data|performance|metrics|results|funnel|pipeline)\b",
        r"\b(?:compare|benchmark|contrast)\b",
        r"\b(?:break\s*down|deep\s*dive|investigate)\b",
    )
]


# ── env var for extra keywords ──────────────────────────────────────────────

_ENV_WORKFLOW_EXTRA_BUILDER_KEYWORDS = "EOS_WORKFLOW_EXTRA_BUILDER_KEYWORDS"
_ENV_WORKFLOW_EXTRA_PRODUCT_KEYWORDS = "EOS_WORKFLOW_EXTRA_PRODUCT_KEYWORDS"


# ── classifier ──────────────────────────────────────────────────────────────


def classify_workflow_intent(
    text: str,
    mode: str,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Classify a request into intent + workflow kind.

    Returns::

        {
          "intent": "conversation" | "skill_tool" | "workflow",
          "workflow_kind": "none" | "builder_dev" | "product_runtime"
                          | "content_ops" | "analysis" | "system_ops",
          "reason": str,
          "confidence": "high" | "low",
          "delegation_version": "v1",
        }

    Classification is rule-based only. First matching pattern wins.
    No LLM. No fuzzy matching. Deterministic.
    """
    if not text or not text.strip():
        return _result(INTENT_CONVERSATION, KIND_NONE, "empty_input", "high")

    clean = text.strip()

    # ── DEBUG: trace classification (remove after fix confirmed) ──────
    import sys as _sys

    _dbg = f"[workflow_delegation] classifying: {clean[:120]!r} | mode={mode}"
    print(_dbg, file=_sys.stderr)

    # 0. Planning-only exclusion — pass through to CC session
    for pat in _PLANNING_ONLY_PATTERNS:
        if pat.search(clean):
            _reason = f"planning_only_exclusion:{pat.pattern[:40]}"
            print(
                f"[workflow_delegation] → STEP 0 matched: {_reason}",
                file=_sys.stderr,
            )
            return _result(INTENT_CONVERSATION, KIND_NONE, _reason, "high")

    # 1. Check builder_dev workflow patterns
    for pat in _WORKFLOW_BUILDER_DEV_PATTERNS:
        if pat.search(clean):
            _reason = f"pattern:{pat.pattern[:40]}"
            print(
                f"[workflow_delegation] → STEP 1 matched (builder_dev): {_reason}",
                file=_sys.stderr,
            )
            return _result(INTENT_WORKFLOW, KIND_BUILDER_DEV, _reason, "high")

    # 2. Check product_runtime workflow patterns
    for pat in _WORKFLOW_PRODUCT_RUNTIME_PATTERNS:
        if pat.search(clean):
            return _result(
                INTENT_WORKFLOW,
                KIND_PRODUCT_RUNTIME,
                f"pattern:{pat.pattern[:40]}",
                "high",
            )

    # 3. Check content_ops workflow patterns
    for pat in _WORKFLOW_CONTENT_OPS_PATTERNS:
        if pat.search(clean):
            return _result(
                INTENT_WORKFLOW, KIND_CONTENT_OPS, f"pattern:{pat.pattern[:40]}", "high"
            )

    # 4. Check system_ops workflow patterns
    for pat in _WORKFLOW_SYSTEM_OPS_PATTERNS:
        if pat.search(clean):
            return _result(
                INTENT_WORKFLOW, KIND_SYSTEM_OPS, f"pattern:{pat.pattern[:40]}", "high"
            )

    # 5. Check analysis patterns
    for pat in _ANALYSIS_PATTERNS:
        if pat.search(clean):
            return _result(
                INTENT_WORKFLOW, KIND_ANALYSIS, f"pattern:{pat.pattern[:40]}", "high"
            )

    # 6. Check skill/tool patterns
    for pat in _SKILL_TOOL_PATTERNS:
        if pat.search(clean):
            return _result(
                INTENT_SKILL_TOOL, KIND_NONE, f"pattern:{pat.pattern[:40]}", "high"
            )

    # 7. Check env-var extra keywords (mode-specific)
    extra_result = _check_extra_keywords(clean, mode)
    if extra_result:
        return extra_result

    # 8. Default: conversation
    return _result(INTENT_CONVERSATION, KIND_NONE, "no_pattern_matched", "high")


def _result(
    intent: str,
    workflow_kind: str,
    reason: str,
    confidence: str,
) -> dict[str, Any]:
    return {
        "intent": intent,
        "workflow_kind": workflow_kind,
        "reason": reason,
        "confidence": confidence,
        "delegation_version": DELEGATION_VERSION,
    }


def _check_extra_keywords(
    text: str,
    mode: str,
) -> Optional[dict[str, Any]]:
    """Check env-var supplied extra keywords for the current mode."""
    if mode == "builder":
        raw = os.getenv(_ENV_WORKFLOW_EXTRA_BUILDER_KEYWORDS, "")
        kind = KIND_BUILDER_DEV
    elif mode == "product":
        raw = os.getenv(_ENV_WORKFLOW_EXTRA_PRODUCT_KEYWORDS, "")
        kind = KIND_PRODUCT_RUNTIME
    else:
        return None

    if not raw.strip():
        return None

    lower = text.lower()
    for kw in raw.split(","):
        kw = kw.strip().lower()
        if kw and kw in lower:
            return _result(INTENT_WORKFLOW, kind, f"extra_keyword:{kw}", "low")

    return None


# ── mode-safe workflow policy ───────────────────────────────────────────────

# Which workflow kinds are allowed per mode
_BUILDER_ALLOWED_KINDS = frozenset(
    {
        KIND_NONE,
        KIND_BUILDER_DEV,
        KIND_CONTENT_OPS,
        KIND_ANALYSIS,
        KIND_SYSTEM_OPS,
    }
)

_PRODUCT_ALLOWED_KINDS = frozenset(
    {
        KIND_NONE,
        KIND_PRODUCT_RUNTIME,
        KIND_CONTENT_OPS,
        KIND_ANALYSIS,
        KIND_SYSTEM_OPS,
    }
)

_UNKNOWN_ALLOWED_KINDS = frozenset(
    {
        KIND_NONE,
        KIND_ANALYSIS,
        KIND_SYSTEM_OPS,
    }
)


def resolve_workflow_policy(
    mode: str,
    intent_result: dict[str, Any],
) -> dict[str, Any]:
    """Decide whether a classified workflow intent is allowed in the current mode.

    Returns::

        {
          "allowed": bool,
          "mode": str,
          "intent": str,
          "workflow_kind": str,
          "execution_class": "conversation" | "skill_tool" | "workflow",
          "policy_reason": str,
          "delegation_version": "v1",
        }

    Policy rules:
    - Builder mode allows builder_dev and broad system ops.
    - Product mode allows product_runtime and safe ops.
    - Product mode NEVER silently becomes builder mode.
    - Unknown mode allows only conversation and safe ops.
    - Conversation and skill_tool intents are always allowed.
    """
    intent = intent_result.get("intent", INTENT_CONVERSATION)
    kind = intent_result.get("workflow_kind", KIND_NONE)

    # Conversation and skill_tool are always allowed
    if intent in (INTENT_CONVERSATION, INTENT_SKILL_TOOL):
        return _policy_result(
            allowed=True,
            mode=mode,
            intent=intent,
            workflow_kind=kind,
            execution_class=intent,
            policy_reason="non_workflow_always_allowed",
        )

    # Workflow: check mode allowlist
    if mode == "builder":
        allowed_kinds = _BUILDER_ALLOWED_KINDS
    elif mode == "product":
        allowed_kinds = _PRODUCT_ALLOWED_KINDS
    else:
        allowed_kinds = _UNKNOWN_ALLOWED_KINDS

    allowed = kind in allowed_kinds

    if allowed:
        reason = f"{kind}_allowed_in_{mode}_mode"
    elif mode == "product" and kind == KIND_BUILDER_DEV:
        reason = "builder_dev_blocked_in_product_mode"
    else:
        reason = f"{kind}_not_allowed_in_{mode}_mode"

    return _policy_result(
        allowed=allowed,
        mode=mode,
        intent=intent,
        workflow_kind=kind,
        execution_class="workflow" if allowed else "conversation",
        policy_reason=reason,
    )


def _policy_result(
    *,
    allowed: bool,
    mode: str,
    intent: str,
    workflow_kind: str,
    execution_class: str,
    policy_reason: str,
) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "mode": mode,
        "intent": intent,
        "workflow_kind": workflow_kind,
        "execution_class": execution_class,
        "policy_reason": policy_reason,
        "delegation_version": DELEGATION_VERSION,
    }


# ── metadata enrichment ────────────────────────────────────────────────────


def enrich_metadata(
    meta: dict[str, Any],
    text: str,
    mode: str,
) -> dict[str, Any]:
    """Classify intent, resolve policy, and attach workflow metadata to *meta*.

    Returns the same dict with workflow fields added (mutation + return).
    This is the single call-site for the transport layer.

    Added keys::

        workflow_intent       — "conversation" | "skill_tool" | "workflow"
        workflow_kind         — "none" | "builder_dev" | etc.
        workflow_allowed      — bool
        workflow_policy_reason — str
        workflow_confidence   — "high" | "low"
        workflow_execution_class — "conversation" | "skill_tool" | "workflow"
        workflow_delegation_version — "v1"
    """
    intent_result = classify_workflow_intent(text, mode, metadata=meta)
    policy_result = resolve_workflow_policy(mode, intent_result)

    meta["workflow_intent"] = intent_result["intent"]
    meta["workflow_kind"] = intent_result["workflow_kind"]
    meta["workflow_allowed"] = policy_result["allowed"]
    meta["workflow_policy_reason"] = policy_result["policy_reason"]
    meta["workflow_confidence"] = intent_result["confidence"]
    meta["workflow_execution_class"] = policy_result["execution_class"]
    meta["workflow_delegation_version"] = DELEGATION_VERSION

    return meta
