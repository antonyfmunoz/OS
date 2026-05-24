"""UMH Workstation CLI entry point."""

from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="umh",
        description="UMH Workstation — voice-first intelligence runtime",
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    parser.add_argument("--text-only", action="store_true", help="Text-only mode (no mic/speaker)")
    parser.add_argument(
        "--voice-mode",
        choices=["ambient", "push-to-talk"],
        default="ambient",
        help="Voice input mode (default: ambient)",
    )
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("diag", help="Run system diagnostics")
    sub.add_parser("setup", help="First-boot setup / onboarding")
    sub.add_parser("status", help="Show workstation status")
    sub.add_parser("voice-setup", help="Configure voice cloning + wake command")
    sub.add_parser("settings", help="View / edit preferences")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from umh import __version__

        print(f"umh {__version__}")
        return 0

    sys.path.insert(0, "/opt/OS")

    if args.command == "diag":
        from umh.diagnostics import run_diagnostics

        return run_diagnostics()

    if args.command == "setup":
        from umh.boot import run_first_boot

        return run_first_boot(voice_mode=args.voice_mode.replace("-", "_"))

    if args.command == "status":
        from umh.daily import show_status

        return show_status()

    if args.command == "voice-setup":
        from umh.voice import run_voice_setup

        return run_voice_setup()

    if args.command == "settings":
        from umh.profile import show_settings

        return show_settings()

    if args.daemon:
        print("Daemon mode not yet implemented (Sprint 5)")
        return 1

    from umh.boot import run_boot

    voice_mode = args.voice_mode.replace("-", "_")
    return run_boot(text_only=args.text_only, voice_mode=voice_mode)


if __name__ == "__main__":
    raise SystemExit(main())
