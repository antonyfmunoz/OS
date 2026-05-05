"""UMH CLI — command-line interface for the Universal Meta Harness.

Usage:
    python -m umh status
    python -m umh run "What should I focus on today?"
    python -m umh capabilities
    python -m umh adapters
    python -m umh trace "analyze my pipeline"
"""

from __future__ import annotations

import json
import sys


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        _print_help()
        return 0

    command = args[0]

    if command == "status":
        return _cmd_status()
    elif command == "run":
        if len(args) < 2:
            print('Usage: python -m umh run "<input>"')
            return 1
        return _cmd_run(" ".join(args[1:]))
    elif command == "capabilities":
        return _cmd_capabilities()
    elif command == "adapters":
        return _cmd_adapters()
    elif command == "trace":
        if len(args) < 2:
            print('Usage: python -m umh trace "<input>"')
            return 1
        return _cmd_trace(" ".join(args[1:]))
    elif command in ("help", "--help", "-h"):
        _print_help()
        return 0
    else:
        print(f"Unknown command: {command}")
        _print_help()
        return 1


def _cmd_status() -> int:
    from umh.adapters.base import list_adapters
    from umh.capability.registry import get_registry

    registry = get_registry()
    adapters = list_adapters()

    print("UMH — Universal Meta Harness")
    print("=" * 40)
    print(
        f"Capabilities: {registry.size} registered, "
        f"{len(registry.list_available())} available"
    )
    print(f"Adapters:")
    for name, available in adapters.items():
        status = "OK" if available else "stub"
        print(f"  {name:15s} [{status}]")
    print()

    from umh.memory.storage import get_storage

    store = get_storage()
    print(f"Storage: {type(store).__name__} ({len(store.all_keys())} keys)")

    return 0


def _cmd_run(input_text: str) -> int:
    from umh.run import run

    result = run(input_text)

    print(f"Run: {result.run_id}")
    print(f"Operation: {result.operation}")
    print(f"Capability: {result.capability_used}")
    print(f"Success: {result.success}")
    print(f"Latency: {result.trace.total_ms}ms")
    print()
    print("Response:")
    print(result.response)

    return 0 if result.success else 1


def _cmd_capabilities() -> int:
    from umh.capability.registry import get_registry

    registry = get_registry()
    caps = registry.list_all()

    print("Registered Capabilities")
    print("=" * 40)
    for cap in caps:
        avail = "available" if cap.available else "unavailable"
        print(
            f"  {cap.name:20s} [{cap.capability_type:8s}] "
            f"q={cap.quality_score:.2f} [{avail}]"
        )
        print(f"    {cap.description}")
        if cap.tags:
            print(f"    tags: {', '.join(cap.tags)}")
        perf = cap.performance
        if perf.total_runs > 0:
            print(
                f"    runs={perf.total_runs} "
                f"success={perf.success_rate:.0%} "
                f"avg_latency={perf.avg_latency_ms:.0f}ms"
            )
        print()

    return 0


def _cmd_adapters() -> int:
    from umh.adapters.base import get_adapter, list_adapters

    adapters = list_adapters()

    print("Adapter Status")
    print("=" * 40)
    for name, available in adapters.items():
        adapter = get_adapter(name)
        status = "OK" if available else "stub"
        detail = ""
        if hasattr(adapter, "model"):
            detail = f" model={adapter.model}"
        if hasattr(adapter, "host"):
            detail += f" host={adapter.host}"
        print(f"  {name:15s} [{status:4s}] {type(adapter).__name__}{detail}")

    return 0


def _cmd_trace(input_text: str) -> int:
    from umh.run import run

    result = run(input_text)

    print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0 if result.success else 1


def _print_help() -> None:
    print("UMH — Universal Meta Harness")
    print()
    print("Commands:")
    print("  status         Show system status")
    print('  run "<input>"  Run the full pipeline')
    print("  capabilities   List registered capabilities")
    print("  adapters       Show adapter status")
    print('  trace "<input>" Run with full JSON trace output')
    print("  help           Show this help")
    print()
    print("Usage: python -m umh <command> [args]")
