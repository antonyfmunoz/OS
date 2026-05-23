"""
Discord bot commands — extracted from discord_bot.py.

All @bot.command decorated functions live here.
Registered at import time via register_commands(bot, ...).
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import discord
from discord.ext import commands

from substrate.observability.error_recorder import record_error as _record_error
from substrate.execution.bridge.session_discord_bridge import send_reply as _send_reply

# ─── Shared context (set by register_commands) ──────────────────────────────

_ctx: dict = {}


def register_commands(
    bot: commands.Bot,
    *,
    ctx_eos,
    gateway,
    ve,
    onboarding,
    run_gateway,
    run_day_command,
    format_day_result,
    send_day_response,
    ai_name_getter,
    default_venture_id: str,
    founder_id: int,
    repo_root: Path,
    discord_server_manager_cls,
) -> None:
    """Register all bot commands.  Called once from discord_bot.py."""
    _ctx.update(
        bot=bot,
        ctx_eos=ctx_eos,
        gateway=gateway,
        ve=ve,
        onboarding=onboarding,
        run_gateway=run_gateway,
        run_day_command=run_day_command,
        format_day_result=format_day_result,
        send_day_response=send_day_response,
        ai_name_getter=ai_name_getter,
        default_venture_id=default_venture_id,
        founder_id=founder_id,
        repo_root=repo_root,
        DiscordServerManager=discord_server_manager_cls,
    )

    # ── Accessor shortcuts ──────────────────────────────────────────────
    def _ai_name() -> str:
        return _ctx["ai_name_getter"]()

    FOUNDER_ID = founder_id
    _REPO_ROOT = repo_root
    _gateway = gateway
    _ctx_eos = ctx_eos
    _onboarding = onboarding
    _ve = ve
    _DEFAULT_VENTURE_ID = default_venture_id
    DiscordServerManager = discord_server_manager_cls

    # ─── Session watcher commands ────────────────────────────────────────

    @bot.command(name="answer")
    async def cmd_answer(ctx: commands.Context, session_name: str, *, text: str):
        """Answer a CC session question: !answer dex_builder_main <your answer>"""
        if ctx.author.id != FOUNDER_ID:
            await ctx.reply("Founder only.")
            return
        try:
            from substrate.execution.bridge.session_discord_bridge import get_bridge

            result = await get_bridge().handle_answer_command(session_name, text)
            await ctx.reply(result)
        except Exception as e:
            _record_error("cmd_answer", e)
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
            _record_error("cmd_mfa", e)
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
            _record_error("cmd_fire_export", e)
            await ctx.reply(f"Error: {e}")

    @bot.command(name="watcher_status")
    async def cmd_watcher_status(ctx: commands.Context):
        """Show session watcher status."""
        if ctx.author.id != FOUNDER_ID:
            await ctx.reply("Founder only.")
            return
        try:
            import time as _time

            from substrate.execution.bridge.session_watcher import _WATCHERS, _WATCHERS_LOCK

            with _WATCHERS_LOCK:
                if not _WATCHERS:
                    await ctx.reply("No watchers running.")
                    return
                from substrate.execution.bridge.discord_output_policy import get_display_name

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
            _record_error("cmd_watcher_status", e)
            await ctx.reply(f"Error: {e}")

    # ─── Core commands ───────────────────────────────────────────────────

    @bot.command(name="brief")
    async def cmd_brief(ctx: commands.Context):
        """Trigger morning brief on demand."""
        _run_gw = _ctx["run_gateway"]
        async with ctx.typing():
            loop = asyncio.get_event_loop()
            output = await loop.run_in_executor(
                None,
                lambda: _run_gw("morning brief", ctx.channel.name, str(ctx.author)),
            )
        await ctx.reply(output or "Brief generated.")

    @bot.command(name="status")
    async def cmd_status(ctx: commands.Context):
        """Portfolio health check — scans all ventures and shows binding constraint."""
        async with ctx.typing():
            loop = asyncio.get_event_loop()

            def _portfolio_scan():
                try:
                    from substrate.control_plane.strategy.portfolio_advisor import (
                        PortfolioAdvisor as PortfolioAgent,
                    )

                    pa = PortfolioAgent(_ctx_eos)
                    ventures = pa.scan_all_ventures()
                    return pa.generate_portfolio_brief(ventures)
                except Exception as e:
                    _record_error("portfolio_scan", e)
                    return f"Portfolio scan failed: {e}"

            output = await loop.run_in_executor(None, _portfolio_scan)

        await _send_reply(ctx.channel, output or "Status retrieved.")

    @bot.command(name="portfolio")
    async def cmd_portfolio(ctx: commands.Context):
        """Trigger the weekly portfolio brief on demand."""
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
            f"🎙️ **{_ai_name()} connected.** Talk to me. Drop an audio file and I'll transcribe + respond.",
        )
        if not already_connected:
            # Import _listen_loop from main module (no circular import risk —
            # commands module is imported after _listen_loop is defined)
            from services.discord_bot import _listen_loop

            await asyncio.sleep(3)
            asyncio.create_task(_listen_loop(vc, ctx.channel))

    @bot.command(name="leave")
    async def cmd_leave(ctx: commands.Context):
        """Disconnect from voice channel."""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await _send_reply(ctx.channel, f"👁️ **{_ai_name()} disconnected.**")
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
            _record_error("cmd_outcome", e)
            await ctx.reply(f"❌ Failed: {e}")

    @bot.command(name="eod")
    async def cmd_eod(ctx: commands.Context):
        """Trigger EOD sync manually."""
        subprocess.Popen(["python3", str(_REPO_ROOT / "scripts" / "eod_sync.py")])
        await ctx.reply("📊 EOD sync running...")

    @bot.command(name="openday")
    async def cmd_openday(ctx: commands.Context, *, args: str = ""):
        """Open the operator's day. Usage: !openday [workspace=builder] [node=local]"""
        if ctx.author.id != FOUNDER_ID:
            await ctx.reply("Founder only.")
            return
        _run_day_cmd = _ctx["run_day_command"]
        _fmt_day = _ctx["format_day_result"]
        _send_day = _ctx["send_day_response"]
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
                lambda: _run_day_cmd(
                    "open_day",
                    workspace=workspace,
                    node_preference=node_pref,
                    discord_channel_id=str(ctx.channel.id),
                ),
            )
            formatted = _fmt_day(result)
            await _send_day(ctx.channel, formatted)

    @bot.command(name="closeday")
    async def cmd_closeday(ctx: commands.Context, *, args: str = ""):
        """Close the operator's day. Usage: !closeday [continuity notes as free text]"""
        if ctx.author.id != FOUNDER_ID:
            await ctx.reply("Founder only.")
            return
        _run_day_cmd = _ctx["run_day_command"]
        _fmt_day = _ctx["format_day_result"]
        _send_day = _ctx["send_day_response"]
        continuity = args.strip() if args.strip() else None
        async with ctx.typing():
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: _run_day_cmd(
                    "close_day",
                    continuity_text=continuity,
                    discord_channel_id=str(ctx.channel.id),
                ),
            )
            formatted = _fmt_day(result)
            await _send_day(ctx.channel, formatted)

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
            _record_error("cmd_accept", e)
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
            _record_error("cmd_decline", e)
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
            from substrate.state.context.context import load_context_from_env
            from substrate.state.storage.db import get_conn
            from adapters.google_workspace.gws_connector import GWSConnector
            from substrate.governance.quality.quality_gate import gate_outgoing_email
            import json as _json

            _local_ctx = load_context_from_env()

            with get_conn(_local_ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT id, payload_json FROM events
                    WHERE org_id = %s
                    AND event_type = 'email_draft_pending'
                    AND payload_json->>'status' = 'pending_approval'
                    ORDER BY created_at DESC
                    LIMIT 1
                """,
                    (str(_local_ctx.org_id),),
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
                        with get_conn(_local_ctx.org_id) as cur:
                            cur.execute(
                                """
                                UPDATE events
                                SET payload_json = payload_json ||
                                    '{"awaiting_force_send": true}'::jsonb
                                WHERE id = %s
                            """,
                                (row["id"],),
                            )
                        return
                except Exception as _qg_err:
                    _record_error("quality_gate", _qg_err)

            # Send the email
            if to_email:
                gws = GWSConnector()
                result = gws.send_email(
                    to_email=to_email,
                    subject=subject,
                    body=body,
                )
                if result.get("id"):
                    with get_conn(_local_ctx.org_id) as cur:
                        cur.execute(
                            """
                            UPDATE events
                            SET payload_json = payload_json ||
                                '{"status": "sent"}'::jsonb
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
                with get_conn(_local_ctx.org_id) as cur:
                    cur.execute(
                        """
                        UPDATE events
                        SET payload_json = payload_json ||
                            '{"status": "approved"}'::jsonb
                        WHERE id = %s
                    """,
                        (row["id"],),
                    )
                await ctx.reply(
                    f"✅ Approved (no recipient email on file).\nDraft:\n```\n{draft[:400]}\n```"
                )
        except Exception as e:
            _record_error("cmd_unknown", e)
            await ctx.reply(f"❌ Error: {e}")

    @bot.command(name="force_send")
    async def cmd_force_send(ctx: commands.Context):
        """Force-send an email that failed the quality gate."""
        try:
            from substrate.state.context.context import load_context_from_env
            from substrate.state.storage.db import get_conn
            from adapters.google_workspace.gws_connector import GWSConnector
            import json as _json

            _local_ctx = load_context_from_env()

            with get_conn(_local_ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT id, payload_json FROM events
                    WHERE org_id = %s
                    AND event_type = 'email_draft_pending'
                    AND payload_json->>'awaiting_force_send' = 'true'
                    ORDER BY created_at DESC
                    LIMIT 1
                """,
                    (str(_local_ctx.org_id),),
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
                with get_conn(_local_ctx.org_id) as cur:
                    cur.execute(
                        """
                        UPDATE events
                        SET payload_json = payload_json ||
                            '{"status": "sent", "force_sent": true}'::jsonb
                        WHERE id = %s
                    """,
                        (row["id"],),
                    )
                await ctx.reply(f"✅ Force sent to {to_email}")
            else:
                await ctx.reply("❌ Send failed. Check GWS token.")
        except Exception as e:
            _record_error("cmd_force_send", e)
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
            from substrate.governance.policy.confidentiality import create_confidential_session

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
            _record_error("cmd_confidential", e)
            await ctx.reply(f"❌ Error: {e}")

    @bot.command(name="pending")
    async def cmd_pending(ctx: commands.Context):
        """Show all pending approval emails."""
        try:
            from substrate.state.context.context import load_context_from_env
            from substrate.state.storage.db import get_conn
            import json as _json

            _local_ctx = load_context_from_env()
            with get_conn(_local_ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT id, payload_json, created_at
                    FROM events
                    WHERE org_id = %s
                    AND event_type = 'email_draft_pending'
                    AND payload_json->>'status' = 'pending_approval'
                    ORDER BY created_at DESC
                    LIMIT 10
                """,
                    (str(_local_ctx.org_id),),
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
            _record_error("cmd_pending", e)
            await ctx.reply(f"❌ Error: {e}")

    @bot.command(name="relationship")
    async def cmd_relationship(ctx: commands.Context, *, name: str = ""):
        """Show relationship health for a contact. Usage: !relationship [name]"""
        if not name:
            await ctx.reply("Usage: `!relationship [contact name]`")
            return
        try:
            from substrate.understanding.intelligence.person_recognition import (
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
            _record_error("cmd_relationship", e)
            await ctx.reply(f"❌ Error: {e}")

    @bot.command(name="nurture")
    async def cmd_nurture(ctx: commands.Context, *, name: str = ""):
        """Draft a warm check-in message for a contact. Usage: !nurture [name]"""
        if not name:
            await ctx.reply("Usage: `!nurture [contact name]`")
            return
        try:
            from substrate.understanding.intelligence.person_recognition import build_intelligence_profile

            profile = build_intelligence_profile(name=name)
            notes = getattr(profile, "notes", None) or "No prior context available"
            last_contact = getattr(profile, "last_contact", None) or "unknown"

            draft = (
                f"Subject: Hey {name}\n\n"
                f"Hey {name}, been a minute — hope you're doing well. "
                f"Would love to catch up when you have time.\n\n"
                f"— Antony"
            )
            try:
                from substrate.execution.runtime.model_router import get_router, TaskType

                _router = get_router()
                _model = _router.route(TaskType.FAST_RESPONSE)
                ai_draft = _router.call(
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
                if ai_draft and len(ai_draft) > 20:
                    draft = ai_draft
            except Exception as _nd_err:
                _record_error("nurture_ai_draft", _nd_err, {"contact": name})

            await ctx.reply(
                f"📧 Check-in draft for {name}:\n```\n{draft[:500]}\n```\n`!approve_followup` to send."
            )
        except Exception as e:
            _record_error("cmd_nurture", e)
            await ctx.reply(f"❌ Error: {e}")

    @bot.command(name="expenses")
    async def cmd_expenses(ctx: commands.Context):
        """Show month-to-date expenses. Usage: !expenses"""
        try:
            from substrate.state.finance.expense_tracker import get_monthly_summary

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
            _record_error("cmd_expenses", e)
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

        first_q = _onboarding.get_next_question(session)
        if first_q:
            await _send_reply(ctx.channel, first_q)

    @bot.command(name="sync")
    async def cmd_sync(ctx: commands.Context):
        """Run the Daily Sync meeting now."""
        async with ctx.typing():

            def _run():
                try:
                    from substrate.control_plane.scheduling.daily_sync import DailySyncEngine

                    dse = DailySyncEngine(_ctx_eos)
                    return dse.run_sync()
                except Exception as e:
                    _record_error("cmd_run_helper", e)
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
                    _record_error("cmd_run_helper", e)
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
                    except Exception as _dp_err:
                        _record_error("draft_parse", _dp_err, {"file": str(f)})
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
                    _record_error("cmd_run_helper", e)
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
                    _record_error("cmd_run_helper", e)
                    return f"❌ Error: {e}"

            loop = asyncio.get_event_loop()
            output = await loop.run_in_executor(None, _run)
        await ctx.reply(output)

    @bot.command(name="waiting")
    async def cmd_waiting(ctx: commands.Context):
        """Show what's in the Waiting On folder."""
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
                    _record_error("cmd_run_helper", e)
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
                    _record_error("cmd_run_helper", e)
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
                    _record_error("cmd_run_helper", e)
                    return f"Folder update error: {e}"

            loop = asyncio.get_event_loop()
            output = await loop.run_in_executor(None, _run)
        await ctx.reply(output)

    @bot.command(name="delegated")
    async def cmd_delegated(ctx: commands.Context):
        """Show overdue delegations."""

        def _run():
            try:
                from substrate.control_plane.delegation.delegation_tracker import get_overdue_delegations

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
                _record_error("cmd_run_helper", e)
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
        await ctx.reply(output)

    @bot.command(name="subscriptions")
    async def cmd_subscriptions(ctx: commands.Context):
        """Show subscription registry and upcoming renewals."""

        def _run():
            try:
                from substrate.state.finance.subscription_tracker import (
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
                _record_error("cmd_run_helper", e)
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
                from substrate.state.finance.subscription_tracker import add_subscription

                vendor = parts[0]
                amount = float(parts[1].replace("$", ""))
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
                _record_error("cmd_run_helper", e)
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
        await ctx.reply(output)

    @bot.command(name="help")
    async def cmd_help(ctx: commands.Context):
        """Show available commands."""
        ai_name = _ai_name()
        lines = [
            f"**{ai_name} — Discord Commands**",
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

    # ─── Webhook helpers ─────────────────────────────────────────────────
    # (post_to_channel etc. stay in discord_bot.py since they are used
    #  by other modules that import from there)

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
                from substrate.control_plane.strategy.task_yield_matrix import (
                    run_yield_audit,
                    format_yield_report,
                )

                tasks = [t.strip() for t in args.replace("\n", ",").split(",") if t.strip()]
                if not tasks:
                    return "No tasks found. Separate with commas."
                results = run_yield_audit(tasks)
                return format_yield_report(results)
            except Exception as e:
                _record_error("cmd_run_helper", e)
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
                    from substrate.state.metrics.founder_rate import (
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
                    _record_error("cmd_run_helper", e)
                    return f"❌ Error: {e}"

            loop = asyncio.get_event_loop()
            output = await loop.run_in_executor(None, _run)
        else:

            def _get():
                try:
                    from substrate.state.metrics.founder_rate import get_current_founder_rate

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
                    _record_error("cmd__get", e)
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
                from substrate.state.metrics.founder_rate import log_time_block

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
                _record_error("cmd_run_helper", e)
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
        await ctx.reply(output)

    @bot.command(name="timeaudit")
    async def cmd_timeaudit(ctx: commands.Context):
        """View 7-day time and energy audit summary."""

        def _run():
            try:
                from substrate.state.metrics.founder_rate import get_time_audit_summary

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
                _record_error("cmd_run_helper", e)
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
        await ctx.reply(output)

    @bot.command(name="idealweek")
    async def cmd_perfectweek(ctx: commands.Context):
        """View your ideal week template."""

        def _run():
            try:
                from substrate.control_plane.scheduling.ideal_week import get_ideal_week

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
                _record_error("cmd_run_helper", e)
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
                from substrate.control_plane.scheduling.ideal_week import create_process_capture

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
                _record_error("cmd_run_helper", e)
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
                _record_error("cmd_run_helper", e)
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
                _record_error("cmd_run_helper", e)
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
                _record_error("cmd_run_helper", e)
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
                _record_error("cmd_run_helper", e)
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
                from substrate.state.metrics.founder_rate import get_no_list

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
                _record_error("cmd_run_helper", e)
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
                from substrate.state.metrics.founder_rate import add_to_no_list

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
                _record_error("cmd_run_helper", e)
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
                from substrate.state.context.context import load_context_from_env
                from substrate.state.storage.db import get_conn
                from zoneinfo import ZoneInfo as _ZI
                from datetime import datetime as _dt

                _PDT = _ZI("America/Los_Angeles")
                parts = [p.strip() for p in args.split("|")]
                score_str = parts[0]
                score = int(score_str) if score_str.isdigit() else 5
                score = max(1, min(10, score))
                drained = parts[1] if len(parts) > 1 else ""
                energized = parts[2] if len(parts) > 2 else ""

                _local_ctx = load_context_from_env()
                with get_conn(_local_ctx.org_id) as cur:
                    cur.execute(
                        """
                        INSERT INTO events
                        (org_id, event_type, payload_json, handled_by)
                        VALUES (%s, %s, %s, %s)
                    """,
                        (
                            str(_local_ctx.org_id),
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
                _record_error("cmd_run_helper", e)
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
        await ctx.reply(output)

    @bot.command(name="year")
    async def cmd_year(ctx: commands.Context):
        """View annual plan (Annual Architecture)."""

        def _run():
            try:
                from substrate.control_plane.scheduling.ideal_week import get_annual_architecture

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
                _record_error("cmd_run_helper", e)
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
        await ctx.reply(output)

    @bot.command(name="rocks")
    async def cmd_rocks(ctx: commands.Context):
        """View this quarter's rocks."""

        def _run():
            try:
                from substrate.control_plane.scheduling.ideal_week import get_current_quarter_rocks
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
                _record_error("cmd_run_helper", e)
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
        await ctx.reply(output)

    # ─── Invoice commands ────────────────────────────────────────────────

    @bot.command(name="invoices")
    async def cmd_invoices(ctx: commands.Context):
        """List all invoices. Usage: !invoices"""

        def _run():
            try:
                from substrate.state.finance.expense_tracker import get_invoices, get_overdue_invoices

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
                _record_error("cmd_run_helper", e)
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
                from substrate.state.finance.expense_tracker import create_invoice, generate_invoice_text

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
                _record_error("cmd_run_helper", e)
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
                from substrate.state.finance.expense_tracker import generate_expense_report

                return generate_expense_report(month or None)
            except Exception as e:
                _record_error("cmd_run_helper", e)
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, _run)
        await _send_reply(ctx.channel, f"📊 **Expense Report:**\n```\n{report}\n```")

    @bot.command(name="budget")
    async def cmd_budget(ctx: commands.Context, target: str = "10000"):
        """Budget vs actual. Usage: !budget [revenue target optional]"""

        def _run():
            try:
                from substrate.state.finance.expense_tracker import generate_budget_vs_actual

                t = float(target.replace("$", "").replace(",", ""))
                return generate_budget_vs_actual(revenue_target=t)
            except Exception as e:
                _record_error("cmd_run_helper", e)
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, _run)
        await _send_reply(ctx.channel, f"📊 **Budget vs Actual:**\n```\n{report}\n```")

    # ─── Doc / brief / slides / factcheck commands ───────────────────────

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
                _record_error("cmd_run_helper", e)
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
                from substrate.control_plane.strategy.portfolio_advisor import PortfolioAdvisor as PortfolioAgent
                from substrate.state.context.context import load_context_from_env

                local_ctx = load_context_from_env()
                pa = PortfolioAgent(local_ctx)
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
                _record_error("cmd_run_helper", e)
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
                _record_error("cmd_run_helper", e)
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
                _record_error("cmd_run_helper", e)
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
                _record_error("cmd_run_helper", e)
                return f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
        await _send_reply(ctx.channel, output)

    # ─── Personal admin commands ─────────────────────────────────────────

    @bot.command(name="dates")
    async def cmd_dates(ctx: commands.Context):
        """List upcoming important dates (60 days). Usage: !dates"""

        def _run():
            try:
                from substrate.control_plane.scheduling.personal_admin import get_upcoming_dates

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
                _record_error("cmd_run_helper", e)
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
                from substrate.control_plane.scheduling.personal_admin import add_important_date

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
                _record_error("cmd_run_helper", e)
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
                from substrate.control_plane.scheduling.personal_admin import research_gift

                parts = [p.strip() for p in args.split("|")]
                person = parts[0]
                occasion = parts[1] if len(parts) > 1 else "birthday"
                budget = float(parts[2].replace("$", "")) if len(parts) > 2 else 100
                ideas = research_gift(person, occasion, budget)
                return f"🎁 **Gift ideas for {person} — {occasion}:**\n{ideas[:1500]}"
            except Exception as e:
                _record_error("cmd_run_helper", e)
                return f"❌ Error: {e}"

        await ctx.reply("🎁 Researching gifts...")
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, _run)
        await _send_reply(ctx.channel, output)

    # ─── Travel research commands ────────────────────────────────────────

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
                _record_error("cmd_run_helper", e)
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
                _record_error("cmd_run_helper", e)
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
                _record_error("cmd_run_helper", e)
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
            from substrate.governance.quality.quality_gate import quality_check

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
            _record_error("cmd_proofread", e)
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
            _record_error("cmd_minutes", e)
            await ctx.reply(f"❌ Error: {e}")

    @bot.command(name="okr")
    async def cmd_okr(ctx: commands.Context, subcommand: str = "report", *, args: str = ""):
        """OKR tracking. Usage: !okr report | !okr set [venture] | [objective] | [KR, target, unit]"""
        if subcommand == "report":
            try:
                from substrate.state.metrics.okr_tracker import generate_okr_report

                report = generate_okr_report()
                await _send_reply(ctx.channel, report)
            except Exception as e:
                _record_error("cmd_okr", e)
                await ctx.reply(f"❌ Error: {e}")

        elif subcommand == "set":
            if not args or "|" not in args:
                await ctx.reply(
                    "Usage: `!okr set [venture_id] | [objective] | [KR description], [target], [unit]`\n"
                    "Example: `!okr set lyfe_institute | Hit first sale | Revenue, 750, $`"
                )
                return
            try:
                from substrate.state.metrics.okr_tracker import set_okr

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
                _record_error("cmd_okr", e)
                await ctx.reply(f"❌ Error: {e}")
        else:
            await ctx.reply("Usage: `!okr report` or `!okr set [venture] | [objective] | [KRs...]`")

    @bot.command(name="event")
    async def cmd_event(ctx: commands.Context, *, args: str = ""):
        """Manage events. Usage: !event list | !event [name] | [type] | [date] | [location] | [budget]"""
        if not args or args.strip() == "list":
            try:
                from substrate.control_plane.events.event_manager import get_events

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
                _record_error("cmd_event", e)
                await ctx.reply(f"❌ Error: {e}")
            return

        if "|" in args:
            parts = [p.strip() for p in args.split("|")]
            try:
                from substrate.control_plane.events.event_manager import create_event

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
                _record_error("cmd_event", e)
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
            from substrate.control_plane.events.event_manager import draft_talking_points

            await ctx.reply("📝 Drafting talking points...")
            topic = parts[0]
            audience = parts[1]
            duration = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 30
            fmt = parts[3] if len(parts) > 3 else "talk"
            points = draft_talking_points(topic, audience, duration, fmt)
            await _send_reply(ctx.channel, points)
        except Exception as e:
            _record_error("cmd_talkingpoints", e)
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
            from substrate.control_plane.events.event_manager import log_pr_media_inquiry

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
            _record_error("cmd_pr", e)
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
            from substrate.understanding.intelligence.stakeholder_map import generate_board_update_brief

            await ctx.reply("📋 Generating board update...")
            brief = generate_board_update_brief(venture_id)
            await _send_reply(ctx.channel, f"📋 **Board Update — {venture_id}:**\n{brief}")
        except Exception as e:
            _record_error("cmd_board_update", e)
            await ctx.reply(f"❌ Error: {e}")

    @bot.command(name="announce")
    async def cmd_announce(ctx: commands.Context, *, args: str = ""):
        """Draft announcement. Usage: !announce [topic] | [audience] | [key message] | [type]"""
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
            _record_error("cmd_announce", e)
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
            _record_error("cmd_crisis", e)
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
            _record_error("cmd_itinerary", e)
            await ctx.reply(f"❌ Error: {e}")

    @bot.command(name="approve_task")
    async def cmd_approve_task(ctx: commands.Context, task_id: str = ""):
        """Approve a pending agent task result. Usage: !approve_task [task_id]"""
        if not task_id:
            await ctx.reply("Usage: `!approve_task [task_id]`")
            return
        try:
            import json as _json
            from substrate.state.context.context import load_context_from_env
            from substrate.state.storage.db import get_conn

            _local_ctx = load_context_from_env()

            with get_conn(_local_ctx.org_id) as cur:
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
                    (str(_local_ctx.org_id), f"{task_id}%"),
                )
                row = cur.fetchone()

            if not row:
                await ctx.reply(f"Task `{task_id}` not found.")
                return

            payload = row["payload_json"]
            if isinstance(payload, str):
                payload = _json.loads(payload)

            with get_conn(_local_ctx.org_id) as cur:
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
            _record_error("cmd_approve_task", e)
            await ctx.reply(f"❌ Error: {e}")

    @bot.command(name="tasks")
    async def cmd_tasks(ctx: commands.Context):
        """Show pending task queue split by human vs AI."""
        try:
            from substrate.state.context.context import load_context_from_env
            from substrate.control_plane.coordination.coordination_engine import CoordinationEngine

            _local_ctx = load_context_from_env()
            coordination = CoordinationEngine(_local_ctx)

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
            _record_error("cmd_tasks", e)
            await ctx.reply(f"❌ Error: {e}")

    @bot.command(name="agent_results")
    async def cmd_agent_results(ctx: commands.Context):
        """Show last 24h agent task results."""
        try:
            import json as _json
            from substrate.state.context.context import load_context_from_env
            from substrate.state.storage.db import get_conn

            _local_ctx = load_context_from_env()

            with get_conn(_local_ctx.org_id) as cur:
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
                    (str(_local_ctx.org_id),),
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
            _record_error("cmd_agent_results", e)
            await ctx.reply(f"❌ Error: {e}")

    @bot.command(name="trace")
    async def cmd_trace(ctx: commands.Context, limit: int = 5):
        """Show recent execution traces (builder mode only)."""
        try:
            from substrate.execution.bridge.discord_mode_routing import resolve_discord_mode

            gid = str(ctx.guild.id) if ctx.guild else None
            cid = str(ctx.channel.id)
            mode = resolve_discord_mode(gid, cid)

            if mode == "product":
                await ctx.reply("Trace output is not available in product mode.")
                return

            from substrate.execution.bridge.execution_trace import (
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
            _record_error("cmd_trace", e)
            await ctx.reply(f"Trace error: {e}", tts=False)
