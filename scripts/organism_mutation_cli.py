#!/usr/bin/env python3
"""organism_mutation_cli.py — CLI for governed mutations.

Provides a command-line surface for the organism's governed mutation pipeline.
Used for C35 Property 3 (Distributed State Consistency) validation and
day-to-day operator interaction with the mutation system.

Usage:
    python3 scripts/organism_mutation_cli.py submit <mutation_name> <intent>
    python3 scripts/organism_mutation_cli.py pending [--limit N]
    python3 scripts/organism_mutation_cli.py approve <envelope_id> [--by operator]
    python3 scripts/organism_mutation_cli.py reject <envelope_id> <reason>
    python3 scripts/organism_mutation_cli.py journal <envelope_id>
    python3 scripts/organism_mutation_cli.py specs [--risk low|medium|high|critical]
    python3 scripts/organism_mutation_cli.py status
    python3 scripts/organism_mutation_cli.py qualify [--property N]

UMH substrate CLI. Instance-agnostic.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

sys.path.insert(0, "/opt/OS")


def _get_organism():
    """Get running organism components or exit."""
    try:
        from substrate.organism.governed_spine import GovernedExecutionSpine
        from substrate.organism.mutation_router import MutationRouter
        from substrate.organism.mutation_registry import MutationRegistry
        from substrate.organism.event_spine import EventSpine
        from substrate.organism.execution_journal import ExecutionJournal
        from substrate.organism.outcome_learning import OutcomeLearningLoop

        registry = MutationRegistry()
        event_spine = EventSpine()
        journal = ExecutionJournal()
        learning = OutcomeLearningLoop()

        spine = GovernedExecutionSpine(
            event_spine=event_spine,
            mutation_registry=registry,
            journal=journal,
            learning=learning,
        )
        router = MutationRouter(spine=spine, registry=registry)

        return {
            "spine": spine,
            "router": router,
            "registry": registry,
            "event_spine": event_spine,
            "journal": journal,
            "learning": learning,
        }
    except Exception as exc:
        print(f"Error initializing organism: {exc}")
        sys.exit(1)


def cmd_submit(args: argparse.Namespace) -> None:
    """Submit a governed mutation."""
    org = _get_organism()

    from transports.api.governed import governed_mutation

    def execute_fn() -> tuple[str, bool]:
        return (f"CLI mutation: {args.intent}", True)

    response = governed_mutation(
        mutation_name=args.mutation_name,
        intent=args.intent,
        execute_fn=execute_fn,
        source="cli",
    )

    print(json.dumps({
        "success": response.success,
        "envelope_id": response.envelope_id,
        "status": response.status,
        "output": response.output[:200] if response.output else "",
        "awaiting_approval": response.awaiting_approval,
    }, indent=2))


def cmd_pending(args: argparse.Namespace) -> None:
    """List pending mutations awaiting approval."""
    org = _get_organism()
    pending = org["spine"].pending_envelopes(limit=args.limit)

    if not pending:
        print("No pending mutations.")
        return

    for p in pending:
        print(f"  {p.get('envelope_id', '?')[:12]}  "
              f"{p.get('intent', '?')[:60]}  "
              f"risk={p.get('risk_level', '?')}  "
              f"source={p.get('source', '?')}")


def cmd_approve(args: argparse.Namespace) -> None:
    """Approve a pending mutation."""
    org = _get_organism()
    result = org["spine"].approve(args.envelope_id, approved_by=args.by)

    if result is None:
        print(f"Envelope {args.envelope_id} not found or not pending.")
        return

    print(json.dumps({
        "envelope_id": result.envelope_id,
        "status": result.status.value,
        "success": result.result_success,
        "output": result.result_output[:200] if result.result_output else "",
    }, indent=2))


def cmd_reject(args: argparse.Namespace) -> None:
    """Reject a pending mutation."""
    org = _get_organism()
    result = org["spine"].reject(args.envelope_id, reason=args.reason)

    if result is None:
        print(f"Envelope {args.envelope_id} not found or not pending.")
        return

    print(f"Rejected: {result.envelope_id} — {args.reason}")


def cmd_journal(args: argparse.Namespace) -> None:
    """Show journal entries for an envelope."""
    org = _get_organism()
    entries = org["journal"].entries_for(args.envelope_id)

    if not entries:
        print(f"No journal entries for {args.envelope_id}")
        return

    for e in entries:
        d = e.to_dict()
        print(f"  [{d.get('phase', '?')}] {d.get('source', '?')} "
              f"@ {time.strftime('%H:%M:%S', time.localtime(d.get('timestamp', 0)))}")
        if d.get("details"):
            for k, v in d["details"].items():
                print(f"    {k}: {str(v)[:80]}")


def cmd_specs(args: argparse.Namespace) -> None:
    """List registered mutation specs."""
    org = _get_organism()

    if args.risk:
        specs = org["registry"].specs_by_risk().get(args.risk, [])
    else:
        specs = org["registry"].all_specs()

    print(f"Registered mutation specs: {len(specs)}")
    for s in specs:
        print(f"  {s.name:<40} risk={s.risk_level:<8} "
              f"approval={'yes' if s.require_approval else 'no'}")


def cmd_status(args: argparse.Namespace) -> None:
    """Show organism status."""
    org = _get_organism()

    spine_data = org["spine"].to_dict()
    learning_summary = org["learning"].summary()
    journal_stats = org["journal"].statistics()
    event_snapshot = org["event_spine"].snapshot()

    print("=== Organism Status ===")
    print(f"Spine: executed={spine_data.get('total_executed', 0)} "
          f"succeeded={spine_data.get('total_succeeded', 0)} "
          f"failed={spine_data.get('total_failed', 0)} "
          f"rejected={spine_data.get('total_rejected', 0)}")
    print(f"Learning: outcomes={learning_summary.get('total_outcomes', 0)} "
          f"signals={learning_summary.get('total_signals', 0)}")
    print(f"Journal: entries={journal_stats.get('total_entries', 0)}")
    print(f"Events: total={event_snapshot.get('total_events', 0)} "
          f"subscribers={len(event_snapshot.get('subscribers', []))}")

    reliability = learning_summary.get("reliability_scores", {})
    if reliability:
        print("\nReliability scores:")
        for action_type, score in sorted(reliability.items()):
            bar = "#" * int(score * 20)
            print(f"  {action_type:<30} {score:.3f} [{bar:<20}]")


def cmd_qualify(args: argparse.Namespace) -> None:
    """Run C35 qualification (or a single property)."""
    from substrate.organism.qualification_harness import QualificationHarness

    harness = QualificationHarness()
    print(f"Qualification harness loaded with {len(harness._mutations)} existing mutations.")

    if args.property:
        print(f"Property {args.property} validation requires organism components.")
        print("Use the full qualification runner for property-level validation.")
        return

    report = harness.generate_report([])
    print(harness.format_report_markdown(report))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Organism Mutation CLI — governed mutation commands",
    )
    sub = parser.add_subparsers(dest="command")

    p_submit = sub.add_parser("submit", help="Submit a governed mutation")
    p_submit.add_argument("mutation_name", help="Registered mutation spec name")
    p_submit.add_argument("intent", help="Human-readable intent")

    p_pending = sub.add_parser("pending", help="List pending mutations")
    p_pending.add_argument("--limit", type=int, default=20)

    p_approve = sub.add_parser("approve", help="Approve a pending mutation")
    p_approve.add_argument("envelope_id", help="Envelope ID to approve")
    p_approve.add_argument("--by", default="operator", help="Approver identity")

    p_reject = sub.add_parser("reject", help="Reject a pending mutation")
    p_reject.add_argument("envelope_id", help="Envelope ID to reject")
    p_reject.add_argument("reason", help="Rejection reason")

    p_journal = sub.add_parser("journal", help="Show journal for an envelope")
    p_journal.add_argument("envelope_id", help="Envelope ID")

    p_specs = sub.add_parser("specs", help="List mutation specs")
    p_specs.add_argument("--risk", choices=["low", "medium", "high", "critical"])

    sub.add_parser("status", help="Show organism status")

    p_qualify = sub.add_parser("qualify", help="Run C35 qualification")
    p_qualify.add_argument("--property", type=int, help="Single property number")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "submit": cmd_submit,
        "pending": cmd_pending,
        "approve": cmd_approve,
        "reject": cmd_reject,
        "journal": cmd_journal,
        "specs": cmd_specs,
        "status": cmd_status,
        "qualify": cmd_qualify,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
