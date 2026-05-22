"""
EntrepreneurOS Discord Bot — DEX conversational layer.

Auto-joins founder's voice channel. Routes text through EOS gateway.
Smart routing: simple → local Qwen (free) → Claude via EOS.
AI name is user-configurable via BIS or AI_NAME env var.

Channel map (create these in your server):
  🧠 EOS:
    #general           — freeform conversation with DEX
    #morning-brief     — daily brief (auto-posted at 6am)
    #decisions         — decisions queue
    #wins              — closed deals and wins
    #agent-activity    — EOS agent log
  ⚡ Empyrean Creative:
    #empyrean-strategy — strategy
    #empyrean-pipeline — sales pipeline
    #empyrean-outreach — outreach tracking
  🏢 Lyfe Institute:
    #lyfe-strategy     — strategy
    #lyfe-pipeline     — Initiate Arena pipeline
    #lyfe-outreach     — Instagram DM tracking
  👤 Personal Brand:
    #brand-strategy    — brand strategy
    #content-ideas     — content ideas and calendar

Setup:
  1. discord.com/developers/applications → New Application
  2. Bot section → Add Bot → copy token
  3. Enable: Message Content Intent, Server Members Intent, Presence Intent
  4. OAuth2 → URL Generator → scopes: bot
     Permissions: Send Messages, Read Message History, Add Reactions,
                  Connect (voice), Speak (voice), Use Slash Commands
  5. Invite bot to your server
  6. Fill DISCORD_BOT_TOKEN, FOUNDER_DISCORD_ID, and channel IDs in .env
  7. docker compose up -d os-discord
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)
import re
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


# ─── Asyncio-level voice task exception suppressor ────────────────────────────
# on_error only catches event handler exceptions — Task exceptions (like the
# _MissingSentinel crash from poll_voice_ws) bypass it entirely. This handler
# intercepts them at the event loop level before they kill the process.


def _handle_task_exception(loop, context):
    exception = context.get("exception")
    if exception:
        msg = str(exception)
        if "_MissingSentinel" in msg or "poll_event" in msg or "poll_voice_ws" in msg:
            return  # silently ignore voice WS errors
    loop.default_exception_handler(context)


import discord
from discord.ext import commands
import wave
import time
from discord.sinks import Sink as AudioSink

# ─── Path bootstrap ───────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPT_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from dotenv import load_dotenv

load_dotenv(_SCRIPT_DIR / ".env")
load_dotenv(_REPO_ROOT / "runtime" / ".env")

# ─── EOS imports ──────────────────────────────────────────────────────────────

# Pin top-level runtime before control_plane.runtime shadows the name
import importlib.util as _ilu

_rt_spec = _ilu.find_spec("runtime", [str(_REPO_ROOT)])
if _rt_spec and "runtime" not in sys.modules:
    _rt_mod = _ilu.module_from_spec(_rt_spec)
    sys.modules["runtime"] = _rt_mod
    if _rt_spec.submodule_search_locations:
        _rt_mod.__path__ = list(_rt_spec.submodule_search_locations)
    if _rt_spec.loader:
        _rt_spec.loader.exec_module(_rt_mod)

from control_plane.runtime.gateway import EntrepreneurOSGateway
from state.context.context import load_context_from_env
from understanding.knowledge.knowledge_integrator import KnowledgeIntegrator
from execution.voice.voice_engine import VoiceEngine
from state.business.business_instance import get_ai_name
from interface.discord.discord_utils import chunk_message, post_to_webhook
from execution.transport.session_discord_bridge import send_reply as _send_reply
from execution.transport.discord_text_transport import (
    maybe_mirror_discord_text_message as _maybe_pseudo_live_text,
)

# Graceful import for substrate modules that may not exist yet
try:
    from execution.transport.message_framing import get_inbound_buffer
except ImportError:
    get_inbound_buffer = None

from execution.transport.event_spine import (
    EventType as _FrameEventType,
    create_event as _frame_create_event,
)

try:
    from execution.transport.event_store import get_event_store as _frame_get_event_store
except ImportError:
    _frame_get_event_store = None

try:
    from execution.transport.interaction_archive import (
        archive_inbound as _archive_inbound,
        Interface as _ArchiveInterface,
    )
except ImportError:
    _archive_inbound = None
    _ArchiveInterface = None

# Install the router-backed voice-session responder at import time so that
# every Discord pseudo-live text ingress (which flows through
# inject_transcript → VoiceSessionRuntime.submit_utterance → global responder)
# routes through runtime.model_router.call_with_fallback instead of the
# substrate's default "[role] heard: ..." stub. Idempotent; safe to call
# multiple times. The substrate architecture is preserved — we are only
# replacing the pluggable responder hook the substrate already exposes.
try:
    from execution.transport.voice_eos_responder import (
        install_default_eos_voice_responder as _install_voice_router_responder,
        is_eos_voice_responder_installed as _is_voice_router_responder_installed,
    )

    if not _is_voice_router_responder_installed():
        _install_voice_router_responder()
        print(
            "[Discord] voice-session responder = router-backed "
            "(runtime.voice_eos_responder → model_router.call_with_fallback)",
            flush=True,
        )
    else:
        print(
            "[Discord] voice-session responder already router-backed",
            flush=True,
        )
except Exception as _voice_responder_install_err:  # noqa: BLE001
    print(
        f"[Discord] WARNING: failed to install router-backed voice responder: "
        f"{_voice_responder_install_err} — Discord pseudo-live will echo stub",
        flush=True,
    )

# ─── Handler imports ─────────────────────────────────────────────────────────

from interface.presence.handlers.intent_handler import run_gateway as _handler_run_gateway
from interface.presence.handlers.intent_handler import CHANNEL_MAP as _HANDLER_CHANNEL_MAP
from interface.presence.handlers.pipeline_handler import handle_pipeline_update
from interface.presence.handlers.cc_command_handler import try_inline_commands
from interface.presence.handlers.substrate_command_handler import (
    handle_substrate_command,
    is_substrate_command,
    log_startup as _substrate_log_startup,
)

# ─── Initialise ───────────────────────────────────────────────────────────────

_ctx_eos = load_context_from_env()
_gateway = EntrepreneurOSGateway()  # singleton — no ctx arg
_ki = KnowledgeIntegrator(_ctx_eos)
_ve = VoiceEngine()

from control_plane.onboarding.onboarding_engine import OnboardingEngine as _OnboardingEngine

_onboarding = _OnboardingEngine(_ctx_eos)

# Resolve AI name — refreshed on_ready so renames take effect on reconnect
AI_NAME = get_ai_name(_ctx_eos)

# Default venture for requests that don't specify one
_DEFAULT_VENTURE_ID = _ctx_eos.active_venture_id or os.getenv(
    "DEFAULT_VENTURE_ID", "lyfe_institute"
)

# Founder Discord user ID — bot auto-joins founder's voice channel
FOUNDER_ID = int(os.getenv("FOUNDER_DISCORD_ID", "0"))

# Channel sessions — one persistent session_id per channel
# Preserves conversation continuity within each channel across messages
_channel_sessions: dict[str, str] = {}

# ─── Multi-part message accumulation ─────────────────────────────────────────
# When founder sends Part 1/2, Part 2/2 etc., accumulate before processing.
_multipart_buffers: dict[str, dict] = {}
# channel -> {'parts': {1: text, 2: text, ...}, 'total': N, 'username': str}
_multipart_flush_tasks: dict[str, "asyncio.Task"] = {}

# ─── Pending captures (venture disambiguation) ───────────────────────────────
# When a task/idea is ambiguous, we store it here and ask the founder which venture.
# channel_id -> {'text': str, 'type': str}
_pending_captures: dict[str, dict] = {}

# ─── Pending events (calendar conflict confirmation) ─────────────────────────
# When a conflict is detected, we store the parsed event here for confirmation.
# channel_id -> parsed event dict
_pending_events: dict[str, dict] = {}

_PART_RE_WORD = re.compile(r"(?i)\bpart\s+(\d+)\s*/\s*(\d+)\b")  # "Part 1/2"
_PART_RE_START = re.compile(r"(?im)^(\d+)\s*/\s*(\d+)\s*[:\-\s]")  # "1/2:" at line start


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


# ─── Silence-detecting voice sink ─────────────────────────────────────────────


class SilenceDetectingSink(AudioSink):
    def __init__(self, on_utterance, silence_threshold: float = 1.5):
        super().__init__()
        self.on_utterance = on_utterance
        self.silence_threshold = silence_threshold
        self._buffers = {}
        self._last_audio = {}
        self._running = True

    def write(self, data, user):
        if user is None:
            return
        uid = user  # user is already an int user_id
        if uid not in self._buffers:
            self._buffers[uid] = []
        self._buffers[uid].append(bytes(data))  # data is decoded PCM bytes
        self._last_audio[uid] = time.time()

    def cleanup(self):
        self._running = False
        self.finished = True  # prevent base-class format_audio crash

    async def monitor_silence(self, vc):
        while self._running and vc.is_connected():
            await asyncio.sleep(0.3)
            now = time.time()
            to_flush = [
                uid
                for uid, t in list(self._last_audio.items())
                if now - t >= self.silence_threshold and self._buffers.get(uid)
            ]
            for uid in to_flush:
                frames = self._buffers.pop(uid, [])
                self._last_audio.pop(uid, None)
                if frames:
                    audio_path = tempfile.mktemp(suffix=".wav")
                    with wave.open(audio_path, "wb") as wf:
                        wf.setnchannels(2)  # Discord: stereo
                        wf.setsampwidth(2)  # 16-bit samples
                        wf.setframerate(48000)  # 48 kHz
                        wf.writeframes(b"".join(frames))
                    asyncio.create_task(self.on_utterance(uid, audio_path))


def transcribe_with_groq(audio_path: str) -> str:
    try:
        from groq import Groq as GroqClient

        client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
                language="en",
            )
        text = result.text.strip()
        print(f"[Groq STT] Transcribed: {text[:50]}")
        return text
    except Exception as e:
        print(f"[Groq STT] Error: {e}")
        return ""


# ─── Channel IDs ──────────────────────────────────────────────────────────────
CHANNEL_IDS: dict[str, int] = {
    "morning-brief": 1485765524766982234,
    "general": 1486289444830056540,
    "decisions": 1485765720775200808,
    "wins": 1485765745312010260,
    "agent-activity": 1486267275857235999,
    "empyrean-strategy": 1486267278239731823,
    "empyrean-pipeline": 1486267279028129863,
    "empyrean-outreach": 1486267280311586896,
    "lyfe-strategy": 1486267281901092976,
    "lyfe-pipeline": 1486267283373293568,
    "lyfe-outreach": 1486267284681920546,
    "brand-strategy": 1486267286309441566,
    "content-ideas": 1486267286913417278,
}

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

# ─── Day ritual helpers ───────────────────────────────────────────────────────

_OPEN_DAY_PHRASES = [
    r"start my day",
    r"open day",
    r"open my day",
    r"open session",
]

_CLOSE_DAY_PHRASES = [
    r"close day",
    r"end my day",
    r"close my day",
    r"close session",
    r"eod",
]

_OPEN_EXACT = [r"good morning"]
_CLOSE_EXACT = [r"good night"]

_OPEN_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_OPEN_DAY_PHRASES) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_CLOSE_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_CLOSE_DAY_PHRASES) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_OPEN_EXACT_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_OPEN_EXACT) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_CLOSE_EXACT_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_CLOSE_EXACT) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)


def _detect_day_command(text: str) -> str | None:
    if text.startswith("!"):
        return None
    if _OPEN_PATTERN.match(text):
        return "open_day"
    if _CLOSE_PATTERN.match(text):
        return "close_day"
    if _OPEN_EXACT_PATTERN.match(text):
        return "open_day"
    if _CLOSE_EXACT_PATTERN.match(text):
        return "close_day"
    return None


def _run_day_command(
    cmd: str,
    *,
    workspace: str | None = None,
    node_preference: str | None = None,
    discord_channel_id: str | None = None,
    continuity_text: str | None = None,
) -> dict:
    try:
        from execution.transport.day_workflows import close_day, open_day

        if cmd == "open_day":
            return open_day(
                workspace=workspace,
                node_preference=node_preference,
                discord_channel_id=discord_channel_id,
            )
        elif cmd == "close_day":
            return close_day(
                continuity_notes=continuity_text,
                discord_channel_id=discord_channel_id,
            )
        else:
            return {"status": "error", "detail": f"unknown command: {cmd}"}
    except Exception as e:
        print(f"[DayRitual] error in {cmd}: {e}")
        return {"status": "error", "detail": str(e)}


def _format_day_result(result: dict) -> str:
    status = result.get("status", "error")

    if status == "already_open":
        ws = result.get("active_workspace", "unknown")
        mode = result.get("day_mode", "unknown")
        opened = result.get("opened_at", "unknown")
        return f"Day is already open.\nWorkspace: {ws} | Mode: {mode} | Opened: {opened}"

    if status == "not_open":
        return "No day is currently open. Use `start my day` or `!openday` first."

    if status == "error":
        return f"Day ritual error: {result.get('detail', 'unknown')}"

    # open_day ok
    if "briefing" in result:
        b = result["briefing"]
        mode = result.get("day_mode", "unknown")
        ws = result.get("active_workspace", "unknown")
        left_off = b.get("where_we_left_off") or "Fresh start."
        priorities = b.get("unfinished_priorities") or []
        overnight = b.get("overnight_tasks") or []
        first_action = b.get("recommended_first_action") or "Check your priorities."
        resume = b.get("resume_context")
        lines = [
            f"**Day Open** — {mode}",
            f"Workspace: {ws} | Node: {result.get('node_preference', 'auto')}",
            "",
            f"**Where we left off:**\n{left_off}",
            "",
        ]
        if priorities:
            lines.append("**Unfinished priorities:**")
            for p in priorities:
                lines.append(f"- {p}")
        else:
            lines.append("**Unfinished priorities:**\nNone.")
        lines.append("")
        if overnight:
            lines.append("**Overnight tasks:**")
            for t in overnight:
                lines.append(f"- {t}")
        else:
            lines.append("**Overnight tasks:**\nNone.")
        lines.append("")
        lines.append(f"**Recommended first action:**\n{first_action}")
        if resume:
            lines.append(f"\n**Resume context:**\n{resume}")
        warning = result.get("ritual_warning")
        if warning:
            lines.append(f"\n_Ritual warning: {warning}_")
        return "\n".join(lines)

    # close_day ok
    if "summary" in result:
        s = result["summary"]
        completed = s.get("completed_today") or []
        unresolved = s.get("unresolved") or []
        overnight = s.get("overnight_tasks") or []
        notes = s.get("continuity_notes")
        mode = s.get("day_mode", "inactive")
        lines = [f"**Day Closed** — {mode}", ""]
        if completed:
            lines.append("**Completed today:**")
            for c in completed:
                lines.append(f"- {c}")
        else:
            lines.append("**Completed today:**\nNothing logged.")
        lines.append("")
        if unresolved:
            lines.append("**Unresolved:**")
            for u in unresolved:
                lines.append(f"- {u}")
        else:
            lines.append("**Unresolved:**\nAll clear.")
        lines.append("")
        if overnight:
            lines.append("**Overnight tasks:**")
            for t in overnight:
                lines.append(f"- {t}")
        else:
            lines.append("**Overnight tasks:**\nNone.")
        if notes:
            lines.append(f"\n**Continuity notes:**\n{notes}")
        warning = result.get("ritual_warning")
        if warning:
            lines.append(f"\n_Ritual warning: {warning}_")
        return "\n".join(lines)

    return f"Day ritual completed with status: {status}"


async def _send_day_response(invoking_channel, formatted_text: str) -> None:
    await _send_reply(invoking_channel, formatted_text)
    # Best-effort mirror to #morning-brief
    try:
        _mb_id = CHANNEL_IDS.get("morning-brief")
        if _mb_id and str(invoking_channel.id) != str(_mb_id):
            _mb_chan = bot.get_channel(_mb_id)
            if _mb_chan:
                await _send_reply(_mb_chan, formatted_text)
    except Exception as _mirror_exc:
        print(f"[DayRitual] mirror to #morning-brief failed: {_mirror_exc}")


# ─── Active meeting state ─────────────────────────────────────────────────────

_active_meeting: dict = {
    "type": None,  # 'sales_call', 'strategy_session', etc.
    "lead_name": None,
    "started_at": None,
    "notes": [],  # raw utterances captured
    "key_points": [],  # AI-extracted insights
}

# ─── Intent → gateway request type mapping ───────────────────────────────────

_INTENT_TO_TEAM: dict[str, tuple[str | None, str | None]] = {
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

# ─── Bot setup ────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.presences = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
)

# Guard: don't attempt voice connects before on_ready fires.
# on_voice_state_update can fire during gateway resume before the bot
# is fully initialised — connecting to voice in that window causes a
# _MissingSentinel / poll_event crash.
_bot_ready: bool = False


# ─── Global error handler ─────────────────────────────────────────────────────


@bot.event
async def on_error(event, *args, **kwargs):
    """Prevent voice WS errors from killing the bot process."""
    err = traceback.format_exc()
    if "_MissingSentinel" in err or "poll_voice_ws" in err:
        print("[Voice] WS error caught — ignoring")
        return
    print(f"[Bot] Error in {event}: {err}")


# ─── Gateway routing ──────────────────────────────────────────────────────────


def _build_request(text: str, intent: str, channel_name: str, username: str) -> dict:
    """Build a valid EntrepreneurOSGateway request dict from classified intent."""
    if intent == "BRIEF":
        # Only trigger the full brief dump if explicitly requested
        # Otherwise route through cognitive loop — soul doc governs response
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
        # Casual or ambiguous — let the cognitive loop handle it
        return {
            "type": "agent_task",
            "prompt": text,
            "username": username,
            "venture_id": _DEFAULT_VENTURE_ID,
            "task_type": "ANALYZE",
        }

    if intent == "PORTFOLIO":
        return {"type": "status", "prompt": text, "username": username}

    team, sub_agent = _INTENT_TO_TEAM.get(intent, (None, None))
    req: dict = {
        "type": "agent_task",
        "prompt": text,
        "username": username,
        "venture_id": _DEFAULT_VENTURE_ID,
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


def _detect_pipeline_update(text: str) -> tuple[str, str] | None:
    """
    Detect natural language pipeline stage updates.
    Returns (stage, lead_hint) or None if not a pipeline update.

    Examples:
      "just closed that lead" → ("Won", "")
      "he ghosted" → ("Lost", "")
      "closed alex" → ("Won", "alex")
      "that lead booked a call" → ("Booked", "")
    """
    text_lower = text.lower()

    won_signals = [
        "just closed",
        "closed the deal",
        "closed them",
        "they signed",
        "they paid",
        "just won",
        "deal closed",
        "sale closed",
        "they bought",
        "just sold",
        "sold them",
        "closed a deal",
        "closed a sale",
    ]
    lost_signals = [
        "ghosted",
        "not interested",
        "lost that",
        "dead lead",
        "he left",
        "she left",
        "they left",
        "no response",
        "went cold",
        "lost them",
        "fell off",
        "dropped off",
        "unqualified",
    ]
    booked_signals = [
        "booked a call",
        "scheduled a call",
        "just booked",
        "call booked",
        "set a call",
        "locked in a call",
    ]

    stage = None
    for s in won_signals:
        if s in text_lower:
            stage = "Won"
            break
    # Bare "closed <Name>" pattern — word boundary check
    if not stage:
        import re as _re

        if _re.search(r"\bclosed\s+[A-Z][a-z]+", text):
            stage = "Won"

    if not stage:
        for s in lost_signals:
            if s in text_lower:
                stage = "Lost"
                break
    if not stage:
        for s in booked_signals:
            if s in text_lower:
                stage = "Booked"
                break

    if not stage:
        return None

    # Try to extract a lead name hint — @username or capitalized word after keyword
    import re

    username_match = re.search(r"@(\w+)", text)
    lead_hint = username_match.group(1) if username_match else ""

    if not lead_hint:
        name_match = re.search(r"(?:closed|lost|booked|sold|won)\s+([A-Z][a-z]+)", text)
        lead_hint = name_match.group(1) if name_match else ""

    return (stage, lead_hint)


def _run_gateway(
    text: str,
    channel_name: str,
    username: str,
    guild_id: str | None = None,
    channel_id: str | None = None,
    memory_only: bool = False,
) -> str:
    """
    Classify intent, build request, call gateway, return output text.
    Runs synchronously — called from asyncio executor to avoid blocking.
    Delegates to handlers.intent_handler.run_gateway.

    memory_only: when True, skip LLM call and only write to memory.
    Used by bypass paths that already sent a response to the user.
    """
    return _handler_run_gateway(
        text=text,
        channel_name=channel_name,
        username=username,
        gateway=_gateway,
        ki=_ki,
        channel_sessions=_channel_sessions,
        default_venture_id=_DEFAULT_VENTURE_ID,
        guild_id=guild_id,
        channel_id=channel_id,
        memory_only=memory_only,
    )


# ─── Meeting mode ─────────────────────────────────────────────────────────────


async def handle_meeting_voice(
    text: str,
    meeting_type: str,
    channel,
) -> str:
    """Handle voice input during a meeting — surfaces context, detects signals."""
    _active_meeting["notes"].append(text)
    text_lower = text.lower()

    if any(
        w in text_lower
        for w in [
            "objection",
            "they said",
            "pushback",
            "concern",
            "but what about",
        ]
    ):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: __import__("runtime.agent_teams", fromlist=["run_team_task"]).run_team_task(
                team="sales",
                sub_agent="objection_handler",
                prompt=f"Objection on call: {text}",
                venture_id=_DEFAULT_VENTURE_ID,
                ctx=_ctx_eos,
            ),
        )
        return result.get("output", "")

    elif any(
        w in text_lower
        for w in [
            "price",
            "cost",
            "how much",
            "what does it cost",
            "investment",
        ]
    ):
        return (
            "Initiate Arena: $750 one-time. "
            "Frame as investment not cost. "
            "Ask: what is staying stuck worth to you?"
        )

    elif any(
        w in text_lower
        for w in [
            "close",
            "ready",
            "lets do it",
            "let's do it",
            "sign up",
            "where do i pay",
        ]
    ):
        if channel:
            await _send_reply(
                channel,
                f"💰 **{AI_NAME}: Buying signal detected.**\n"
                f"Send the Whop link now.\n\n— {AI_NAME}",
            )
        return "Buying signal. Send the link."

    elif any(
        w in text_lower
        for w in [
            "end meeting",
            "wrap up",
            "that is all",
            "thanks everyone",
        ]
    ):
        await end_active_meeting(channel)
        return "Meeting ended. Running post-meeting automation."

    else:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _gateway.handle(
                {
                    "type": "agent_task",
                    "prompt": text,
                    "venture_id": _DEFAULT_VENTURE_ID,
                }
            ),
        )
        return result.get("output", "")


async def start_meeting_mode(
    meeting_type: str,
    lead_name: str = "",
    channel=None,
) -> str:
    """Activate meeting mode — loads pre-meeting brief, announces to channel."""
    from datetime import datetime, timezone

    _active_meeting["type"] = meeting_type
    _active_meeting["lead_name"] = lead_name
    _active_meeting["started_at"] = datetime.now(timezone.utc).isoformat()
    _active_meeting["notes"] = []
    _active_meeting["key_points"] = []
    try:
        from execution.transport.storage import get_storage

        get_storage().put("active_meeting", dict(_active_meeting))
    except Exception:
        pass

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: __import__("runtime.agent_teams", fromlist=["run_team_task"]).run_team_task(
            team="sales",
            sub_agent="closer",
            prompt=(
                f"Pre-meeting brief for {meeting_type} with "
                f"{lead_name or 'lead'}. What do I need to know?"
            ),
            venture_id=_DEFAULT_VENTURE_ID,
            ctx=_ctx_eos,
        ),
    )
    brief = result.get("output", "")

    if channel:
        await _send_reply(
            channel,
            f"📋 **{AI_NAME}: Meeting started — {meeting_type}**\n\n{brief}\n\n— {AI_NAME}",
        )

    # speak brief (fire-and-forget)
    asyncio.create_task(
        asyncio.get_event_loop().run_in_executor(
            None, _ve.speak, f"Meeting mode active. {brief[:200]}"
        )
    )

    return brief


async def end_active_meeting(channel=None) -> None:
    """End meeting mode and generate post-meeting summary."""
    if not _active_meeting["type"]:
        return

    notes = "\n".join(_active_meeting["notes"][-20:])
    meeting_type = _active_meeting["type"]
    lead_name = _active_meeting["lead_name"] or "lead"

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _gateway.handle(
            {
                "type": "agent_task",
                "prompt": (
                    f"Summarize this {meeting_type} with {lead_name}. "
                    f"Key points, outcome, next steps:\n\n{notes}"
                ),
                "venture_id": _DEFAULT_VENTURE_ID,
            }
        ),
    )
    summary = result.get("output", "")

    if channel:
        await _send_reply(
            channel,
            f"📝 **{AI_NAME}: Meeting summary**\n\n{summary}\n\n— {AI_NAME}",
        )

    # clear state
    _active_meeting["type"] = None
    _active_meeting["lead_name"] = None
    _active_meeting["notes"] = []
    _active_meeting["key_points"] = []
    try:
        from execution.transport.storage import get_storage

        get_storage().put("active_meeting", dict(_active_meeting))
    except Exception:
        pass


# ─── Startup ──────────────────────────────────────────────────────────────────


async def _warmup_cc_sdk():
    """Pre-load cc_sdk session on startup to reduce cold start latency.

    Skips warmup entirely when system is under high pressure — the subprocess
    spawn would worsen the load spike during recovery restarts.
    """
    await asyncio.sleep(10)
    try:
        from state.work.work_state import _measure_pressure, Pressure

        p = _measure_pressure()
        if p in (Pressure.HIGH, Pressure.CRITICAL):
            logger.info("[Startup] cc_sdk warmup skipped — pressure=%s", p.value)
            return

        from adapters.model_adapters.cc_sdk import query_cc_sync

        result = query_cc_sync(
            prompt="Ready.",
            task_type="fast_response",
            agent_id="dex",
            max_budget_usd=0.01,
        )
        if result:
            logger.info(
                "[Startup] cc_sdk warm — session %s... %dms",
                result.session_id[:8],
                result.latency_ms,
            )
        else:
            logger.warning("[Startup] cc_sdk warm failed")
    except Exception as e:
        logger.warning("[Startup] cc_sdk warm error: %s", e)


@bot.event
async def on_ready():
    global AI_NAME, _bot_ready

    # Reset immediately so any voice state events replayed during this
    # RESUME cycle are ignored until we're fully ready.
    _bot_ready = False

    # Suppress _MissingSentinel / poll_voice_ws Task exceptions at the loop level.
    # These crash the process when voice WS dies — on_error doesn't reach them.
    asyncio.get_event_loop().set_exception_handler(_handle_task_exception)

    AI_NAME = get_ai_name(_ctx_eos)  # refresh in case BIS updated

    # Clean up any stale/broken voice clients left from the previous session.
    # py-cord tries to resume voice connections on reconnect — if the resume
    # fails (Task poll_event crash) the client object lingers in a broken state
    # and our join guard would skip the founder's next join attempt.
    for guild in bot.guilds:
        if guild.voice_client:
            try:
                await guild.voice_client.disconnect(force=True)
                print("[Voice] Cleaned up stale voice client on ready")
            except Exception:
                pass

    # Short grace period: Discord replays voice state events during RESUME
    # right around on_ready. Wait for that window to pass before allowing
    # our handler to act on voice events.
    await asyncio.sleep(2)
    _bot_ready = True

    # ── Restore persisted session state from SubstrateStorage ──────────
    try:
        from execution.transport.storage import get_storage

        _store = get_storage()
        _restored = 0
        for _key in _store.all_keys():
            if _key.startswith("session:"):
                _chan = _key[len("session:") :]
                _channel_sessions[_chan] = _store.get(_key)
                _restored += 1
        if _restored:
            print(f"[Discord] Restored {_restored} channel session(s) from storage")
        _meeting_state = _store.get("active_meeting")
        if _meeting_state and _meeting_state.get("type"):
            _active_meeting["type"] = _meeting_state["type"]
            _active_meeting["lead_name"] = _meeting_state.get("lead_name")
            _active_meeting["started_at"] = _meeting_state.get("started_at")
            _active_meeting["notes"] = _meeting_state.get("notes", [])
            _active_meeting["key_points"] = _meeting_state.get("key_points", [])
            print(f"[Discord] Restored active meeting: {_meeting_state['type']}")
    except Exception as _restore_err:
        print(f"[Discord] Session restore failed (non-blocking): {_restore_err}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"over you — {AI_NAME}",
        )
    )
    print(f"[Discord] {AI_NAME} online as {bot.user} (id={bot.user.id})")
    print(f"[Discord] Serving {len(bot.guilds)} server(s)")

    # Start ambient refresh (same as Telegram bot)
    try:
        from control_plane.orchestrator.orchestrator import start_ambient_refresh_loop

        start_ambient_refresh_loop(_ctx_eos)
        print("[Discord] Ambient refresh started")
    except Exception as e:
        print(f"[Discord] Ambient refresh skipped: {e}")

    _substrate_log_startup()

    # Set up EOS Discord structure (idempotent — only creates missing channels)
    for guild in bot.guilds:
        bot.loop.create_task(_setup_server_structure(guild))

    # Warm up cc_sdk session (pre-load DEX agent, reduce cold start)
    asyncio.create_task(_warmup_cc_sdk())

    # ── Start CC reply webhook receiver ──────────────────────────────────
    # Receives POSTs from the CC Stop hook with assistant replies and
    # dispatches them to the correct Discord channel.
    try:
        from cc_webhook_receiver import start_webhook_server

        await start_webhook_server(bot, AI_NAME)
    except Exception as e:
        print(f"[Discord] CC webhook receiver failed to start: {e}")

    # ── Wire up session watcher → Discord bridge ───────────────────────────
    # SessionWatcher polls tmux panes for mid-session pauses (plan mode,
    # permission requests, questions).  SessionDiscordBridge renders them
    # as interactive Discord messages with buttons.
    try:
        from execution.transport.session_discord_bridge import get_bridge
        from execution.transport.session_watcher import start_watcher

        bridge = get_bridge()
        bridge.set_bot(bot)

        start_watcher("vps", "dex_builder_main", on_event=bridge.on_watcher_event)
        start_watcher("vps", "dex_product_main", on_event=bridge.on_watcher_event)
        print("[Discord] Session watchers + Discord bridge started")
    except Exception as e:
        print(f"[Discord] Session watcher/bridge setup failed: {e}")

    # ── Start Station Daemon (background heartbeat loop) ─────────────────
    try:
        from execution.transport.station_daemon import start_station_daemon

        start_station_daemon()
        print("[Discord] Station daemon started")
    except Exception as e:
        print(f"[Discord] Station daemon failed to start: {e}")


# ─── Auto-join voice ──────────────────────────────────────────────────────────


@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
):
    # Only watch the founder, and only after the bot is fully ready
    if not _bot_ready or FOUNDER_ID == 0 or member.id != FOUNDER_ID:
        return

    # Get general text channel for announcements
    general = None
    general_id = CHANNEL_IDS.get("general")
    if general_id:
        general = bot.get_channel(general_id)
    if not general:
        general = discord.utils.get(member.guild.text_channels, name="general")

    # Founder JOINED a voice channel (before=None, after=Channel)
    if after.channel is not None and before.channel is None:
        # Capture channel reference at event time — after.channel may be None later
        target_channel = after.channel
        print(f"[Voice] Branch: FOUNDER JOINED {target_channel.name}")
        await asyncio.sleep(3)
        # Re-check: founder must still be in that channel after the sleep.
        # If they left during the 3s window the LEFT branch already fired but
        # found no voice_client — without this guard we'd connect anyway.
        if member not in target_channel.members:
            print("[Voice] Founder left during sleep — aborting connect")
            return
        if member.guild.voice_client:
            return  # already connected
        vc = None
        max_attempts = 2
        await asyncio.sleep(10)
        print("[Voice] Starting connect sequence")
        for attempt in range(max_attempts):
            try:
                # Verify founder is still in the target channel before each attempt
                founder_member = member.guild.get_member(FOUNDER_ID)
                if (
                    not founder_member
                    or not founder_member.voice
                    or founder_member.voice.channel != target_channel
                ):
                    print("[Voice] Founder no longer in target channel — aborting")
                    return
                if target_channel is None:
                    print("[Voice] Channel reference lost — aborting")
                    return

                # disconnect any lingering voice client before each attempt
                if member.guild.voice_client:
                    try:
                        await member.guild.voice_client.disconnect(force=True)
                        await asyncio.sleep(1)
                    except Exception:
                        pass

                vc = await target_channel.connect(
                    timeout=15.0,
                    reconnect=False,  # we handle reconnects ourselves
                )
                print(f"[Voice] Connected on attempt {attempt + 1}")
                break  # success
            except discord.errors.ConnectionClosed as e:
                if "4006" in str(e) or "session" in str(e).lower():
                    wait = 5 if attempt == 0 else (attempt + 1) * 30
                    print(f"[Voice] 4006 on attempt {attempt + 1} — waiting {wait}s before retry")
                    # Force-disconnect any stale session before retry
                    if member.guild.voice_client:
                        try:
                            await member.guild.voice_client.disconnect(force=True)
                        except Exception:
                            pass
                    await asyncio.sleep(wait)
                    continue
                print(f"[Voice] Connect closed: {e}")
                return
            except Exception as e:
                print(f"[Voice] Connect failed: {e}")
                if "Already connected" in str(e):
                    if member.guild.voice_client:
                        try:
                            await member.guild.voice_client.disconnect(force=True)
                            await asyncio.sleep(2)
                        except Exception:
                            pass
                    continue
                return
        else:
            print("[Voice] Max connect attempts reached — aborting")
            return

        # verify WS initialized before starting the listen loop
        await asyncio.sleep(2)
        if not hasattr(vc, "ws") or vc.ws is discord.utils.MISSING:
            print("[Voice] WS not initialized — aborting")
            try:
                await vc.disconnect(force=True)
            except Exception:
                pass
            return

        print(f"[Voice] WS ready: {type(vc.ws).__name__}")
        if general:
            await _send_reply(
                general,
                f"👁️ **{AI_NAME} Joined {target_channel.name} voice chat.**",
            )
        asyncio.create_task(_listen_loop(vc, general))

    # Founder LEFT voice channel (before=Channel, after=None)
    elif before.channel is not None and after.channel is None:
        print(f"[Voice] Branch: FOUNDER LEFT {before.channel.name}")
        if member.guild.voice_client:
            try:
                await member.guild.voice_client.disconnect()
            except Exception:
                pass
        if general:
            await _send_reply(
                general,
                f"👁️ **{AI_NAME} Disconnected from {before.channel.name} voice chat.**",
            )

    # Founder SWITCHED channels (both not None)
    elif (
        before.channel is not None
        and after.channel is not None
        and before.channel.id != after.channel.id
    ):
        print(f"[Voice] Branch: FOUNDER SWITCHED {before.channel.name} → {after.channel.name}")
        if member.guild.voice_client:
            try:
                await member.guild.voice_client.move_to(after.channel)
            except Exception:
                pass
        if general:
            await _send_reply(general, f"👁️ **{AI_NAME} followed you to {after.channel.name}.**")


async def _listen_loop(
    vc: discord.VoiceClient,
    text_channel: discord.TextChannel | None,
) -> None:
    """
    Silence-detection voice loop.

    SilenceDetectingSink accumulates per-user audio frames and flushes each
    user's buffer after 1.5 s of silence.  Groq whisper-large-v3-turbo
    transcribes the resulting WAV.  All routing logic is unchanged.
    """
    print("[Voice] *** LISTEN LOOP STARTED ***")
    print(f"[Voice] Channel: {vc.channel}")

    async def on_utterance(user_id: int, audio_path: str) -> None:
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, transcribe_with_groq, audio_path)
            try:
                os.remove(audio_path)
            except Exception:
                pass

            if not text or len(text.split()) < 2:
                return

            print(f"[Voice] Heard: {text}")

            # ── Bounded substrate mirror (opt-in, default OFF) ──────────────
            # When EOS_DISCORD_VOICE_TRANSPORT_ENABLED is truthy, mirror this
            # transcript through the bounded voice seam so it lands in
            # voice_session / audio_loop / SPEAK_TEXT alongside the existing
            # gateway routing. Never raises. Returns None when disabled.
            try:
                from execution.transport.discord_voice_transport import (
                    maybe_mirror_discord_utterance,
                )

                _guild_id = (
                    str(getattr(getattr(vc, "channel", None), "guild", None).id)
                    if getattr(vc, "channel", None) is not None
                    and getattr(vc.channel, "guild", None) is not None
                    else None
                )
                _channel_id = (
                    str(vc.channel.id) if getattr(vc, "channel", None) is not None else None
                )
                # Pass `voice_client=vc` so that when
                # EOS_DISCORD_VOICE_PLAYBACK_ENABLED is also truthy, the
                # mirror hook can opportunistically attach the live VC and
                # play the EOS reply back into the channel. Default-off:
                # if either env var is unset, this is a transcript-only no-op.
                maybe_mirror_discord_utterance(
                    text,
                    user_id=user_id,
                    guild_id=_guild_id,
                    channel_id=_channel_id,
                    voice_client=vc,
                )
            except Exception as _mirror_err:  # noqa: BLE001
                print(f"[Voice] substrate mirror skipped: {_mirror_err}")

            should_respond, classification = _ve.should_respond(text, 0.0)
            print(f"[Voice] [{classification}] respond={should_respond}")

            if not should_respond:
                return

            # ── Voice-first: play ack BEFORE LLM call (eliminates dead air) ──
            try:
                from execution.transport.voice_first import (
                    needs_ack,
                    play_ack,
                    VOICE_SYSTEM_SUFFIX,
                )

                if needs_ack(text):
                    asyncio.create_task(play_ack(vc))
                _voice_prompt_suffix = VOICE_SYSTEM_SUFFIX
            except Exception:
                _voice_prompt_suffix = ""

            context_summary = _ve.intelligent.get_context_summary()
            prompt = f"{context_summary}\n\nCurrent: {text}" if context_summary else text
            prompt += _voice_prompt_suffix

            # Auto-detect meeting context
            if not _active_meeting.get("type"):
                meeting_ctx = _ve.intelligent.detect_meeting_context(
                    text, list(_ve.intelligent.context_window)
                )
                if meeting_ctx and meeting_ctx["confidence"] > 0.6:
                    _active_meeting["type"] = meeting_ctx["type"]
                    if text_channel:
                        await _send_reply(
                            text_channel,
                            f"📋 **{AI_NAME}: {meeting_ctx['type']} detected.**\n"
                            f"Taking notes. I'll surface relevant context as needed.\n\n— {AI_NAME}",
                        )

            meeting_type = _active_meeting.get("type")

            if meeting_type:
                _active_meeting["notes"].append(text)
                response = await handle_meeting_voice(text, meeting_type, text_channel)
                if not response:
                    result = await loop.run_in_executor(
                        None,
                        lambda: _gateway.handle(
                            {
                                "type": "agent_task",
                                "prompt": prompt,
                                "sub_agent": "executive_assistant",
                                "venture_id": _DEFAULT_VENTURE_ID,
                            }
                        ),
                    )
                    response = result.get("output", "")
            elif _ve.is_simple_query(text) and _ve.is_running():
                response = await loop.run_in_executor(None, _ve.query_local, text)
                if not response:
                    result = await loop.run_in_executor(
                        None,
                        lambda: _gateway.handle(
                            {
                                "type": "agent_task",
                                "prompt": prompt,
                                "sub_agent": "executive_assistant",
                                "venture_id": _DEFAULT_VENTURE_ID,
                            }
                        ),
                    )
                    response = result.get("output", "")
            else:
                result = await loop.run_in_executor(
                    None,
                    lambda: _gateway.handle(
                        {
                            "type": "agent_task",
                            "prompt": prompt,
                            "sub_agent": "executive_assistant",
                            "venture_id": _DEFAULT_VENTURE_ID,
                        }
                    ),
                )
                response = result.get("output", "")

            if not response:
                return

            _ve.intelligent.add_to_context(text, classification, response)

            # ── Voice-first response path ─────────────────────────────
            # Speak FIRST, then post text as transcript/subtitle.
            try:
                from execution.transport.voice_first import (
                    voice_first_respond,
                )

                user = bot.get_user(user_id)
                name = user.display_name if user else "You"
                vf_result = await voice_first_respond(
                    vc,
                    utterance=text,
                    response=response,
                    voice_engine=_ve,
                    text_channel=text_channel,
                    user_name=name,
                    ai_name=AI_NAME,
                    ack_already_played=True,
                )
                if vf_result.spoke:
                    print(
                        f"[Voice] voice-first: spoke={vf_result.spoke} ack={vf_result.ack_played}"
                    )
                elif vf_result.error:
                    print(f"[Voice] voice-first degraded: {vf_result.error}")
            except Exception as _vf_err:
                print(f"[Voice] voice-first import/call failed, falling back: {_vf_err}")
                # Fallback: original text-first path
                if text_channel:
                    user = bot.get_user(user_id)
                    name = user.display_name if user else "You"
                    msg = f"\U0001f3a4 **{name}:** {text}\n**{AI_NAME}:** {response}"
                    await _send_reply(text_channel, msg)
                audio_out = await loop.run_in_executor(None, _ve.speak, response[:300])
                if audio_out and os.path.exists(audio_out):
                    while vc.is_playing():
                        await asyncio.sleep(0.3)
                    if vc.is_connected():
                        vc.play(discord.FFmpegPCMAudio(audio_out))

            try:
                _ki.integrate(
                    content=(f"Voice [{classification}]:\nUser: {text}\n{AI_NAME}: {response}"),
                    source="discord_voice",
                    category="conversation",
                    metadata={
                        "classification": classification,
                        "meeting_type": _active_meeting.get("type"),
                    },
                )
            except Exception as e:
                print(f"[Voice] KI integrate failed: {e}")

        except Exception as e:
            print(f"[Voice] Utterance error: {e}")
            import traceback

            traceback.print_exc()

    sink = SilenceDetectingSink(on_utterance=on_utterance, silence_threshold=1.5)

    try:
        vc.start_recording(sink, lambda *a: None, None)
        print("[Voice] Silence detection active")
    except Exception as e:
        print(f"[Voice] Failed to start: {e}")
        import traceback

        traceback.print_exc()
        return

    asyncio.create_task(sink.monitor_silence(vc))

    if text_channel:
        await _send_reply(text_channel, f"👁️ **{AI_NAME} is listening.**")

    while vc.is_connected():
        await asyncio.sleep(1)

    print("[Voice] Disconnected — stopping")
    sink.cleanup()
    try:
        vc.stop_recording()
    except Exception:
        pass

    print("[Voice] Loop ended")


# ─── Message handler ──────────────────────────────────────────────────────────


@bot.event
async def on_message(message: discord.Message):
    # Ignore self and other bots
    if message.author == bot.user or message.author.bot:
        return

    # Wake idle system — a real user message is a work signal
    try:
        from state.work.work_state import record_signal, reset_idle_counter

        record_signal()
        reset_idle_counter()
    except Exception:
        pass

    # Handle audio file attachments → transcribe → route → speak back
    if message.attachments:
        for att in message.attachments:
            ext = Path(att.filename).suffix.lower()
            if ext in {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".opus"}:
                async with message.channel.typing():
                    tmp = tempfile.mktemp(suffix=ext)
                    await att.save(tmp)
                    loop = asyncio.get_event_loop()
                    transcribed = await loop.run_in_executor(None, _ve.transcribe, tmp)
                    if transcribed:
                        await message.add_reaction("🎙️")
                        _att_gid = str(message.guild.id) if message.guild else None
                        _att_cid = str(message.channel.id)
                        response = await loop.run_in_executor(
                            None,
                            lambda: _run_gateway(
                                transcribed,
                                getattr(message.channel, "name", "dm"),
                                str(message.author),
                                guild_id=_att_gid,
                                channel_id=_att_cid,
                            ),
                        )
                        reply = f"🎙️ **You said:** {transcribed}\n**{AI_NAME}:** {response}"
                        await _send_reply(message.channel, reply)
                        # Speak in voice if connected
                        if message.guild and message.guild.voice_client:
                            vc = message.guild.voice_client
                            if vc.is_connected() and not vc.is_playing():
                                audio_out = await loop.run_in_executor(
                                    None, _ve.speak, response[:300]
                                )
                                if audio_out and os.path.exists(audio_out):
                                    vc.play(discord.FFmpegPCMAudio(audio_out))
                    else:
                        await message.reply("Could not transcribe that audio.")
                    try:
                        Path(tmp).unlink(missing_ok=True)
                    except Exception:
                        pass
                return

    text = message.content.strip()
    if not text:
        await bot.process_commands(message)
        return

    channel_name = message.channel.name if hasattr(message.channel, "name") else "dm"
    username = str(message.author)

    # #wins is one-way announcement channel
    if channel_name == "wins":
        await bot.process_commands(message)
        return

    # ── Inbound multi-message buffering (/buffer + /done) ────────────────────
    _ib = get_inbound_buffer() if get_inbound_buffer else None
    _uid = str(message.author.id)
    _cid_str = str(message.channel.id)

    if text.strip().lower() == "/done" and _ib is not None:
        group = _ib.finalize(_uid, _cid_str)
        if group is None:
            await _send_reply(message.channel, "No active buffer to finalize.")
            await bot.process_commands(message)
            return
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
        except Exception:
            pass  # tracing failure must never block the request path
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
        except Exception:
            pass  # archive failure must never block message path
        # Replace text with combined buffer and fall through to normal processing
        text = group.combined_text
        await _send_reply(
            message.channel,
            f"Buffer finalized — {group.message_count} message(s), "
            f"{group.combined_text_length} chars. Processing...",
        )
        # Fall through to normal processing with the combined text

    elif text.strip().lower() == "/buffer" and _ib is not None:
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
        _bf_gid = str(message.guild.id) if message.guild else None
        _bf_cid = str(message.channel.id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _run_gateway(
                text,
                channel_name,
                username,
                guild_id=_bf_gid,
                channel_id=_bf_cid,
                memory_only=True,
            ),
        )
        await bot.process_commands(message)
        return

    elif _ib is not None and _ib.has_active(_uid, _cid_str):
        # Active buffer exists — accumulate instead of processing
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
        except Exception:
            pass
        count = group.message_count
        await message.add_reaction("📝")
        if count % 3 == 0:
            await _send_reply(
                message.channel,
                f"Buffered {count} messages. Send /done when ready.",
            )
        _ba_gid = str(message.guild.id) if message.guild else None
        _ba_cid = str(message.channel.id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _run_gateway(
                text,
                channel_name,
                username,
                guild_id=_ba_gid,
                channel_id=_ba_cid,
                memory_only=True,
            ),
        )
        await bot.process_commands(message)
        return

    # ── Day ritual intercept (before onboarding/CC injection/gateway) ────────
    _day_cmd = _detect_day_command(text)
    if _day_cmd:
        async with message.channel.typing():
            loop = asyncio.get_event_loop()
            _day_result = await loop.run_in_executor(
                None,
                lambda cmd=_day_cmd: _run_day_command(
                    cmd,
                    discord_channel_id=str(message.channel.id),
                ),
            )
            _day_text = _format_day_result(_day_result)
            await _send_day_response(message.channel, _day_text)
        _dr_gid = str(message.guild.id) if message.guild else None
        _dr_cid = str(message.channel.id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _run_gateway(
                text,
                channel_name,
                username,
                guild_id=_dr_gid,
                channel_id=_dr_cid,
                memory_only=True,
            ),
        )
        return

    # ── Active onboarding session — route before anything else ────────────────
    if message.guild:
        _ob_session = _onboarding.get_session(str(message.guild.id))
        if _ob_session and not _ob_session.completed:
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
                        provision_result["results"]["discord"] = f"error: {_de}"

                    completion = _onboarding.get_completion_message(
                        provision_result["data"],
                        provision_result["results"],
                    )
                    await _send_reply(message.channel, completion)
                except Exception as _pe:
                    print(f"[Onboarding] Provisioning error: {_pe}")
                    await _send_reply(
                        message.channel,
                        f"⚠️ Provisioning encountered an issue: {_pe}\n"
                        "Run `!onboard` again to retry.",
                    )
            _ob_gid = str(message.guild.id) if message.guild else None
            _ob_cid = str(message.channel.id)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: _run_gateway(
                    text,
                    channel_name,
                    username,
                    guild_id=_ob_gid,
                    channel_id=_ob_cid,
                    memory_only=True,
                ),
            )
            return

    # ── Archive single inbound verbatim ──────────────────────────────────
    try:
        _archive_inbound(
            text,
            interface=_ArchiveInterface.DISCORD.value,
            metadata={
                "type": "single",
                "user_id": _uid,
                "channel_id": _cid_str,
                "channel_name": channel_name,
            },
        )
    except Exception:
        pass  # archive failure must never block message path

    # ── Substrate commands (spine/router routed) ───────────────────────
    if is_substrate_command(text):
        await handle_substrate_command(message, text)
        return

    # ── Orchestration ingress (mode-gated) ──────────────────────────────
    # When EOS_DISCORD_ORCHESTRATION_ENABLED=1, route through the substrate
    # orchestration layer instead of CC injection / PseudoLive / Gateway.
    # This is the single clean Discord text → orchestration boundary.
    # When disabled (default), falls through to the existing CC/PseudoLive chain.
    _orch_handled = False
    try:
        from execution.transport.discord_ingress_adapter import ingest_and_emit

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
                from execution.transport.operator_trace import (
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
                print(f"[Orchestration] trace format error: {_trace_err}", flush=True)
    except Exception as _orch_err:  # noqa: BLE001
        print(f"[Orchestration] ingress error: {_orch_err}", flush=True)

    if _orch_handled:
        _oh_gid = str(message.guild.id) if message.guild else None
        _oh_cid = str(message.channel.id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _run_gateway(
                text,
                channel_name,
                username,
                guild_id=_oh_gid,
                channel_id=_oh_cid,
                memory_only=True,
            ),
        )
        await bot.process_commands(message)
        return

    # ── Session-first CC injection ───────────────────────────────────────
    # DORMANT: session_registry, session_router, surface_registry,
    # live_loop, input_router modules do not exist yet.
    # This block will activate when runtime/ is fully built.
    _cc_injected = False

    if _cc_injected:
        _ccm_gid = str(message.guild.id) if message.guild else None
        _ccm_cid = str(message.channel.id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _run_gateway(
                f"[CC Session] {text}",
                channel_name,
                username,
                guild_id=_ccm_gid,
                channel_id=_ccm_cid,
                memory_only=True,
            ),
        )
        await bot.process_commands(message)
        return

    # ── PseudoLive fallback — full pipeline via gateway/model_router ──────
    # Fires only when CC injection failed (session missing, tmux down, etc).
    try:
        _pl_result = _maybe_pseudo_live_text(
            text,
            guild_id=str(message.guild.id) if message.guild else None,
            channel_id=str(message.channel.id),
            user_id=str(message.author.id),
        )
    except Exception as _ple:  # noqa: BLE001
        print(f"[PseudoLive] hook error: {_ple}")
        _pl_result = None

    if _pl_result is not None:
        _pl_ingress = _pl_result.get("ingress") or {}
        _pl_env = _pl_result.get("envelope") or {}
        _pl_status = _pl_ingress.get("status")
        if _pl_status not in ("disabled", "gate_denied"):
            # Transport was active — NEVER fall through to gateway/Gemini.
            # If envelope is ok, send the reply. Otherwise return gracefully.
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
                        print(f"[PseudoLive] send failed: {_se}")

                # ── Post-delivery finalization ───────────────────────
                # Uses run_lifecycle proposal to prevent duplicate
                # finalization when watcher/webhook also fire.
                _pl_fin = _pl_result.get("finalization_ready") or {}
                if _pl_fin.get("should_finalize"):
                    # Hard guard: drop if lifecycle is sealed
                    _pl_terminal = False
                    try:
                        from execution.transport.run_lifecycle import (
                            is_run_terminally_finalized as _pl_term_check,
                        )

                        _pl_session_check = _pl_fin.get("source_session", "")
                        if _pl_session_check and _pl_term_check(_pl_session_check):
                            print(
                                f"[PseudoLive] Late finalization dropped: "
                                f"session={_pl_session_check} — terminally finalized"
                            )
                            _pl_terminal = True
                    except Exception:
                        pass

                    if not _pl_terminal:
                        try:
                            _pl_session = _pl_fin.get("source_session", "")
                            from execution.transport.run_lifecycle import (
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
                                from execution.transport.task_finalization import (
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
                            print(f"[PseudoLive] finalization failed: {_fin_e}")

                _deferred = _pl_result.get("deferred_tts") or {}
                _tts_node = _deferred.get("node_id")
                _tts_text = _deferred.get("spoken_text") or ""
                _tts_role = _deferred.get("role_slug") or "ea_orchestrator"
                if _tts_node and _tts_text:
                    try:
                        from execution.transport.station_helpers import propose_speak_text

                        propose_speak_text(
                            _tts_node,
                            _tts_text,
                            issued_by=f"discord_text:{_tts_role}",
                        )
                    except Exception as _te:  # noqa: BLE001
                        print(f"[PseudoLive] deferred TTS failed: {_te}")
            else:
                print(
                    f"[PseudoLive] CC session failed: status={_pl_status} "
                    f"detail={_pl_ingress.get('detail', '')}"
                )
            _plm_gid = str(message.guild.id) if message.guild else None
            _plm_cid = str(message.channel.id)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: _run_gateway(
                    f"[CC Session] {text}",
                    channel_name,
                    username,
                    guild_id=_plm_gid,
                    channel_id=_plm_cid,
                    memory_only=True,
                ),
            )
            return

    # Meeting mode triggers — natural language detection
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
        _ms_gid = str(message.guild.id) if message.guild else None
        _ms_cid = str(message.channel.id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _run_gateway(
                text,
                channel_name,
                username,
                guild_id=_ms_gid,
                channel_id=_ms_cid,
                memory_only=True,
            ),
        )
        return

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
        _me_gid = str(message.guild.id) if message.guild else None
        _me_cid = str(message.channel.id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _run_gateway(
                text,
                channel_name,
                username,
                guild_id=_me_gid,
                channel_id=_me_cid,
                memory_only=True,
            ),
        )
        return

    # ── Pending capture resolution (1/2/3 venture reply) ────────────────────
    _channel_id = str(message.channel.id)
    if _channel_id in _pending_captures and text.strip() in (
        "1",
        "2",
        "3",
        "1️⃣",
        "2️⃣",
        "3️⃣",
    ):
        _pending = _pending_captures.pop(_channel_id)
        import json as _json

        _ventures_list = _json.loads(os.getenv("VENTURES_JSON", "[]"))
        _venture_map = {str(i + 1): v["id"] for i, v in enumerate(_ventures_list)}
        _venture_id = _venture_map.get(
            text.strip().replace("\ufe0f\u20e3", ""), _DEFAULT_VENTURE_ID
        )
        try:
            from understanding.signals.founder_capture import capture

            capture(_pending["text"], venture_id=_venture_id)
            _icon = "💡" if _pending["type"] == "idea" else "✅"
            await _send_reply(message.channel, f"{_icon} Added to your list.")
        except Exception:
            pass
        _fc_gid = str(message.guild.id) if message.guild else None
        _fc_cid = str(message.channel.id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _run_gateway(
                _pending["text"],
                channel_name,
                username,
                guild_id=_fc_gid,
                channel_id=_fc_cid,
                memory_only=True,
            ),
        )
        return

    # ── Pipeline update detection (delegated to handler) ────────────────────
    if await handle_pipeline_update(message, text):
        _pl_gid = str(message.guild.id) if message.guild else None
        _pl_cid = str(message.channel.id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _run_gateway(
                text,
                channel_name,
                username,
                guild_id=_pl_gid,
                channel_id=_pl_cid,
                memory_only=True,
            ),
        )
        return

    # ── Founder capture — detect tasks/ideas, write to Your list + Notion ────
    try:
        from understanding.signals.founder_capture import should_capture, capture

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
                    f"{'💡' if _ctype == 'idea' else '✅'} Got it. Which venture is this for?\n"
                    f"{_choices}",
                )
                _pending_captures[_channel_id] = {"text": text, "type": _ctype}
                _ac_gid = str(message.guild.id) if message.guild else None
                _ac_cid = str(message.channel.id)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: _run_gateway(
                        text,
                        channel_name,
                        username,
                        guild_id=_ac_gid,
                        channel_id=_ac_cid,
                        memory_only=True,
                    ),
                )
                return

            _capture_result = capture(text, venture_id=_venture_id)
            if _capture_result.get("captured"):
                _icon = "💡" if _ctype == "idea" else "✅"
                await _send_reply(message.channel, f"{_icon} Added to your list.")
    except Exception:
        pass  # Never let capture break the main flow

    # ── Multi-part accumulation ───────────────────────────────────────────────
    part_info = _detect_part(text)
    if part_info:
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
                        lambda: _run_gateway(
                            combined, cname, uname, guild_id=_fl_gid, channel_id=_fl_cid
                        ),
                    )
                if out:
                    await _send_response(orig_message, out)

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
            return

        else:
            # Final part — assemble and fall through to normal processing
            buf = _multipart_buffers.pop(ch_key, None)
            if buf:
                text = _assemble_parts(buf)

    # ── Inline commands (delegated to handler) ──────────────────────────────
    if await try_inline_commands(message, text, _pending_events):
        _ic_gid = str(message.guild.id) if message.guild else None
        _ic_cid = str(message.channel.id)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _run_gateway(
                text,
                channel_name,
                username,
                guild_id=_ic_gid,
                channel_id=_ic_cid,
                memory_only=True,
            ),
        )
        return

    # All messages → full EOS gateway (execution_contract pipeline)
    _gid = str(message.guild.id) if message.guild else None
    _cid = str(message.channel.id)
    async with message.channel.typing():
        loop = asyncio.get_event_loop()

        output = await loop.run_in_executor(
            None,
            lambda: _run_gateway(text, channel_name, username, guild_id=_gid, channel_id=_cid),
        )

    if output:
        # Determine if founder is in a voice channel before responding
        founder_in_voice = False
        founder_member = None
        try:
            if message.guild and message.author.id == FOUNDER_ID:
                founder_member = message.guild.get_member(FOUNDER_ID)
                if founder_member and founder_member.voice and founder_member.voice.channel:
                    founder_in_voice = True
        except Exception:
            pass

        # Always post text response
        await _send_response(message, output)

        if founder_in_voice:
            # Also speak via TTS in voice channel
            try:
                vc = message.guild.voice_client
                if not vc or not vc.is_connected():
                    vc = await founder_member.voice.channel.connect(
                        timeout=10.0,
                        reconnect=False,
                    )
                audio_path = await asyncio.get_event_loop().run_in_executor(
                    None, _ve.speak, output[:300]
                )
                if audio_path and os.path.exists(audio_path):
                    while vc.is_playing():
                        await asyncio.sleep(0.3)

                    def cleanup(error):
                        try:
                            os.remove(audio_path)
                        except Exception:
                            pass

                    vc.play(
                        discord.FFmpegPCMAudio(audio_path),
                        after=cleanup,
                    )
                    print(f"[Voice] Speaking: {output[:50]}...")
            except Exception as e:
                print(f"[Voice] TTS check: {e}")

    await bot.process_commands(message)


async def _send_response(message: discord.Message, output: str) -> None:
    """Send response to Discord with full footer intact."""
    output = output.rstrip() + f"\n\n— {AI_NAME}"
    await _send_reply(message.channel, output)


# ─── Discord Server Manager ───────────────────────────────────────────────────


class DiscordServerManager:
    """Idempotent Discord server structure manager.
    Creates channels and categories only if they don't already exist.
    Called on bot ready and via !setup command.
    """

    def __init__(self, guild: discord.Guild):
        self.guild = guild

    async def ensure_category(self, name: str) -> discord.CategoryChannel:
        """Find or create a category."""
        existing = discord.utils.get(self.guild.categories, name=name)
        if existing:
            return existing
        cat = await self.guild.create_category(name)
        print(f"[Discord] Created category: {name}")
        return cat

    async def ensure_channel(
        self,
        name: str,
        category_name: str | None = None,
        topic: str = "",
        channel_type: str = "text",
    ) -> discord.abc.GuildChannel | None:
        """Find or create a channel. Returns channel object."""
        if channel_type == "voice":
            existing = discord.utils.get(self.guild.voice_channels, name=name)
        else:
            existing = discord.utils.get(self.guild.text_channels, name=name)
        if existing:
            return existing

        category = None
        if category_name:
            category = await self.ensure_category(category_name)

        try:
            if channel_type == "voice":
                ch = await self.guild.create_voice_channel(name=name, category=category)
            else:
                ch = await self.guild.create_text_channel(name=name, topic=topic, category=category)
            print(f"[Discord] Created #{name}")
            return ch
        except discord.Forbidden:
            print(f"[Discord] Permission denied creating #{name}")
            return None
        except Exception as e:
            print(f"[Discord] Error creating #{name}: {e}")
            return None

    async def setup_eos_structure(self) -> list[str]:
        """Create full EOS Discord structure. Only creates what doesn't exist."""
        print("[Discord] Setting up EOS structure...")

        structure: dict[str, list[tuple[str, str, str]]] = {
            "🧠 EOS": [
                ("general", "text", "Main conversation with DEX"),
                ("morning-brief", "text", "Daily intelligence from DEX"),
                ("decisions", "text", "Logged decisions"),
                ("wins", "text", "Closed deals and wins"),
                ("agent-activity", "text", "EOS agent activity log"),
            ],
            "⚡ Empyrean Creative": [
                ("empyrean-strategy", "text", "Empyrean Creative strategic decisions"),
                ("empyrean-pipeline", "text", "Empyrean Creative sales pipeline"),
                ("empyrean-outreach", "text", "Empyrean Creative outreach tracking"),
            ],
            "🏢 Lyfe Institute": [
                ("lyfe-strategy", "text", "Lyfe Institute strategy"),
                ("lyfe-pipeline", "text", "Initiate Arena pipeline"),
                ("lyfe-outreach", "text", "Instagram DM tracking"),
            ],
            "👤 Personal Brand": [
                ("brand-strategy", "text", "Personal brand strategy"),
                ("content-ideas", "text", "Content ideas and calendar"),
            ],
            "🎙️ Voice": [
                ("Founder's Office", "voice", ""),
            ],
        }

        created: list[str] = []
        for category_name, channels in structure.items():
            for ch_name, ch_type, topic in channels:
                ch = await self.ensure_channel(
                    name=ch_name,
                    category_name=category_name,
                    topic=topic,
                    channel_type=ch_type,
                )
                if ch:
                    created.append(ch_name)

        # Remove War Room if it exists — one voice channel only
        war_room_vc = discord.utils.get(self.guild.voice_channels, name="War Room")
        if war_room_vc:
            await war_room_vc.delete(reason="One voice channel only")
            print("[Discord] Removed War Room voice")

        print(f"[Discord] Structure ready: {len(created)} channels verified")
        return created

    async def align_structure(self) -> None:
        """
        Enforce the canonical EOS channel layout.
        Moves uncategorized channels into 🧠 EOS.
        Removes redundant generic channels.
        Safe to call on every startup.
        """
        print("[Discord] Aligning structure...")

        # Get or create 🧠 EOS category
        eos_cat = discord.utils.get(self.guild.categories, name="🧠 EOS")
        if not eos_cat:
            eos_cat = await self.guild.create_category("🧠 EOS")
            print("[Discord] Created 🧠 EOS category")

        # Recreate #general if deleted, or move if uncategorized
        general = discord.utils.get(self.guild.text_channels, name="general")
        if not general:
            general = await self.guild.create_text_channel(
                name="general",
                topic="Primary conversation with DEX",
                category=eos_cat,
            )
            print("[Discord] Recreated #general")
        elif general.category != eos_cat:
            await general.edit(category=eos_cat)
            print("[Discord] Moved #general → 🧠 EOS")

        # Move these channels into 🧠 EOS if not already there
        move_to_eos = ["morning-brief", "decisions", "wins", "agent-activity"]
        for ch_name in move_to_eos:
            ch = discord.utils.get(self.guild.text_channels, name=ch_name)
            if ch and ch.category != eos_cat:
                await ch.edit(category=eos_cat)
                print(f"[Discord] Moved #{ch_name} → 🧠 EOS")

        # Remove redundant generic channels — company-specific equivalents exist
        for ch_name in ("strategy", "outreach", "content"):
            ch = discord.utils.get(self.guild.text_channels, name=ch_name)
            if ch:
                await ch.delete(reason="Redundant — company-specific channels exist")
                print(f"[Discord] Removed #{ch_name}")

        # War Room guard — belt-and-suspenders
        war_room = discord.utils.get(self.guild.voice_channels, name="War Room")
        if war_room:
            await war_room.delete(reason="One voice channel only")
            print("[Discord] Removed War Room voice")

        print("[Discord] Structure aligned ✅")

    async def update_for_stage_change(
        self,
        company: str,
        new_stage: int,
    ) -> list[str]:
        """Create stage-appropriate channels when a venture advances."""
        stage_channels: dict[int, list[tuple[str, str, str]]] = {
            2: [
                (f"{company}-content", "text", "Content strategy (unlocked Stage 2)"),
                (f"{company}-systems", "text", "Systems and processes"),
            ],
            3: [
                (f"{company}-hiring", "text", "Hiring and team building"),
                (f"{company}-operations", "text", "Operations management"),
            ],
        }

        new_channels = stage_channels.get(new_stage, [])
        category_name = company.replace("_", " ").title()
        created: list[str] = []

        for ch_name, ch_type, topic in new_channels:
            ch = await self.ensure_channel(
                name=ch_name,
                category_name=category_name,
                topic=topic,
            )
            if ch:
                created.append(ch_name)

        # Announce in general
        general = discord.utils.get(self.guild.text_channels, name="general")
        if general:
            await _send_reply(
                general,
                f"🎯 **Stage {new_stage} unlocked for {company}.**\n\n"
                f"New channels and primitives now active.\n"
                f"{AI_NAME} has updated your operating system.\n\n— {AI_NAME}",
            )

        return created


