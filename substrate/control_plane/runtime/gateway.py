"""
EntrepreneurOSGateway — single control plane for all AI operations.

Every AI request enters here. Nothing calls agent_runtime, event_bus,
orchestrator, or agent_teams directly from outside runtime.

Request schema:
    {
        "type":       "agent_task" | "event" | "status" | "brief",
        "team":       "sales" | "research" | "content" | None,
        "sub_agent":  str | None,
        "prompt":     str,
        "venture_id": str | None,
        "username":   str | None,
        "task_type":  str | None,
        # for type=event
        "event_type": str | None,
        "payload":    dict | None,
        # optional override — force approval gate
        "action":     "send" | "delete" | "payment" | None,
    }

Usage:
    from substrate.control_plane.runtime.gateway import EntrepreneurOSGateway
    gw = EntrepreneurOSGateway()
    result = gw.handle({"type": "brief", "prompt": "", "venture_id": "lyfe_institute"})
"""

import json
import logging
import os
import re as _re
import sys
import threading
import uuid as _uuid_mod
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from substrate.state.storage.db import get_conn, ORG_ID

# ─── Constants ────────────────────────────────────────────────────────────────

APPROVALS_DIR = Path(_REPO_ROOT) / "orchestrator" / "approvals"
PENDING_DIR = APPROVALS_DIR / "pending"
APPROVED_DIR = APPROVALS_DIR / "approved"

# Sub-agents that require approval regardless of prompt — only agents that
# exclusively execute external sends with zero internal-only use cases.
# Intentionally empty: action flags and prompt patterns handle this more
# precisely. Listing a sub-agent here blocks ALL requests to that agent,
# including analysis, logging, and status checks — which is too broad.
_APPROVAL_REQUIRED_AGENTS: frozenset[str] = frozenset()

# Explicit action flags that always require approval
# "publish" removed — Discord and Notion are internal systems
_APPROVAL_REQUIRED_ACTIONS = frozenset({"send", "delete", "payment"})

# Prompt patterns that signal external sends on behalf of the founder
_EXTERNAL_SEND_PATTERNS = (
    "send dm",
    "send message",
    "send outreach",
    "send email",
    "message them",
    "reply to them",
    "dm them",
    "dm him",
    "dm her",
    "send it to",
    "send this to",
    "send this message",
    "post on instagram",
    "post on tiktok",
    "send to prospect",
    "outreach to",
)

# Prompt patterns for clearly internal operations — short-circuit to auto-execute
_AUTO_EXECUTE_PATTERNS = (
    # Lead / pipeline writes
    "log lead",
    "log this lead",
    "add this lead",
    "save this lead",
    "log to pipeline",
    "update pipeline",
    "add to pipeline",
    "add to crm",
    # Notion writes
    "log to notion",
    "update notion",
    "add to notion",
    "save to notion",
    "write to notion",
    "create notion",
    # Task operations (internal)
    "create task",
    "add task",
    "new task",
    # Activity / memory writes
    "log activity",
    "log this",
    "save this",
    "store this",
    "note this",
    "remember this",
    "record this",
    # BIS / system updates
    "update bis",
    "update my bis",
    # Briefs (system-generated, not founder sends)
    "morning brief",
    # Internal Discord / Telegram posts
    "post to discord",
    "post in discord",
    # General read/query patterns — reads never need approval
    "what is",
    "what are",
    "show me",
    "tell me",
    "give me",
    "how is",
    "status of",
    "check ",
    "list ",
    "get ",
    "fetch ",
    "summarize ",
    "how many",
    "how much",
)

# Signals that indicate a purely informational message (no action requested)
_INFORMATIONAL_SIGNALS: tuple[str, ...] = (
    "here is",
    "here's",
    "fyi",
    "context:",
    "note:",
    "for context",
    "just so you know",
    "updating you",
    "for your reference",
    "heads up",
    "background:",
    "to update you",
    "letting you know",
    "i wanted to let you know",
    "adding context",
    "some context",
    "log this",
    "logging",
    "recording",
)

# Signals that indicate an external action is being requested
_ACTION_SIGNALS: tuple[str, ...] = (
    "send dm",
    "send message",
    "send email",
    "send outreach",
    "message him",
    "message her",
    "message them",
    "dm him",
    "dm her",
    "dm them",
    "reach out",
    "post on instagram",
    "post on tiktok",
    "outreach to",
    "publish to",
    "email him",
    "email her",
    "buy ",
    "pay ",
    "delete ",
    "remove all",
)

# Required fields in every request
_REQUIRED_FIELDS = {"type"}

# Valid request types
_VALID_TYPES = {"agent_task", "event", "status", "brief"}

# Email instruction signals — founder correcting GPS folder classification
EMAIL_INSTRUCTION_SIGNALS: tuple[str, ...] = (
    "move this email",
    "that email should",
    "put emails from",
    "emails like this",
    "this label should",
    "never put",
    "always put",
    "delete this label",
    "should go to",
    "belongs in",
    "wrong folder",
    "misclassified",
)

# Automation triggers — handled before the AI routing layer
AUTOMATION_TRIGGERS: dict[str, list[str]] = {
    "rename_ai": [
        "call you",
        "name you",
        "rename you",
        "your name is",
        "call my ai",
        "name my ai",
        "rename to",
        "i want to call you",
    ],
}


from substrate.observability.error_recorder import record_error as _record_error


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")


# ─── EntrepreneurOSGateway (singleton) ───────────────────────────────────────────────────


