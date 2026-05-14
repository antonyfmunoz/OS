"""
ExecutionContract — unified execution entry point for all EOS AI operations.

Every message in, every response out. Eight mandatory steps, no exceptions.
Never raises — always returns a result dict with ok=True/False.

Usage:
    from core.execution_contract import run_task

    result = run_task(
        text="What's my pipeline looking like?",
        channel="discord",
        mode="builder",
        username="antony",
    )
    print(result["response"])
    print(result["ok"])
"""

import sys
import threading
import time
import uuid as _uuid

import os
_REPO_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from runtime.context import load_context_from_env, EOSContext
from state.storage.db import get_conn, ORG_ID
from runtime.transport.execution_trace import (
    new_trace,
    update_trace,
    finalize_trace,
    get_trace_history,
)


# ---------------------------------------------------------------------------
# Session persistence — load or create session_id per channel
# ---------------------------------------------------------------------------


def _resolve_session(channel: str, username: str) -> str:
    """Load existing session_id for this channel+user, or create one.

    Sessions persist across messages in the same channel so that
    ConversationMemory can stitch multi-turn conversations.
    """
    session_key = f"{channel}:{username}"
    try:
        with get_conn() as cur:
            cur.execute(
                """
                SELECT session_id FROM messages
                WHERE org_id = %s AND channel = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (ORG_ID, channel),
            )
            row = cur.fetchone()
            if row:
                return str(row["session_id"])
    except Exception:
        pass
    return str(_uuid.uuid4())


# ---------------------------------------------------------------------------
# Core contract
# ---------------------------------------------------------------------------


def run_task(
    text: str,
    channel: str,
    mode: str,
    username: str,
    metadata: dict | None = None,
) -> dict:
    """Execute a single task through the full EOS pipeline.

    Args:
        text: Raw user input.
        channel: Origin channel — "discord", "telegram", "voice", "cli".
        mode: Routing mode — "builder", "product", "unknown".
        username: Who sent the message.
        metadata: Optional dict passed through to gateway request.

    Returns:
        {
            "response": str,
            "trace_id": str,
            "session_id": str,
            "provider": str,
            "path": "gateway|workflow|command|capture",
            "logged": bool,
            "ok": bool,
            "error": str | None,
        }
    """
    t0 = time.monotonic()
    trace_id = str(_uuid.uuid4())
    session_id = ""
    provider = ""
    path = "gateway"
    logged = False
    response = ""
    error = None

    try:
        # ── 1. INGEST ────────────────────────────────────────────────
        # Normalize input, assign trace_id and session_id.
        session_id = _resolve_session(channel, username)
        trace = new_trace(
            source=channel,
            mode=mode,
            session_name=f"{channel}:{username}",
        )
        trace_id = trace["trace_id"]

        # ── 2. NORMALIZE ─────────────────────────────────────────────
        # Clean text, detect channel/mode context.
        clean_text = text.strip() if text else ""
        if not clean_text:
            return _result(
                response="",
                trace_id=trace_id,
                session_id=session_id,
                provider="",
                path=path,
                logged=False,
                ok=False,
                error="empty input",
            )

        # ── 3. ROUTE ─────────────────────────────────────────────────
        # Call gateway.classify_intent() to determine path.
        from control_plane.runtime.gateway import EOSGateway

        gw = EOSGateway()
        intent = gw.classify_intent(clean_text)
        update_trace(trace, workflow_intent=intent)

        # Map intent → gateway request type
        request_type = "agent_task"
        if intent == "BRIEF":
            request_type = "brief"
        elif intent == "PORTFOLIO":
            request_type = "agent_task"

        path = f"gateway:{intent.lower()}"

        # ── 4. PROPOSE ───────────────────────────────────────────────
        # Build request object for gateway.
        request = {
            "type": request_type,
            "prompt": clean_text,
            "channel": channel,
            "username": username,
            "session_id": session_id,
            "venture_id": (metadata or {}).get("venture_id"),
            "team": (metadata or {}).get("team"),
            "sub_agent": (metadata or {}).get("sub_agent"),
        }
        if metadata:
            # Pass through action flags if present
            if "action" in metadata:
                request["action"] = metadata["action"]

        # ── 5. VALIDATE ──────────────────────────────────────────────
        # Check authority_engine if action is irreversible.
        action = request.get("action")
        if action:
            try:
                from governance.policy.authority_engine import AuthorityEngine

                ctx = load_context_from_env()
                ae = AuthorityEngine(ctx)
                check = ae.check_can_execute(action)
                if not check["can_execute"]:
                    update_trace(trace, result="blocked")
                    finalize_trace(trace, result="blocked")
                    get_trace_history().record(trace)
                    return _result(
                        response=f"Action '{action}' blocked: {check['reason']}",
                        trace_id=trace_id,
                        session_id=session_id,
                        provider="",
                        path=path,
                        logged=False,
                        ok=False,
                        error=check["reason"],
                    )
            except Exception as e:
                # Authority check failure is non-fatal — log and continue
                print(f"[ExecutionContract] authority check failed: {e}")

        # ── 6. EXECUTE ───────────────────────────────────────────────
        # Call gateway.handle(request) → cognitive_loop → agent_runtime → model_router.
        gw_result = gw.handle(request)

        if gw_result.get("status") == "error":
            error = gw_result.get("error", "unknown gateway error")
            response = error
            update_trace(trace, result="error")
        elif gw_result.get("status") == "pending":
            response = gw_result.get("message", "Queued for approval.")
            path = "gateway:pending"
            update_trace(trace, result="deferred")
        else:
            response = gw_result.get("output", "")
            # Gateway returns model name as "model" (not "model_used")
            model_name = gw_result.get("model") or gw_result.get("model_used") or ""
            provider = model_name
            update_trace(trace, result="success")

        # Capture session_id from gateway if it created one
        session_id = gw_result.get("session_id", session_id)

        # ── 7. LOG ───────────────────────────────────────────────────
        # Write user message + assistant response to memory.py messages table.
        # Non-blocking — DB failure never breaks response.
        try:
            from state.memory.memory import ConversationMemory

            ctx = load_context_from_env()
            cm = ConversationMemory(ctx)
            # Store user message (gateway may have already stored it,
            # but ConversationMemory uses sequence_num so dupes are harmless)
            cm.store(
                session_id=session_id,
                role="user",
                content=clean_text,
                channel=channel,
                agent="execution_contract",
                metadata={"trace_id": trace_id, "username": username},
            )
            # Store assistant response
            if response:
                cm.store(
                    session_id=session_id,
                    role="assistant",
                    content=response,
                    channel=channel,
                    agent="execution_contract",
                    metadata={"trace_id": trace_id, "provider": provider},
                )
            logged = True
        except Exception as e:
            print(f"[ExecutionContract] LOG failed (non-blocking): {e}")
            logged = False

        # ── 8. LEARN ─────────────────────────────────────────────────
        # Write to interactions table, trigger embedding async.
        _learn_async(
            trace_id=trace_id,
            text=clean_text,
            response=response,
            channel=channel,
            username=username,
            provider=provider,
        )

        # Finalize trace and record
        latency_ms = int((time.monotonic() - t0) * 1000)
        # provider holds "provider/model" from agent_runtime — split for trace
        _prov, _model = _split_provider_model(provider)
        finalize_trace(
            trace,
            provider=_prov or None,
            model=_model or None,
            latency_ms=latency_ms,
            result=trace.get("result", "success"),
        )
        get_trace_history().record(trace)

        return _result(
            response=response,
            trace_id=trace_id,
            session_id=session_id,
            provider=provider,
            path=path,
            logged=logged,
            ok=error is None,
            error=error,
        )

    except Exception as exc:
        # Never raise — always return ok=False
        latency_ms = int((time.monotonic() - t0) * 1000)
        print(f"[ExecutionContract] FATAL: {exc}")
        return _result(
            response=str(exc),
            trace_id=trace_id,
            session_id=session_id,
            provider=provider,
            path=path,
            logged=logged,
            ok=False,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_provider_model(raw: str) -> tuple[str, str]:
    """Split 'provider/model' format from agent_runtime into (provider, model).

    agent_runtime.run() returns model_used as "provider/model_id", e.g.
    "claude_cli/tmux:dex_main", "gemini/gemini-2.5-flash", "groq/llama-3.3-70b".
    Gateway passes this through as the "model" key.

    Returns (provider, model) or (raw, raw) if no slash found.
    """
    if not raw:
        return ("", "")
    if "/" in raw:
        provider, model = raw.split("/", 1)
        return (provider.strip(), model.strip())
    return (raw, raw)


def _result(
    response: str,
    trace_id: str,
    session_id: str,
    provider: str,
    path: str,
    logged: bool,
    ok: bool,
    error: str | None,
) -> dict:
    """Build the canonical return dict."""
    return {
        "response": response,
        "trace_id": trace_id,
        "session_id": session_id,
        "provider": provider,
        "path": path,
        "logged": logged,
        "ok": ok,
        "error": error,
    }


def _learn_async(
    trace_id: str,
    text: str,
    response: str,
    channel: str,
    username: str,
    provider: str,
) -> None:
    """Write to interactions table and trigger embedding — non-blocking."""

    def _do() -> None:
        try:
            from state.memory.memory import AgentMemory
            from execution.runtime.agent_runtime import AgentResult

            ar = AgentResult(
                output=response or "",
                model_used=provider or "unknown",
                tokens_used={"input": 0, "output": 0, "total": 0},
                skill_used="execution_contract",
            )
            mem = AgentMemory()
            mem.log(
                agent_result=ar,
                venture_id=None,
                input_summary=text[:300],
                agent="execution_contract",
                task_type=channel,
                lead_username=username,
            )
        except Exception as e:
            print(f"[ExecutionContract] LEARN failed (async): {e}")

    threading.Thread(target=_do, daemon=True).start()
