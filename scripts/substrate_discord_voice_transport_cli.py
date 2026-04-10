#!/usr/bin/env python3
"""
Discord voice transport CLI — bounded operator interface to the
Discord voice transport adapter.

Subcommands:
  status      Show transport status_report() for a (guild, channel) pair.
  start       Start a bounded voice session for the transport node.
  inject      Inject a single transcript-only utterance.
  end         End the active voice session for the transport node.
  report      Recent transport history (JSON).

This CLI never opens a real Discord voice connection. It is a façade
over the bounded seam:

    DiscordVoiceTransport.inject_utterance(text)
    → inject_transcript(source="discord_voice")
    → voice session → responder → SPEAK_TEXT

Usage examples:
    python3 scripts/substrate_discord_voice_transport_cli.py status

    python3 scripts/substrate_discord_voice_transport_cli.py status \\
        --guild 1234567890 --channel 9876543210

    python3 scripts/substrate_discord_voice_transport_cli.py start \\
        --guild 1234 --channel 5678 --role ea_orchestrator

    python3 scripts/substrate_discord_voice_transport_cli.py inject \\
        --guild 1234 --channel 5678 \\
        --user 99 --text "what is on the agenda today"

    python3 scripts/substrate_discord_voice_transport_cli.py end \\
        --guild 1234 --channel 5678 --reason cli-end
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "/opt/OS")


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _transport(args: argparse.Namespace):
    from eos_ai.substrate.discord_voice_transport import (
        get_default_discord_voice_transport,
    )

    return get_default_discord_voice_transport(
        guild_id=args.guild,
        channel_id=args.channel,
        role_slug=getattr(args, "role", "ea_orchestrator"),
    )


def cmd_status(args: argparse.Namespace) -> int:
    t = _transport(args)
    payload = t.status_report(history_limit=args.limit)
    _print_json(payload)
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    t = _transport(args)
    _print_json(t.start_session(role_slug=args.role))
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    t = _transport(args)
    result = t.inject_utterance(
        args.text,
        user_id=args.user,
        role_slug=args.role,
        metadata={"issued_by": "discord_voice_transport_cli"},
    )
    _print_json(result)
    status = (result.get("status") or "").lower()
    return 0 if status == "ok" else 1


def cmd_end(args: argparse.Namespace) -> int:
    t = _transport(args)
    _print_json(t.end_session(reason=args.reason))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from eos_ai.substrate.discord_voice_transport import get_transport_history

    rows = get_transport_history().latest(limit=args.limit, node_id=args.node)
    _print_json([r.as_dict() for r in rows])
    return 0


# ── Playback subcommands (use a local fake VC, never opens Discord) ──────────


class _FakeVoiceClient:
    """Test/operator fake. Records play() calls without touching Discord."""

    def __init__(self) -> None:
        self.played: list = []
        self._playing = False

    def is_playing(self) -> bool:
        return self._playing

    def play(self, source, after=None) -> None:
        self.played.append(source)
        self._playing = False
        if callable(after):
            try:
                after(None)
            except Exception:
                pass


def cmd_attach_fake(args: argparse.Namespace) -> int:
    t = _transport(args)
    fake = _FakeVoiceClient()
    _print_json(t.attach_voice_client(fake, enabled=True))
    return 0


def cmd_detach(args: argparse.Namespace) -> int:
    t = _transport(args)
    _print_json(t.detach_voice_client())
    return 0


def cmd_play(args: argparse.Namespace) -> int:
    t = _transport(args)
    if not t._playback_enabled:  # noqa: SLF001
        # Auto-attach a fake so operators can test playback safely.
        t.attach_voice_client(_FakeVoiceClient(), enabled=True)
    _print_json(t.play_reply(args.text))
    return 0


def cmd_playback_status(args: argparse.Namespace) -> int:
    from eos_ai.substrate.discord_voice_playback import (
        get_playback_history,
        probe_playback_capability,
    )

    t = _transport(args)
    payload = {
        "transport_node_id": t.node_id,
        "playback_enabled": t._playback_enabled,  # noqa: SLF001
        "attached_vc": t._attached_vc is not None,  # noqa: SLF001
        "capability": probe_playback_capability(),
        "recent_playback": [
            r.as_dict()
            for r in get_playback_history().latest(limit=args.limit, node_id=t.node_id)
        ],
    }
    _print_json(payload)
    return 0


def _common_target(p: argparse.ArgumentParser) -> None:
    p.add_argument("--guild", default=None, help="Discord guild id")
    p.add_argument("--channel", default=None, help="Discord voice channel id")
    p.add_argument("--role", default="ea_orchestrator")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="transport status report")
    _common_target(s)
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_status)

    st = sub.add_parser("start", help="start a voice session for this transport")
    _common_target(st)
    st.set_defaults(func=cmd_start)

    i = sub.add_parser("inject", help="inject one transcript via the transport")
    _common_target(i)
    i.add_argument("--text", required=True)
    i.add_argument("--user", default=None, help="discord user id (optional)")
    i.set_defaults(func=cmd_inject)

    e = sub.add_parser("end", help="end the active voice session for this transport")
    _common_target(e)
    e.add_argument("--reason", default="cli-end")
    e.set_defaults(func=cmd_end)

    r = sub.add_parser("report", help="recent transport history")
    r.add_argument("--node", default=None)
    r.add_argument("--limit", type=int, default=10)
    r.set_defaults(func=cmd_report)

    af = sub.add_parser(
        "attach-fake",
        help="attach a local fake VoiceClient (safe — no Discord connection)",
    )
    _common_target(af)
    af.set_defaults(func=cmd_attach_fake)

    dt = sub.add_parser("detach", help="detach the current VoiceClient")
    _common_target(dt)
    dt.set_defaults(func=cmd_detach)

    pl = sub.add_parser(
        "play",
        help="render text and dispatch to attached VC (auto-attaches fake if none)",
    )
    _common_target(pl)
    pl.add_argument("--text", required=True)
    pl.set_defaults(func=cmd_play)

    ps = sub.add_parser("playback-status", help="playback capability + recent history")
    _common_target(ps)
    ps.add_argument("--limit", type=int, default=10)
    ps.set_defaults(func=cmd_playback_status)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