class EntrepreneurOSGateway:
    """
    Singleton gateway. EntrepreneurOSGateway() always returns the same instance.
    Thread-safe.
    """

    _instance: "EntrepreneurOSGateway | None" = None
    _class_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "EntrepreneurOSGateway":
        with cls._class_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._init_dirs()
                cls._instance = instance
        return cls._instance

    def _init_dirs(self) -> None:
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        APPROVED_DIR.mkdir(parents=True, exist_ok=True)

    # ─── Conversation memory helpers ─────────────────────────────────────────

    _MEMORY_SIGNALS = (
        "what did i say",
        "what did we discuss",
        "what was i saying",
        "messages ago",
        "last message",
        "earlier i said",
        "find everything",
        "search for",
        "pull everything",
        "word for word",
        "what have we talked about",
        "give me everything",
        "list everything",
    )

    def _is_memory_query(self, text: str) -> bool:
        t = text.lower()
        return any(s in t for s in self._MEMORY_SIGNALS)

    def _handle_memory_query(self, text: str, session_id: str, cm: object) -> str:
        """Return memory response string, or '' if query not matched."""
        t = text.lower()

        # "X messages ago"
        ago = _re.search(r"(\d+)\s*messages?\s*ago", t)
        if ago:
            n = int(ago.group(1))
            msgs = cm.get_session(session_id)
            user_msgs = [m for m in msgs if m.role == "user"]
            if len(user_msgs) >= n:
                target = user_msgs[-n]
                ts = target.created_at.strftime("%H:%M") if target.created_at else ""
                return f'You said:\n\n"{target.content}"\n\n({ts})'
            return "Could not find that message in this session."

        # session dump — "today" / "this session" / "give me everything"
        if any(
            s in t
            for s in [
                "today",
                "this session",
                "give me everything",
                "list everything",
                "what have we talked about",
            ]
        ):
            msgs = cm.get_session(session_id)
            if not msgs:
                return "No messages recorded in this session yet."
            lines = ["Here is everything from this session:\n"]
            for msg in msgs:
                prefix = "You" if msg.role == "user" else "AI"
                ts = msg.created_at.strftime("%H:%M") if msg.created_at else ""
                lines.append(f"[{ts}] {prefix}: {msg.content}")
            return "\n".join(lines)

        # full-text search — "find X" / "search for X"
        srch = _re.search(r"(?:find|search for|pull)\s+(.+)", t)
        if srch:
            query = srch.group(1).strip()
            results = cm.search(query, limit=5)
            if not results:
                return f'Nothing found for "{query}".'
            lines = [f'Found {len(results)} messages matching "{query}":\n']
            for msg in results:
                prefix = "You" if msg.role == "user" else "AI"
                ts = msg.created_at.strftime("%Y-%m-%d %H:%M") if msg.created_at else ""
                lines.append(f"[{ts}] {prefix}: {msg.content}")
            return "\n".join(lines)

        return ""

    def _init_conversation_memory(
        self, request: dict
    ) -> tuple[object | None, str, str]:
        """
        Set up ConversationMemory for this request.
        Returns (cm, session_id, channel). cm is None on failure.
        """
        session_id = request.get("session_id") or str(_uuid_mod.uuid4())
        channel = request.get("channel", "unknown")
        prompt = request.get("prompt", "")
        rtype = request.get("type", "")
        if not prompt or rtype not in ("agent_task", "brief"):
            return None, session_id, channel
        try:
            from substrate.state.memory.memory import ConversationMemory
            from substrate.state.context.context import load_context_from_env

            ctx = load_context_from_env()
            cm = ConversationMemory(ctx)
            return cm, session_id, channel
        except Exception as e:
            print(f"[Gateway] ConversationMemory init failed (non-blocking): {e}")
            return None, session_id, channel

    # ─── Automation handler ───────────────────────────────────────────────────

    def _handle_automation(self, request: dict) -> dict | None:
        """
        Check request prompt against AUTOMATION_TRIGGERS.
        Returns a result dict if an automation fired, else None.
        Automations bypass the AI routing layer — handled directly.
        """
        import re

        text = request.get("prompt", "")
        if not text:
            return None

        # rename_ai — user wants to rename their AI instance
        rename_keywords = AUTOMATION_TRIGGERS.get("rename_ai", [])
        if any(kw in text.lower() for kw in rename_keywords):
            match = re.search(
                r"(?:call you|name you|rename to|"
                r"your name is|call my ai|"
                r"name my ai|i want to call you)\s+"
                r"([A-Za-z][a-zA-Z0-9]{1,20})",
                text,
                re.IGNORECASE,
            )
            if match:
                new_name = match.group(1).upper()
                try:
                    from substrate.state.context.context import load_context_from_env
                    from substrate.state.business.business_instance import BusinessInstanceManager

                    ctx = load_context_from_env()
                    bim = BusinessInstanceManager(ctx)
                    venture_id = (
                        request.get("venture_id") or bim.get_default_venture_id()
                    )
                    bis = bim.get_bis(venture_id) if venture_id else None
                    if bis:
                        old_name = bis.ai_name
                        bis.ai_name = new_name
                        bim.save_bis(bis)
                        return {
                            "status": "ok",
                            "output": (f"Done. I'm {new_name} now. Was {old_name}."),
                            "action": "rename_ai",
                            "new_name": new_name,
                        }
                except Exception as e:
                    _record_error("rename_ai", e, {"new_name": new_name})
                    print(f"[Gateway] rename_ai failed: {e}")

        return None

    # ─── Email instruction handler ────────────────────────────────────────────

    def _detect_email_instruction(self, text: str) -> bool:
        t = text.lower()
        return any(s in t for s in EMAIL_INSTRUCTION_SIGNALS)

    _EMAIL_FOLDERS = (
        "antony", "to respond", "review", "responded",
        "waiting on", "receipts-financials", "newsletters",
    )

    @staticmethod
    def _deterministic_extract_email_instruction(text: str) -> dict | None:
        """Regex-based folder instruction extraction — deterministic fallback."""
        t = text.lower()
        folder = None
        for f in EntrepreneurOSGateway._EMAIL_FOLDERS:
            if f in t:
                folder = f.title()
                break
        if not folder:
            return None
        return {"folder_name": folder, "instruction": text}

    def _handle_email_instruction(self, request: dict) -> dict | None:
        """
        Detect and process founder email folder correction instructions.
        Updates the folder definition in Neon so all future classifications
        use the new rule. Deterministic extraction first, AI refines.
        """
        text = request.get("prompt", "")
        if not text or not self._detect_email_instruction(text):
            return None

        # Deterministic extraction first
        data = self._deterministic_extract_email_instruction(text)

        # Try AI for richer extraction
        try:
            from substrate.state.context.context import load_context_from_env
            from adapters.google_workspace.email_gps import EmailGPS
            from substrate.execution.runtime.model_router import get_router, TaskType

            ctx_eos = load_context_from_env()
            gps = EmailGPS(ctx_eos)
            router = get_router(ctx_eos)

            extraction = router.call_with_fallback(
                TaskType.ANALYSIS,
                prompt=(
                    f"Extract the email folder instruction "
                    f"from this message.\n\n"
                    f"Message: {text}\n\n"
                    f"Available folders: Antony, To Respond, Review, "
                    f"Responded, Waiting On, Receipts-Financials, Newsletters\n\n"
                    f"Return JSON only:\n"
                    f'{{"folder_name": "exact folder name", '
                    f'"instruction": "what should change"}}'
                ),
                max_tokens=120,
            )

            import re as _json_re

            match = _json_re.search(r"\{.*\}", extraction, _json_re.DOTALL)
            if match:
                ai_data = json.loads(match.group())
                if ai_data.get("folder_name"):
                    data = ai_data
        except Exception as e:
            _record_error("email_instruction_ai", e, {"text": text[:200]})
            print(f"[Gateway] Email instruction AI failed (using deterministic): {e}")

        if not data or not data.get("folder_name"):
            return None

        folder = data["folder_name"]
        instruction = data.get("instruction", text)

        try:
            from substrate.state.context.context import load_context_from_env
            from adapters.google_workspace.email_gps import EmailGPS

            ctx_eos = load_context_from_env()
            gps = EmailGPS(ctx_eos)
            new_purpose = gps.update_folder_purpose(folder, instruction)
            if new_purpose:
                return {
                    "status": "ok",
                    "output": (
                        f'Updated "{folder}" definition.\n\n'
                        f"New rule: {new_purpose}\n\n"
                        f"All future emails will use this definition. "
                        f"Run `!inbox` to apply to new emails."
                    ),
                    "action": "email_folder_update",
                }
        except Exception as e:
            _record_error("email_instruction_update", e, {"folder": folder})
            print(f"[Gateway] Email folder update failed: {e}")

        return None

    # ─── Schema validation ────────────────────────────────────────────────────

    def _validate(self, request: dict) -> str | None:
        """Return an error string if the request is invalid, else None."""
        missing = _REQUIRED_FIELDS - request.keys()
        if missing:
            return f"Missing required field(s): {missing}"
        rtype = request.get("type")
        if rtype not in _VALID_TYPES:
            return f"Invalid type '{rtype}'. Must be one of: {_VALID_TYPES}"
        if rtype == "agent_task" and not request.get("prompt"):
            return "agent_task requires a non-empty 'prompt' field"
        if rtype == "event" and not request.get("event_type"):
            return "event requires a non-empty 'event_type' field"
        return None

    # ─── Approval detection ───────────────────────────────────────────────────

    def _is_informational(self, prompt: str) -> bool:
        """
        True if the message is purely informational — context, FYI, logging,
        or a multi-part continuation. These NEVER need approval.

        Checks:
          1. Part X/Y or continuation marker → always informational
          2. Has an informational signal AND no external action signal
        """
        # Part indicators — always a context accumulation, never an action
        if _re.search(r"(?i)\bpart\s+\d+/\d+\b|\b\d+\s*/\s*\d+\b", prompt):
            return True
        if any(s in prompt for s in ("continued", "cont'd", "cont.")):
            return True

        # Has informational signal AND no external action signal
        has_info = any(s in prompt for s in _INFORMATIONAL_SIGNALS)
        has_action = any(s in prompt for s in _ACTION_SIGNALS)
        return has_info and not has_action

    def _requires_approval(self, request: dict) -> bool:
        """
        Tiered approval gate.

        NEVER approve:
          - Purely informational messages (FYI, context, logging, Part X/Y)
          - Reading any data
          - Writing to Notion / pipeline DB / activity log / BIS
          - Storing context or memory
          - Morning brief

        ALWAYS approve:
          - Sending DM as founder (Instagram, email, any external channel)
          - Making any payment
          - Deleting any data
          - Any irreversible external action on founder's behalf

        Rule: internal reads/writes = auto
              external actions in the world as the founder = approve
        """
        action = request.get("action", "")
        prompt = request.get("prompt", "").lower()

        # 0. Purely informational — never queue for approval
        if self._is_informational(prompt):
            return False

        # 1. Internal operations short-circuit — never need approval
        if any(pat in prompt for pat in _AUTO_EXECUTE_PATTERNS):
            return False

        # 2. Explicit action flag set by caller
        if action in _APPROVAL_REQUIRED_ACTIONS:
            return True

        # 3. Prompt signals external send on behalf of the founder
        if any(pat in prompt for pat in _EXTERNAL_SEND_PATTERNS):
            return True

        # 4. Irreversible or financial keywords in prompt
        _irreversible = (
            "delete ",
            "remove all ",
            "drop table",
            "charge ",
            "pay ",
            "make payment",
        )
        if any(kw in prompt for kw in _irreversible):
            return True

        return False

    # ─── Event logging ────────────────────────────────────────────────────────

    def _log_gateway_event(
        self,
        request: dict,
        outcome: str,
        result_summary: str = "",
    ) -> str:
        """Log every gateway request to Neon events table."""
        payload = {
            "request_type": request.get("type"),
            "team": request.get("team"),
            "sub_agent": request.get("sub_agent"),
            "venture_id": request.get("venture_id"),
            "username": request.get("username"),
            "outcome": outcome,
            "summary": result_summary[:300],
            # Substrate capability telemetry — additive, observability only.
            # Populated upstream by capability_tagging.tag_request().
            "required_capabilities": request.get("required_capabilities") or [],
        }
        try:
            with get_conn(ORG_ID) as cur:
                cur.execute(
                    """
                    INSERT INTO events (org_id, event_type, payload_json, handled_by)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        ORG_ID,
                        f"gateway:{request.get('type', 'unknown')}",
                        json.dumps(payload),
                        json.dumps(["EntrepreneurOSGateway"]),
                    ),
                )
                return str(cur.fetchone()["id"])
        except Exception as e:
            print(f"[Gateway] _log_gateway_event failed: {e}")
            return ""

    # ─── Routing ──────────────────────────────────────────────────────────────

    def handle(self, request: dict) -> dict:
        """
        Validate, optionally gate for approval, then route and return result.

        Returns a dict with at minimum:
            {"status": "ok"|"error"|"pending", ...result fields}
        """
        # 0-pre. Substrate capability tagging (additive, observability only).
        # Annotates request["required_capabilities"] so downstream logging
        # and future capability-aware routing can see what was needed.
        # NEVER raises — tag_request swallows and logs internally.
        try:
            from substrate.execution.transport.capability_tagging import tag_request

            tag_request(request)
        except Exception as _cap_e:
            print(f"[Gateway] capability tagging skipped: {_cap_e}")

        # 0. Automation check — handles before AI routing
        automation_result = self._handle_automation(request)
        if automation_result is not None:
            return automation_result

        # 0b. Email instruction — founder correcting GPS folder definitions
        email_instr_result = self._handle_email_instruction(request)
        if email_instr_result is not None:
            return email_instr_result

        # 1. Validate
        err = self._validate(request)
        if err:
            self._log_gateway_event(request, "error", err)
            return {"status": "error", "error": err}

        # 2. Approval gate
        if self._requires_approval(request):
            approval_id = self.queue_for_approval(request)
            self._log_gateway_event(request, "pending", f"approval_id={approval_id}")
            return {
                "status": "pending",
                "approval_id": approval_id,
                "message": (
                    f"Request queued for approval. "
                    f"Use /approve {approval_id} to execute."
                ),
            }

        # 2b. Conversation memory — store user message, check memory query
        cm, session_id, channel = self._init_conversation_memory(request)
        prompt = request.get("prompt", "")
        if cm and prompt:
            try:
                cm.store(
                    session_id=session_id,
                    role="user",
                    content=prompt,
                    channel=channel,
                )
                # Memory query — answer from stored messages without calling AI
                if self._is_memory_query(prompt):
                    mem_resp = self._handle_memory_query(prompt, session_id, cm)
                    if mem_resp:
                        cm.store(
                            session_id=session_id,
                            role="assistant",
                            content=mem_resp,
                            channel=channel,
                            agent="memory",
                        )
                        self._log_gateway_event(request, "ok", "memory_query")
                        return {
                            "status": "ok",
                            "output": mem_resp,
                            "session_id": session_id,
                            "source": "memory",
                        }
            except Exception as _mem_err:
                print(f"[Gateway] Memory store failed (non-blocking): {_mem_err}")

        # 2c. Stage transition detection — fires before AI routing
        stage_context = ""
        if prompt and request.get("type") in ("agent_task", "brief"):
            try:
                from substrate.state.lifecycle.stage_manager import detect_stage_transition, StageManager
                from substrate.state.context.context import load_context_from_env as _load_ctx

                transition = detect_stage_transition(prompt)
                if transition.get("detected"):
                    ctx_eos = _load_ctx()
                    sm = StageManager(ctx_eos)

                    # Venture from request, then BIM default. Text-keyword routing
                    # was venture-specific leakage and has been removed — venture
                    # selection must come from explicit request or BIM lookup.
                    from substrate.state.business.business_instance import BusinessInstanceManager as _BIM

                    _bim_st = _BIM(ctx_eos)
                    venture_id = (
                        request.get("venture_id") or _bim_st.get_default_venture_id()
                    )
                    if not venture_id:
                        raise RuntimeError("no venture available for stage transition")

                    tr = sm.advance_stage(
                        venture_id=venture_id,
                        new_stage=transition["new_stage"],
                    )
                    stage_context = tr.message
                    print(
                        f"[Gateway] Stage transition: "
                        f"{tr.previous_stage} → {tr.new_stage}"
                    )
            except Exception as _st_err:
                print(f"[Gateway] Stage transition failed: {_st_err}")

        # 2d. Self-awareness — disabled (learning/ removed in convergence)
        if prompt and request.get("type") in ("agent_task", "brief"):
            try:
                # learning/ removed in convergence — SelfAwarenessEngine no longer exists
                pass
            except Exception as _sa_err:
                print(f"[SelfAwareness] {_sa_err}")

        # 3. Route
        rtype = request["type"]
        try:
            if rtype == "event":
                result = self._route_event(request)
            elif rtype == "agent_task":
                # Input Intelligence Layer — elevate underpowered inputs
                # before they reach the cognitive loop
                try:
                    from substrate.understanding.intelligence.input_intelligence import InputIntelligence
                    from substrate.state.context.context import load_context_from_env as _load_ii_ctx

                    _prompt = request.get("prompt", "")
                    _venture_id = request.get("venture_id")
                    _ii = InputIntelligence(ctx=_load_ii_ctx(), venture_id=_venture_id)
                    _ii_result = _ii.process(_prompt, venture_id=_venture_id)
                    if _ii_result.was_enhanced:
                        request = {
                            **request,
                            "prompt": _ii_result.enhanced,
                            "_original_prompt": _ii_result.original,
                            "_enhancement_reason": _ii_result.enhancement_reason,
                            "_signal_type": _ii_result.signal_type,
                        }
                except Exception as _ii_err:
                    import logging

                    logging.getLogger(__name__).warning(
                        f"InputIntelligence failed, passing original: {_ii_err}"
                    )
                result = self._route_agent_task(request, session_id=session_id, cm=cm)
            elif rtype == "status":
                result = self._route_status(request)
            elif rtype == "brief":
                result = self._route_brief(request)
            else:
                result = {"status": "error", "error": f"Unhandled type: {rtype}"}
        except Exception as exc:
            _record_error(f"route_{rtype}", exc, {
                "type": rtype, "prompt": prompt[:200] if prompt else "",
            })
            self._log_gateway_event(request, "error", str(exc))
            from substrate.execution.runtime.execution_spine import _deterministic_response
            fallback_output = _deterministic_response(prompt) if prompt else (
                "All intelligence providers are currently unavailable. "
                "Your request has been logged and will be processed when service resumes."
            )
            return {"status": "ok", "output": fallback_output, "fallback": True}

        # 3b. Prepend stage transition message if one fired
        if stage_context and result.get("output"):
            result["output"] = stage_context + "\n\n---\n\n" + result["output"]
        elif stage_context:
            result["output"] = stage_context

        # 3c. Store assistant response and tag result with session_id
        if cm and result.get("output"):
            try:
                cm.store(
                    session_id=session_id,
                    role="assistant",
                    content=result["output"],
                    channel=channel,
                    agent="system",
                )
            except Exception as _cm_status_err:
                print(f"[Gateway] Status memory store failed: {_cm_status_err}")
        if session_id:
            result["session_id"] = session_id

        summary = json.dumps(result)[:300]
        self._log_gateway_event(request, "ok", summary)
        return result

    # ─── Route: event ─────────────────────────────────────────────────────────

    def _route_event(self, request: dict) -> dict:
        from substrate.control_plane.events.event_bus import EventBus

        event_type = request["event_type"]
        payload = request.get("payload") or {}
        bus = EventBus()
        results = bus.publish(event_type, payload)
        return {
            "status": "ok",
            "event_type": event_type,
            "handlers": len(results),
        }

    # ─── Web search ───────────────────────────────────────────────────────────

    _WEB_SEARCH_SIGNALS: tuple[str, ...] = (
        "what is the current",
        "latest news",
        "right now",
        "today's",
        "this week",
        "how much does",
        "what's the price",
        "look up",
        "search for",
        "find me",
        "what are people saying",
        "trending",
        "recent",
    )

    def _needs_web_search(self, text: str) -> bool:
        t = text.lower()
        return any(s in t for s in self._WEB_SEARCH_SIGNALS)

    def _web_search(self, query: str) -> str:
        try:
            from substrate.execution.runtime.model_router import get_router, TaskType as RouterTaskType

            router = get_router()
            result = router.call_with_fallback(
                RouterTaskType.WEB_SEARCH,
                prompt=(
                    f"Search query: {query}\n\n"
                    f"Provide a concise, factual answer with current information. "
                    f"2-3 sentences maximum."
                ),
                max_tokens=200,
            )
            return result or ""
        except Exception as e:
            _record_error("web_search", e, {"query": query[:200]})
            print(f"[WebSearch] {e}")
            return ""

    # ─── EA routing ───────────────────────────────────────────────────────────

    def _validate_output(
        self, output: str, agent_type: str, provider: str
    ) -> tuple[str, float, bool]:
        """
        Validate agent output quality at gateway boundary.
        Returns: (output, score, passed)
        Provider-aware thresholds — lower for weaker models.
        """
        if not output:
            return output, 0.0, False

        thresholds = {
            "claude_cli": 0.0,  # CC is trusted primary — never reject
            "claude": 0.75,
            "anthropic": 0.75,
            "gemini": 0.60,
            "ollama": 0.55,
            "gemma": 0.50,
        }
        threshold = 0.50
        provider_lower = provider.lower()
        for key, val in thresholds.items():
            if key in provider_lower:
                threshold = val
                break

        try:
            from substrate.governance.quality.quality_gate import QualityTransformationGate

            from substrate.state.context.context import load_context_from_env

            ctx = load_context_from_env()
            gate = QualityTransformationGate(ctx)
            # Use transform() with minimal signal for scoring
            result = gate.transform(
                output=output,
                input_text="",
                classified_signal={},
            )
            score = result.overall_score
            passed = score >= threshold

            if not passed:
                import logging

                logging.getLogger(__name__).warning(
                    f"[Quality] {agent_type} scored {score:.2f} "
                    f"(threshold {threshold}) via {provider}"
                )

            return output, score, passed

        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"[Quality] Gate failed: {e}")
            return output, 0.5, True

    def _route_to_agent(self, text: str, comm_type: str = "text") -> str:
        """
        Determine which agent should handle this request.
        EA handles 90% of cases. Only escalates to CEOs or Portfolio Advisor
        for genuinely company-specific or portfolio-level decisions.

        Returns agent_id string.
        """
        try:
            from substrate.control_plane.agents.agent_hierarchy import AgentHierarchy

            return AgentHierarchy().route_request(text)
        except Exception:
            return "executive_assistant"

    # ─── Route: agent_task ────────────────────────────────────────────────────

    def _route_agent_task(self, request: dict, session_id: str = None, cm=None) -> dict:
        from substrate.execution.runtime.agent_runtime import AgentRuntime, TaskType
        from substrate.control_plane.runtime.cognitive_loop import CognitiveLoop
        from substrate.state.context.context import load_context_from_env

        prompt = request["prompt"]
        # Preserve the true raw user message before any gateway augmentation.
        # _original_prompt is set by InputIntelligence when it enhances; if
        # not present, the request["prompt"] is the original user text.
        _raw_user_input = request.get("_original_prompt", prompt)
        venture_id = request.get("venture_id")
        username = request.get("username")
        team = request.get("team")
        sub_agent = request.get("sub_agent")

        ctx = load_context_from_env()

        # Real-time web search — prepend result to prompt if signal detected
        if self._needs_web_search(prompt):
            _web_result = self._web_search(prompt)
            if _web_result:
                prompt = f"REAL-TIME SEARCH RESULT:\n{_web_result}\n\n{prompt}"
                print("[Gateway] Web search used")

        # ── ExecutionSpine — new unified path ────────────────────────────────
        # Attempts the new spine. On ANY failure, falls back to the existing
        # CognitiveLoop branches below. This is the Phase 2 transition layer.
        try:
            from substrate.control_plane.context.context_builder import ContextBuilder
            from substrate.execution.runtime.execution_spine import ExecutionSpine

            _spine_agent = sub_agent or "executive_assistant"
            if team and not sub_agent:
                _spine_agent = {
                    "dex": "executive_assistant",
                    "lyfe_ceo": "lyfe_ceo",
                    "brand_ceo": "brand_ceo",
                    "portfolio_advisor": "portfolio_advisor",
                }.get(team, "executive_assistant")
            if not _spine_agent:
                try:
                    _spine_agent = self._route_to_agent(prompt)
                except Exception:
                    _spine_agent = "executive_assistant"

            _spine_authority = "analyze"
            task_type_str = request.get("task_type", "analyze").upper()
            try:
                _spine_task_type = TaskType[task_type_str]
            except KeyError:
                _spine_task_type = TaskType.ANALYZE

            builder = ContextBuilder()
            unified_ctx = builder.build(
                ctx,
                request.get("prompt", prompt),
                session_id or "",
                agent=_spine_agent,
                venture_id=venture_id,
                channel=request.get("channel", ""),
                conversation_memory=cm,
            )

            spine = ExecutionSpine()
            _spine_response = spine.run(
                message=prompt,
                unified_context=unified_ctx,
                agent_type=_spine_agent,
                authority_class=_spine_authority,
                session_id=session_id,
                channel_id=request.get("channel", ""),
                org_id=str(ctx.org_id),
                user_id=str(ctx.user_id),
                task_type=_spine_task_type,
                venture_id=venture_id,
            )

            print(
                f"[Gateway] ExecutionSpine OK: agent={_spine_agent} "
                f"tokens~{unified_ctx.estimated_tokens} "
                f"failed_sources={len(unified_ctx.failed_sources)}"
            )

            return {
                "status": "ok",
                "interaction_id": None,
                "model": "spine",
                "skill": None,
                "output": _spine_response,
                "tokens": unified_ctx.estimated_tokens,
                "iterations": 1,
                "was_enhanced": False,
                "quality_score": 0.5,
                "quality_passed": True,
                "original_prompt": _raw_user_input,
                "enhanced_prompt": prompt if prompt != _raw_user_input else "",
                "enhancement_reason": request.get("_enhancement_reason", ""),
            }
        except Exception as _spine_err:
            import logging
            logging.getLogger(__name__).error(
                f"ExecutionSpine failed, falling back to CognitiveLoop: {_spine_err}"
            )
            _record_error("execution_spine", _spine_err, {
                "agent": _spine_agent, "prompt": prompt[:200],
            })

        # ── CognitiveLoop fallback — existing code below unchanged ───────────
        loop = CognitiveLoop(ctx)

        # Named agent teams — direct agent routing with context injection
        _NAMED_AGENT_TEAMS = frozenset(
            {
                "dex",
                "lyfe_ceo",
                "brand_ceo",
                "portfolio_advisor",
            }
        )

        # ── Agent → principle domain mapping ─────────────────────────────
        _AGENT_DOMAIN_MAP = {
            "executive_assistant": "ops",
            "sales_agent": "sales",
            "outreach_agent": "sales",
            "content_agent": "content",
            "research_agent": "research",
            "intelligence_agent": "research",
            "operations_agent": "ops",
            "finance_agent": "analyze",
            "marketing_agent": "content",
            "customer_success_agent": "ops",
            "lyfe_ceo": "strategy",
            "lyfe_institute_ceo": "strategy",
            "empyrean_ceo": "strategy",
            "brand_ceo": "content",
            "personal_brand_ceo": "content",
            "ceo_agent": "strategy",
            "portfolio_agent": "analyze",
            "portfolio_advisor": "analyze",
        }

        # ── CEO task classifier — selects relevant deep standards section ─
        _CEO_AGENTS = frozenset(
            {
                "lyfe_ceo",
                "lyfe_institute_ceo",
                "empyrean_ceo",
                "brand_ceo",
                "personal_brand_ceo",
                "ceo_agent",
            }
        )

        def _classify_ceo_task(prompt_text: str) -> str:
            p = prompt_text.lower()
            if any(
                x in p
                for x in [
                    "constraint",
                    "bottleneck",
                    "blocking",
                    "slow",
                    "stuck",
                    "not working",
                    "stalled",
                    "what to focus",
                ]
            ):
                return "constraint"
            if any(
                x in p
                for x in [
                    "offer",
                    "price",
                    "product",
                    "deliver",
                    "promise",
                    "guarantee",
                    "value",
                ]
            ):
                return "offer"
            if any(
                x in p
                for x in [
                    "hire",
                    "team",
                    "delegate",
                    "who should",
                    "role",
                    "barrel",
                    "ammunition",
                ]
            ):
                return "hiring"
            if any(
                x in p
                for x in [
                    "metric",
                    "kpi",
                    "number",
                    "measure",
                    "track",
                    "reply rate",
                    "close rate",
                    "dm",
                ]
            ):
                return "metrics"
            if any(
                x in p
                for x in [
                    "decide",
                    "should i",
                    "choice",
                    "option",
                    "which",
                    "reversible",
                    "irreversible",
                ]
            ):
                return "decisions"
            if any(
                x in p
                for x in [
                    "stage",
                    "next level",
                    "advance",
                    "grow",
                    "scale",
                    "validation",
                    "acquisition",
                ]
            ):
                return "stage"
            return "constraint"  # default — most common at Stage 1

        def _inject_agent_context(prompt_text: str, agent_id: str) -> str:
            """Single injection point for CEO, portfolio, agent, and domain standards."""
            # CEO deep standards — try skill first, fall back to Python module
            if agent_id in _CEO_AGENTS:
                try:
                    from substrate.state.registries.skill_registry import get_skill_registry

                    _sr = get_skill_registry()
                    _ceo_skill = _sr.get_skill("ceo_framework")
                    if _ceo_skill and _ceo_skill.content:
                        _task_class = _classify_ceo_task(prompt_text)
                        prompt_text = (
                            f"CEO OPERATING STANDARDS "
                            f"(task: {_task_class}):\n{_ceo_skill.content}\n\n"
                            f"{prompt_text}"
                        )
                        print(f"[Gateway] CEO standards from skill: {_task_class}")
                    else:
                        raise ValueError("ceo_framework skill not found")
                except Exception:
                    # Fallback to Python module
                    try:
                        from substrate.control_plane.agents.ceo_operational_standards import (
                            get_constraint_rules,
                            get_offer_rules,
                            get_delegation_rules,
                            get_hiring_rules,
                            get_metric_rules,
                            get_decision_rules,
                            get_stage_rules,
                            get_growth_rules,
                        )

                        _ceo_section_map = {
                            "constraint": get_constraint_rules,
                            "offer": get_offer_rules,
                            "hiring": get_hiring_rules,
                            "metrics": get_metric_rules,
                            "decisions": get_decision_rules,
                            "stage": get_stage_rules,
                        }
                        _task_class = _classify_ceo_task(prompt_text)
                        _getter = _ceo_section_map.get(
                            _task_class, get_constraint_rules
                        )
                        _ceo_deep = _getter()
                        _ceo_deep += "\n" + get_growth_rules()
                        if _task_class != "constraint":
                            _ceo_deep += "\n" + get_delegation_rules()
                        prompt_text = (
                            f"CEO OPERATING STANDARDS "
                            f"(task: {_task_class}):\n{_ceo_deep}\n\n"
                            f"{prompt_text}"
                        )
                        print(f"[Gateway] CEO standards from Python: {_task_class}")
                    except Exception as _ceo_err:
                        print(f"[Gateway] CEO standards: {_ceo_err}")

            # Portfolio advisor deep standards — try skill first, fall back to Python module
            if agent_id == "portfolio_advisor":
                try:
                    from substrate.state.registries.skill_registry import get_skill_registry

                    _sr_pa = get_skill_registry()
                    _pa_skill = _sr_pa.get_skill("portfolio_framework")
                    if _pa_skill and _pa_skill.content:
                        prompt_text = (
                            f"PORTFOLIO ADVISOR OPERATING STANDARDS "
                            f":\n{_pa_skill.content}\n\n"
                            f"{prompt_text}"
                        )
                        print("[Gateway] Portfolio advisor standards from skill")
                    else:
                        raise ValueError("portfolio_framework skill not found")
                except Exception:
                    try:
                        from substrate.control_plane.strategy.portfolio_advisor_standards import (
                            get_all_standards as get_pa_standards,
                        )

                        _pa_deep = get_pa_standards()
                        if _pa_deep:
                            prompt_text = (
                                f"PORTFOLIO ADVISOR OPERATING STANDARDS "
                                f":\n{_pa_deep}\n\n"
                                f"{prompt_text}"
                            )
                            print("[Gateway] Portfolio advisor standards from Python")
                    except Exception as _pa_err:
                        print(f"[Gateway] Portfolio advisor standards: {_pa_err}")

            # Universal agent standards
            try:
                from substrate.governance.principles.principle_engine import PrincipleEngine

                _pe = PrincipleEngine(ctx)
                _standards = _pe.format_agent_standards(agent_id)
                if _standards:
                    prompt_text = f"{_standards}\n\n{prompt_text}"
                    print(f"[Gateway] Agent standards injected: {agent_id}")
            except Exception as _se_err:
                print(f"[Gateway] Standards inject: {_se_err}")

            # Domain-specific principles
            try:
                from substrate.governance.principles.principle_engine import PrincipleEngine

                _pe_d = PrincipleEngine(ctx)
                _domain = _AGENT_DOMAIN_MAP.get(agent_id, "ops")
                _domain_principles = _pe_d.format_for_prompt(_domain)
                if _domain_principles:
                    prompt_text = f"{_domain_principles}\n\n{prompt_text}"
                    print(f"[Gateway] Domain principles injected: {_domain}")
            except Exception as _dp_err:
                print(f"[Gateway] Domain principles: {_dp_err}")

            return prompt_text

        if team and team in _NAMED_AGENT_TEAMS:
            agent_id = {
                "dex": "executive_assistant",
                "lyfe_ceo": "lyfe_ceo",
                "brand_ceo": "brand_ceo",
                "portfolio_advisor": "portfolio_advisor",
            }[team]

            if agent_id == "executive_assistant":
                # DEX — inject EA operational standards + leverage detection
                try:
                    from substrate.understanding.patterns.leverage_patterns import detect_leverage_killer

                    leverage = detect_leverage_killer(prompt)
                    if leverage:
                        prompt = leverage["intervention"] + "\n\n" + prompt
                except Exception as e:
                    logger.debug(f"suppressed {type(e).__name__}: {e}", exc_info=True)

                try:
                    from substrate.state.registries.skill_registry import get_skill_registry

                    _sr_ea = get_skill_registry()
                    _ea_skill = _sr_ea.get_skill("ea_framework")
                    if _ea_skill and _ea_skill.content:
                        prompt = f"OPERATIONAL STANDARDS:\n{_ea_skill.content}\n\n---\n\n{prompt}"
                        print("[Gateway] EA standards from skill")
                    else:
                        raise ValueError("ea_framework skill not found")
                except Exception:
                    try:
                        from substrate.control_plane.agents.ea_operational_standards import get_all_standards

                        ea_standards = get_all_standards()
                        prompt = (
                            f"OPERATIONAL STANDARDS:\n{ea_standards}\n\n---\n\n{prompt}"
                        )
                        print("[Gateway] EA standards from Python")
                    except Exception as _dex_err:
                        print(f"[Gateway] DEX context inject: {_dex_err}")

            elif agent_id == "portfolio_advisor":
                # Portfolio Advisor — inject live portfolio data
                try:
                    from substrate.control_plane.strategy.portfolio_advisor import (
                        PortfolioAdvisor as PortfolioAgent,
                    )

                    _pa = PortfolioAgent(ctx)
                    _ventures = _pa.scan_all_ventures()
                    _port_brief = _pa.generate_portfolio_brief(_ventures)
                    prompt = f"PORTFOLIO DATA:\n{_port_brief}\n\n{prompt}"
                except Exception as _pa_err:
                    print(f"[Gateway] Portfolio Advisor inject: {_pa_err}")

            # Unified standards injection — CEO, portfolio, agent, domain
            prompt = _inject_agent_context(prompt, agent_id)

            result = loop.run(
                input=prompt,
                session_id=session_id,
                cm=cm,
                agent=agent_id,
                task_type=TaskType.ANALYZE,
                venture_id=venture_id,
                channel=request.get("channel", ""),
                raw_input=_raw_user_input,
            )

        elif team:
            # Team task — resolve via agent_teams then run through cognitive loop
            from substrate.control_plane.agents.agent_teams import route as team_route

            config = team_route(team, sub_agent)
            result = loop.run(
                input=prompt,
                session_id=session_id,
                cm=cm,
                agent=f"{team}.{sub_agent}",
                task_type=config.task_type,
                venture_id=venture_id,
                skill_name=config.skill_name,
                channel=request.get("channel", ""),
                raw_input=_raw_user_input,
            )
        else:
            # Direct task — route to correct agent via hierarchy, then run
            task_type_str = request.get("task_type", "analyze").upper()
            try:
                task_type = TaskType[task_type_str]
            except KeyError:
                task_type = TaskType.ANALYZE

            # Sub_agent override → use it; else intent routing → hierarchy fallback
            agent_to_use = sub_agent

            if not agent_to_use:
                try:
                    from substrate.control_plane.router.intent_router import IntentRouter, IntentDomain

                    ir = IntentRouter(ctx)
                    domain = ir.route(prompt)
                    agent_to_use = ir.get_agent(domain)
                    print(f"[Gateway] Intent: {domain.value} → {agent_to_use}")

                    # Portfolio domain — inject live portfolio data into prompt
                    if domain == IntentDomain.PORTFOLIO:
                        try:
                            from substrate.control_plane.strategy.portfolio_advisor import (
                                PortfolioAdvisor as PortfolioAgent,
                            )

                            pa = PortfolioAgent(ctx)
                            ventures = pa.scan_all_ventures()
                            port_brief = pa.generate_portfolio_brief(ventures)
                            prompt = f"PORTFOLIO DATA:\n{port_brief}\n\n{prompt}"
                        except Exception as _pe:
                            print(f"[Gateway] Portfolio inject: {_pe}")

                    # CEO domain — inject company primitives into prompt
                    elif domain == IntentDomain.CEO:
                        try:
                            from substrate.control_plane.agents.ceo_agent import CEOAgent

                            _ceo = CEOAgent(ctx)
                            _prims = _ceo.detect_primitives()
                            prompt = (
                                f"CEO CONTEXT:\n"
                                f"Stage: {_prims.get('stage', 1)}\n"
                                f"Revenue: ${_prims.get('current_revenue', 0)}\n"
                                f"Clients: {_prims.get('client_count', 0)}\n"
                                f"Channel: {_prims.get('primary_channel', '')}\n\n"
                                f"{prompt}"
                            )
                        except Exception as _ce:
                            print(f"[Gateway] CEO inject: {_ce}")

                except Exception as _ir_err:
                    print(f"[Gateway] Intent routing: {_ir_err}")

            if not agent_to_use:
                agent_to_use = self._route_to_agent(prompt)

            # Log delegation if routing to a CEO agent
            if agent_to_use in _CEO_AGENTS:
                try:
                    from substrate.control_plane.delegation.delegation_tracker import log_delegation

                    log_delegation(
                        task=prompt[:200],
                        delegated_to=agent_to_use,
                        due_hours=24,
                    )
                except Exception as _del_err:
                    print(f"[Gateway] Delegation log failed: {_del_err}")

            # Unified standards injection — CEO, portfolio, agent, domain
            prompt = _inject_agent_context(prompt, agent_to_use)

            result = loop.run(
                input=prompt,
                session_id=session_id,
                cm=cm,
                agent=agent_to_use,
                task_type=task_type,
                venture_id=venture_id,
                channel=request.get("channel", ""),
                raw_input=_raw_user_input,
            )

        if result.status == "pending_approval":
            return {
                "status": "pending",
                "approval_id": result.approval_id,
                "message": (
                    f"Request queued for approval. "
                    f"Use /approve {result.approval_id} to execute."
                ),
            }

        # Permanently integrate this exchange into the knowledge base
        try:
            from substrate.understanding.knowledge.knowledge_integrator import KnowledgeIntegrator

            _ki = KnowledgeIntegrator(ctx)
            if prompt and result.output:
                _ki.integrate(
                    content=f"Q: {prompt[:500]}\nA: {(result.output or '')[:500]}",
                    source="gateway_conversation",
                    category="conversation",
                    metadata={
                        "team": team,
                        "sub_agent": sub_agent,
                        "venture_id": venture_id,
                    },
                )
        except Exception as _ki_err:
            print(f"[Gateway] Knowledge integration failed: {_ki_err}")

        # Feedback loop — disabled (learning/ removed in convergence)
        try:
            # learning/ removed in convergence — FeedbackLoop no longer exists
            pass
        except Exception as e:
            print(f"[FeedbackLoop] {e}")

        # Accountability — detect and log commitments in founder's message
        try:
            from substrate.governance.accountability.accountability import AccountabilityEngine

            ae = AccountabilityEngine(ctx)
            commitment = ae.detect_commitment(prompt, venture_id or "")
            if commitment:
                print(f"[Accountability] Logged: {commitment.text[:50]}")
        except Exception as e:
            print(f"[Accountability] {e}")

        # Decision log — detect and permanently record decisions
        try:
            from substrate.state.logs.decision_log import DecisionLog

            _dl = DecisionLog(ctx)
            if _dl.detect_decision(prompt):
                _dl.log_from_message(prompt, venture_id=venture_id or "")
        except Exception as e:
            print(f"[DecisionLog] {e}")

        # Store conversation turn in session memory
        try:
            if cm and session_id and result.output:
                cm.store(
                    session_id=session_id,
                    role="user",
                    content=request.get("prompt", ""),
                    channel=request.get("channel", "discord"),
                    agent="executive_assistant",
                )
                cm.store(
                    session_id=session_id,
                    role="assistant",
                    content=result.output,
                    channel=request.get("channel", "discord"),
                    agent="executive_assistant",
                )
        except Exception as e:
            print(f"[Gateway] cm.store failed: {e}")

        # Quality gate — score output at gateway boundary
        _quality_score = 0.5
        _quality_passed = True
        if result.output:
            _, _quality_score, _quality_passed = self._validate_output(
                result.output,
                agent_type=sub_agent or team or "unknown",
                provider=result.model_used or "",
            )

        return {
            "status": "ok",
            "interaction_id": result.interaction_id,
            "model": result.model_used,
            "skill": result.skill_used,
            "output": result.output,
            "tokens": result.tokens_used,
            "iterations": result.iterations,
            "was_enhanced": result.was_enhanced,
            "quality_score": round(_quality_score, 3),
            "quality_passed": _quality_passed,
            "original_prompt": request.get(
                "_original_prompt", request.get("prompt", "")
            ),
            "enhanced_prompt": request.get("prompt", "")
            if request.get("_original_prompt")
            else "",
            "enhancement_reason": request.get("_enhancement_reason", ""),
        }

    # ─── Route: status ────────────────────────────────────────────────────────

    def _route_status(self, request: dict) -> dict:
        from observability.status.status import (
            _fetch_7d_raw,
            _fetch_total_interactions,
            _fetch_last_orchestrator_run,
            _cost_est,
        )
        from substrate.state.business.venture_knowledge import VentureKnowledgeBase

        rows_7d = _fetch_7d_raw()
        total_interactions = _fetch_total_interactions()
        last_orch = _fetch_last_orchestrator_run()

        # Venture north star
        ventures = []
        for vid in VentureKnowledgeBase.list_ventures():
            v = VentureKnowledgeBase.get(vid)
            pct = (
                round(v.monthly_revenue / v.monthly_target * 100, 1)
                if v.monthly_target > 0
                else 0.0
            )
            ventures.append(
                {
                    "venture_id": vid,
                    "revenue": v.monthly_revenue,
                    "target": v.monthly_target,
                    "pct": pct,
                    "stage": v.stage,
                }
            )

        # Events table count
        try:
            with get_conn(ORG_ID) as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM events WHERE org_id = %s", (ORG_ID,)
                )
                events_count = cur.fetchone()["cnt"]
        except Exception:
            events_count = 0

        # Format readable output for Discord display
        venture_lines = []
        for v in ventures:
            bar = "█" * int(v["pct"] / 10) + "░" * (10 - int(v["pct"] / 10))
            venture_lines.append(
                f"  {v['venture_id']}: ${v['revenue']:,.0f} / ${v['target']:,.0f} "
                f"[{bar}] {v['pct']}% — Stage {v['stage']}"
            )

        last_orch_str = last_orch["timestamp"][:19] if last_orch else "never"
        neon_status = "✅ connected" if events_count > 0 else "⚠️ no events"
        output_lines = (
            [
                "**EOS SYSTEM STATUS**",
                "",
                "**NORTH STAR**",
            ]
            + venture_lines
            + [
                "",
                "**ACTIVITY**",
                f"  Interactions (total)  : {total_interactions:,}",
                f"  Interactions (7d)     : {len(rows_7d)}",
                f"  Cost (7d)             : ${round(_cost_est(rows_7d), 4):.4f}",
                f"  Events logged         : {events_count:,}",
                f"  Last orchestrator run : {last_orch_str}",
                "",
                "**INFRASTRUCTURE**",
                f"  Neon database         : {neon_status}",
            ]
        )

        return {
            "status": "ok",
            "interactions_total": total_interactions,
            "interactions_7d": len(rows_7d),
            "cost_7d_usd": round(_cost_est(rows_7d), 4),
            "events_logged": events_count,
            "last_orchestrator": last_orch_str,
            "ventures": ventures,
            "output": "\n".join(output_lines),
        }

    # ─── Route: brief ─────────────────────────────────────────────────────────

    def _route_brief(self, request: dict) -> dict:
        """Notion-first brief: run morning cycle, write to Notion, return URL."""
        try:
            from substrate.control_plane.orchestrator.orchestrator import run_full_morning_cycle
            from substrate.state.context.context import load_context_from_env

            ctx = load_context_from_env()
            result = run_full_morning_cycle(ctx, return_content=True)

            notion_url = (result or {}).get("notion_url", "")
            message = (result or {}).get("message", "")

            if notion_url:
                return {
                    "status": "ok",
                    "output": f"📋 Morning Brief ready\n{notion_url}",
                    "notion_url": notion_url,
                }
            else:
                # Fallback: return summary if Notion failed
                summary = message[:500] if message else "Brief generated. Check Notion."
                return {
                    "status": "ok",
                    "output": summary,
                }

        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"[Brief] Route failed: {e}")
            _record_error("route_brief", e)
            # Data-driven fallback — pull what we can from Neon
            fallback_lines = ["MORNING BRIEF (offline mode)", ""]
            try:
                from substrate.state.business.venture_knowledge import VentureKnowledgeBase

                for vid in VentureKnowledgeBase.list_ventures():
                    v = VentureKnowledgeBase.get(vid)
                    pct = (
                        round(v.monthly_revenue / v.monthly_target * 100, 1)
                        if v.monthly_target > 0
                        else 0.0
                    )
                    fallback_lines.append(
                        f"{vid}: ${v.monthly_revenue:,.0f}/${v.monthly_target:,.0f} ({pct}%)"
                    )
            except Exception:
                fallback_lines.append("Venture data unavailable.")
            fallback_lines.append("")
            fallback_lines.append("Focus: revenue. Send 20 outreach messages today.")
            return {
                "status": "ok",
                "output": "\n".join(fallback_lines),
                "fallback": True,
            }

    # ─── Approval queue ───────────────────────────────────────────────────────

    def queue_for_approval(self, request: dict) -> str:
        """
        Write request to pending/ directory.
        Returns approval_id (timestamp-based, human-readable).
        """
        approval_id = f"{_timestamp_id()}_{request.get('type', 'req')}"
        pending_file = PENDING_DIR / f"{approval_id}.json"
        record = {
            "approval_id": approval_id,
            "queued_at": _utcnow(),
            "request": request,
            "status": "pending",
        }
        pending_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(f"[Gateway] Approval queued: {approval_id}")
        return approval_id

    def approve(self, approval_id: str) -> dict:
        """
        Move pending → approved, then execute the original request.
        Returns the execution result.
        """
        pending_file = PENDING_DIR / f"{approval_id}.json"
        approved_file = APPROVED_DIR / f"{approval_id}.json"

        if not pending_file.exists():
            # Check if already approved
            if approved_file.exists():
                return {"status": "error", "error": f"{approval_id} already approved"}
            return {"status": "error", "error": f"Approval {approval_id} not found"}

        record = json.loads(pending_file.read_text(encoding="utf-8"))
        record["status"] = "approved"
        record["approved_at"] = _utcnow()

        # Move to approved/
        approved_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
        pending_file.unlink()
        print(f"[Gateway] Approved: {approval_id}")

        # Execute bypassing the approval gate (approved request runs directly)
        original_request = record["request"]
        rtype = original_request.get("type")
        try:
            if rtype == "event":
                result = self._route_event(original_request)
            elif rtype == "agent_task":
                result = self._route_agent_task(original_request)
            elif rtype == "status":
                result = self._route_status(original_request)
            elif rtype == "brief":
                result = self._route_brief(original_request)
            else:
                result = {"status": "error", "error": f"Unknown type: {rtype}"}
        except Exception as exc:
            result = {"status": "error", "error": str(exc)}

        self._log_gateway_event(
            original_request, "approved_executed", json.dumps(result)[:300]
        )
        return result

    # ─── Multi-part ordering ──────────────────────────────────────────────────

    def split_and_order_prompt(self, text: str) -> list[str]:
        """
        Detect whether a prompt contains multiple distinct instructions and
        return them as an ordered list.  Single-part prompts return [text].

        Detection priority:
          1. Numbered list  — "1. ...\n2. ..."
          2. Connector split — lines starting with "also", "another", etc.
        """
        import re

        # Numbered list: two or more "N. ..." items
        numbered = re.findall(r"^\d+\.\s+.+$", text, re.MULTILINE)
        if len(numbered) >= 2:
            return [re.sub(r"^\d+\.\s+", "", n).strip() for n in numbered]

        # Connector split on newlines before transition words
        parts = re.split(
            r"\n+(?=(?:also|another|additionally|and also|one more|finally)\b)",
            text,
            flags=re.IGNORECASE,
        )
        if len(parts) >= 2:
            return [p.strip() for p in parts if p.strip()]

        return [text]

    def handle_ordered(self, request: dict) -> list[dict]:
        """
        Split the prompt into ordered parts and process each sequentially.
        Returns a list of result dicts in order.  Single-part prompts return
        a one-element list so callers can always iterate uniformly.
        """
        text = request.get("prompt", "")
        parts = self.split_and_order_prompt(text)

        if len(parts) == 1:
            return [self.handle(request)]

        results = []
        for i, part in enumerate(parts):
            part_request = {**request, "prompt": part}
            result = self.handle(part_request)
            result["part"] = i + 1
            result["total_parts"] = len(parts)
            results.append(result)
        return results

    _INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
        "CONVERSATION": ("hey ", "hi ", "hello", "what's up", "how are you",
                         "good morning", "good evening", "sup ", "yo "),
        "BRIEF": ("morning brief", "status update", "how are things",
                  "what's happening", "daily brief", "give me a summary"),
        "STRATEGY": ("strategic", "priorities", "what should i focus",
                     "what matters most", "north star", "binding constraint"),
        "OUTREACH": ("dm ", "leads", "pipeline", "prospect", "reply rate",
                     "who replied", "follow up", "outreach", "cold email"),
        "RESEARCH": ("market research", "competitor", "industry", " icp ",
                     "research ", "what's working in the market"),
        "CONTENT": ("content idea", "hook", "caption", "what to post",
                    "thumbnail", "reel", "tweet"),
        "DECISION": ("should i", "evaluating", "is this a good idea",
                     "advice on", "which option", "decide between"),
        "TASK": ("do this", "run this", "handle this", "delegate",
                 "make this happen", "execute this", "deploy"),
        "INTEL": ("signal", "market move", "alert", "what's happening out there",
                  "intelligence report"),
        "PORTFOLIO": ("all companies", "overall status", "capital allocation",
                      "big picture", "portfolio", "across ventures"),
        "JOURNAL": ("here's what happened", "reporting back", "fyi",
                    "logging ", "update:", "here is what"),
        "MODEL": ("model preference", "switching model", "cost mode",
                  "which ai", "which model", "use opus", "use haiku"),
    }

    def classify_intent(self, text: str) -> str:
        """
        Classify a natural language message into one of the known intents.
        Deterministic keyword matching first, AI refines ambiguous cases.
        """
        t = text.lower()

        for intent, keywords in self._INTENT_KEYWORDS.items():
            if any(kw in t for kw in keywords):
                return intent

        # No keyword match — try AI for ambiguous cases
        _VALID = set(self._INTENT_KEYWORDS.keys()) | {"UNKNOWN"}
        try:
            from substrate.execution.runtime.model_router import call_with_fallback, TaskType

            _SYSTEM = (
                "Classify this message into exactly one intent. "
                "Reply with ONLY the intent word.\n"
                "INTENTS: " + ", ".join(sorted(self._INTENT_KEYWORDS.keys()))
                + ", UNKNOWN"
            )
            result = call_with_fallback(
                prompt=text,
                system=_SYSTEM,
                task_type=TaskType.CLASSIFY,
            )
            intent = result.output.strip().upper().split()[0]
            return intent if intent in _VALID else "UNKNOWN"
        except Exception as e:
            _record_error("classify_intent", e, {"text": text[:200]})
            print(f"[Gateway] classify_intent AI failed: {e}")
            return "UNKNOWN"

    def get_pending_approvals(self) -> list[dict]:
        """Return all requests waiting for approval."""
        pending = []
        for f in sorted(PENDING_DIR.glob("*.json")):
            try:
                record = json.loads(f.read_text(encoding="utf-8"))
                pending.append(
                    {
                        "approval_id": record.get("approval_id"),
                        "queued_at": record.get("queued_at"),
                        "type": record.get("request", {}).get("type"),
                        "sub_agent": record.get("request", {}).get("sub_agent"),
                        "action": record.get("request", {}).get("action"),
                        "prompt": record.get("request", {}).get("prompt", "")[:80],
                    }
                )
            except Exception as exc:
                pending.append({"file": f.name, "error": str(exc)})
        return pending


# ─── Module-level helper ──────────────────────────────────────────────────────


def get_gateway() -> EntrepreneurOSGateway:
    """Return the singleton EntrepreneurOSGateway instance."""
    return EntrepreneurOSGateway()


def ingest_external_context(
    source: str,
    content: str,
    context_type: str = "design_decision",
    venture_id: str | None = None,
) -> str:
    """
    Capture context from any external source into Neon + embed immediately.

    source:       'telegram_manual' | 'claude_ai' | 'voice_note' | 'document' | 'manual'
    context_type: 'design_decision' | 'architectural_spec' | 'user_feedback'
                  | 'strategic_insight' | 'correction' | 'user_note'

    Stores as an interaction in Neon and triggers async embedding so the
    note is immediately retrievable by any agent via semantic search.

    Returns the interaction_id (UUID).
    """
    from substrate.state.memory.memory import AgentMemory
    from substrate.execution.runtime.agent_runtime import AgentResult

    result = AgentResult(
        output=content[:500],
        model_used="external",
        tokens_used={"total": 0},
        skill_used=None,
    )
    mem = AgentMemory()
    interaction_id = mem.log(
        agent_result=result,
        venture_id=venture_id,
        input_summary=f"[{source}] {context_type}",
        agent=f"external_{source}",
        task_type=context_type,
    )
    return interaction_id