async def _setup_server_structure(guild: discord.Guild) -> None:
    """Called on_ready to ensure EOS Discord structure exists."""
    try:
        mgr = DiscordServerManager(guild)
        await mgr.setup_eos_structure()
        await mgr.align_structure()
    except Exception as e:
        print(f"[Discord] Server setup error: {e}")


# ─── Session watcher commands ────────────────────────────────────────────────


@bot.command(name="answer")
async def cmd_answer(ctx: commands.Context, session_name: str, *, text: str):
    """Answer a CC session question: !answer dex_builder_main <your answer>"""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply("Founder only.")
        return
    try:
        from execution.transport.session_discord_bridge import get_bridge

        result = await get_bridge().handle_answer_command(session_name, text)
        await ctx.reply(result)
    except Exception as e:
        await ctx.reply(f"Error: {e}")


@bot.command(name="mfa")
async def cmd_mfa(ctx: commands.Context, service: str, *, code: str):
    """Respond to an MFA challenge: !mfa claude 123456 or !mfa chatgpt approved"""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply("Founder only.")
        return
    try:
        from services.local_bridge_client import send_mfa_response

        response_type = (
            "approved" if code.lower().strip() in ("approved", "approve", "yes") else "code"
        )
        ok = send_mfa_response(service.lower(), code.strip(), response_type)
        if ok:
            await ctx.reply(f"✅ MFA response delivered to **{service}** ({response_type})")
        else:
            await ctx.reply(
                f"❌ Failed to deliver MFA response — bridge unreachable or no pending challenge"
            )
    except Exception as e:
        await ctx.reply(f"Error: {e}")


