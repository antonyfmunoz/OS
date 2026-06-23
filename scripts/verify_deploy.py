#!/usr/bin/env python3
"""Standalone post-deploy verification script.

Usage:
    python3 scripts/verify_deploy.py <app_name> <public_url> [--health-path /api/health] [--expected-values pk_test_,pk_live_]

Runs the DeployVerificationWorker pipeline and prints results.
Exit code 0 = all checks passed, 1 = failures detected.
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.deploy_verification_worker import (
    DeployVerificationWorker,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Post-deploy verification for UMH projections"
    )
    parser.add_argument("app_name", help="Application name (e.g. eos-app)")
    parser.add_argument("public_url", help="Public URL (e.g. https://entrepreneuros.net)")
    parser.add_argument(
        "--health-path",
        default="/api/health",
        help="Health endpoint path (default: /api/health)",
    )
    parser.add_argument(
        "--expected-values",
        default="",
        help="Comma-separated expected bundle values (e.g. pk_test_,pk_live_)",
    )
    parser.add_argument(
        "--health-timeout",
        type=float,
        default=120.0,
        help="Health check timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    expected = (
        [v.strip() for v in args.expected_values.split(",") if v.strip()]
        if args.expected_values
        else None
    )

    worker = DeployVerificationWorker()
    result = worker.verify_deployment(
        app_name=args.app_name,
        public_url=args.public_url,
        health_path=args.health_path,
        expected_bundle_values=expected,
        health_timeout_seconds=args.health_timeout,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "PASSED" if result.overall_passed else "FAILED"
        print(f"\n=== Deploy Verification: {status} ===")
        print(f"App: {result.app_name}")
        print(f"URL: {result.public_url}")
        print(f"Duration: {result.total_duration_ms}ms")
        print()
        for check in result.checks:
            icon = "✅" if check.status.value == "passed" else "❌"
            print(f"  {icon} {check.check_name}: {check.detail}")
        if result.critical_failures:
            print()
            print("Critical failures:")
            for failure in result.critical_failures:
                print(f"  ❌ {failure}")
        print()

    return 0 if result.overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
