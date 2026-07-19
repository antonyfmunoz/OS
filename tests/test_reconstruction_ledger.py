"""Tests for the append-preserving claim ledger + deterministic scoring."""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("UMH_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(REPO_ROOT))

from substrate.understanding.reconstruction import contracts as C
from substrate.understanding.reconstruction import ledger as L

_FULL = {
    "directness": 1,
    "source_authority": 1,
    "method_strength": 1,
    "independence": 1,
    "scope_match": 1,
    "recency": 1,
    "runtime_verification": 1,
}


class TestLedger:
    def test_full_factors_score_one(self):
        assert abs(L.support_score(_FULL)["score"] - 1.0) < 1e-9

    def test_contradiction_caps_and_flags(self):
        r = L.support_score(dict(_FULL, contradiction=0.9))
        assert r["contradicted"] and r["score"] <= L.CONTRADICTED_SCORE_CAP

    def test_missing_factors_preserved(self):
        r = L.support_score({"directness": 1})
        assert r["factors"]["source_authority"] is None and r["completeness"] < 1.0
        assert any(n.startswith("missing:") for n in r["notes"])

    def test_empty_factors_zero(self):
        r = L.support_score({})
        assert r["score"] == 0.0 and "no-present-factors" in r["notes"]

    def test_score_docstring_states_not_probability(self):
        doc = " ".join(L.support_score.__doc__.lower().split())
        assert "not a calibrated probability" in doc

    def test_transition_validated(self):
        led = L.ClaimLedger()
        e = led.append(C.ClaimLedgerEntry("p", "c", "s", "proposed", "r"))
        led.transition(e, "supported")
        try:
            led.transition(e, "deployed")
            assert False
        except ValueError:
            pass

    def test_supersede_preserves_history(self):
        led = L.ClaimLedger()
        e = led.append(
            C.ClaimLedgerEntry(
                "p",
                "c",
                "s",
                "supported",
                "r",
                recorded_at="2026-01-01",
                support_score=0.8,
            )
        )
        repl = C.ClaimLedgerEntry(
            "p",
            "c",
            "s",
            "supported",
            "r2",
            recorded_at="2026-02-01",
            support_score=0.95,
        )
        led.supersede(e, repl)
        assert len(led.entries) == 2
        bs = led.belief_state()
        assert len(bs) == 1 and bs[0].support_score == 0.95

    def test_reconstruct_as_of_past(self):
        led = L.ClaimLedger()
        e = led.append(C.ClaimLedgerEntry("p", "c", "s", "proposed", "r", recorded_at="2026-01-01"))
        led.transition(e, "supported", recorded_at="2026-02-01", support_score=0.9)
        assert led.reconstruct_as_of("2026-01-15")[0].status == "proposed"
        assert led.reconstruct_as_of("2026-03-01")[0].status == "supported"

    def test_independence_shared_root_one_line(self):
        c = C.ClaimLedgerEntry(
            "p",
            "t",
            "s",
            "supported",
            "r",
            supporting_observation_ids=("o1", "o2", "o3"),
        )
        rep = L.independence_report(
            [c], {"o1": "s1", "o2": "s1", "o3": "s2"}, {"s1": "root", "s2": "root"}
        )
        assert rep[c.lineage_id()]["independent_lines"] == 1

    def test_independence_distinct_roots(self):
        c = C.ClaimLedgerEntry(
            "p2",
            "t",
            "s",
            "supported",
            "r",
            supporting_observation_ids=("o1", "o2"),
        )
        rep = L.independence_report([c], {"o1": "s1", "o2": "s2"})
        assert rep[c.lineage_id()]["independent_lines"] == 2
