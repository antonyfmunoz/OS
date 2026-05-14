"""
Intent classification and gateway routing.
Extracted from discord_bot.py — handles message intent
detection, request building, and gateway execution.
"""

import json
import os
import re
import sys
import uuid as _uuid_mod
from datetime import datetime
from zoneinfo import ZoneInfo

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# Channel name → intent routing hint
CHANNEL_MAP: dict[str, str | None] = {
    "morning-brief": "BRIEF",
    "general": None,
    "decisions": "DECISION",
    "wins": None,
    "agent-activity": None,
    "empyrean-strategy": "STRATEGY",
    "empyrean-pipeline": "OUTREACH",
    "empyrean-outreach": "OUTREACH",
    "lyfe-strategy": "STRATEGY",
    "lyfe-pipeline": "OUTREACH",
    "lyfe-outreach": "OUTREACH",
    "brand-strategy": "STRATEGY",
    "content-ideas": "CONTENT",
}

# Intent → gateway request type mapping
_INTENT_TO_TEAM: dict[str, tuple[str | None, str | None]] = {
    "CONVERSATION": ("dex", None),
    "OUTREACH": ("sales", "outreach_writer"),
    "RESEARCH": ("research", "market_analyst"),
    "CONTENT": ("content", "content_writer"),
    "STRATEGY": (None, None),
    "DECISION": (None, None),
    "TASK": (None, None),
    "INTEL": ("research", "signal_analyst"),
    "PORTFOLIO": (None, None),
    "JOURNAL": (None, None),
    "MODEL": (None, None),
    "UNKNOWN": (None, None),
}


def build_request(
    text: str,
    intent: str,
    channel_name: str,
    username: str,
    default_venture_id: str,
) -> dict:
    """Build a valid EOSGateway request dict from classified intent."""
    if intent == "BRIEF":
        explicit_brief_triggers = [
            "morning brief",
            "give me the brief",
            "brief me",
            "run the brief",
            "daily brief",
            "show brief",
            "what's the brief",
            "pull the brief",
        ]
        if any(trigger in text.lower() for trigger in explicit_brief_triggers):
            return {"type": "brief", "prompt": text, "username": username}
        return {
            "type": "agent_task",
            "prompt": text,
            "username": username,
            "venture_id": default_venture_id,
            "task_type": "ANALYZE",
        }

    if intent == "PORTFOLIO":
        return {"type": "status", "prompt": text, "username": username}

    team, sub_agent = _INTENT_TO_TEAM.get(intent, (None, None))
    req: dict = {
        "type": "agent_task",
        "prompt": text,
        "username": username,
        "venture_id": default_venture_id,
    }
    if team:
        req["team"] = team
        req["sub_agent"] = sub_agent
    else:
        task_map = {
            "STRATEGY": "ANALYZE",
            "DECISION": "ANALYZE",
            "TASK": "GENERATE",
            "JOURNAL": "SUMMARIZE",
            "MODEL": "ANALYZE",
            "UNKNOWN": "ANALYZE",
            "OUTREACH": "GENERATE",
            "CONTENT": "GENERATE",
            "INTEL": "ANALYZE",
            "PORTFOLIO": "ANALYZE",
        }
        req["task_type"] = task_map.get(intent, "ANALYZE")
        req["sub_agent"] = "executive_assistant"
    return req