@bot.command(name="fire_export")
async def cmd_fire_export(ctx: commands.Context, service: str = "all"):
    """Trigger a browser export: !fire_export claude or !fire_export all"""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply("Founder only.")
        return
    try:
        from services.trigger_export import fire_export

        await ctx.reply(f"🚀 Triggering export: **{service}**...")
        result = fire_export(service.lower())
        if result.get("ok"):
            await ctx.reply(f"✅ Bridge accepted: {result.get('message', 'dispatched')}")
        else:
            await ctx.reply(f"❌ Failed: {result.get('error', 'unknown')}")
    except Exception as e:
        await ctx.reply(f"Error: {e}")


@bot.command(name="watcher_status")
async def cmd_watcher_status(ctx: commands.Context):
    """Show session watcher status."""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply("Founder only.")
        return
    try:
        import time as _time

        from execution.transport.session_watcher import _WATCHERS, _WATCHERS_LOCK

        with _WATCHERS_LOCK:
            if not _WATCHERS:
                await ctx.reply("No watchers running.")
                return
            from execution.transport.discord_output_policy import get_display_name

            lines = []
            for name, w in _WATCHERS.items():
                display = get_display_name(name)
                status = "🟢 running" if w.is_running else "🔴 stopped"
                ago = int(_time.time() - w.last_activity)
                if ago < 60:
                    age_str = f"{ago}s ago"
                elif ago < 3600:
                    age_str = f"{ago // 60}m ago"
                else:
                    age_str = f"{ago // 3600}h ago"
                preview = w.last_reply_preview[:80] if w.last_reply_preview else "—"
                lines.append(
                    f"**{display}**: {status} — `{w.state.value}` — {age_str}\n  └ {preview}"
                )
        await ctx.reply("\n".join(lines))
    except Exception as e:
        await ctx.reply(f"Error: {e}")


