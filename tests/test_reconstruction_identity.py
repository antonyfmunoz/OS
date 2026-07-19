"""Tests for the identity-resolution record lifecycle."""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("UMH_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(REPO_ROOT))

from substrate.understanding.reconstruction import contracts as C
from substrate.understanding.reconstruction import identity as I


class TestIdentity:
    def test_merge_requires_evidence(self):
        log = I.IdentityResolutionLog()
        try:
            log.append(C.IdentityResolution(("a", "b"), "merge", "r"))
            assert False
        except ValueError:
            pass

    def test_valid_merge(self):
        log = I.IdentityResolutionLog()
        log.append(C.IdentityResolution(("a", "b"), "merge", "r", supporting_evidence_ids=("e1",)))
        assert len(log.merges()) == 1

    def test_needs_two_candidates(self):
        log = I.IdentityResolutionLog()
        try:
            log.append(C.IdentityResolution(("a",), "link", "r"))
            assert False
        except ValueError:
            pass

    def test_supersede_flips_and_preserves(self):
        log = I.IdentityResolutionLog()
        m = log.append(
            C.IdentityResolution(
                ("a", "b"),
                "merge",
                "r",
                supporting_evidence_ids=("e1",),
                recorded_at="2026-01-01",
            )
        )
        log.supersede(
            m,
            C.IdentityResolution(("a", "b"), "remain_separate", "r2", recorded_at="2026-02-01"),
        )
        assert len(log.entries) == 2
        assert log.current()[0].verdict == "remain_separate"
        assert log.merges() == []

    def test_candidate_pair_sorted(self):
        assert I.candidate_pair("z", "a") == ("a", "z")