def run_gateway(
    text: str,
    channel_name: str,
    username: str,
    gateway,
    ki,
    channel_sessions: dict,
    default_venture_id: str,
    guild_id: str | None = None,
    channel_id: str | None = None,
    memory_only: bool = False,
) -> str:
    """
    Classify intent, build request, call gateway, return output text.
    Runs synchronously — called from asyncio executor to avoid blocking.
    """
    if channel_name not in channel_sessions:
        channel_sessions[channel_name] = str(_uuid_mod.uuid4())
        try:
            from runtime.substrate.storage import get_storage
            get_storage().put(f"session:{channel_name}", channel_sessions[channel_name])
        except Exception:
            pass
    session_id = channel_sessions[channel_name]

    # Classify intent
    intent = gateway.classify_intent(text)
    print(f"[Discord] #{channel_name} | {username} | intent={intent}")

    # Memory-only mode: log the interaction without calling the LLM.
    # Used by bypass paths that already handled the response (pipeline updates, etc).
    if memory_only:
        try:
            from runtime.context import load_context_from_env
            from state.memory.memory import ConversationMemory

            _mo_ctx = load_context_from_env()
            _mo_cm = ConversationMemory(_mo_ctx)
            _mo_cm.store(
                session_id=session_id,
                role="user",
                content=text[:10000],
                channel=f"discord_{channel_name}",
                agent="bypass_handler",
            )
        except Exception as _mo_err:
            print(f"[IntentHandler] memory_only write failed: {_mo_err}")
        try:
            ki.integrate(
                content=f"Discord #{channel_name}\nUser: {text[:300]}\nSystem: [handled by bypass]",
                source="discord_conversation",
                category="conversation",
                metadata={"channel": channel_name, "user": username, "intent": intent, "memory_only": True},
            )
        except Exception:
            pass
        return ""

    # Use channel hint if intent is UNKNOWN
    if intent == "UNKNOWN":
        channel_hint = CHANNEL_MAP.get(channel_name)
        if channel_hint:
            intent = channel_hint

    # Build and send
    req = build_request(text, intent, channel_name, username, default_venture_id)
    req["session_id"] = session_id
    req["channel"] = f"discord_{channel_name}"

    # Person recognition — inject context if a known person is mentioned
    try:
        _names = re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", text)
        if _names:
            from runtime.person_recognition import recognize_person

            for _name in _names[:2]:
                _rec = recognize_person(name=_name)
                if _rec.get("known") and _rec.get("confidence") == "high":
                    print(f"[Discord] Known person mentioned: {_name}")
                    req["known_person"] = _name
                    req["person_context"] = _rec.get("context", "")
                    break
    except Exception:
        pass

    # Cloning loop — detect when text answers an open DEX question
    try:
        from runtime.context import load_context_from_env
        from runtime.db import get_conn

        _cl_ctx = load_context_from_env()

        with get_conn(_cl_ctx.org_id) as _cl_cur:
            _cl_cur.execute(
                """
                SELECT id, payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'dex_question'
                AND (payload_json->>'answered' IS NULL
                     OR payload_json->>'answered' != 'true')
                AND created_at >= NOW() - INTERVAL '48 hours'
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (str(_cl_ctx.org_id),),
            )
            _open_q = _cl_cur.fetchone()

        if _open_q:
            _q_payload = _open_q["payload_json"]
            if isinstance(_q_payload, str):
                _q_payload = json.loads(_q_payload)
            _question = _q_payload.get("question", "")

            from execution.runtime.model_router import call_with_fallback as _cl_cwf

            _cl_result = _cl_cwf(
                prompt=f"""Does this message answer this question?
Question: {_question}
Message: {text}
Return JSON: {{"answers": true, "answer_summary": "brief summary"}}""",
                task_type="fast_response",
            )
            _cl_check = (_cl_result.output if _cl_result else "").strip()

            if "```" in _cl_check:
                _cl_check = _cl_check.split("```")[1].replace("json", "").strip()
            _cl_data = json.loads(_cl_check)

            if _cl_data.get("answers"):
                _cl_now = datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()
                with get_conn(_cl_ctx.org_id) as _cl_cur2:
                    _cl_cur2.execute(
                        """
                        UPDATE events
                        SET payload_json = payload_json || %s::jsonb
                        WHERE id = %s
                    """,
                        (
                            json.dumps(
                                {
                                    "answered": "true",
                                    "answer": _cl_data.get("answer_summary", ""),
                                    "answered_at": _cl_now,
                                }
                            ),
                            _open_q["id"],
                        ),
                    )

                with get_conn(_cl_ctx.org_id) as _cl_cur3:
                    _cl_cur3.execute(
                        """
                        INSERT INTO events
                        (org_id, event_type, payload_json, handled_by)
                        VALUES (%s, %s, %s, %s)
                    """,
                        (
                            str(_cl_ctx.org_id),
                            "dex_learning",
                            json.dumps(
                                {
                                    "question": _question,
                                    "answer": _cl_data.get("answer_summary", ""),
                                    "raw_answer": text,
                                    "learned_at": _cl_now,
                                }
                            ),
                            "dex_cloning_loop",
                        ),
                    )
    except Exception:
        pass

    # No List enforcement
    try:
        from runtime.founder_rate import check_against_no_list

        _nl_violations = check_against_no_list(text)
        if _nl_violations:
            req["no_list_violations"] = _nl_violations
    except Exception:
        pass

    # Resolve Discord mode context — registry-first, env fallback.
    # mode_context injects routing metadata into thread-local state
    # so model_router's Claude CLI backend targets the correct session.
    _mode_cm = None
    try:
        from runtime.substrate.discord_mode_routing import (
            mode_context as _mc,
            resolve_discord_mode,
        )
        from runtime.session_registry import get_registry

        _discord_mode = resolve_discord_mode(guild_id, channel_id)

        _reg = get_registry()
        _reg_session = _reg.resolve_by_channel(str(channel_id)) if channel_id else None

        if _reg_session:
            _mode_cm = _mc(
                _reg_session.mode,
                target=_reg_session.node,
                session_name=_reg_session.tmux_name,
                guild_id=guild_id,
                channel_id=channel_id,
                source="registry",
                delegated_local=(_reg_session.node == "local"),
                delegation_reason=None,
                policy_version=None,
            )
        else:
            from runtime.substrate.discord_mode_routing import resolve_mode_session

            _mode_session = resolve_mode_session(
                _discord_mode, guild_id=guild_id, channel_id=channel_id
            )
            _mode_cm = _mc(
                _discord_mode,
                target=_mode_session.get("target"),
                session_name=_mode_session.get("session_name"),
                guild_id=guild_id,
                channel_id=channel_id,
                source=_mode_session.get("source"),
                delegated_local=_mode_session.get("delegated_local", False),
                delegation_reason=_mode_session.get("delegation_reason"),
                policy_version=_mode_session.get("policy_version"),
            )
    except Exception as _mode_err:
        print(f"[IntentHandler] mode_context setup failed: {_mode_err}")

    # Gateway handles all classification and routing — wrapped in mode_context
    # so model_router picks up the correct Claude CLI session target.
    if _mode_cm is not None:
        with _mode_cm:
            result = gateway.handle(req)
    else:
        result = gateway.handle(req)

    if result.get("status") == "error":
        print(f"[Discord] Gateway error: {result.get('error')}")
        return f"Something went wrong: {result.get('error', 'unknown error')}"

    if result.get("status") == "pending":
        return (
            f"Queued for approval — use `!approve {result['approval_id']}` to execute."
        )

    output = result.get("output") or result.get("brief") or ""

    # Integrate into permanent knowledge
    try:
        ki.integrate(
            content=(
                f"Discord #{channel_name}\nUser: {text[:300]}\nSystem: {output[:300]}"
            ),
            source="discord_conversation",
            category="conversation",
            metadata={"channel": channel_name, "user": username, "intent": intent},
        )
    except Exception as e:
        print(f"[Discord] KI integrate failed (non-blocking): {e}")

    return output