# ─── Commands ─────────────────────────────────────────────────────────────────


@bot.command(name="brief")
async def cmd_brief(ctx: commands.Context):
    """Trigger morning brief on demand."""
    async with ctx.typing():
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(
            None,
            lambda: _run_gateway("morning brief", ctx.channel.name, str(ctx.author)),
        )
    await ctx.reply(output or "Brief generated.")


@bot.command(name="status")
async def cmd_status(ctx: commands.Context):
    """Portfolio health check — scans all ventures and shows binding constraint."""
    async with ctx.typing():
        loop = asyncio.get_event_loop()

        def _portfolio_scan():
            try:
                from control_plane.strategy.portfolio_advisor import (
                    PortfolioAdvisor as PortfolioAgent,
                )

                pa = PortfolioAgent(_ctx_eos)
                ventures = pa.scan_all_ventures()
                return pa.generate_portfolio_brief(ventures)
            except Exception as e:
                return f"Portfolio scan failed: {e}"

        output = await loop.run_in_executor(None, _portfolio_scan)

    await _send_reply(ctx.channel, output or "Status retrieved.")


@bot.command(name="portfolio")
async def cmd_portfolio(ctx: commands.Context):
    """Trigger the weekly portfolio brief on demand."""
    import subprocess

    subprocess.Popen(["python3", str(_REPO_ROOT / "scripts" / "portfolio_brief.py")])
    await ctx.reply("📊 Portfolio brief generating...")


@bot.command(name="join")
async def cmd_join(ctx: commands.Context):
    """Join the voice channel the user is currently in."""
    if not ctx.author.voice:
        await ctx.reply("Join a voice channel first.")
        return
    channel = ctx.author.voice.channel
    already_connected = bool(ctx.voice_client)
    if already_connected:
        await ctx.voice_client.move_to(channel)
        vc = ctx.voice_client
    else:
        vc = await channel.connect()
    await _send_reply(
        ctx.channel,
        f"🎙️ **{AI_NAME} connected.** Talk to me. Drop an audio file and I'll transcribe + respond.",
    )
    # Only start the listen loop on a fresh connect.
    # Auto-join (on_voice_state_update) already started it if the bot
    # was already in a channel — starting a second loop causes duplicate recording.
    if not already_connected:
        await asyncio.sleep(3)  # wait for voice WS to initialize
        asyncio.create_task(_listen_loop(vc, ctx.channel))


