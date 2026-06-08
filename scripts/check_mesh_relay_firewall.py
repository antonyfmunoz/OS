#!/usr/bin/env python3
"""Check mesh relay firewall state for correctness and safety.

Reports:
- Relay port and validation status
- Docker bridge CIDR
- Whether UMH_MESH_RELAY chain exists and has correct rules
- Whether legacy top-of-chain ACCEPT rules exist (unsafe)
- Whether duplicate rules exist
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

_RELAY_CHAIN = "UMH_MESH_RELAY"
_DOCKER_CIDR = "172.18.0.0/16"

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
WARN = "\033[33mWARN\033[0m"


def _run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def main() -> int:
    from transports.node_mesh.config import load_mesh_config

    config = load_mesh_config()
    relay_port = config.port + 1
    issues = 0

    print(f"Mesh relay firewall check")
    print(f"{'=' * 50}")

    # 1. Port validation
    print(f"\n[1] Relay port: {relay_port}")
    if 1024 <= relay_port <= 65535:
        print(f"    Validation: {PASS} (in range 1024-65535)")
    else:
        print(f"    Validation: {FAIL} (out of range)")
        issues += 1

    # 2. Docker bridge CIDR
    try:
        rc, out = _run(["docker", "network", "inspect", "os_eos_network"])
        if rc == 0:
            data = json.loads(out)
            cidr = data[0]["IPAM"]["Config"][0]["Subnet"]
            match = cidr == _DOCKER_CIDR
            print(f"\n[2] Docker bridge CIDR: {cidr}")
            print(f"    Matches expected ({_DOCKER_CIDR}): {PASS if match else FAIL}")
            if not match:
                issues += 1
        else:
            print(f"\n[2] Docker bridge: {WARN} could not inspect os_eos_network")
    except Exception as e:
        print(f"\n[2] Docker bridge: {WARN} {e}")

    # 3. Dedicated chain exists
    rc, _ = _run(["iptables", "-L", _RELAY_CHAIN, "-n"])
    chain_exists = rc == 0
    print(f"\n[3] Chain {_RELAY_CHAIN}: {'exists' if chain_exists else 'MISSING'} {PASS if chain_exists else FAIL}")
    if not chain_exists:
        issues += 1

    # 4. Chain has correct ACCEPT rule
    if chain_exists:
        rc, chain_rules = _run(["iptables", "-S", _RELAY_CHAIN])
        accept_rules = [
            r for r in chain_rules.splitlines()
            if "ACCEPT" in r and str(relay_port) in r and _DOCKER_CIDR in r
        ]
        print(f"\n[4] Chain ACCEPT rule (port {relay_port}, src {_DOCKER_CIDR}):")
        if len(accept_rules) == 1:
            print(f"    {PASS} exactly 1 rule")
            print(f"    Rule: {accept_rules[0]}")
        elif len(accept_rules) == 0:
            print(f"    {FAIL} no matching ACCEPT rule")
            issues += 1
        else:
            print(f"    {WARN} {len(accept_rules)} duplicate rules")
            for r in accept_rules:
                print(f"    Rule: {r}")
            issues += 1
    else:
        print(f"\n[4] Chain rules: {FAIL} chain does not exist")

    # 5. INPUT jumps to chain
    rc, input_rules = _run(["iptables", "-S", "INPUT"])
    jumps = [r for r in input_rules.splitlines() if _RELAY_CHAIN in r]
    print(f"\n[5] INPUT → {_RELAY_CHAIN} jump:")
    if len(jumps) == 1:
        print(f"    {PASS} exactly 1 jump")
    elif len(jumps) == 0:
        print(f"    {FAIL} no jump to {_RELAY_CHAIN}")
        issues += 1
    else:
        print(f"    {WARN} {len(jumps)} duplicate jumps")
        issues += 1

    # 6. Check for legacy unsafe top-of-chain ACCEPT
    legacy_rules = [
        r for r in input_rules.splitlines()
        if "ACCEPT" in r and str(relay_port) in r and _DOCKER_CIDR in r
        and _RELAY_CHAIN not in r
    ]
    print(f"\n[6] Legacy top-of-chain ACCEPT (unsafe):")
    if not legacy_rules:
        print(f"    {PASS} none found")
    else:
        print(f"    {FAIL} {len(legacy_rules)} legacy rule(s) — should be removed")
        for r in legacy_rules:
            print(f"    Rule: {r}")
        issues += 1

    # 7. Duplicate check across all of INPUT
    all_8095 = [r for r in input_rules.splitlines() if str(relay_port) in r]
    print(f"\n[7] Total INPUT rules referencing port {relay_port}: {len(all_8095)}")
    if len(all_8095) <= 1:
        print(f"    {PASS} no duplicates")
    else:
        print(f"    {WARN} multiple rules — review for duplicates")
        for r in all_8095:
            print(f"    {r}")

    # Summary
    print(f"\n{'=' * 50}")
    if issues == 0:
        print(f"Result: {PASS} — firewall is correctly configured")
    else:
        print(f"Result: {FAIL} — {issues} issue(s) found")
    return issues


if __name__ == "__main__":
    sys.exit(main())
