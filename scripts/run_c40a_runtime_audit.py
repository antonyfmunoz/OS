"""C40A Phase 1 — Runtime Boundary Audit.

Probes every runtime hop in the mesh dispatch chain, records payload shapes,
measures latency, identifies the exact point where the command key drops.

Usage:
    python3 scripts/run_c40a_runtime_audit.py [--live]

    --live  Also probe Beast via real mesh dispatch (requires Beast connected)
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

_REPO_ROOT = Path(os.environ.get("UMH_ROOT", "/opt/OS"))
DATA_DIR = _REPO_ROOT / "data" / "umh" / "c40a"
_MESH_HTTP_PORT = int(os.environ.get("UMH_MESH_HTTP_PORT", "8095"))


@dataclass
class HopResult:
    hop_id: str
    source: str
    destination: str
    transport: str
    payload_in_keys: list[str] = field(default_factory=list)
    payload_out_keys: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    status: str = "untested"
    error: str | None = None
    notes: str = ""


@dataclass
class SurfaceInfo:
    surface_id: str
    entry_point: str
    auth: str
    organism_access: str
    governed: str
    push_mechanism: str


@dataclass
class BoundaryMap:
    audit_timestamp: str = ""
    hops: list[dict[str, Any]] = field(default_factory=list)
    surfaces: list[dict[str, Any]] = field(default_factory=list)
    mesh_health: dict[str, Any] = field(default_factory=dict)
    beast_status: dict[str, Any] = field(default_factory=dict)
    serialization_tests: list[dict[str, Any]] = field(default_factory=list)
    known_issues: list[dict[str, Any]] = field(default_factory=list)
    live_dispatch_results: list[dict[str, Any]] = field(default_factory=list)


def _check_mesh_health() -> dict[str, Any]:
    """Probe mesh relay /health endpoint."""
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(
            f"http://localhost:{_MESH_HTTP_PORT}/health",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        latency = (time.monotonic() - t0) * 1000
        return {
            "status": "healthy",
            "data": data,
            "latency_ms": round(latency, 1),
        }
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc), "latency_ms": 0}


def _check_mesh_nodes() -> dict[str, Any]:
    """Probe mesh relay /nodes endpoint."""
    try:
        req = urllib.request.Request(
            f"http://localhost:{_MESH_HTTP_PORT}/nodes",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return {"status": "ok", "nodes": data, "count": len(data)}
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc)}


def _test_serialization_chain() -> list[dict[str, Any]]:
    """Simulate the exact serialization at each hop without network calls.

    This catches JSON encoding/decoding mismatches locally.
    """
    results = []

    # Payload as browser_evidence_collector sends it
    bec_payload = {
        "node_id": "windows-desktop",
        "capability": "shell",
        "params": {"command": "echo test_c40a", "timeout": 30},
        "timeout": 30,
    }

    # Payload as _mesh_dispatch sends it
    md_payload = {
        "node_id": "windows-desktop",
        "capability": "shell",
        "params": {"argv": ["echo", "test_c40a"], "cwd": "/tmp"},
        "timeout": 30,
    }

    for label, payload in [("bec_command_path", bec_payload), ("md_argv_path", md_payload)]:
        test = {"label": label, "steps": [], "final_status": "unknown"}

        # Step 1: JSON encode (what gets sent over HTTP)
        encoded = json.dumps(payload)
        decoded = json.loads(encoded)
        test["steps"].append({
            "step": "http_encode_decode",
            "params_keys": list(decoded.get("params", {}).keys()),
            "match": decoded == payload,
        })

        # Step 2: Relay extracts params (server.py:979)
        relay_params = decoded.get("params", {})
        relay_capability = decoded.get("capability", "")
        test["steps"].append({
            "step": "relay_extract_params",
            "params_keys": list(relay_params.keys()),
            "capability": relay_capability,
        })

        # Step 3: Relay wraps in JSON-RPC (server.py:1000-1012)
        rpc_msg = {
            "jsonrpc": "2.0",
            "method": "capability.execute",
            "params": {
                "request_id": "test-req-id",
                "capability_name": relay_capability,
                "params": relay_params,
                "timeout_seconds": decoded.get("timeout", 15),
            },
            "id": "test-req-id",
        }
        rpc_encoded = json.dumps(rpc_msg)
        rpc_decoded = json.loads(rpc_encoded)
        test["steps"].append({
            "step": "relay_jsonrpc_wrap",
            "outer_params_keys": list(rpc_decoded.get("params", {}).keys()),
            "inner_params_keys": list(rpc_decoded.get("params", {}).get("params", {}).keys()),
        })

        # Step 4: Client extracts (client.py:454-457)
        msg_params = rpc_decoded.get("params", {})
        cap_name = msg_params.get("capability_name", "")
        cap_params = msg_params.get("params", {})
        test["steps"].append({
            "step": "client_extract_cap_params",
            "cap_name": cap_name,
            "cap_params_keys": list(cap_params.keys()),
        })

        # Step 5: Adapter checks (shell.py:17-18)
        argv = cap_params.get("argv")
        command = cap_params.get("command", "")
        has_argv = bool(argv and isinstance(argv, list))
        has_command = bool(command)
        test["steps"].append({
            "step": "adapter_check",
            "has_argv": has_argv,
            "has_command": has_command,
            "would_succeed": has_argv or has_command,
        })

        test["final_status"] = "pass" if (has_argv or has_command) else "FAIL"
        results.append(test)

    return results


def _test_governance_bypass() -> dict[str, Any]:
    """Check the shell.execute vs shell governance bypass."""
    try:
        from nodes.windows.umh_node.governance import validate_request
        from nodes.windows.umh_node.config import CapabilityConfig

        config = CapabilityConfig()

        # Test with "shell" (what browser_evidence_collector sends)
        allowed_shell, reason_shell = validate_request(
            "shell",
            {"command": "echo test", "timeout": 30},
            "REVERSIBLE_WRITE",
            config,
        )

        # Test with "shell.execute" (what MeshNodeRuntimeAdapter sends)
        allowed_dotted, reason_dotted = validate_request(
            "shell.execute",
            {"command": "echo test", "timeout": 30},
            "REVERSIBLE_WRITE",
            config,
        )

        # Test with allowed_commands restriction
        restricted_config = CapabilityConfig(allowed_commands=["python3", "echo"])
        allowed_restricted, reason_restricted = validate_request(
            "shell",
            {"command": "echo test", "timeout": 30},
            "REVERSIBLE_WRITE",
            restricted_config,
        )
        allowed_dotted_restricted, reason_dotted_restricted = validate_request(
            "shell.execute",
            {"command": "echo test", "timeout": 30},
            "REVERSIBLE_WRITE",
            restricted_config,
        )

        bypass_exists = allowed_dotted_restricted and not allowed_restricted
        return {
            "status": "tested",
            "shell_allowed": allowed_shell,
            "shell_execute_allowed": allowed_dotted,
            "shell_restricted_allowed": allowed_restricted,
            "shell_execute_restricted_allowed": allowed_dotted_restricted,
            "governance_bypass_confirmed": bypass_exists,
            "notes": (
                "shell.execute bypasses allowed_commands check because "
                "governance.py:53 checks capability_name == 'shell' exactly"
                if bypass_exists
                else "No bypass detected (allowed_commands may be empty)"
            ),
        }
    except ImportError as exc:
        return {"status": "skipped", "error": f"Cannot import governance: {exc}"}


def _test_runtime_adapter_capability_name() -> dict[str, Any]:
    """Check what capability name MeshNodeRuntimeAdapter sends."""
    try:
        import inspect
        from substrate.organism.runtime_adapters import MeshNodeRuntimeAdapter

        source = inspect.getsource(MeshNodeRuntimeAdapter.execute)
        sends_shell_execute = '"shell.execute"' in source or "'shell.execute'" in source
        sends_shell = ('"shell"' in source or "'shell'" in source) and not sends_shell_execute

        return {
            "status": "tested",
            "sends_shell_execute": sends_shell_execute,
            "sends_shell": sends_shell,
            "notes": (
                "MeshNodeRuntimeAdapter sends 'shell.execute' — "
                "this causes governance bypass when allowed_commands is set"
                if sends_shell_execute
                else "MeshNodeRuntimeAdapter sends 'shell' — correct"
            ),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _live_dispatch_test(command: str, timeout: int = 30) -> dict[str, Any]:
    """Send a real dispatch to Beast and record the full response."""
    t0 = time.monotonic()
    try:
        payload = json.dumps({
            "node_id": "windows-desktop",
            "capability": "shell",
            "params": {"command": command, "timeout": timeout},
            "timeout": timeout,
        }).encode()

        req = urllib.request.Request(
            f"http://localhost:{_MESH_HTTP_PORT}/dispatch",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout + 10) as resp:
            data = json.loads(resp.read().decode())

        latency = (time.monotonic() - t0) * 1000
        return {
            "command": command,
            "latency_ms": round(latency, 1),
            "response": data,
            "success": data.get("ok", False),
            "error": data.get("error"),
        }
    except Exception as exc:
        latency = (time.monotonic() - t0) * 1000
        return {
            "command": command,
            "latency_ms": round(latency, 1),
            "response": None,
            "success": False,
            "error": str(exc),
        }


def _live_dispatch_argv_test(argv: list[str], timeout: int = 30) -> dict[str, Any]:
    """Send a real dispatch using argv path."""
    t0 = time.monotonic()
    try:
        payload = json.dumps({
            "node_id": "windows-desktop",
            "capability": "shell",
            "params": {"argv": argv, "timeout": timeout},
            "timeout": timeout,
        }).encode()

        req = urllib.request.Request(
            f"http://localhost:{_MESH_HTTP_PORT}/dispatch",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout + 10) as resp:
            data = json.loads(resp.read().decode())

        latency = (time.monotonic() - t0) * 1000
        return {
            "argv": argv,
            "latency_ms": round(latency, 1),
            "response": data,
            "success": data.get("ok", False),
            "error": data.get("error"),
        }
    except Exception as exc:
        latency = (time.monotonic() - t0) * 1000
        return {
            "argv": argv,
            "latency_ms": round(latency, 1),
            "response": None,
            "success": False,
            "error": str(exc),
        }


def _build_surfaces() -> list[dict[str, Any]]:
    """Document all operator surfaces."""
    surfaces = [
        SurfaceInfo(
            surface_id="cockpit",
            entry_point="transports/api/cockpit_*.py",
            auth="Clerk JWT",
            organism_access="HTTP API → governed_mutation() → MutationRouter → spine",
            governed="FULLY_GOVERNED",
            push_mechanism="WebSocket pulse every ~2s",
        ),
        SurfaceInfo(
            surface_id="cli",
            entry_point="scripts/organism_mutation_cli.py",
            auth="local process",
            organism_access="direct governed_mutation() → MutationRouter → spine",
            governed="FULLY_GOVERNED",
            push_mechanism="stdout (no push)",
        ),
        SurfaceInfo(
            surface_id="discord",
            entry_point="services/discord_bot.py",
            auth="Discord bot token",
            organism_access="signal_factory → gateway (conversational) | API → governed_mutation() (approvals)",
            governed="PARTIAL — approvals governed, conversational bypasses",
            push_mechanism="Discord messages",
        ),
        SurfaceInfo(
            surface_id="voice",
            entry_point="umh/voice_server.py",
            auth="WebSocket session",
            organism_access="I/O bridge → browser → cockpit routes → governed_mutation()",
            governed="FULLY_GOVERNED (lifecycle routes)",
            push_mechanism="WebSocket STT/TTS",
        ),
        SurfaceInfo(
            surface_id="browser_evidence",
            entry_point="substrate/meta_ide/browser_evidence_collector.py",
            auth="mesh relay (no auth on localhost)",
            organism_access="mesh dispatch → Beast → Chrome → evidence (read-only verification)",
            governed="N/A — verification, not mutation",
            push_mechanism="none (request/response)",
        ),
        SurfaceInfo(
            surface_id="mesh_dispatch",
            entry_point="transports/api/_mesh_dispatch.py",
            auth="mesh relay (iptables scoped)",
            organism_access="HTTP relay → WS → Beast ShellAdapter",
            governed="N/A — execution dispatch, not organism mutation",
            push_mechanism="none (request/response)",
        ),
        SurfaceInfo(
            surface_id="event_spine",
            entry_point="substrate/organism/event_spine.py",
            auth="in-process",
            organism_access="direct pub/sub (18 domains)",
            governed="N/A — event broadcast, not mutation",
            push_mechanism="subscriber callbacks",
        ),
    ]
    return [asdict(s) for s in surfaces]


def run_audit(live: bool = False) -> BoundaryMap:
    """Execute the full runtime boundary audit."""
    boundary_map = BoundaryMap()
    boundary_map.audit_timestamp = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print("C40A Phase 1 — Runtime Boundary Audit")
    print("=" * 60)

    # 1. Serialization chain tests (offline, no network)
    print("\n[1/6] Testing serialization chain (offline)...")
    boundary_map.serialization_tests = _test_serialization_chain()
    for test in boundary_map.serialization_tests:
        status = test["final_status"]
        label = test["label"]
        print(f"  {label}: {status}")
        for step in test["steps"]:
            step_name = step["step"]
            if "would_succeed" in step:
                print(f"    {step_name}: would_succeed={step['would_succeed']}")
            elif "match" in step:
                print(f"    {step_name}: encode/decode match={step['match']}")

    # 2. Governance bypass test
    print("\n[2/6] Testing governance bypass (shell vs shell.execute)...")
    gov_result = _test_governance_bypass()
    boundary_map.known_issues.append({
        "id": "governance_capability_name",
        "test_result": gov_result,
    })
    if gov_result.get("governance_bypass_confirmed"):
        print("  CONFIRMED: shell.execute bypasses allowed_commands check")
    else:
        print(f"  Result: {gov_result.get('notes', gov_result.get('status'))}")

    # 3. Runtime adapter capability name
    print("\n[3/6] Checking MeshNodeRuntimeAdapter capability name...")
    adapter_result = _test_runtime_adapter_capability_name()
    boundary_map.known_issues.append({
        "id": "runtime_adapter_capability_name",
        "test_result": adapter_result,
    })
    print(f"  {adapter_result.get('notes', adapter_result.get('status'))}")

    # 4. Mesh health
    print("\n[4/6] Probing mesh relay health...")
    boundary_map.mesh_health = _check_mesh_health()
    print(f"  Status: {boundary_map.mesh_health['status']}")
    if boundary_map.mesh_health["status"] == "healthy":
        print(f"  Latency: {boundary_map.mesh_health['latency_ms']}ms")
        nodes_data = boundary_map.mesh_health.get("data", {})
        print(f"  Connected nodes: {nodes_data.get('connected_nodes', '?')}")

    # 5. Beast status
    print("\n[5/6] Checking Beast node status...")
    nodes_result = _check_mesh_nodes()
    boundary_map.beast_status = nodes_result
    if nodes_result["status"] == "ok":
        beast_nodes = [n for n in nodes_result.get("nodes", []) if "windows" in str(n.get("id", "")).lower() or "desktop" in str(n.get("id", "")).lower()]
        if beast_nodes:
            beast = beast_nodes[0]
            print(f"  Beast connected: {beast.get('id')}")
            print(f"  Capabilities: {beast.get('capabilities', [])}")
            print(f"  Last heartbeat: {beast.get('last_heartbeat', '?')}")
        else:
            print("  Beast not found in connected nodes")
    else:
        print(f"  Nodes endpoint: {nodes_result['status']}")

    # 6. Live dispatch tests (only with --live flag)
    if live:
        print("\n[6/6] Running live dispatch tests against Beast...")

        # Test command path (what browser_evidence_collector uses)
        print("  Testing command path (echo)...")
        cmd_result = _live_dispatch_test("echo c40a_audit_command_path")
        boundary_map.live_dispatch_results.append({"path": "command", **cmd_result})
        print(f"    Success: {cmd_result['success']}, Latency: {cmd_result['latency_ms']}ms")
        if cmd_result.get("error"):
            print(f"    Error: {cmd_result['error']}")
        if cmd_result.get("response"):
            rd = cmd_result["response"].get("result_data", {})
            print(f"    stdout: {rd.get('stdout', '').strip()[:100]}")

        # Test argv path (what _mesh_dispatch uses)
        print("  Testing argv path (echo)...")
        argv_result = _live_dispatch_argv_test(["echo", "c40a_audit_argv_path"])
        boundary_map.live_dispatch_results.append({"path": "argv", **argv_result})
        print(f"    Success: {argv_result['success']}, Latency: {argv_result['latency_ms']}ms")
        if argv_result.get("error"):
            print(f"    Error: {argv_result['error']}")
        if argv_result.get("response"):
            rd = argv_result["response"].get("result_data", {})
            print(f"    stdout: {rd.get('stdout', '').strip()[:100]}")

        # Test with a more complex command (similar to browser_evidence_collector)
        print("  Testing complex command path...")
        complex_cmd = "python3 -c \"import json; print(json.dumps({'status': 'alive', 'source': 'c40a_audit'}))\""
        complex_result = _live_dispatch_test(complex_cmd, timeout=60)
        boundary_map.live_dispatch_results.append({"path": "complex_command", **complex_result})
        print(f"    Success: {complex_result['success']}, Latency: {complex_result['latency_ms']}ms")
        if complex_result.get("error"):
            print(f"    Error: {complex_result['error']}")

    else:
        print("\n[6/6] Live dispatch tests: SKIPPED (use --live to enable)")
        boundary_map.live_dispatch_results.append({"path": "skipped", "notes": "Use --live flag"})

    # Build hop documentation
    boundary_map.hops = [
        asdict(HopResult(
            hop_id="bec_to_relay",
            source="substrate/meta_ide/browser_evidence_collector.py:100",
            destination="transports/node_mesh/server.py:973",
            transport=f"HTTP POST localhost:{_MESH_HTTP_PORT}/dispatch",
            payload_in_keys=["node_id", "capability", "params", "timeout"],
            payload_out_keys=["node_id", "capability", "params", "timeout"],
            status="documented",
            notes="json.dumps() → urllib POST. Params: {command, timeout}",
        )),
        asdict(HopResult(
            hop_id="relay_extract",
            source="transports/node_mesh/server.py:979",
            destination="transports/node_mesh/server.py:1000",
            transport="in-process",
            payload_in_keys=["node_id", "capability", "params", "timeout"],
            payload_out_keys=["jsonrpc", "method", "params.request_id", "params.capability_name", "params.params", "params.timeout_seconds"],
            status="documented",
            notes="body.get('params', {}) extracts inner params dict. Wraps in JSON-RPC.",
        )),
        asdict(HopResult(
            hop_id="relay_to_beast_ws",
            source="transports/node_mesh/server.py:1012",
            destination="nodes/windows/umh_node/client.py:423",
            transport="WebSocket (json.dumps → ws.send)",
            payload_in_keys=["jsonrpc", "method", "params", "id"],
            payload_out_keys=["method", "params.capability_name", "params.params"],
            status="documented",
            notes="JSON-RPC over WS. Client routes on method='capability.execute'.",
        )),
        asdict(HopResult(
            hop_id="beast_client_extract",
            source="nodes/windows/umh_node/client.py:454-457",
            destination="nodes/windows/umh_node/adapters/shell.py:16",
            transport="in-process function call",
            payload_in_keys=["params.capability_name", "params.params"],
            payload_out_keys=["operation(=cap_name)", "params(=cap_params)"],
            status="documented",
            notes="cap_params = params.get('params', {}). adapter.execute(cap_name, cap_params)",
        )),
        asdict(HopResult(
            hop_id="beast_response",
            source="nodes/windows/umh_node/client.py:525-538",
            destination="transports/node_mesh/server.py:448-459",
            transport="WebSocket JSON-RPC response",
            payload_in_keys=["success", "stdout", "stderr", "exit_code"],
            payload_out_keys=["jsonrpc", "result.success", "result.result_data", "result.latency_ms"],
            status="documented",
            notes="Adapter result wrapped in JSON-RPC response. Relay resolves pending future.",
        )),
    ]

    # Build surface inventory
    boundary_map.surfaces = _build_surfaces()

    return boundary_map


def main() -> None:
    live = "--live" in sys.argv

    boundary_map = run_audit(live=live)

    # Write results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_DIR / "runtime_boundary_map.json"
    with open(output_path, "w") as f:
        json.dump(asdict(boundary_map), f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"Audit complete. Results: {output_path}")
    print(f"{'=' * 60}")

    # Summary
    ser_tests = boundary_map.serialization_tests
    all_pass = all(t["final_status"] == "pass" for t in ser_tests)
    print(f"\nSerialization tests: {'ALL PASS' if all_pass else 'FAILURES DETECTED'}")
    print(f"Hops documented: {len(boundary_map.hops)}")
    print(f"Surfaces documented: {len(boundary_map.surfaces)}")
    print(f"Known issues: {len(boundary_map.known_issues)}")

    if boundary_map.live_dispatch_results:
        live_results = [r for r in boundary_map.live_dispatch_results if r.get("path") != "skipped"]
        if live_results:
            successes = sum(1 for r in live_results if r.get("success"))
            print(f"Live dispatch: {successes}/{len(live_results)} succeeded")

    # Return exit code based on serialization
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