@bot.command(name="leave")
async def cmd_leave(ctx: commands.Context):
    """Disconnect from voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await _send_reply(ctx.channel, f"👁️ **{AI_NAME} disconnected.**")
    else:
        await ctx.reply("Not connected to any voice channel.")


@bot.command(name="say")
async def cmd_say(ctx: commands.Context, *, text: str):
    """Speak text aloud in the voice channel."""
    if not ctx.voice_client:
        await ctx.reply("Use `!join` first to connect to voice.")
        return
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
    loop = asyncio.get_event_loop()
    audio_path = await loop.run_in_executor(None, _ve.speak, text)
    if audio_path and os.path.exists(audio_path):
        ctx.voice_client.play(discord.FFmpegPCMAudio(audio_path))
        await _send_reply(ctx.channel, f"🔊 {text[:80]}{'...' if len(text) > 80 else ''}")
    else:
        await ctx.reply("TTS failed — check that espeak is installed.")


@bot.command(name="outcome")
async def cmd_outcome(ctx: commands.Context, *, args: str = ""):
    """Capture post-meeting outcome. Usage: !outcome <event_id> [what decided] | [open loops]"""
    if not args:
        await ctx.reply("Usage: `!outcome <event_id> [outcomes] | [open loops]`")
        return
    try:
        parts = args.strip().split("|")
        left_tokens = parts[0].strip().split()
        event_id = left_tokens[0] if left_tokens else ""
        outcomes_text = " ".join(left_tokens[1:]) if len(left_tokens) > 1 else ""
        open_loops_text = parts[1].strip() if len(parts) > 1 else ""

        from adapters.calendar.meetings import update_meeting_outcome

        ok = update_meeting_outcome(
            calendly_event_id=event_id,
            status="Completed",
            outcomes=outcomes_text,
            open_loops=open_loops_text,
        )
        if ok:
            await ctx.reply("✅ Outcome captured and synced to Notion.")
        else:
            await ctx.reply("⚠️ Captured locally but Notion sync failed — check NOTION_MEETINGS_ID.")
    except Exception as e:
        await ctx.reply(f"❌ Failed: {e}")


@bot.command(name="eod")
async def cmd_eod(ctx: commands.Context):
    """Trigger EOD sync manually."""
    import subprocess

    subprocess.Popen(["python3", str(_REPO_ROOT / "scripts" / "eod_sync.py")])
    await ctx.reply("📊 EOD sync running...")


@bot.command(name="openday")
async def cmd_openday(ctx: commands.Context, *, args: str = ""):
    """Open the operator's day. Usage: !openday [workspace=builder] [node=local]"""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply("Founder only.")
        return
    workspace = None
    node_pref = None
    for part in args.split():
        if part.startswith("workspace="):
            workspace = part.split("=", 1)[1]
        elif part.startswith("node="):
            node_pref = part.split("=", 1)[1]
    async with ctx.typing():
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _run_day_command(
                "open_day",
                workspace=workspace,
                node_preference=node_pref,
                discord_channel_id=str(ctx.channel.id),
            ),
        )
        formatted = _format_day_result(result)
        await _send_day_response(ctx.channel, formatted)


@bot.command(name="closeday")
async def cmd_closeday(ctx: commands.Context, *, args: str = ""):
    """Close the operator's day. Usage: !closeday [continuity notes as free text]"""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply("Founder only.")
        return
    continuity = args.strip() if args.strip() else None
    async with ctx.typing():
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _run_day_command(
                "close_day",
                continuity_text=continuity,
                discord_channel_id=str(ctx.channel.id),
            ),
        )
        formatted = _format_day_result(result)
        await _send_day_response(ctx.channel, formatted)


@bot.command(name="accept")
async def cmd_accept(ctx: commands.Context, event_id: str = ""):
    """Accept a pending calendar invite. Usage: !accept <event_id>"""
    if not event_id:
        await ctx.reply("Usage: `!accept <event_id>`")
        return
    try:
        from scripts.calendar_invite_handler import respond_to_invite

        ok = respond_to_invite(event_id, "accepted")
        await ctx.reply("✅ Accepted." if ok else "❌ Failed to accept.")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="decline")
async def cmd_decline(ctx: commands.Context, event_id: str = ""):
    """Decline a pending calendar invite. Usage: !decline <event_id>"""
    if not event_id:
        await ctx.reply("Usage: `!decline <event_id>`")
        return
    try:
        from scripts.calendar_invite_handler import respond_to_invite

        ok = respond_to_invite(event_id, "declined")
        await ctx.reply("❌ Declined." if ok else "❌ Failed to decline.")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="approve")
async def cmd_approve(ctx: commands.Context, approval_id: str = ""):
    """Approve a pending gateway action."""
    if not approval_id:
        await ctx.reply("Usage: `!approve <approval_id>`")
        return
    result = _gateway.approve(approval_id)
    if result.get("status") == "ok":
        output = result.get("output") or "Approved and executed."
        await _send_reply(ctx.channel, output)
    else:
        await ctx.reply(f"Error: {result.get('error', 'unknown')}")


@bot.command(name="approve_followup")
async def cmd_approve_followup(ctx: commands.Context):
    """Approve and send the most recent pending follow-up email draft."""
    try:
        from state.context.context import load_context_from_env
        from state.storage.db import get_conn
        from adapters.google_workspace.gws_connector import GWSConnector
        from governance.quality.quality_gate import gate_outgoing_email
        import json as _json

        _ctx = load_context_from_env()

        with get_conn(_ctx.org_id) as cur:
            cur.execute(
                """
                SELECT id, payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'email_draft_pending'
                AND payload_json->>\'status\' = \'pending_approval\'
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (str(_ctx.org_id),),
            )
            row = cur.fetchone()

        if not row:
            await ctx.reply("No pending emails to approve.")
            return

        payload = row["payload_json"]
        if isinstance(payload, str):
            payload = _json.loads(payload)

        draft = payload.get("draft", "")
        to_email = payload.get("to_email", "")
        email_type = payload.get("type", "unknown")

        # Parse subject and body from draft
        lines = draft.strip().split("\n")
        subject = ""
        body_lines = []
        in_body = False
        for line in lines:
            if line.lower().startswith("subject:"):
                subject = line[8:].strip()
            elif subject and not in_body and line.strip() == "":
                in_body = True
            elif in_body:
                body_lines.append(line)
        body = "\n".join(body_lines).strip()

        if not subject:
            subject = f"Follow-up — {email_type}"
        if not body:
            body = draft

        # Run quality gate before sending
        if to_email:
            try:
                qr = gate_outgoing_email(
                    subject=subject,
                    body=body,
                    to_email=to_email,
                )
                if qr.get("score", 10) < 6:
                    await ctx.reply(
                        f"⚠️ Quality score: {qr['score']}/10\n"
                        f"Issues: {', '.join(qr.get('issues', [])[:2])}\n"
                        f"Run `!proofread` to review before sending, "
                        f"or `!force_send` to send anyway."
                    )
                    with get_conn(_ctx.org_id) as cur:
                        cur.execute(
                            """
                            UPDATE events
                            SET payload_json = payload_json ||
                                \'{"awaiting_force_send": true}\'::jsonb
                            WHERE id = %s
                        """,
                            (row["id"],),
                        )
                    return
            except Exception:
                pass

        # Send the email
        if to_email:
            gws = GWSConnector()
            result = gws.send_email(
                to_email=to_email,
                subject=subject,
                body=body,
            )
            if result.get("id"):
                with get_conn(_ctx.org_id) as cur:
                    cur.execute(
                        """
                        UPDATE events
                        SET payload_json = payload_json ||
                            \'{"status": "sent"}\'::jsonb
                        WHERE id = %s
                    """,
                        (row["id"],),
                    )
                await ctx.reply(
                    f"✅ **Email sent to {to_email}**\nSubject: {subject}\nPreview: {body[:200]}..."
                )
            else:
                await ctx.reply(
                    f"❌ Send failed. Check GWS token.\n"
                    f"Draft preserved — try again after "
                    f"`gws auth login`"
                )
        else:
            # No recipient — mark approved, no send
            with get_conn(_ctx.org_id) as cur:
                cur.execute(
                    """
                    UPDATE events
                    SET payload_json = payload_json ||
                        \'{"status": "approved"}\'::jsonb
                    WHERE id = %s
                """,
                    (row["id"],),
                )
            await ctx.reply(
                f"✅ Approved (no recipient email on file).\nDraft:\n```\n{draft[:400]}\n```"
            )
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="force_send")
async def cmd_force_send(ctx: commands.Context):
    """Force-send an email that failed the quality gate."""
    try:
        from state.context.context import load_context_from_env
        from state.storage.db import get_conn
        from adapters.google_workspace.gws_connector import GWSConnector
        import json as _json

        _ctx = load_context_from_env()

        with get_conn(_ctx.org_id) as cur:
            cur.execute(
                """
                SELECT id, payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'email_draft_pending'
                AND payload_json->>\'awaiting_force_send\' = \'true\'
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (str(_ctx.org_id),),
            )
            row = cur.fetchone()

        if not row:
            await ctx.reply("No email awaiting force send.")
            return

        payload = row["payload_json"]
        if isinstance(payload, str):
            payload = _json.loads(payload)

        draft = payload.get("draft", "")
        to_email = payload.get("to_email", "")
        lines = draft.strip().split("\n")
        subject = next(
            (l[8:].strip() for l in lines if l.lower().startswith("subject:")),
            "Follow-up",
        )
        body = draft

        gws = GWSConnector()
        result = gws.send_email(to_email, subject, body)
        if result.get("id"):
            with get_conn(_ctx.org_id) as cur:
                cur.execute(
                    """
                    UPDATE events
                    SET payload_json = payload_json ||
                        \'{"status": "sent", "force_sent": true}\'::jsonb
                    WHERE id = %s
                """,
                    (row["id"],),
                )
            await ctx.reply(f"✅ Force sent to {to_email}")
        else:
            await ctx.reply("❌ Send failed. Check GWS token.")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="confidential")
async def cmd_confidential(ctx: commands.Context, *, args: str = ""):
    """Start a confidential session. Usage: !confidential [topic] | [parties] | [level]"""
    parts = [p.strip() for p in args.split("|")] if args else []
    if not parts or not parts[0]:
        await ctx.reply(
            "🔒 Confidential session modes:\n"
            "`!confidential [topic] | [parties] | [level]`\n"
            "Levels: restricted, private, sealed\n\n"
            "• **restricted** — metadata logged, no content\n"
            "• **private** — memory only, not logged\n"
            "• **sealed** — nothing retained"
        )
        return
    try:
        from governance.policies.confidentiality import create_confidential_session

        topic = parts[0]
        parties = [p.strip() for p in parts[1].split(",")] if len(parts) > 1 else ["Antony"]
        level = parts[2] if len(parts) > 2 else "restricted"
        create_confidential_session(topic, parties, level)
        await ctx.reply(
            f"🔒 **Confidential session started**\n"
            f"Topic: {topic}\n"
            f"Level: {level}\n"
            f"Handling: "
            f"{'Metadata only' if level == 'restricted' else 'Memory only — not logged'}"
        )
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="pending")
async def cmd_pending(ctx: commands.Context):
    """Show all pending approval emails."""
    try:
        from state.context.context import load_context_from_env
        from state.storage.db import get_conn
        import json as _json

        _ctx = load_context_from_env()
        with get_conn(_ctx.org_id) as cur:
            cur.execute(
                """
                SELECT id, payload_json, created_at
                FROM events
                WHERE org_id = %s
                AND event_type = 'email_draft_pending'
                AND payload_json->>\'status\' = \'pending_approval\'
                ORDER BY created_at DESC
                LIMIT 10
            """,
                (str(_ctx.org_id),),
            )
            rows = cur.fetchall()
        if not rows:
            await ctx.reply("✅ No pending emails.")
            return
        lines = [f"📧 **Pending emails ({len(rows)}):**"]
        for i, r in enumerate(rows, 1):
            p = r["payload_json"]
            if isinstance(p, str):
                p = _json.loads(p)
            lines.append(
                f"{i}. {p.get('type', 'unknown')} → "
                f"{p.get('to_email', 'no recipient')} — "
                f"{str(r['created_at'])[:16]}"
            )
        lines.append("\n`!approve_followup` sends the most recent one.")
        await ctx.reply("\n".join(lines))
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="relationship")
async def cmd_relationship(ctx: commands.Context, *, name: str = ""):
    """Show relationship health for a contact. Usage: !relationship [name]"""
    if not name:
        await ctx.reply("Usage: `!relationship [contact name]`")
        return
    try:
        from understanding.intelligence.person_recognition import (
            score_relationship_health,
            build_intelligence_profile,
        )

        _health = score_relationship_health(name=name)
        _profile = build_intelligence_profile(name=name)

        _bar = "█" * int(_health["score"] * 10) + "░" * (10 - int(_health["score"] * 10))
        _rel_lines = [
            f"**Relationship: {name}**",
            f"Health: [{_bar}] {_health['score']:.0%} — {_health['status']}",
            f"Last contact: {_health['last_contact']}",
            f"Meetings: {_health['total_meetings']} total, {_health['completed_meetings']} completed",
        ]
        if _health.get("no_shows"):
            _rel_lines.append(f"⚠️ {_health['no_shows']} no-show(s)")
        if _health.get("factors"):
            _rel_lines.append(f"Factors: {', '.join(_health['factors'])}")
        if _profile.notes:
            _rel_lines.append(f"\n💡 {_profile.notes}")

        await ctx.reply("\n".join(_rel_lines))
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="nurture")
async def cmd_nurture(ctx: commands.Context, *, name: str = ""):
    """Draft a warm check-in message for a contact. Usage: !nurture [name]"""
    if not name:
        await ctx.reply("Usage: `!nurture [contact name]`")
        return
    try:
        from execution.runtime.model_router import get_router, TaskType
        from understanding.intelligence.person_recognition import build_intelligence_profile

        _router = get_router()
        _model = _router.route(TaskType.FAST_RESPONSE)
        profile = build_intelligence_profile(name=name)
        notes = getattr(profile, "notes", None) or "No prior context available"
        last_contact = getattr(profile, "last_contact", None) or "unknown"
        draft = _router.call(
            _model,
            f"""Draft a warm check-in message for {name}.

Context: {notes}
Last contact: {last_contact}

Antony's voice — casual, genuine, no agenda.
2-3 sentences max. Not salesy.

Subject: [subject]
[body]
[Antony]""",
        ).strip()
        await ctx.reply(
            f"📧 Check-in draft for {name}:\n```\n{draft[:500]}\n```\n`!approve_followup` to send."
        )
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="expenses")
async def cmd_expenses(ctx: commands.Context):
    """Show month-to-date expenses. Usage: !expenses"""
    try:
        from state.finance.expense_tracker import get_monthly_summary

        summary = get_monthly_summary()
        if not summary.get("total"):
            await ctx.reply("💳 No expenses logged this month.")
            return
        lines = [f"💳 **Expenses — Month to date: ${summary['total']:,.2f}**"]
        for cat, amt in sorted(summary["by_category"].items(), key=lambda x: x[1], reverse=True):
            lines.append(f"• {cat}: ${amt:,.2f}")
        lines.append(f"\n_{summary['count']} transactions_")
        await ctx.reply("\n".join(lines))
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="setup")
async def cmd_setup(ctx: commands.Context):
    """Setup EOS Discord server structure. Founder only."""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply("Only the founder can run setup.")
        return
    async with ctx.typing():
        mgr = DiscordServerManager(ctx.guild)
        created = await mgr.setup_eos_structure()
    await ctx.reply(
        f"✅ **EOS Discord structure ready.**\n"
        f"{len(created)} channels verified across all companies."
    )


@bot.command(name="align")
async def cmd_align(ctx: commands.Context):
    """Align Discord structure with EOS architecture. Founder only."""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply("Only the founder can run this.")
        return
    async with ctx.typing():
        mgr = DiscordServerManager(ctx.guild)
        await mgr.align_structure()
    await ctx.reply(
        "✅ Discord structure aligned.\n🧠 EOS category organized.\nRedundant channels removed."
    )


@bot.command(name="report")
async def cmd_report(ctx: commands.Context, report_type: str = "profile"):
    """Send EOS reports on demand. Types: profile, pulse. Founder only."""
    if ctx.author.id != FOUNDER_ID:
        await ctx.reply("Founder only.")
        return

    if report_type == "profile":
        async with ctx.typing():
            profile_path = _REPO_ROOT / "data" / "founder_profile.md"
            if not profile_path.exists():
                await ctx.reply("No profile yet. Run a GWS scan first.")
                return
            profile = profile_path.read_text()
        await _send_reply(ctx.channel, f"**📊 EOS LEARNING REPORT**\n\n{profile}")
        await ctx.message.add_reaction("✅")

    elif report_type == "pulse":
        await ctx.reply("Running world pulse scan... (this takes a minute)")
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: (
                __import__("runtime.world_pulse", fromlist=["WorldPulse"])
                .WorldPulse(_ctx_eos)
                .run_pulse_scan()
            ),
        )
        total = results.get("total_integrated", 0)
        await ctx.reply(
            f"✅ Pulse scan complete. {total} items integrated. Report posted via webhook."
        )

    else:
        await ctx.reply("Usage: `!report profile` or `!report pulse`")


@bot.command(name="onboard")
async def cmd_onboard(ctx: commands.Context):
    """Start the EOS onboarding flow for a new founder."""
    if not ctx.guild:
        await ctx.reply("Run this in a server, not a DM.")
        return

    session = _onboarding.start_session(
        org_id=str(ctx.guild.id),
        user_id=str(ctx.author.id),
    )
    welcome = _onboarding.get_welcome_message()
    await ctx.reply(welcome)

    # Get and send the first question immediately
    first_q = _onboarding.get_next_question(session)
    if first_q:
        await _send_reply(ctx.channel, first_q)


@bot.command(name="sync")
async def cmd_sync(ctx: commands.Context):
    """Run the Daily Sync meeting now."""
    async with ctx.typing():

        def _run():
            try:
                from control_plane.scheduling.daily_sync import DailySyncEngine

                dse = DailySyncEngine(_ctx_eos)
                return dse.run_sync()
            except Exception as e:
                return f"Daily sync error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="inbox")
async def cmd_inbox(ctx: commands.Context):
    """Show Email GPS status — current inbox routing."""
    async with ctx.typing():

        def _run():
            try:
                from adapters.google_workspace.email_gps import EmailGPS

                gps = EmailGPS(_ctx_eos)
                processed = gps.process_inbox(limit=20)
                return gps.generate_inbox_report(processed)
            except Exception as e:
                return f"Email GPS error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="draft")
