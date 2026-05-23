"""
Discord message handlers — extracted from discord_bot.py.

Each handler was extracted verbatim from on_message to keep the dispatcher
readable.  Return conventions:
  - handlers that terminate processing return True  (caller returns early)
  - handlers that mutate text return (True, new_text) or (False, text)
  - helpers prefixed with _ are not called directly from the dispatcher

Initialised via init() from discord_bot.py at module load time.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path

import discord

from substrate.observability.error_recorder import record_error as _record_error
from substrate.execution.bridge.session_discord_bridge import send_reply as _send_reply
from substrate.execution.bridge.discord_text_transport import (
    maybe_mirror_discord_text_message as _maybe_pseudo_live_text,
)

from substrate.execution.bridge.event_spine import (
    EventType as _FrameEventType,
    create_event as _frame_create_event,
)

try:
    from substrate.execution.bridge.event_store import get_event_store as _frame_get_event_store
except ImportError:
    _frame_get_event_store = None

try:
    from substrate.execution.bridge.interaction_archive import (
        archive_inbound as _archive_inbound,
        Interface as _ArchiveInterface,
    )
except ImportError:
    _archive_inbound = None
    _ArchiveInterface = None

from transports.presence.handlers.pipeline_handler import handle_pipeline_update
from transports.presence.handlers.cc_command_handler import try_inline_commands

logger = logging.getLogger(__name__)


# ─── Shared context (set by init()) ──────────────────────────────────────────

_ctx: dict = {}

# Module-level mutable state for multi-part / pending captures
_multipart_buffers: dict[str, dict] = {}
# channel -> {'parts': {1: text, 2: text, ...}, 'total': N, 'username': str}
_multipart_flush_tasks: dict[str, asyncio.Task] = {}

# Pending captures (venture disambiguation)
# channel_id -> {'text': str, 'type': str}
_pending_captures: dict[str, dict] = {}

# Pending events (calendar conflict confirmation)
# channel_id -> parsed event dict
_pending_events: dict[str, dict] = {}

_PART_RE_WORD = re.compile(r"(?i)\bpart\s+(\d+)\s*/\s*(\d+)\b")
_PART_RE_START = re.compile(r"(?im)^(\d+)\s*/\s*(\d+)\s*[:\-\s]")


def init(
    *,
    bot,
    run_gateway,
    run_day_command,
    format_day_result,
    send_day_response,
    onboarding,
    ve,
    ai_name_getter,
    default_venture_id: str,
    founder_id: int,
    start_meeting_mode_fn,
    end_active_meeting_fn,
    discord_server_manager_cls,
    send_response_fn,
) -> None:
    """Store references to bot-level objects.  Called once from discord_bot.py."""
    _ctx.update(
        bot=bot,
        run_gateway=run_gateway,
        run_day_command=run_day_command,
        format_day_result=format_day_result,
        send_day_response=send_day_response,
        onboarding=onboarding,
        ve=ve,
        ai_name_getter=ai_name_getter,
        default_venture_id=default_venture_id,
        founder_id=founder_id,
        start_meeting_mode=start_meeting_mode_fn,
        end_active_meeting=end_active_meeting_fn,
        DiscordServerManager=discord_server_manager_cls,
        send_response=send_response_fn,
    )


def get_pending_events() -> dict:
    """Expose pending_events dict for cc_command_handler integration."""
    return _pending_events


# ─── Accessor shortcuts ─────────────────────────────────────────────────────

def _bot():
    return _ctx["bot"]


def _ai_name() -> str:
    return _ctx["ai_name_getter"]()


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _detect_part(text: str) -> tuple[int, int] | None:
    """Return (part_num, total) if text is a multi-part fragment, else None."""
    m = _PART_RE_WORD.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _PART_RE_START.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _assemble_parts(buf: dict) -> str:
    """Combine buffered parts in order into a single prompt."""
    parts = buf.get("parts", {})
    ordered = [parts[i] for i in sorted(parts.keys()) if i in parts]
    return "\n\n".join(ordered)


# ─── Memory gateway helper ──────────────────────────────────────────────────


async def _memory_gateway(
    text: str,
    channel_name: str,
    username: str,
    message: discord.Message,
    *,
    prefix: str = "",
) -> None:
    """Write a message to gateway memory (memory_only=True).  Best-effort."""
    _gid = str(message.guild.id) if message.guild else None
    _cid = str(message.channel.id)
    prompt = f"{prefix}{text}" if prefix else text
    _run_gw = _ctx["run_gateway"]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: _run_gw(
            prompt,
            channel_name,
            username,
            guild_id=_gid,
            channel_id=_cid,
            memory_only=True,
        ),
    )


# ── Attachment handlers ──────────────────────────────────────────────────────


async def _handle_audio_attachment(message: discord.Message) -> bool:
    """Transcribe audio file attachments, route through gateway, speak back.
    Returns True if an audio attachment was found and handled."""
    _run_gw = _ctx["run_gateway"]
    ve = _ctx["ve"]
    ai_name = _ai_name()
    for att in message.attachments:
        ext = Path(att.filename).suffix.lower()
        if ext in {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".opus"}:
            async with message.channel.typing():
                tmp = tempfile.mktemp(suffix=ext)
                await att.save(tmp)
                loop = asyncio.get_event_loop()
                transcribed = await loop.run_in_executor(None, ve.transcribe, tmp)
                if transcribed:
                    await message.add_reaction("\U0001f399️")
                    _att_gid = str(message.guild.id) if message.guild else None
                    _att_cid = str(message.channel.id)
                    response = await loop.run_in_executor(
                        None,
                        lambda: _run_gw(
                            transcribed,
                            getattr(message.channel, "name", "dm"),
                            str(message.author),
                            guild_id=_att_gid,
                            channel_id=_att_cid,
                        ),
                    )
                    reply = f"\U0001f399️ **You said:** {transcribed}\n**{ai_name}:** {response}"
                    await _send_reply(message.channel, reply)
                    # Speak in voice if connected
                    if message.guild and message.guild.voice_client:
                        vc = message.guild.voice_client
                        if vc.is_connected() and not vc.is_playing():
                            audio_out = await loop.run_in_executor(
                                None, ve.speak, response[:300]
                            )
                            if audio_out and os.path.exists(audio_out):
                                import discord as _disc
                                vc.play(_disc.FFmpegPCMAudio(audio_out))
                else:
                    await message.reply("Could not transcribe that audio.")
                try:
                    Path(tmp).unlink(missing_ok=True)
                except Exception as _tmp_err:
                    _record_error("temp_audio_cleanup", _tmp_err)
            return True
    return False


async def _handle_image_attachment(message: discord.Message) -> bool:
    """Run vision analysis on image attachments.
    Returns True if an image attachment was found and handled."""
    for att in message.attachments:
        if att.content_type and att.content_type.startswith("image/"):
            async with message.channel.typing():
                try:
                    img_bytes = await att.read()
                    mime = att.content_type or "image/jpeg"
                    prompt = message.content.strip() or "Describe what you see in this image."
                    loop = asyncio.get_event_loop()
                    from substrate.execution.runtime.model_router import call_with_fallback as _vision_cwf

                    result = await loop.run_in_executor(
                        None,
                        lambda: _vision_cwf(
                            prompt=prompt,
                            task_type="multimodal",
                            images=[(img_bytes, mime)],
                        ),
                    )
                    output = result.output if hasattr(result, "output") else str(result)
                    if output:
                        await message.reply(f"\U0001f441️ {output}")
                    else:
                        await message.reply("I couldn't analyze that image right now.")
                except Exception as e:
                    _record_error("vision_analysis", e)
                    logger.warning(f"Vision analysis failed: {e}")
                    await message.reply("Vision analysis failed — try again.")
            return True
    return False


# ── Buffer handlers ──────────────────────────────────────────────────────────


async def _handle_buffer_done(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
    _ib,
    _uid: str,
    _cid_str: str,
) -> tuple[bool, str]:
    """Handle /done — finalize inbound buffer.
    Returns (handled, text).  When handled=False the caller should fall
    through to normal processing with the (possibly replaced) text."""
    bot = _bot()
    group = _ib.finalize(_uid, _cid_str)
    if group is None:
        await _send_reply(message.channel, "No active buffer to finalize.")
        await bot.process_commands(message)
        return (True, text)
    # Emit INBOUND_FINALIZED spine event
    try:
        _ib_store = _frame_get_event_store()
        _ib_event = _frame_create_event(
            _FrameEventType.INBOUND_FINALIZED,
            source="discord_inbound",
            target="eos_gateway",
            payload=group.serialize(),
            correlation_id=group.group_id,
        )
        _ib_store.append(_ib_event)
    except Exception as _ev_err:
        _record_error("event_spine_finalized", _ev_err)
    # Archive buffered inbound verbatim (logical message, not individual chunks)
    try:
        _archive_inbound(
            group.combined_text,
            interface=_ArchiveInterface.DISCORD.value,
            correlation_id=group.group_id,
            logical_message_id=group.group_id,
            metadata={
                "type": "buffered",
                "message_count": group.message_count,
                "user_id": _uid,
                "channel_id": _cid_str,
            },
        )
    except Exception as _ar_err:
        _record_error("archive_buffered", _ar_err)
    # Replace text with combined buffer and fall through to normal processing
    text = group.combined_text
    await _send_reply(
        message.channel,
        f"Buffer finalized — {group.message_count} message(s), "
        f"{group.combined_text_length} chars. Processing...",
    )
    return (False, text)


async def _handle_buffer_start(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
    _ib,
    _uid: str,
    _cid_str: str,
) -> bool:
    """Handle /buffer — start a new inbound buffer.  Always returns True (handled)."""
    bot = _bot()
    if _ib.has_active(_uid, _cid_str):
        count = _ib.get_count(_uid, _cid_str)
        await _send_reply(
            message.channel,
            f"Buffer already active — {count} message(s). "
            "Send more messages, then /done when ready.",
        )
    else:
        # Start an empty buffer — next messages will accumulate
        _ib.add(_uid, _cid_str, "")
        # Remove the empty placeholder — it was just to create the group
        _ib_key = f"{_uid}:{_cid_str}"
        with _ib._lock:
            buf = _ib._buffers.get(_ib_key)
            if buf and buf.messages == [""]:
                buf.messages.clear()
        await _send_reply(
            message.channel,
            "Buffer started. Send your messages, then /done when ready.",
        )
    await _memory_gateway(text, channel_name, username, message)
    await bot.process_commands(message)
    return True


async def _handle_buffer_accumulate(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
    _ib,
    _uid: str,
    _cid_str: str,
) -> bool:
    """Accumulate a message into an active inbound buffer.  Always returns True."""
    bot = _bot()
    group = _ib.add(_uid, _cid_str, text)
    # Emit INBOUND_RECEIVED spine event
    try:
        _ib_store = _frame_get_event_store()
        _ib_event = _frame_create_event(
            _FrameEventType.INBOUND_RECEIVED,
            source="discord_inbound",
            target="buffer",
            payload={
                "group_id": group.group_id,
                "user_id": _uid,
                "channel_id": _cid_str,
                "message_index": group.message_count,
                "text_length": len(text),
            },
            correlation_id=group.group_id,
        )
        _ib_store.append(_ib_event)
    except Exception as _ev2_err:
        _record_error("event_spine_received", _ev2_err)
    count = group.message_count
    await message.add_reaction("\U0001f4dd")
    if count % 3 == 0:
        await _send_reply(
            message.channel,
            f"Buffered {count} messages. Send /done when ready.",
        )
    await _memory_gateway(text, channel_name, username, message)
    await bot.process_commands(message)
    return True


# ── Day ritual handler ───────────────────────────────────────────────────────


async def _handle_day_ritual(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
    day_cmd: str,
) -> bool:
    """Execute a day open/close ritual.  Always returns True (handled)."""
    _run_day_cmd = _ctx["run_day_command"]
    _fmt_day = _ctx["format_day_result"]
    _send_day = _ctx["send_day_response"]
    async with message.channel.typing():
        loop = asyncio.get_event_loop()
        _day_result = await loop.run_in_executor(
            None,
            lambda cmd=day_cmd: _run_day_cmd(
                cmd,
                discord_channel_id=str(message.channel.id),
            ),
        )
        _day_text = _fmt_day(_day_result)
        await _send_day(message.channel, _day_text)
    await _memory_gateway(text, channel_name, username, message)
    return True


# ── Onboarding handler ──────────────────────────────────────────────────────


async def _handle_onboarding(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
) -> bool:
    """Route through active onboarding session.
    Returns True if an active onboarding session consumed the message."""
    _onboarding = _ctx["onboarding"]
    DiscordServerManager = _ctx["DiscordServerManager"]
    if not message.guild:
        return False
    _ob_session = _onboarding.get_session(str(message.guild.id))
    if not _ob_session or _ob_session.completed:
        return False

    # Store answer to the last question asked
    if _ob_session.pending_question:
        _onboarding.store_answer(_ob_session, text)

    next_q = _onboarding.get_next_question(_ob_session)

    if next_q:
        await _send_reply(message.channel, next_q)
    else:
        # All questions answered — provision
        await _send_reply(message.channel, "⚙️ **Provisioning your EOS...**")
        try:
            provision_result = await _onboarding.analyze_and_provision(_ob_session)

            # Discord structure (handled here — engine can't import bot)
            try:
                mgr = DiscordServerManager(message.guild)
                await mgr.setup_eos_structure()
                await mgr.align_structure()
                provision_result["results"]["discord"] = "provisioned"
                print("[Onboarding] Discord structure provisioned")
            except Exception as _de:
                _record_error("onboarding_discord_provision", _de)
                provision_result["results"]["discord"] = f"error: {_de}"

            completion = _onboarding.get_completion_message(
                provision_result["data"],
                provision_result["results"],
            )
            await _send_reply(message.channel, completion)
        except Exception as _pe:
            _record_error("onboarding_provision", _pe)
            print(f"[Onboarding] Provisioning error: {_pe}")
            await _send_reply(
                message.channel,
                f"⚠️ Provisioning encountered an issue: {_pe}\n"
                "Run `!onboard` again to retry.",
            )
    await _memory_gateway(text, channel_name, username, message)
    return True


# ── Orchestration ingress handler ────────────────────────────────────────────


async def _handle_orchestration_ingress(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
    _uid: str,
    _cid_str: str,
) -> bool:
    """Route through substrate orchestration layer (mode-gated).
    Returns True if orchestration accepted the message."""
    bot = _bot()
    _orch_handled = False
    try:
        from substrate.execution.bridge.discord_ingress_adapter import ingest_and_emit

        _orch_result = ingest_and_emit(
            text=text,
            user_id=_uid,
            channel_id=_cid_str,
            guild_id=str(message.guild.id) if message.guild else "",
            channel_name=channel_name,
        )
        if _orch_result.accepted:
            _orch_handled = True
            print(
                f"[Orchestration] Ingested: intent_type={_orch_result.intent_type} "
                f"event_id={_orch_result.intent_id}",
                flush=True,
            )
            # Structured trace reply (best-effort)
            try:
                from substrate.execution.bridge.operator_trace import (
                    OperatorTrace,
                    format_trace_for_discord,
                )

                _orch_trace = OperatorTrace(
                    ingress_source="discord_ingress_adapter",
                    ingress_transport="discord_text",
                    ingress_text=text[:200],
                    operator_id=_uid,
                    intent_type=_orch_result.intent_type,
                    intent_id=_orch_result.intent_id,
                    intent_status="accepted",
                )
                _trace_text = format_trace_for_discord(_orch_trace)
                await _send_reply(message.channel, _trace_text)
            except Exception as _trace_err:  # noqa: BLE001
                _record_error("orchestration_trace", _trace_err)
                print(f"[Orchestration] trace format error: {_trace_err}", flush=True)
    except Exception as _orch_err:  # noqa: BLE001
        _record_error("orchestration_ingress", _orch_err)
        print(f"[Orchestration] ingress error: {_orch_err}", flush=True)

    if _orch_handled:
        await _memory_gateway(text, channel_name, username, message)
        await bot.process_commands(message)
        return True

    return False


# ── CC injection handler (dormant) ───────────────────────────────────────────


async def _handle_cc_injection(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
) -> bool:
    """Session-first CC injection.
    DORMANT: session_registry, session_router, surface_registry,
    live_loop, input_router modules do not exist yet.
    This block will activate when runtime/ is fully built.
    Returns True if CC injection consumed the message."""
    bot = _bot()
    _cc_injected = False

    if _cc_injected:
        await _memory_gateway(text, channel_name, username, message, prefix="[CC Session] ")
        await bot.process_commands(message)
        return True

    return False


# ── PseudoLive handler ───────────────────────────────────────────────────────


async def _handle_pseudolive(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
) -> bool:
    """PseudoLive fallback — full pipeline via gateway/model_router.
    Fires only when CC injection failed (session missing, tmux down, etc).
    Returns True if PseudoLive handled the message (caller should return)."""
    try:
        _pl_result = _maybe_pseudo_live_text(
            text,
            guild_id=str(message.guild.id) if message.guild else None,
            channel_id=str(message.channel.id),
            user_id=str(message.author.id),
        )
    except Exception as _ple:  # noqa: BLE001
        _record_error("pseudolive_hook", _ple)
        print(f"[PseudoLive] hook error: {_ple}")
        _pl_result = None

    if _pl_result is None:
        return False

    _pl_ingress = _pl_result.get("ingress") or {}
    _pl_env = _pl_result.get("envelope") or {}
    _pl_status = _pl_ingress.get("status")
    if _pl_status in ("disabled", "gate_denied"):
        return False

    # Transport was active — NEVER fall through to gateway/Gemini.
    if _pl_env.get("status") == "ok":
        _pl_plan = _pl_env.get("emit_plan") or [
            {
                "content": _pl_env.get("content", ""),
                "tts": False,
                "role": "combined",
            }
        ]
        _visible_content = ""
        for _pl_entry in _pl_plan:
            _role = _pl_entry.get("role", "combined")
            if _role == "spoken":
                continue
            _entry_content = (_pl_entry.get("content") or "").strip()
            if _entry_content:
                _visible_content = _entry_content
                break
        _pl_delivery_ok = False
        if _visible_content:
            try:
                _pl_delivery_ok = await _send_reply(message.channel, _visible_content)
            except Exception as _se:  # noqa: BLE001
                _record_error("pseudolive_send", _se)
                print(f"[PseudoLive] send failed: {_se}")

        # ── Post-delivery finalization ───────────────────────
        _pl_fin = _pl_result.get("finalization_ready") or {}
        if _pl_fin.get("should_finalize"):
            _pl_terminal = False
            try:
                from substrate.execution.bridge.run_lifecycle import (
                    is_run_terminally_finalized as _pl_term_check,
                )

                _pl_session_check = _pl_fin.get("source_session", "")
                if _pl_session_check and _pl_term_check(_pl_session_check):
                    print(
                        f"[PseudoLive] Late finalization dropped: "
                        f"session={_pl_session_check} — terminally finalized"
                    )
                    _pl_terminal = True
            except Exception as _lc_err:
                _record_error("pseudolive_lifecycle_check", _lc_err)

            if not _pl_terminal:
                try:
                    _pl_session = _pl_fin.get("source_session", "")
                    from substrate.execution.bridge.run_lifecycle import (
                        propose_run_completion as _pl_propose,
                    )

                    _pl_proposal = _pl_propose(
                        _pl_session,
                        "pseudolive",
                        payload={
                            "delivery_ok": _pl_delivery_ok,
                            "correlation_id": _pl_fin.get("correlation_id", ""),
                        },
                    )
                    if not _pl_proposal.accepted:
                        print(f"[PseudoLive] Proposal rejected: {_pl_proposal.reason}")
                    else:
                        from substrate.execution.bridge.task_finalization import (
                            finalize_completed_task as _pl_finalize,
                        )

                        _pl_fin_result = _pl_finalize(
                            delivery_success=_pl_delivery_ok,
                            delivery_mode="pseudolive",
                            source_session=_pl_session,
                            role=_pl_fin.get("role", ""),
                            interface="discord",
                            final_output=(_visible_content or "")[:2000],
                            clear_target=_pl_fin.get("clear_target", "vps"),
                            correlation_id=_pl_fin.get("correlation_id", ""),
                            auto_clear=_pl_fin.get("should_clear") or None,
                        )
                        if _pl_fin_result.clear_executed:
                            print("[PseudoLive] Auto-clear executed")
                except Exception as _fin_e:  # noqa: BLE001
                    _record_error("pseudolive_finalization", _fin_e)
                    print(f"[PseudoLive] finalization failed: {_fin_e}")

        _deferred = _pl_result.get("deferred_tts") or {}
        _tts_node = _deferred.get("node_id")
        _tts_text = _deferred.get("spoken_text") or ""
        _tts_role = _deferred.get("role_slug") or "ea_orchestrator"
        if _tts_node and _tts_text:
            try:
                from substrate.execution.bridge.station_helpers import propose_speak_text

                propose_speak_text(
                    _tts_node,
                    _tts_text,
                    issued_by=f"discord_text:{_tts_role}",
                )
            except Exception as _te:  # noqa: BLE001
                _record_error("pseudolive_tts", _te)
                print(f"[PseudoLive] deferred TTS failed: {_te}")
    else:
        print(
            f"[PseudoLive] CC session failed: status={_pl_status} "
            f"detail={_pl_ingress.get('detail', '')}"
        )
    await _memory_gateway(text, channel_name, username, message, prefix="[CC Session] ")
    return True


# ── Meeting mode handler ─────────────────────────────────────────────────────


async def _handle_meeting_trigger(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
) -> bool:
    """Detect meeting start/end triggers.
    Returns True if a meeting trigger was matched."""
    start_meeting_mode = _ctx["start_meeting_mode"]
    end_active_meeting = _ctx["end_active_meeting"]
    # Start meeting
    meeting_match = re.search(
        r"(?:start|begin|kick off|starting)\s+"
        r"(?:a\s+)?(?:meeting|call|session|review)"
        r"(?:\s+with\s+(\w+))?",
        text,
        re.IGNORECASE,
    )
    if meeting_match:
        lead = meeting_match.group(1) or ""
        await start_meeting_mode("sales_call", lead, message.channel)
        await _memory_gateway(text, channel_name, username, message)
        return True

    # End meeting
    if any(
        p in text.lower()
        for p in [
            "end the meeting",
            "end meeting",
            "wrap up",
            "meeting over",
            "call done",
            "done with the call",
        ]
    ):
        await end_active_meeting(message.channel)
        await _memory_gateway(text, channel_name, username, message)
        return True

    return False


# ── Pending capture resolution handler ───────────────────────────────────────


async def _handle_pending_capture(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
) -> bool:
    """Handle venture selection (1/2/3) for a pending capture.
    Returns True if a pending capture was resolved."""
    default_venture_id = _ctx["default_venture_id"]
    _channel_id = str(message.channel.id)
    if _channel_id not in _pending_captures:
        return False
    if text.strip() not in ("1", "2", "3", "1️⃣", "2️⃣", "3️⃣"):
        return False

    _pending = _pending_captures.pop(_channel_id)
    import json as _json

    _ventures_list = _json.loads(os.getenv("VENTURES_JSON", "[]"))
    _venture_map = {str(i + 1): v["id"] for i, v in enumerate(_ventures_list)}
    _venture_id = _venture_map.get(
        text.strip().replace("️⃣", ""), default_venture_id
    )
    try:
        from substrate.understanding.signals.founder_capture import capture

        capture(_pending["text"], venture_id=_venture_id)
        _icon = "\U0001f4a1" if _pending["type"] == "idea" else "✅"
        await _send_reply(message.channel, f"{_icon} Added to your list.")
    except Exception as _cap_err:
        _record_error("founder_capture_resolve", _cap_err, {"venture_id": _venture_id})
    await _memory_gateway(_pending["text"], channel_name, username, message)
    return True


# ── Pipeline update handler ──────────────────────────────────────────────────


async def _handle_pipeline_update_check(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
) -> bool:
    """Delegate to the pipeline_handler module.
    Returns True if a pipeline update was detected and handled."""
    if await handle_pipeline_update(message, text):
        await _memory_gateway(text, channel_name, username, message)
        return True
    return False


# ── Founder capture handler ──────────────────────────────────────────────────


async def _handle_founder_capture(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
) -> bool:
    """Detect tasks/ideas and write to founder's list + Notion.
    Returns True only when an ambiguous capture needs venture disambiguation
    (early return required).  Non-ambiguous captures are silent side-effects
    that do NOT prevent fall-through."""
    default_venture_id = _ctx["default_venture_id"]
    try:
        from substrate.understanding.signals.founder_capture import should_capture, capture

        _should, _ctype = should_capture(text)
        if _should:
            _text_lower = text.lower()
            if any(
                w in _text_lower
                for w in [
                    "empyrean",
                    "b2b",
                    "ai infrastructure",
                    "entrepreneuros",
                    "saas",
                ]
            ):
                _venture_id = "empyrean_creative"
            elif any(
                w in _text_lower
                for w in ["brand", "twitch", "content", "vigilante", "personal brand"]
            ):
                _venture_id = "personal_brand"
            elif any(
                w in _text_lower
                for w in [
                    "lyfe",
                    "initiate",
                    "arena",
                    "coaching",
                    "instagram dm",
                    "men 18",
                ]
            ):
                _venture_id = "lyfe_institute"
            else:
                # Ambiguous — ask before capturing
                import json as _json

                _channel_id = str(message.channel.id)
                _ventures_list = _json.loads(os.getenv("VENTURES_JSON", "[]"))
                _num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
                _choices = "  ".join(
                    f"{_num_emojis[i]} {v['name']}"
                    for i, v in enumerate(_ventures_list)
                    if i < len(_num_emojis)
                )
                await _send_reply(
                    message.channel,
                    f"{'\U0001f4a1' if _ctype == 'idea' else '✅'} Got it. Which venture is this for?\n"
                    f"{_choices}",
                )
                _pending_captures[_channel_id] = {"text": text, "type": _ctype}
                await _memory_gateway(text, channel_name, username, message)
                return True  # early return — waiting for venture selection

            _capture_result = capture(text, venture_id=_venture_id)
            if _capture_result.get("captured"):
                _icon = "\U0001f4a1" if _ctype == "idea" else "✅"
                await _send_reply(message.channel, f"{_icon} Added to your list.")
    except Exception as _cap2_err:
        _record_error("founder_capture", _cap2_err)

    return False  # fall through — capture was a side-effect


# ── Multi-part accumulation handler ──────────────────────────────────────────


async def _handle_multipart(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
) -> tuple[bool, str]:
    """Handle Part N/M message accumulation.
    Returns (handled, text).  When handled=True, caller should return.
    When handled=False, text may have been replaced with assembled parts."""
    bot = _bot()
    _run_gw = _ctx["run_gateway"]
    _send_resp = _ctx["send_response"]
    part_info = _detect_part(text)
    if not part_info:
        return (False, text)

    part_num, total_parts = part_info
    ch_key = channel_name

    # Initialise or reset buffer if this is a new series
    if (
        ch_key not in _multipart_buffers
        or _multipart_buffers[ch_key].get("total") != total_parts
    ):
        _multipart_buffers[ch_key] = {
            "parts": {},
            "total": total_parts,
            "username": username,
        }

    _multipart_buffers[ch_key]["parts"][part_num] = text

    # Cancel any existing timeout task for this channel
    if ch_key in _multipart_flush_tasks:
        _multipart_flush_tasks[ch_key].cancel()
        _multipart_flush_tasks.pop(ch_key, None)

    if part_num < total_parts:
        # Not the last part — acknowledge and wait
        await message.add_reaction("⏳")

        async def _flush_after_timeout(
            chan_key: str,
            chan: discord.abc.Messageable,
            orig_message: discord.Message,
            cname: str,
            uname: str,
        ) -> None:
            await asyncio.sleep(30)
            buf = _multipart_buffers.pop(chan_key, None)
            if not buf:
                return
            combined = _assemble_parts(buf)
            _fl_gid = str(orig_message.guild.id) if orig_message.guild else None
            _fl_cid = str(orig_message.channel.id)
            async with chan.typing():
                ev_loop = asyncio.get_event_loop()
                out = await ev_loop.run_in_executor(
                    None,
                    lambda: _run_gw(
                        combined, cname, uname, guild_id=_fl_gid, channel_id=_fl_cid
                    ),
                )
            if out:
                await _send_resp(orig_message, out)

        task = asyncio.create_task(
            _flush_after_timeout(
                ch_key,
                message.channel,
                message,
                channel_name,
                username,
            )
        )
        _multipart_flush_tasks[ch_key] = task
        await bot.process_commands(message)
        return (True, text)

    else:
        # Final part — assemble and fall through to normal processing
        buf = _multipart_buffers.pop(ch_key, None)
        if buf:
            text = _assemble_parts(buf)
        return (False, text)


# ── Inline command handler ───────────────────────────────────────────────────


async def _handle_inline_commands(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
) -> bool:
    """Delegate to cc_command_handler.try_inline_commands.
    Returns True if an inline command was handled."""
    if await try_inline_commands(message, text, _pending_events):
        await _memory_gateway(text, channel_name, username, message)
        return True
    return False


# ── Gateway dispatch handler ─────────────────────────────────────────────────


async def _handle_gateway_dispatch(
    message: discord.Message,
    text: str,
    channel_name: str,
    username: str,
) -> None:
    """Route through EOS gateway and send the response.  Terminal handler."""
    bot = _bot()
    _run_gw = _ctx["run_gateway"]
    _send_resp = _ctx["send_response"]
    ve = _ctx["ve"]
    ai_name = _ai_name()
    founder_id = _ctx["founder_id"]
    _gid = str(message.guild.id) if message.guild else None
    _cid = str(message.channel.id)
    async with message.channel.typing():
        loop = asyncio.get_event_loop()

        output = await loop.run_in_executor(
            None,
            lambda: _run_gw(text, channel_name, username, guild_id=_gid, channel_id=_cid),
        )

    if output:
        # Determine if founder is in a voice channel before responding
        founder_in_voice = False
        founder_member = None
        try:
            if message.guild and message.author.id == founder_id:
                founder_member = message.guild.get_member(founder_id)
                if founder_member and founder_member.voice and founder_member.voice.channel:
                    founder_in_voice = True
        except Exception as _fv_err:
            _record_error("founder_voice_check", _fv_err)

        # Always post text response
        await _send_resp(message, output)

        if founder_in_voice:
            # Also speak via TTS in voice channel
            try:
                import discord as _disc
                vc = message.guild.voice_client
                if not vc or not vc.is_connected():
                    vc = await founder_member.voice.channel.connect(
                        timeout=10.0,
                        reconnect=False,
                    )
                audio_path = await asyncio.get_event_loop().run_in_executor(
                    None, ve.speak, output[:300]
                )
                if audio_path and os.path.exists(audio_path):
                    while vc.is_playing():
                        await asyncio.sleep(0.3)

                    def cleanup(error):
                        try:
                            os.remove(audio_path)
                        except Exception as _cl_err:
                            _record_error("tts_audio_cleanup", _cl_err)

                    vc.play(
                        _disc.FFmpegPCMAudio(audio_path),
                        after=cleanup,
                    )
                    print(f"[Voice] Speaking: {output[:50]}...")
            except Exception as e:
                _record_error("voice_tts", e)
                print(f"[Voice] TTS check: {e}")

    await bot.process_commands(message)
