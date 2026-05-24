"""UMH Workstation CLI entry point."""

from __future__ import annotations

import argparse


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
    sub.add_parser("install", help="Phase 0 — install dependencies + register transport")
    sub.add_parser("setup", help="First-boot setup / onboarding")
    sub.add_parser("status", help="Show workstation status")
    sub.add_parser("voice-setup", help="Configure voice cloning + wake command")
    sub.add_parser("settings", help="View / edit preferences")
    sub.add_parser("permissions", help="View / manage permission grants")
    sub.add_parser("discover", help="Run environment discovery scan")
    sub.add_parser("mesh", help="Show device mesh status")
    sub.add_parser("personality", help="Show personality configuration")
    sub.add_parser("governance", help="Show governance configuration")
    sub.add_parser("scan", help="Run deep diagnostic scan")
    sub.add_parser("profile-inference", help="Show inferred profile modes")
    sub.add_parser("review", help="Show full instance review dashboard")
    sub.add_parser("awakening", help="Run The Awakening reality brief")
    sub.add_parser("continuity", help="Show session continuity state")
    sub.add_parser("transport", help="Show transport registration status")
    sub.add_parser("triggers", help="Show trigger history")
    sub.add_parser("scheduler", help="Show scheduler status")
    sub.add_parser("approvals", help="Show approval queue")
    sub.add_parser("outcomes", help="Show pipeline outcomes")
    sub.add_parser("operator", help="Show operator state")
    sub.add_parser("capabilities", help="Show local capabilities")
    sub.add_parser("health", help="Run subsystem health check")
    sub.add_parser("dashboard", help="Show full workstation status dashboard")
    sub.add_parser("view", help="Show pipeline view frames")

    daemon_parser = sub.add_parser("daemon", help="Manage background daemon")
    daemon_sub = daemon_parser.add_subparsers(dest="daemon_action")
    daemon_sub.add_parser("start", help="Start daemon in foreground")
    daemon_sub.add_parser("status", help="Show daemon status")
    daemon_sub.add_parser("stop", help="Stop running daemon")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from umh import __version__

        print(f"umh {__version__}")
        return 0

    if args.command == "diag":
        from umh.diagnostics import run_diagnostics

        return run_diagnostics()

    if args.command == "install":
        from umh.installer import run_install

        return run_install()

    if args.command == "setup":
        from umh.boot import run_first_boot

        return run_first_boot(
            text_only=args.text_only, voice_mode=args.voice_mode.replace("-", "_")
        )

    if args.command == "status":
        from umh.daily import show_status

        return show_status()

    if args.command == "voice-setup":
        from umh.voice_setup import run_voice_setup_flow

        return run_voice_setup_flow()

    if args.command == "settings":
        from umh.profile import show_settings

        return show_settings()

    if args.command == "permissions":
        from umh.permissions import PermissionStore

        store = PermissionStore()
        store.display()
        return 0

    if args.command == "discover":
        from umh.discovery import DiscoveryScanner

        scanner = DiscoveryScanner()
        print("Running environment discovery scan...")
        scanner.run_synchronous()
        scanner.display_result()
        return 0

    if args.command == "mesh":
        from umh.mesh import show_mesh_status

        return show_mesh_status()

    if args.command == "personality":
        from umh.personality import show_personality

        return show_personality()

    if args.command == "governance":
        from umh.governance_config import show_governance

        return show_governance()

    if args.command == "scan":
        from umh.diagnostic_scan import DiagnosticScanner

        scanner = DiagnosticScanner()
        print("Running diagnostic scan (this may take a minute)...")
        scanner.start_scan(background=False)
        scanner.display_result()
        return 0

    if args.command == "profile-inference":
        from umh.profile_inference import show_inference

        return show_inference()

    if args.command == "review":
        from umh.review import show_review

        return show_review()

    if args.command == "awakening":
        from umh.awakening import show_awakening

        return show_awakening()

    if args.command == "continuity":
        from umh.continuity import show_continuity

        return show_continuity()

    if args.command == "triggers":
        from umh.triggers import show_triggers

        return show_triggers()

    if args.command == "scheduler":
        from umh.scheduler import show_scheduler_status

        return show_scheduler_status()

    if args.command == "approvals":
        from umh.approvals import show_approvals

        return show_approvals()

    if args.command == "outcomes":
        from umh.outcomes import show_outcomes

        return show_outcomes()

    if args.command == "operator":
        from umh.operator_sync import show_operator_state

        return show_operator_state()

    if args.command == "capabilities":
        from umh.capability_router import show_capabilities

        return show_capabilities()

    if args.command == "health":
        from umh.health import format_health, run_health_check

        results = run_health_check()
        print(format_health(results))
        return 0

    if args.command == "dashboard":
        from umh.modes import ModeState
        from umh.status_display import show_status as show_full_status

        show_full_status(mode_state=ModeState())
        return 0

    if args.command == "view":
        from umh.view_renderer import show_view

        show_view()
        return 0

    if args.command == "transport":
        from umh.transport import build_workstation_manifest

        manifest = build_workstation_manifest()
        print(f"Transport: {manifest.integration_id}")
        print("Sockets: signal, capability, outcome, view")
        sockets = []
        if manifest.signal_emitter:
            sockets.append(
                f"  signal:     {len(manifest.signal_emitter.describe_signals())} signal types"
            )
        if manifest.capability_handler:
            sockets.append(
                f"  capability: {len(manifest.capability_handler.describe_capabilities())} capabilities"
            )
        if manifest.outcome_receiver:
            sockets.append("  outcome:    active")
        if manifest.view_subscriber:
            sockets.append("  view:       subscribed")
        print("\n".join(sockets))
        return 0

    if args.command == "daemon":
        action = getattr(args, "daemon_action", None)
        if action == "status":
            from umh.daemon import show_daemon_status

            return show_daemon_status()
        if action == "stop":
            from umh.daemon import stop_daemon

            return stop_daemon()
        # "start" or no action — run daemon in foreground
        from umh.daemon import run_daemon

        return run_daemon()

    if args.daemon:
        from umh.daemon import run_daemon

        return run_daemon()

    from umh.boot import run_boot

    voice_mode = args.voice_mode.replace("-", "_")
    return run_boot(text_only=args.text_only, voice_mode=voice_mode)


if __name__ == "__main__":
    raise SystemExit(main())