async def cmd_draft(ctx: commands.Context):
    """Show email drafts awaiting approval."""
    async with ctx.typing():

        def _run():
            import json
            from pathlib import Path

            PENDING_DIR = _REPO_ROOT / "orchestrator" / "approvals" / "pending"

            drafts = []
            for f in sorted(PENDING_DIR.glob("*.json")):
                try:
                    data = json.loads(f.read_text())
                    req = data.get("request", {})
                    if req.get("type") == "email_draft":
                        drafts.append(
                            {
                                "approval_id": data.get("approval_id"),
                                "to": req.get("to", ""),
                                "subject": req.get("subject", ""),
                                "body": req.get("body", ""),
                                "queued_at": data.get("queued_at", ""),
                            }
                        )
                except Exception:
                    continue

            if not drafts:
                return "📬 No email drafts pending approval."

            lines = [f"📝 **{len(drafts)} Email Draft(s) Pending Approval**\n"]
            for d in drafts[:5]:
                lines.append(
                    f"**ID:** `{d['approval_id']}`\n"
                    f"**To:** {d['to']}\n"
                    f"**Subject:** {d['subject']}\n"
                    f"**Body:**\n{d['body'][:400]}\n"
                    f"→ `!approve {d['approval_id']}` to send\n"
                )
            return "\n".join(lines)

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="cal")
async def cmd_cal(ctx: commands.Context, period: str = "today"):
    """Show calendar. Usage: !cal or !cal week"""
    async with ctx.typing():

        def _run():
            try:
                from adapters.google_workspace.gws_connector import GWSConnector

                gws = GWSConnector()
                if period == "week":
                    events = (
                        gws.get_week_events()
                        if hasattr(gws, "get_week_events")
                        else gws.get_today_events()
                    )
                    label = "This Week"
                else:
                    events = gws.get_today_events()
                    label = "Today"

                if not events:
                    return f"📅 **Calendar {label}:** Clear"
                lines = [f"📅 **Calendar — {label}**"]
                for e in events[:10]:
                    title = e.get("title", "") or e.get("summary", "")
                    start = e.get("start", "")
                    if isinstance(start, dict):
                        start = start.get("dateTime", "") or start.get("date", "")
                    if start and "T" in str(start):
                        start = str(start).split("T")[1][:5]
                    lines.append(f"  {start} — {title}")
                return "\n".join(lines)
            except Exception as e:
                return f"Calendar error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="block")
async def cmd_block(ctx: commands.Context, *, time_range: str = ""):
    """Block focus time on calendar. Usage: !block 2pm-4pm deep work"""
    if not time_range:
        await ctx.reply("Usage: `!block 2pm-4pm deep work`")
        return
    await ctx.reply(
        f"📅 Focus block noted: **{time_range}**\nCalendar blocking via GWS coming in next build."
    )


@bot.command(name="focus")
async def cmd_focus(ctx: commands.Context, hours: str = "2"):
    """Block focus time on calendar now. Usage: !focus [hours]"""
    async with ctx.typing():

        def _run():
            try:
                h = int(hours) if hours.isdigit() else 2
                from adapters.google_workspace.gws_connector import GWSConnector
                from datetime import datetime, timezone, timedelta

                gws = GWSConnector()
                now = datetime.now(timezone.utc)
                event = gws.create_calendar_event(
                    title="🔒 Deep Work — Do Not Disturb",
                    start_iso=now.isoformat(),
                    duration_minutes=h * 60,
                    description="Focus block created by DEX. No meetings.",
                )
                if event:
                    end_time = (now + timedelta(hours=h)).strftime("%I:%M %p")
                    return (
                        f"🔒 Focus block set for **{h}h**. "
                        f"Calendar blocked until **{end_time} UTC**."
                    )
                return "❌ Failed to create focus block — GWS calendar error."
            except Exception as e:
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="waiting")
async def cmd_waiting(ctx: commands.Context):
    """Show what\'s in the Waiting On folder."""
    async with ctx.typing():

        def _run():
            try:
                from adapters.google_workspace.email_gps import EmailGPS

                gps = EmailGPS(_ctx_eos)
                processed = gps.process_inbox(limit=30)
                waiting = gps.get_waiting_on(processed)
                if not waiting:
                    return "⏳ **Waiting On:** Nothing currently waiting on a reply."
                lines = [f"⏳ **Waiting On Reply** ({len(waiting)}):"]
                for e in waiting:
                    lines.append(f"  • {e.from_name or e.from_address}: {e.subject[:50]}")
                return "\n".join(lines)
            except Exception as e:
                return f"Waiting On error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="verify-inbox")
async def cmd_verify_inbox(ctx: commands.Context):
    """Spot-check Gmail GPS labels — sample 5 emails per folder."""
    async with ctx.typing():

        def _run():
            try:
                from adapters.google_workspace.email_gps import EmailGPS

                gps = EmailGPS(_ctx_eos)
                return gps.verify_existing_labels(sample=5)
            except Exception as e:
                return f"Verify inbox error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="folder-update")
async def cmd_folder_update(ctx: commands.Context, folder: str = "", *, instruction: str = ""):
    """Update a GPS folder definition. Usage: !folder-update <folder> <instruction>"""
    if not folder or not instruction:
        await ctx.reply(
            "Usage: `!folder-update <folder> <instruction>`\n"
            "Example: `!folder-update Receipts-Financials Apple marketing emails should never go here`\n"
            "Folders: Antony, To Respond, Review, Responded, Waiting On, Receipts-Financials, Newsletters"
        )
        return

    async with ctx.typing():

        def _run():
            try:
                from adapters.google_workspace.email_gps import EmailGPS

                gps = EmailGPS(_ctx_eos)
                new_purpose = gps.update_folder_purpose(folder, instruction)
                if new_purpose:
                    return (
                        f'✅ **Updated "{folder}"**\n\n'
                        f"New rule: {new_purpose}\n\n"
                        f"All future classifications use this definition."
                    )
                return f'❌ Could not update "{folder}". Check the folder name and try again.'
            except Exception as e:
                return f"Folder update error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="delegated")
async def cmd_delegated(ctx: commands.Context):
    """Show overdue delegations."""

    def _run():
        try:
            from control_plane.delegation.delegation_tracker import get_overdue_delegations

            overdue = get_overdue_delegations()
            if not overdue:
                return "✅ No overdue delegations."
            lines = [f"📋 **Overdue delegations ({len(overdue)}):**"]
            for d in overdue[:8]:
                task = d.get("task", "")[:60]
                to = d.get("delegated_to", "Unknown")
                due = d.get("due_at", "")[:10]
                lines.append(f"• {task} → {to} (due {due})")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="subscriptions")
async def cmd_subscriptions(ctx: commands.Context):
    """Show subscription registry and upcoming renewals."""

    def _run():
        try:
            from state.finance.subscription_tracker import (
                get_subscriptions,
                get_upcoming_renewals,
                get_monthly_subscription_total,
            )

            subs = get_subscriptions()
            renewals = get_upcoming_renewals(days=14)
            monthly = get_monthly_subscription_total()

            if not subs:
                return (
                    "📋 No subscriptions tracked yet.\n"
                    "Add one: `!add_sub [vendor] [amount] [monthly/annual] [YYYY-MM-DD]`"
                )

            lines = [f"📋 **Subscriptions — ${monthly:,.2f}/month**"]
            for s in subs[:10]:
                lines.append(
                    f"• {s['vendor']} — ${s['amount']} "
                    f"({s.get('billing_cycle', 'monthly')}) — "
                    f"renews {s.get('next_renewal', '?')[:10]}"
                )
            if renewals:
                lines.append("\n⚠️ **Renewing soon:**")
                for r in renewals[:3]:
                    lines.append(f"• {r['vendor']} in {r['days_until']}d — ${r['amount']}")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="add_sub")
async def cmd_add_sub(ctx: commands.Context, *, args: str = ""):
    """Add a subscription. Usage: !add_sub [vendor] [amount] [monthly/annual] [YYYY-MM-DD]"""
    parts = args.strip().split()
    if len(parts) < 4:
        await ctx.reply("Usage: `!add_sub [vendor] [amount] [monthly/annual] [YYYY-MM-DD]`")
        return

    def _run():
        try:
            from state.finance.subscription_tracker import add_subscription

            vendor = parts[0]
            amount = float(parts[1])
            cycle = parts[2]
            renewal = parts[3]
            ok = add_subscription(
                vendor=vendor,
                amount=amount,
                billing_cycle=cycle,
                next_renewal=renewal,
            )
            if ok:
                return f"✅ Added: {vendor} — ${amount}/{cycle} — renews {renewal}"
            return "❌ Failed to add subscription."
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="help")
async def cmd_help(ctx: commands.Context):
    """Show available commands."""
    lines = [
        f"**{AI_NAME} — Discord Commands**",
        "",
        "Just type naturally in any channel — I route automatically.",
        "",
        "**EA Commands (DEX Email + Calendar)**",
        "`!sync` — run daily sync meeting now",
        "`!inbox` — Email GPS status",
        "`!draft` — drafts awaiting your approval",
        "`!cal` — today's calendar",
        "`!cal week` — this week's calendar",
        "`!focus [hours]` — block calendar now for deep work (default 2h)",
        "`!block <time> <label>` — block focus time",
        "`!waiting` — what's in Waiting On folder",
        "`!delegated` — overdue delegations",
        "`!subscriptions` — subscription registry + upcoming renewals",
        "`!add_sub [vendor] [amount] [cycle] [date]` — track a subscription",
        "`!verify-inbox` — spot-check GPS label accuracy",
        "`!folder-update <folder> <instruction>` — update GPS folder rule",
        "",
        "**EOS Commands**",
        "`!brief` — morning brief",
        "`!report profile` — EOS learning report from docs",
        "`!report pulse` — run world pulse scan",
        "`!status` — system health check",
        "`!approve <id>` — approve a pending action",
        "`!approve_followup` — approve and send most recent pending email",
        "`!force_send` — bypass quality gate and send flagged email",
        "`!pending` — list all emails awaiting approval",
        "`!confidential [topic] | [parties] | [level]` — start confidential session",
        "`!nurture [name]` — draft a warm check-in for a contact",
        "`!expenses` — month-to-date expense summary",
        "`!join` — connect to your voice channel",
        "`!leave` — disconnect from voice",
        "`!say <text>` — speak text aloud in voice channel",
        "",
        "**Voice**",
        "Drop a `.wav`/`.mp3`/`.ogg` in any channel while connected",
        "→ Whisper transcribes → smart routing (Qwen local or Claude) → speaks back",
        "",
        "**Channels**",
        "`#general` — freeform conversation with DEX",
        "`#morning-brief` — daily brief (auto-posted at 6am)",
        "`#decisions` — decision evaluation",
        "`#wins` — win announcements",
        "`#agent-activity` — EOS agent log",
        "`#empyrean-strategy/pipeline/outreach` — Empyrean Creative",
        "`#lyfe-strategy/pipeline/outreach` — Lyfe Institute",
        "`#brand-strategy` / `#content-ideas` — Personal Brand",
    ]
    await ctx.reply("\n".join(lines))


# ─── Webhook helpers (called by orchestrator and dm_monitor) ──────────────────


async def post_to_channel(channel_name: str, content: str) -> bool:
    """Post content to a named channel by ID. Returns True if sent."""
    channel_id = CHANNEL_IDS.get(channel_name)
    if not channel_id:
        print(f"[Discord] No ID set for channel '{channel_name}' — skipping post")
        return False
    channel = bot.get_channel(channel_id)
    if not channel:
        print(f"[Discord] Channel {channel_id} not found in cache")
        return False
    return await _send_reply(channel, content)


async def post_morning_brief(brief: str) -> None:
    await post_to_channel("morning-brief", brief)


async def post_outreach_alert(alert: str) -> None:
    await post_to_channel("outreach", f"📩 {alert}")


async def post_win(win: str) -> None:
    await post_to_channel("wins", f"🏆 {win}")


@bot.command(name="yield")
async def cmd_drip(ctx: commands.Context, *, args: str = ""):
    """Task Yield Matrix audit. Usage: !yield task1, task2, task3"""
    if not args.strip():
        await ctx.reply(
            "**Task Yield Matrix Audit**\n"
            "List your tasks separated by commas.\n"
            "Usage: `!yield [task1], [task2], [task3]`"
        )
        return

    def _run():
        try:
            from control_plane.strategy.task_yield_matrix import (
                run_yield_audit,
                format_yield_report,
            )

            tasks = [t.strip() for t in args.replace("\n", ",").split(",") if t.strip()]
            if not tasks:
                return "No tasks found. Separate with commas."
            results = run_yield_audit(tasks)
            return format_yield_report(results)
        except Exception as e:
            return f"❌ Error: {e}"

    await ctx.reply(f"🔍 Running Task Yield audit on {len(args.split(','))} tasks...")
    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, report)


@bot.command(name="founderrate")
async def cmd_buyback(ctx: commands.Context, income: str = ""):
    """Set or view Founder Rate. Usage: !founderrate [annual income] or !founderrate"""
    if income.strip():

        def _run():
            try:
                from state.metrics.founder_rate import (
                    calculate_founder_rate,
                    store_founder_rate,
                )

                amount = float(income.replace("$", "").replace(",", ""))
                rate = calculate_founder_rate(amount)
                store_founder_rate(amount)
                return (
                    f"💰 **Founder Rate set:**\n"
                    f"Annual income: ${amount:,.0f}\n"
                    f"Hourly rate: ${rate['hourly_rate']}/hr\n"
                    f"**Founder Rate: ${rate['founder_rate']}/hr**\n\n"
                    f"{rate['interpretation']}"
                )
            except Exception as e:
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
    else:

        def _get():
            try:
                from state.metrics.founder_rate import get_current_founder_rate

                rate = get_current_founder_rate()
                if rate:
                    return (
                        f"💰 **Current Founder Rate: ${rate['founder_rate']}/hr**\n"
                        f"{rate['interpretation']}"
                    )
                return (
                    "No Founder Rate set yet.\n"
                    "Usage: `!founderrate [annual income]`\n"
                    "Example: `!founderrate 120000`"
                )
            except Exception as e:
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _get)
    await ctx.reply(output)


@bot.command(name="logtime")
async def cmd_logtime(ctx: commands.Context, *, args: str = ""):
    """Log a time block. Usage: !logtime [activity] | [minutes] | [energy -2 to 2] | [$ value optional]"""
    if not args or args.count("|") < 2:
        await ctx.reply(
            "Usage: `!logtime [activity] | [minutes] | [energy -2 to 2] | [$ value optional]`\n"
            "Energy: -2=major drain, -1=drain, 0=neutral, 1=energizing, 2=major energy"
        )
        return

    def _run():
        try:
            from state.metrics.founder_rate import log_time_block

            parts = args.split("|")
            activity = parts[0].strip()
            minutes = int(parts[1].strip())
            energy = int(parts[2].strip())
            value = float(parts[3].strip().replace("$", "")) if len(parts) > 3 else 0
            ok = log_time_block(activity, minutes, energy, value)
            energy_label = {
                -2: "Major drain 🔴",
                -1: "Drain 🟠",
                0: "Neutral ⚪",
                1: "Energizing 🟢",
                2: "Major energy ⚡",
            }.get(energy, str(energy))
            if ok:
                return f"⏱️ Logged: {activity} — {minutes}min — {energy_label}"
            return "❌ Failed to log."
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="timeaudit")
async def cmd_timeaudit(ctx: commands.Context):
    """View 7-day time and energy audit summary."""

    def _run():
        try:
            from state.metrics.founder_rate import get_time_audit_summary

            summary = get_time_audit_summary(days=7)
            if not summary.get("total_hours"):
                return (
                    "📊 No time logged this week.\n"
                    "Use `!logtime [activity] | [minutes] | [energy]` to track."
                )
            energy_label = "🟢 Positive" if summary["avg_energy"] > 0 else "🔴 Negative"
            return (
                f"📊 **Time Audit — last 7 days:**\n"
                f"Total tracked: {summary['total_hours']}h\n"
                f"Average energy: {energy_label} ({summary['avg_energy']:+.1f})\n"
                f"High value work: {summary['high_value_pct']}%\n"
                f"Low value work: {summary['low_value_pct']}%"
            )
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="idealweek")
async def cmd_perfectweek(ctx: commands.Context):
    """View your ideal week template."""

    def _run():
        try:
            from control_plane.scheduling.ideal_week import get_ideal_week

            week = get_ideal_week()
            lines = ["**📅 Your Ideal Week:**", ""]
            for day, data in week.items():
                lines.append(f"**{day.capitalize()} — {data['theme']}**")
                lines.append(f"AM: {data['morning']}")
                lines.append(f"PM: {data['afternoon']}")
                protected = data.get("protected", [])
                if protected:
                    lines.append(f"🔒 Protected: {' | '.join(protected)}")
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    msg = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, msg)


@bot.command(name="processcapture")
async def cmd_camcorder(ctx: commands.Context, *, args: str = ""):
    """Create a process capture playbook. Usage: !processcapture [task name] | [describe how you do it]"""
    if "|" not in args:
        await ctx.reply(
            "**Process Capture — create a playbook from how you do a task**\n"
            "Usage: `!processcapture [task name] | [describe how you do it step by step]`\n"
            "Example: `!processcapture Send proposal | I open the template, fill client name, add pricing, send with note`"
        )
        return

    parts = args.split("|", 1)
    task_name = parts[0].strip()
    description = parts[1].strip()

    await ctx.reply(f"🎥 Creating playbook for: {task_name}...")

    def _run():
        try:
            from control_plane.scheduling.ideal_week import create_process_capture

            playbook = create_process_capture(task_name, description)
            if playbook:
                preview = playbook[:800]
                return (
                    f"✅ **Playbook created:** {task_name}\n"
                    f"Saved to skills/Ops/ and registered.\n"
                    f"```\n{preview}\n```"
                )
            return "❌ Playbook creation failed."
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="drive")
async def cmd_drive(ctx: commands.Context):
    """View top-level Google Drive folder structure."""

    def _run():
        try:
            from adapters.google_workspace.gws_connector import GWSConnector

            gws = GWSConnector()
            structure = gws.get_drive_structure()
            if not structure:
                return "📁 Could not retrieve Drive structure (check GWS auth)."
            lines = [f"📁 **Drive structure ({len(structure)} folders):**"]
            for f in structure[:15]:
                lines.append(f"• {f.get('name', 'Unknown')} ({f.get('id', '')})")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="driveaudit")
async def cmd_driveaudit(ctx: commands.Context):
    """Audit Google Drive for organization issues."""
    await ctx.reply("🔍 Auditing Drive...")

    def _run():
        try:
            from adapters.google_workspace.gws_connector import GWSConnector

            gws = GWSConnector()
            issues = gws.audit_drive()
            lines = ["📁 **Drive Audit:**"]
            root_files = issues.get("root_files", [])
            untitled = issues.get("untitled", [])
            if root_files:
                lines.append(f"\n⚠️ **{len(root_files)} files in root (should be in folders):**")
                for f in root_files[:5]:
                    lines.append(f"• {f.get('name', 'Unknown')}")
            if untitled:
                lines.append(f"\n⚠️ **{len(untitled)} untitled documents:**")
                for f in untitled[:5]:
                    lines.append(f"• {f.get('name', 'Unknown')}")
            if not root_files and not untitled:
                lines.append("✅ Drive looks clean.")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="createfolder")
