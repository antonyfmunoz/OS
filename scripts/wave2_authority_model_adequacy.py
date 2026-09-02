#!/usr/bin/env python3
"""Run executable reachability checks for the Wave 2 authority model."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

WITNESSES = (
    "PreLaunchCancel",
    "CancelDuringLaunch",
    "KnownProcessCancel",
    "ConnectionLossDuringExecution",
    "Failed",
    "Cancelled",
    "Reconciliation",
    "StaleAck",
    "ConnectionOverlapAttempt",
    "PumpOverlapAttempt",
    "ResultSentNotAccepted",
    "ClaimSentNotPersisted",
    "JobContainedBeforeResume",
    "ConnectionAActive",
    "PumpAActive",
    "NewExchangePending",
    "ResumeAmbiguous",
    "CleanupIncomplete",
    "SnapshotFailureUnknown",
    "OpenThreadFailureUnknown",
    "ResumeExpected",
    "ResumeUnexpectedZero",
    "ResumeUnexpectedMultiple",
    "ResumeFailure",
    "UnexpectedResumeExistingRunning",
    "UnknownResumeReconciliation",
)

CONSTANTS = """\
AuthorityCapacity = 2
BulkCapacity = 2
ReconCapacity = 2
AuthorityBurstLimit = 2
SendBound = 2
MaxReconChecks = 4
MaxTransportGeneration = 2
MaxGenerationTasks = 2
EnforceConnectionSingleton = TRUE
EnforcePumpSingleton = TRUE
EnforceAckExchangeBinding = TRUE
EnforcePreLaunchCancellation = TRUE
EnforceTerminalCleanup = TRUE
EnforceLaunchUncertaintyTerminalGuard = TRUE
EnforceSnapshotObservationTruth = TRUE
EnforceOpenThreadObservationTruth = TRUE
EnforceResumeResultContract = TRUE
EnforceUnexpectedResumeNoRelaunch = TRUE
EnforceUnknownSuspendTerminalGuard = TRUE
"""


def _run(jar: Path, model_dir: Path, invariant: str, constants: str = CONSTANTS) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".cfg", dir=model_dir, delete=False) as cfg:
        cfg.write(f"SPECIFICATION Spec\n\nCONSTANT\n{constants}\nINVARIANT {invariant}\n")
        cfg_path = Path(cfg.name)
    try:
        with tempfile.TemporaryDirectory(prefix="wave2-tlc-adequacy-") as metadir:
            proc = subprocess.run(
                [
                    "java",
                    "-XX:+UseParallelGC",
                    "-cp",
                    str(jar),
                    "tlc2.TLC",
                    "-noGenerateSpecTE",
                    "-metadir",
                    metadir,
                    "-config",
                    cfg_path.name,
                    "Wave2AuthorityPlaneAdequacy.tla",
                ],
                cwd=model_dir,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
    finally:
        cfg_path.unlink(missing_ok=True)
    expected = f"Invariant {invariant} is violated"
    if proc.returncode == 0 or expected not in proc.stdout:
        raise RuntimeError(
            f"adequacy check {invariant} did not produce its expected witness\n{proc.stdout[-4000:]}"
        )
    return expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("models/wave2_authority_plane_liveness"),
    )
    args = parser.parse_args()
    for witness in WITNESSES:
        _run(args.jar.resolve(), args.model_dir.resolve(), f"NotWitness{witness}")
        print(f"PASS witness {witness}")

    connection_mutant = CONSTANTS.replace(
        "EnforceConnectionSingleton = TRUE", "EnforceConnectionSingleton = FALSE"
    )
    _run(
        args.jar.resolve(),
        args.model_dir.resolve(),
        "AtMostOneActiveConnectionGeneration",
        connection_mutant,
    )
    print("PASS mutation connection singleton guard")
    pump_mutant = CONSTANTS.replace(
        "EnforcePumpSingleton = TRUE", "EnforcePumpSingleton = FALSE"
    )
    _run(
        args.jar.resolve(),
        args.model_dir.resolve(),
        "AtMostOneDurablePumpGeneration",
        pump_mutant,
    )
    print("PASS mutation pump singleton guard")
    for constant, invariant, label in (
        (
            "EnforceAckExchangeBinding",
            "StaleAckForNewExchangeCannotProveAuthority",
            "ACK exchange binding",
        ),
        (
            "EnforcePreLaunchCancellation",
            "PreLaunchCancellationPreventsProcessCreation",
            "pre-launch cancellation",
        ),
        (
            "EnforceTerminalCleanup",
            "OrdinaryTerminalRequiresAdmissibility",
            "terminal cleanup gate",
        ),
        (
            "EnforceLaunchUncertaintyTerminalGuard",
            "LaunchUncertaintyCannotTerminalize",
            "launch uncertainty terminal guard",
        ),
        (
            "EnforceSnapshotObservationTruth",
            "ObservationFailureCannotProveSuspended",
            "snapshot failure remains unknown",
        ),
        (
            "EnforceOpenThreadObservationTruth",
            "ObservationFailureCannotProveSuspended",
            "OpenThread failure remains unknown",
        ),
        (
            "EnforceResumeResultContract",
            "UnexpectedResumeCannotEstablishRunning",
            "unexpected resume cannot establish running",
        ),
        (
            "EnforceUnexpectedResumeNoRelaunch",
            "AtMostOneProcessCreation",
            "unexpected resume cannot relaunch",
        ),
        (
            "EnforceUnknownSuspendTerminalGuard",
            "UnknownLaunchStateCannotTerminalizeFailed",
            "unknown suspend state terminal guard",
        ),
    ):
        mutant = CONSTANTS.replace(f"{constant} = TRUE", f"{constant} = FALSE")
        _run(args.jar.resolve(), args.model_dir.resolve(), invariant, mutant)
        print(f"PASS mutation {label}")
    print("MODEL_ADEQUACY=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