async def cmd_createfolder(ctx: commands.Context, *, name: str = ""):
    """Create a folder in Google Drive. Usage: !createfolder [folder name]"""
    if not name.strip():
        await ctx.reply("Usage: `!createfolder [folder name]`")
        return

    def _run():
        try:
            from adapters.google_workspace.gws_connector import GWSConnector

            gws = GWSConnector()
            result = gws.create_folder(name.strip())
            if result.get("id"):
                return f"📁 Folder created: **{name}**\nID: {result['id']}"
            return "❌ Failed to create folder."
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="trip")
async def cmd_trip(ctx: commands.Context, *, args: str = ""):
    """Build a travel brief. Usage: !trip [event] | [destination] | [start] | [end]"""
    if "|" not in args:
        await ctx.reply(
            "**Trip Brief**\n"
            "Usage: `!trip [event name] | [destination] | [start date] | [end date]`\n"
            "Example: `!trip SaaS Conference | San Francisco, CA | 2026-04-15 | 2026-04-17`"
        )
        return

    def _run():
        try:
            from adapters.calendar.travel_manager import build_travel_brief, log_trip

            parts = [p.strip() for p in args.split("|")]
            title = parts[0]
            destination = parts[1] if len(parts) > 1 else "Unknown"
            start = parts[2] if len(parts) > 2 else ""
            end = parts[3] if len(parts) > 3 else start
            brief = build_travel_brief(title, destination, start, end)
            log_trip(title, destination, start, end)
            return f"✈️ **Travel Brief: {title}**\n\n{brief}"
        except Exception as e:
            return f"❌ Error: {e}"

    await ctx.reply("✈️ Building travel brief...")
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="nolist")
async def cmd_nolist(ctx: commands.Context):
    """View Antony's No List."""

    def _run():
        try:
            from state.metrics.founder_rate import get_no_list

            items = get_no_list()
            if not items:
                return (
                    "📋 No List is empty.\n"
                    "Add with: `!noadd [thing you will never do again] | [reason]`"
                )
            lines = [f"🚫 **No List ({len(items)} items):**"]
            for item in items:
                reason = item.get("reason", "")
                lines.append(f"• {item['item']}" + (f" — {reason}" if reason else ""))
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="noadd")
async def cmd_noadd(ctx: commands.Context, *, args: str = ""):
    """Add to No List. Usage: !noadd [thing] | [reason optional]"""
    if not args.strip():
        await ctx.reply("Usage: `!noadd [thing] | [reason optional]`")
        return

    def _run():
        try:
            from state.metrics.founder_rate import add_to_no_list

            parts = args.split("|", 1)
            item = parts[0].strip()
            reason = parts[1].strip() if len(parts) > 1 else ""
            ok = add_to_no_list(item, reason)
            if ok:
                return (
                    f"🚫 Added to No List: **{item}**\n"
                    f"DEX will flag this if it appears in your tasks or calendar."
                )
            return "❌ Failed to add."
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="energy")
async def cmd_energy(ctx: commands.Context, *, args: str = ""):
    """Log daily energy. Usage: !energy [1-10] | [what drained you] | [what energized you]"""
    if not args.strip():
        await ctx.reply("Usage: `!energy [1-10] | [what drained you] | [what energized you]`")
        return

    def _run():
        try:
            import json as _ej
            from state.context.context import load_context_from_env
            from state.storage.db import get_conn
            from zoneinfo import ZoneInfo as _ZI
            from datetime import datetime as _dt

            _PDT = _ZI("America/Los_Angeles")
            parts = [p.strip() for p in args.split("|")]
            score_str = parts[0]
            score = int(score_str) if score_str.isdigit() else 5
            score = max(1, min(10, score))
            drained = parts[1] if len(parts) > 1 else ""
            energized = parts[2] if len(parts) > 2 else ""

            _ctx = load_context_from_env()
            with get_conn(_ctx.org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO events
                    (org_id, event_type, payload_json, handled_by)
                    VALUES (%s, %s, %s, %s)
                """,
                    (
                        str(_ctx.org_id),
                        "energy_checkin",
                        _ej.dumps(
                            {
                                "score": score,
                                "drained": drained,
                                "energized": energized,
                                "date": _dt.now(_PDT).strftime("%Y-%m-%d"),
                            }
                        ),
                        "dex_energy",
                    ),
                )

            emoji = "🔴" if score <= 3 else "🟡" if score <= 6 else "🟢"
            lines = [f"{emoji} Energy logged: {score}/10"]
            if drained:
                lines.append(f"Drained by: {drained}")
            if energized:
                lines.append(f"Energized by: {energized}")
            if score <= 4:
                lines.append(
                    "\n⚠️ Low energy day. Run `!yield` on your task list "
                    "tomorrow to find what to remove."
                )
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="year")
async def cmd_year(ctx: commands.Context):
    """View annual plan (Annual Architecture)."""

    def _run():
        try:
            from control_plane.scheduling.ideal_week import get_annual_architecture

            plan = get_annual_architecture()
            if not plan:
                return (
                    "📅 No annual plan set yet.\n"
                    "Build one with Claude Code using the annual architecture format:\n"
                    "`save_preloaded_year({q1: {rocks: [], revenue_target: 0}, ...})`"
                )
            lines = ["📅 **Annual Architecture:**"]
            for q in ["q1", "q2", "q3", "q4"]:
                qdata = plan.get(q, {})
                if qdata:
                    lines.append(f"\n**{q.upper()}:**")
                    for r in qdata.get("rocks", []):
                        lines.append(f"• {r}")
                    target = qdata.get("revenue_target", 0)
                    if target:
                        lines.append(f"Revenue target: ${target:,.0f}/mo")
            vacation = plan.get("vacation_blocks", [])
            if vacation:
                lines.append("\n**Vacation blocks:**")
                for v in vacation:
                    lines.append(f"• {v}")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="rocks")
async def cmd_rocks(ctx: commands.Context):
    """View this quarter's rocks."""

    def _run():
        try:
            from control_plane.scheduling.ideal_week import get_current_quarter_rocks
            from datetime import datetime as _rdt

            rocks = get_current_quarter_rocks()
            if not rocks:
                return "🪨 No quarterly rocks set. Use Claude Code to call `save_preloaded_year()` with your plan."
            month = _rdt.now().month
            quarter = f"Q{(month - 1) // 3 + 1}"
            lines = [f"🪨 **{quarter} Rocks:**"]
            for i, rock in enumerate(rocks, 1):
                lines.append(f"{i}. {rock}")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


# ─── Invoice commands ─────────────────────────────────────────────────────────


@bot.command(name="invoices")
async def cmd_invoices(ctx: commands.Context):
    """List all invoices. Usage: !invoices"""

    def _run():
        try:
            from state.finance.expense_tracker import get_invoices, get_overdue_invoices

            all_inv = get_invoices()
            overdue = get_overdue_invoices()
            if not all_inv:
                return (
                    "📄 No invoices yet.\n"
                    "Create one: `!invoice [client] | [email] | [description] | [amount]`"
                )
            overdue_ids = {i.get("invoice_id") for i in overdue}
            lines = [f"📄 **Invoices ({len(all_inv)}):**"]
            for inv in all_inv[:8]:
                if inv.get("invoice_id") in overdue_ids:
                    status_emoji = "🔴"
                elif inv.get("status") == "unpaid":
                    status_emoji = "🟡"
                else:
                    status_emoji = "✅"
                lines.append(
                    f"{status_emoji} {inv['invoice_id']} — "
                    f"{inv['client_name']} — "
                    f"${inv['total']:,.2f} — "
                    f"due {inv['due_date']}"
                )
            if overdue:
                lines.append(f"\n🔴 {len(overdue)} overdue")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="invoice")
async def cmd_invoice(ctx: commands.Context, *, args: str = ""):
    """Create an invoice. Usage: !invoice [client] | [email] | [description] | [amount]"""
    if "|" not in args:
        await ctx.reply(
            "Usage: `!invoice [client name] | [email] | [description] | [amount]`\n"
            "Example: `!invoice Acme Corp | billing@acme.com | AI Setup | 5000`"
        )
        return

    def _run():
        try:
            from state.finance.expense_tracker import create_invoice, generate_invoice_text

            parts = [p.strip() for p in args.split("|")]
            inv = create_invoice(
                client_name=parts[0],
                client_email=parts[1],
                items=[
                    {
                        "description": parts[2],
                        "amount": float(parts[3]),
                        "quantity": 1,
                    }
                ],
            )
            if inv:
                text = generate_invoice_text(inv)
                return (
                    f"📄 **Invoice created: {inv['invoice_id']}**\n"
                    f"```\n{text[:800]}\n```\n"
                    f"Total: ${inv['total']:,.2f} — Due: {inv['due_date']}"
                )
            return "❌ Failed to create invoice."
        except Exception as e:
            return f"❌ Error: {e}"

    await ctx.reply("📄 Creating invoice...")
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="expensereport")
async def cmd_expensereport(ctx: commands.Context, month: str = ""):
    """Monthly expense report. Usage: !expensereport [YYYY-MM optional]"""

    def _run():
        try:
            from state.finance.expense_tracker import generate_expense_report

            return generate_expense_report(month or None)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, f"📊 **Expense Report:**\n```\n{report}\n```")


@bot.command(name="budget")
async def cmd_budget(ctx: commands.Context, target: str = "10000"):
    """Budget vs actual. Usage: !budget [revenue target optional]"""

    def _run():
        try:
            from state.finance.expense_tracker import generate_budget_vs_actual

            t = float(target.replace("$", "").replace(",", ""))
            return generate_budget_vs_actual(revenue_target=t)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, f"📊 **Budget vs Actual:**\n```\n{report}\n```")


# ─── Doc / brief / slides / factcheck commands ────────────────────────────────


@bot.command(name="briefdoc")
async def cmd_briefdoc(ctx: commands.Context, *, args: str = ""):
    """Create a briefing doc. Usage: !briefdoc [title] | [topic] | [context optional]"""
    if not args:
        await ctx.reply("Usage: `!briefdoc [title] | [topic] | [context optional]`")
        return

    def _run():
        try:
            from adapters.google_workspace.doc_creator import create_briefing_doc

            parts = [p.strip() for p in args.split("|")]
            title = parts[0]
            topic = parts[1] if len(parts) > 1 else title
            context = parts[2] if len(parts) > 2 else ""
            result = create_briefing_doc(title, topic, context)
            if result.get("content"):
                preview = result["content"][:800]
                drive_id = result.get("drive_file", {}).get("id", "")
                out = f"📝 **Briefing: {title}**\n```\n{preview}\n```"
                if drive_id:
                    out += f"\n📁 Drive: `{drive_id}`"
                return out
            return f"❌ Failed: {result.get('error')}"
        except Exception as e:
            return f"❌ Error: {e}"

    await ctx.reply("📝 Creating briefing doc...")
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="board")
async def cmd_board(ctx: commands.Context, *, args: str = ""):
    """Generate board update doc. Usage: !board [context optional]"""

    def _run():
        try:
            from adapters.google_workspace.doc_creator import create_briefing_doc
            from control_plane.strategy.portfolio_advisor import PortfolioAdvisor as PortfolioAgent
            from state.context.context import load_context_from_env

            ctx_eos = load_context_from_env()
            pa = PortfolioAgent(ctx_eos)
            ventures = pa.scan_all_ventures()
            portfolio_context = pa.generate_portfolio_brief(ventures)
            result = create_briefing_doc(
                title="Board Update",
                topic="Monthly portfolio review",
                context=portfolio_context + ("\n" + args if args else ""),
                doc_type="board_update",
            )
            if result.get("content"):
                return f"📋 **Board Update:**\n```\n{result['content'][:1200]}\n```"
            return "❌ Failed to generate."
        except Exception as e:
            return f"❌ Error: {e}"

    await ctx.reply("📋 Generating board update...")
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="investor")
async def cmd_investor(ctx: commands.Context, *, args: str = ""):
    """Generate investor update. Usage: !investor [context optional]"""

    def _run():
        try:
            from adapters.google_workspace.doc_creator import create_briefing_doc

            result = create_briefing_doc(
                title="Investor Update",
                topic="Monthly progress update",
                context=args,
                doc_type="investor_update",
            )
            if result.get("content"):
                return f"📊 **Investor Update:**\n```\n{result['content'][:1200]}\n```"
            return "❌ Failed to generate."
        except Exception as e:
            return f"❌ Error: {e}"

    await ctx.reply("📊 Generating investor update...")
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="slides")
async def cmd_slides(ctx: commands.Context, *, args: str = ""):
    """Generate presentation outline. Usage: !slides [title] | [topic] | [count optional]"""
    if not args:
        await ctx.reply("Usage: `!slides [title] | [topic] | [slide count optional]`")
        return

    def _run():
        try:
            from adapters.google_workspace.doc_creator import create_presentation_outline

            parts = [p.strip() for p in args.split("|")]
            title = parts[0]
            topic = parts[1] if len(parts) > 1 else title
            count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 10
            result = create_presentation_outline(title, topic, count)
            slide_list = result.get("slides", {}).get("slides", [])
            if slide_list:
                lines = [f"📊 **{title} — {len(slide_list)} slides:**"]
                for s in slide_list[:5]:
                    lines.append(f"{s['number']}. **{s['title']}** — {s['key_message']}")
                if len(slide_list) > 5:
                    lines.append(f"... and {len(slide_list) - 5} more slides")
                drive_id = result.get("drive_file", {}).get("id", "")
                if drive_id:
                    lines.append(f"\n📁 Full outline saved to Drive: `{drive_id}`")
                return "\n".join(lines)
            return f"❌ Failed: {result.get('error')}"
        except Exception as e:
            return f"❌ Error: {e}"

    await ctx.reply("📊 Creating presentation outline...")
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="factcheck")
async def cmd_factcheck(ctx: commands.Context, *, claim: str = ""):
    """Fact-check a claim. Usage: !factcheck [claim]"""
    if not claim:
        await ctx.reply("Usage: `!factcheck [claim to verify]`")
        return

    def _run():
        try:
            from adapters.google_workspace.doc_creator import fact_check

            result = fact_check(claim)
            verdict_emoji = {
                "TRUE": "✅",
                "FALSE": "❌",
                "PARTIALLY TRUE": "⚠️",
                "UNVERIFIABLE": "❓",
            }.get(result.get("verdict", ""), "❓")
            return (
                f"{verdict_emoji} **{result['verdict']}** "
                f"(confidence: {result['confidence']})\n"
                f"{result['explanation']}"
            )
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


# ─── Personal admin commands ──────────────────────────────────────────────────


@bot.command(name="dates")
async def cmd_dates(ctx: commands.Context):
    """List upcoming important dates (60 days). Usage: !dates"""

    def _run():
        try:
            from control_plane.scheduling.personal_admin import get_upcoming_dates

            dates = get_upcoming_dates(days=60)
            if not dates:
                return (
                    "📅 No important dates tracked yet.\n"
                    "Add with: `!adddate [person] | [MM-DD or YYYY-MM-DD] | [type]`\n"
                    "Types: birthday, anniversary, work_anniversary, other"
                )
            lines = ["📅 **Upcoming important dates (60 days):**"]
            for d in dates:
                days_until = d.get("days_until", "?")
                if isinstance(days_until, int):
                    urgency = "🔴" if days_until <= 7 else "🟡" if days_until <= 14 else "🔵"
                else:
                    urgency = "🔵"
                lines.append(
                    f"{urgency} {d['person']} — {d['type']} — in {days_until} days ({d['date']})"
                )
                if d.get("notes"):
                    lines.append(f"   _{d['notes']}_")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="adddate")
async def cmd_adddate(ctx: commands.Context, *, args: str = ""):
    """Add an important date. Usage: !adddate [person] | [MM-DD] | [type] | [notes optional]"""
    if "|" not in args:
        await ctx.reply(
            "Usage: `!adddate [person] | [MM-DD or YYYY-MM-DD] | [type] | [notes optional]`\n"
            "Types: birthday, anniversary, work_anniversary, other"
        )
        return

    def _run():
        try:
            from control_plane.scheduling.personal_admin import add_important_date

            parts = [p.strip() for p in args.split("|")]
            ok = add_important_date(
                person=parts[0],
                date=parts[1],
                date_type=parts[2],
                notes=parts[3] if len(parts) > 3 else "",
            )
            if ok:
                return f"📅 Date added: **{parts[0]}** — {parts[2]} on {parts[1]}"
            return "❌ Failed to add date."
        except Exception as e:
            return f"❌ Error: {e}"

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name="gift")
async def cmd_gift(ctx: commands.Context, *, args: str = ""):
    """Research gift ideas. Usage: !gift [person] | [occasion] | [budget optional]"""
    if "|" not in args:
        await ctx.reply(
            "Usage: `!gift [person] | [occasion] | [budget optional]`\n"
            "Example: `!gift Mom | birthday | 150`"
        )
        return

    def _run():
        try:
            from control_plane.scheduling.personal_admin import research_gift

            parts = [p.strip() for p in args.split("|")]
            person = parts[0]
            occasion = parts[1] if len(parts) > 1 else "birthday"
            budget = float(parts[2].replace("$", "")) if len(parts) > 2 else 100
            ideas = research_gift(person, occasion, budget)
            return f"🎁 **Gift ideas for {person} — {occasion}:**\n{ideas[:1500]}"
        except Exception as e:
            return f"❌ Error: {e}"

    await ctx.reply("🎁 Researching gifts...")
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


# ─── Travel research commands ─────────────────────────────────────────────────


@bot.command(name="flights")
async def cmd_flights(ctx: commands.Context, *, args: str = ""):
    """Research flights. Usage: !flights [from] | [to] | [date] | [return optional]"""
    if "|" not in args:
        await ctx.reply("Usage: `!flights [from] | [to] | [date] | [return date optional]`")
        return

    def _run():
        try:
            from adapters.calendar.travel_manager import research_flights

            parts = [p.strip() for p in args.split("|")]
            result = research_flights(
                origin=parts[0],
                destination=parts[1],
                date=parts[2] if len(parts) > 2 else "",
                return_date=parts[3] if len(parts) > 3 else "",
            )
            return f"✈️ **Flight research — {parts[0]} → {parts[1]}:**\n{result}"
        except Exception as e:
            return f"❌ Error: {e}"

    await ctx.reply("✈️ Researching flights...")
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="hotels")
async def cmd_hotels(ctx: commands.Context, *, args: str = ""):
    """Research hotels. Usage: !hotels [city] | [check-in] | [check-out] | [budget optional]"""
    if "|" not in args:
        await ctx.reply(
            "Usage: `!hotels [city] | [check-in] | [check-out] | [budget/night optional]`"
        )
        return

    def _run():
        try:
            from adapters.calendar.travel_manager import research_hotels

            parts = [p.strip() for p in args.split("|")]
            city = parts[0]
            check_in = parts[1] if len(parts) > 1 else ""
            check_out = parts[2] if len(parts) > 2 else ""
            budget = float(parts[3].replace("$", "")) if len(parts) > 3 else 200
            result = research_hotels(city, check_in, check_out, budget)
            return f"🏨 **Hotels — {city}:**\n{result}"
        except Exception as e:
            return f"❌ Error: {e}"

    await ctx.reply("🏨 Researching hotels...")
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="restaurants")
async def cmd_restaurants(ctx: commands.Context, *, args: str = ""):
    """Research restaurants. Usage: !restaurants [city] | [occasion] | [budget]"""
    if not args:
        await ctx.reply("Usage: `!restaurants [city] | [occasion] | [budget]`")
        return

    def _run():
        try:
            from adapters.calendar.travel_manager import research_restaurants

            parts = [p.strip() for p in args.split("|")]
            city = parts[0]
            occasion = parts[1] if len(parts) > 1 else "business dinner"
            budget = parts[2] if len(parts) > 2 else "moderate"
            result = research_restaurants(city, occasion, budget)
            return f"🍽️ **Restaurants — {city}:**\n{result}"
        except Exception as e:
            return f"❌ Error: {e}"

    await ctx.reply("🍽️ Researching restaurants...")
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await _send_reply(ctx.channel, output)


@bot.command(name="proofread")
async def cmd_proofread(ctx: commands.Context, *, content: str = ""):
    """Proofread outgoing communications. Usage: !proofread [paste your text here]"""
    if not content:
        await ctx.reply("Usage: `!proofread [paste your email or message here]`")
        return
    try:
        from governance.quality.quality_gate import quality_check

        await ctx.reply("🔍 Running quality check...")
        result = quality_check(content)
        score = result.get("score", 0)
        approved = result.get("approved", False)
        issues = result.get("issues", [])
        suggestions = result.get("suggestions", [])
        revised = result.get("revised_version", "")

        emoji = "✅" if approved else "⚠️"
        lines = [f"{emoji} **Quality Score: {score}/10**"]
        if issues:
            lines.append("\n**Issues:**")
            for i in issues:
                lines.append(f"• {i}")
        if suggestions:
            lines.append("\n**Suggestions:**")
            for s in suggestions:
                lines.append(f"• {s}")
        if revised:
            lines.append(f"\n**Revised version:**\n```\n{revised[:600]}\n```")

        await _send_reply(ctx.channel, "\n".join(lines))
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="minutes")
async def cmd_minutes(ctx: commands.Context, *, args: str = ""):
    """Draft meeting minutes. Usage: !minutes [title] | [person] | [outcomes] | [action items]"""
    if "|" not in args:
        await ctx.reply(
            "Usage: `!minutes [meeting title] | [person] | [outcomes] | [action items]`\n"
            "Example: `!minutes Sales call | John Smith | Agreed on pricing | Send contract by Friday`"
        )
        return
    try:
        from adapters.calendar.meetings import draft_meeting_minutes

        parts = [p.strip() for p in args.split("|")]
        result = draft_meeting_minutes(
            title=parts[0],
            person=parts[1] if len(parts) > 1 else "Attendee",
            outcomes=parts[2] if len(parts) > 2 else "",
            open_loops=parts[3] if len(parts) > 3 else "",
        )
        if result.get("minutes"):
            await ctx.reply(
                f"📋 **Minutes drafted:**\n```\n{result['minutes'][:800]}\n```\nSaved to Drive."
            )
        else:
            await ctx.reply("❌ Failed to draft minutes.")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="okr")
async def cmd_okr(ctx: commands.Context, subcommand: str = "report", *, args: str = ""):
    """OKR tracking. Usage: !okr report | !okr set [venture] | [objective] | [KR, target, unit]"""
    if subcommand == "report":
        try:
            from state.metrics.okr_tracker import generate_okr_report

            report = generate_okr_report()
            await _send_reply(ctx.channel, report)
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")

    elif subcommand == "set":
        if not args or "|" not in args:
            await ctx.reply(
                "Usage: `!okr set [venture_id] | [objective] | [KR description], [target], [unit]`\n"
                "Example: `!okr set lyfe_institute | Hit first sale | Revenue, 750, $`"
            )
            return
        try:
            from state.metrics.okr_tracker import set_okr

            parts = [p.strip() for p in args.split("|")]
            venture_id = parts[0]
            objective = parts[1] if len(parts) > 1 else ""
            key_results = []
            for kr_str in parts[2:]:
                kr_parts = [p.strip() for p in kr_str.split(",")]
                if kr_parts:
                    key_results.append(
                        {
                            "kr": kr_parts[0],
                            "target": float(kr_parts[1]) if len(kr_parts) > 1 else 100,
                            "unit": kr_parts[2] if len(kr_parts) > 2 else "",
                            "current": 0,
                        }
                    )
            ok = set_okr(objective=objective, key_results=key_results, venture_id=venture_id)
            if ok:
                await ctx.reply(
                    f"🎯 **OKR set for {venture_id}:**\n"
                    f"Objective: {objective}\n"
                    f"{len(key_results)} key result(s) added."
                )
            else:
                await ctx.reply("❌ Failed to set OKR.")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")
    else:
        await ctx.reply("Usage: `!okr report` or `!okr set [venture] | [objective] | [KRs...]`")


@bot.command(name="event")
async def cmd_event(ctx: commands.Context, *, args: str = ""):
    """Manage events. Usage: !event list | !event [name] | [type] | [date] | [location] | [budget]"""
    if not args or args.strip() == "list":
        try:
            from control_plane.events.event_manager import get_events

            events = get_events()
            if not events:
                await ctx.reply(
                    "📅 No upcoming events.\n"
                    "Create: `!event [name] | [type] | [date] | [location] | [budget]`\n"
                    "Types: conference, offsite, client_dinner, team_event, speaking, podcast"
                )
                return
            lines = [f"📅 **Upcoming events ({len(events)}):**"]
            for e in events[:6]:
                lines.append(
                    f"• {e['name']} — {e['type']} — {e['date']} — {e.get('location', 'TBD')}"
                )
                incomplete = sum(1 for c in e.get("checklist", []) if not c.get("done"))
                if incomplete:
                    lines.append(f"  ⚠️ {incomplete} checklist items open")
            await ctx.reply("\n".join(lines))
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")
        return

    if "|" in args:
        parts = [p.strip() for p in args.split("|")]
        try:
            from control_plane.events.event_manager import create_event

            budget = 0.0
            if len(parts) > 4:
                try:
                    budget = float(parts[4].replace("$", "").replace(",", ""))
                except ValueError:
                    budget = 0.0
            event = create_event(
                name=parts[0],
                event_type=parts[1] if len(parts) > 1 else "other",
                date=parts[2] if len(parts) > 2 else "",
                location=parts[3] if len(parts) > 3 else "",
                budget=budget,
            )
            if event.get("name"):
                checklist_count = len(event.get("checklist", []))
                await ctx.reply(
                    f"📅 **Event created: {event['name']}**\n"
                    f"Type: {event['type']} | Date: {event['date']}\n"
                    f"✅ {checklist_count} checklist items generated"
                )
            else:
                await ctx.reply("❌ Failed to create event.")
        except Exception as e:
            await ctx.reply(f"❌ Error: {e}")
    else:
        await ctx.reply(
            "Usage:\n"
            "`!event list` — view upcoming events\n"
            "`!event [name] | [type] | [date] | [location] | [budget]` — create event"
        )


@bot.command(name="talkingpoints")
async def cmd_talkingpoints(ctx: commands.Context, *, args: str = ""):
    """Draft talking points. Usage: !talkingpoints [topic] | [audience] | [duration min] | [format]"""
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 2:
        await ctx.reply(
            "Usage: `!talkingpoints [topic] | [audience] | [duration min] | [format]`\n"
            "Formats: talk, panel, podcast, interview, workshop, webinar"
        )
        return
    try:
        from control_plane.events.event_manager import draft_talking_points

        await ctx.reply("📝 Drafting talking points...")
        topic = parts[0]
        audience = parts[1]
        duration = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 30
        fmt = parts[3] if len(parts) > 3 else "talk"
        points = draft_talking_points(topic, audience, duration, fmt)
        await _send_reply(ctx.channel, points)
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="pr")
async def cmd_pr(ctx: commands.Context, *, args: str = ""):
    """Log PR inquiry. Usage: !pr [outlet] | [contact] | [email] | [topic] | [deadline]"""
    if "|" not in args:
        await ctx.reply(
            "Usage: `!pr [outlet] | [contact name] | [email] | [topic] | [deadline]`\n"
            "Example: `!pr TechCrunch | Jane Smith | jane@tc.com | AI in business | March 15`"
        )
        return
    try:
        from control_plane.events.event_manager import log_pr_media_inquiry

        parts = [p.strip() for p in args.split("|")]
        ok = log_pr_media_inquiry(
            outlet=parts[0],
            contact_name=parts[1] if len(parts) > 1 else "",
            contact_email=parts[2] if len(parts) > 2 else "",
            topic=parts[3] if len(parts) > 3 else "",
            deadline=parts[4] if len(parts) > 4 else "",
        )
        if ok:
            await ctx.reply(
                f"📰 PR inquiry logged: {parts[0]}\n"
                f"Contact: {parts[1] if len(parts) > 1 else 'Unknown'}"
            )
        else:
            await ctx.reply("❌ Failed to log PR inquiry.")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="board_update")
async def cmd_board_update(ctx: commands.Context, venture_id: str = ""):
    """Generate board update brief. Usage: !board_update [venture_id]"""
    if not venture_id:
        await ctx.reply(
            "Usage: `!board_update [venture_id]`\nExample: `!board_update lyfe_institute`"
        )
        return
    try:
        from understanding.intelligence.stakeholder_map import generate_board_update_brief

        await ctx.reply("📋 Generating board update...")
        brief = generate_board_update_brief(venture_id)
        await _send_reply(ctx.channel, f"📋 **Board Update — {venture_id}:**\n{brief}")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="announce")
async def cmd_announce(ctx: commands.Context, *, args: str = ""):
    """Draft announcement. Usage: !announce [topic] | [audience] | [key message] | [type: internal/public/press_release]"""
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 3:
        await ctx.reply(
            "Usage: `!announce [topic] | [audience] | [key message] | [type]`\n"
            "Types: internal, team, public, press_release\n"
            "Example: `!announce New program launch | Existing clients | Game of Lyfe is live | public`"
        )
        return
    try:
        from adapters.google_workspace.doc_creator import draft_announcement

        draft = draft_announcement(
            topic=parts[0],
            audience=parts[1],
            key_message=parts[2],
            announcement_type=parts[3] if len(parts) > 3 else "internal",
        )
        await ctx.reply(f"📢 **Announcement draft:**\n```\n{draft[:1500]}\n```")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="crisis")
async def cmd_crisis(ctx: commands.Context, *, args: str = ""):
    """Draft crisis communication. Usage: !crisis [situation] | [affected parties] | [what happened] | [what we are doing]"""
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 3:
        await ctx.reply(
            "Usage: `!crisis [situation] | [affected parties] | [what happened] | [what we are doing]`"
        )
        return
    try:
        from adapters.google_workspace.doc_creator import draft_crisis_communication

        draft = draft_crisis_communication(
            situation=parts[0],
            affected_parties=parts[1] if len(parts) > 1 else "Stakeholders",
            what_happened=parts[2] if len(parts) > 2 else "",
            what_we_are_doing=parts[3] if len(parts) > 3 else "",
        )
        await ctx.reply(f"🚨 **Crisis communication draft:**\n```\n{draft[:1500]}\n```")
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="itinerary")
async def cmd_itinerary(ctx: commands.Context, *, args: str = ""):
    """Generate trip itinerary. Usage: !itinerary [trip name] | [destination] | [start date] | [end date] | [hotel]"""
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 3:
        await ctx.reply(
            "Usage: `!itinerary [trip name] | [destination] | [start date] | [end date] | [hotel]`\n"
            "Example: `!itinerary NYC Trip | New York | 2026-04-10 | 2026-04-13 | The Beekman Hotel`"
        )
        return
    try:
        from adapters.calendar.travel_manager import generate_trip_itinerary

        await ctx.reply("✈️ Generating itinerary...")
        itinerary = generate_trip_itinerary(
            trip_name=parts[0],
            destination=parts[1],
            start_date=parts[2],
            end_date=parts[3] if len(parts) > 3 else parts[2],
            hotel=parts[4] if len(parts) > 4 else "",
        )
        await ctx.reply(
            f"✈️ **Itinerary: {parts[0]}**\n```\n{itinerary[:1500]}\n```\nSaved to Drive."
        )
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="approve_task")
async def cmd_approve_task(ctx: commands.Context, task_id: str = ""):
    """Approve a pending agent task result. Usage: !approve_task [task_id]"""
    if not task_id:
        await ctx.reply("Usage: `!approve_task [task_id]`")
        return
    try:
        import json as _json
        from state.context.context import load_context_from_env
        from state.storage.db import get_conn

        _ctx = load_context_from_env()

        with get_conn(_ctx.org_id) as cur:
            cur.execute(
                """
                SELECT id, payload_json
                FROM events
                WHERE org_id = %s
                AND event_type = 'agent_task_result'
                AND payload_json->>'task_id' LIKE %s
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (str(_ctx.org_id), f"{task_id}%"),
            )
            row = cur.fetchone()

        if not row:
            await ctx.reply(f"Task `{task_id}` not found.")
            return

        payload = row["payload_json"]
        if isinstance(payload, str):
            payload = _json.loads(payload)

        with get_conn(_ctx.org_id) as cur:
            cur.execute(
                """
                UPDATE events
                SET payload_json = payload_json ||
                    '{"approved": true}'::jsonb
                WHERE id = %s
            """,
                (row["id"],),
            )

        result_preview = payload.get("result", "")[:300]
        await ctx.reply(
            f"✅ Task approved: "
            f"{payload.get('description', '')[:60]}\n"
            f"Agent: {payload.get('agent_id', '')}\n"
            f"Result: {result_preview}"
        )
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="tasks")
async def cmd_tasks(ctx: commands.Context):
    """Show pending task queue split by human vs AI."""
    try:
        from state.context.context import load_context_from_env
        from control_plane.coordination.coordination_engine import CoordinationEngine

        _ctx = load_context_from_env()
        coordination = CoordinationEngine(_ctx)

        all_pending = coordination.get_task_queue(status="pending")
        ai_tasks = [t for t in all_pending if t.get("assignee_type") == "agent"]
        human_tasks = [t for t in all_pending if t.get("assignee_type") == "human"]

        lines = [f"📋 **Task Queue — {len(all_pending)} pending:**"]

        if human_tasks:
            lines.append(f"\n👤 **You need to handle ({len(human_tasks)}):**")
            for t in human_tasks[:5]:
                lines.append(f"• [{t['priority']}] {t['description'][:60]}")

        if ai_tasks:
            lines.append(f"\n🤖 **Agents handling ({len(ai_tasks)}):**")
            for t in ai_tasks[:5]:
                lines.append(f"• [{t['priority']}] {t['assignee_id']} — {t['description'][:50]}")

        if not all_pending:
            lines.append("✅ Queue is empty.")

        await _send_reply(ctx.channel, "\n".join(lines))
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="agent_results")
async def cmd_agent_results(ctx: commands.Context):
    """Show last 24h agent task results."""
    try:
        import json as _json
        from state.context.context import load_context_from_env
        from state.storage.db import get_conn

        _ctx = load_context_from_env()

        with get_conn(_ctx.org_id) as cur:
            cur.execute(
                """
                SELECT payload_json, created_at
                FROM events
                WHERE org_id = %s
                AND event_type = 'agent_task_result'
                AND created_at >= NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
                LIMIT 10
            """,
                (str(_ctx.org_id),),
            )
            rows = cur.fetchall()

        if not rows:
            await ctx.reply("📋 No agent results in last 24h.")
            return

        lines = [f"📋 **Agent results ({len(rows)} last 24h):**"]
        for r in rows:
            p = r["payload_json"]
            if isinstance(p, str):
                p = _json.loads(p)
            approved = "✅" if p.get("approved") else ("⚠️" if p.get("requires_approval") else "🔵")
            lines.append(f"{approved} {p.get('agent_id', '')} — {p.get('description', '')[:50]}")

        await _send_reply(ctx.channel, "\n".join(lines))
    except Exception as e:
        await ctx.reply(f"❌ Error: {e}")


@bot.command(name="trace")
async def cmd_trace(ctx: commands.Context, limit: int = 5):
    """Show recent execution traces (builder mode only)."""
    try:
        from execution.transport.discord_mode_routing import resolve_discord_mode

        gid = str(ctx.guild.id) if ctx.guild else None
        cid = str(ctx.channel.id)
        mode = resolve_discord_mode(gid, cid)

        if mode == "product":
            await ctx.reply("Trace output is not available in product mode.")
            return

        from execution.transport.execution_trace import (
            format_trace_compact,
            get_trace_history,
        )

        capped = max(1, min(limit, 20))
        traces = get_trace_history().latest(limit=capped)
        if not traces:
            await ctx.reply("No traces recorded yet.")
            return

        lines = [f"**Execution Traces** (last {len(traces)}):", "```"]
        for t in traces:
            lines.append(format_trace_compact(t))
        lines.append("```")
        await _send_reply(ctx.channel, "\n".join(lines))
    except Exception as e:
        await ctx.reply(f"Trace error: {e}", tts=False)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("[Discord] DISCORD_BOT_TOKEN not set in .env — exiting")
        sys.exit(1)

    print(f"[Discord] Starting {AI_NAME} Discord bot...")
    bot.run(token, reconnect=True)
    # No in-process restart loop — py-cord closes the event loop on exit
    # and it cannot be reused. Docker restart: on-failure handles restarts
    # at the process level, giving each restart a fresh event loop.
