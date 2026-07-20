"""Grounded Self-Model evaluation (DOMAIN_RECONSTRUCTION_SPEC §13-14).

Deterministic pure functions over the run artifacts produced by builder.py.
Shared by tests and scripts/verify_grounded_self_model.py. NO subprocess, no
network, no mutation of the run — every function reads the run directory and
returns dicts.

The five evaluation classes (§4.12): retrieval, structural, temporal,
mechanism-safety, decision-usefulness. Plus the acceptance vector and the four
terminal statuses (§4.12): OPERATIONAL / PARTIALLY_OPERATIONAL /
INSUFFICIENT_EVIDENCE / FAILED. "COMPLETE" is never a status; N/A is never a pass.

The load-bearing check (§4.3): no ClaimLedgerEntry with status "supported" whose
supporting observations are ALL declaration-facet.

Convergence citations are VERIFIED, not pattern-matched: acceptance parses
every [claimentry:...] / [obs:...] / [identityentry:...] / [source:...] token
out of convergence.md and resolves each against the actual ledgers — a heading
alone can never satisfy the criterion.

DQ3 tests the ABILITY TO DISTINGUISH documented/configured state from runtime
state: it passes when the deployment_configured-vs-running check was performed,
whether or not a mismatch was found — "no mismatch within observed coverage"
is a valid answer, and a fully-running system does not fail.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Literal

from substrate.understanding.reconstruction.competency_questions import COMPETENCY_IDS
from substrate.understanding.reconstruction.contracts import (
    DECLARATION_FACETS,
    SCHEMA_VERSION,
)
from substrate.understanding.reconstruction.provenance import file_sha256

logger = logging.getLogger(__name__)

FinalStatus = Literal["OPERATIONAL", "PARTIALLY_OPERATIONAL", "INSUFFICIENT_EVIDENCE", "FAILED"]

VALID_CLAIM_STATUSES: frozenset[str] = frozenset(
    {"proposed", "supported", "contested", "superseded", "falsified", "unresolved"}
)

# Criteria whose FAIL forces a non-OPERATIONAL / FAILED terminal status (§14).
CRITICAL_CRITERIA: tuple[str, ...] = (
    "all_claims_evidenced_or_marked",
    "evidence_refs_resolve",
    "provenance_integrity",
    "append_preserving",
    "no_design_as_implementation",
    "no_basis_free_causal",
    "no_secrets_emitted",
    "ten_questions_answered_or_unknown",
    "convergence_cites_ids",
    "gates_clean_flag",
    "targeted_tests_flag",
)

# Criteria whose FAIL denotes an INTEGRITY/SAFETY violation → FAILED terminal.
_INTEGRITY_SAFETY_CRITERIA: frozenset[str] = frozenset(
    {
        "evidence_refs_resolve",
        "provenance_integrity",
        "append_preserving",
        "no_design_as_implementation",
        "no_basis_free_causal",
        "no_secrets_emitted",
    }
)

# Secret-leak signatures scanned across emitted artifacts.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*['\"][^'\"]{8,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
)

# Record-id citation tokens in convergence.md — parsed AND resolved.
_CITATION_RE = re.compile(
    r"\[((?:claimentry|obs|identityentry|source|causal|activity):[0-9a-f]{64})\]"
)


# ── artifact loading ────────────────────────────────────────────────────────


def _read_json(run_dir: Path, name: str) -> Any:
    p = run_dir / name
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _read_jsonl(run_dir: Path, name: str) -> list[dict[str, Any]]:
    p = run_dir / name
    if not p.is_file():
        return []
    out: list[dict[str, Any]] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw:
            out.append(json.loads(raw))
    return out


def load_run(run_dir: str | Path) -> dict[str, Any]:
    """Load every artifact from a run directory into a single dict.

    claims.jsonl is the AUTHORITATIVE ledger (model.json holds only indexes)."""
    rd = Path(run_dir)
    return {
        "run_dir": rd,
        "manifest": _read_json(rd, "manifest.json") or {},
        "model": _read_json(rd, "model.json") or {},
        "coverage": _read_json(rd, "coverage.json") or {},
        "divergence": _read_json(rd, "divergence.json") or {},
        "sources": _read_jsonl(rd, "sources.jsonl"),
        "observations": _read_jsonl(rd, "observations.jsonl"),
        "claims": _read_jsonl(rd, "claims.jsonl"),
        "activities": _read_jsonl(rd, "activities.jsonl"),
        "identities": _read_jsonl(rd, "identity_resolutions.jsonl"),
    }


# ── class 1: retrieval ──────────────────────────────────────────────────────


def check_retrieval(run: dict[str, Any]) -> dict[str, Any]:
    """Records retrievable by id / subject / facet / source from artifacts."""
    obs = run["observations"]
    by_id = {o["id"]: o for o in obs}
    by_subject: dict[str, list[str]] = {}
    by_facet: dict[str, list[str]] = {}
    by_source: dict[str, list[str]] = {}
    for o in obs:
        by_subject.setdefault(o["subject"], []).append(o["id"])
        facet = o.get("maturity_facet")
        if facet:
            by_facet.setdefault(facet, []).append(o["id"])
        by_source.setdefault(o["source_id"], []).append(o["id"])
    findings: list[str] = []
    ok = True
    # Every claim's supporting obs must be retrievable by id.
    for c in run["claims"]:
        for oid in c.get("supporting_observation_ids", []):
            if oid not in by_id:
                ok = False
                findings.append(f"claim {c['id']} cites unretrievable obs {oid}")
    return {
        "passed": ok,
        "retrievable_by_id": len(by_id),
        "distinct_subjects": len(by_subject),
        "distinct_facets": len(by_facet),
        "distinct_sources": len(by_source),
        "findings": findings,
    }


# ── class 2: structural ─────────────────────────────────────────────────────


def check_structural(run: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    ok = True

    def note(msg: str) -> None:
        nonlocal ok
        ok = False
        findings.append(msg)

    # schema_version present on artifacts + records
    for name in ("model", "coverage", "divergence"):
        art = run[name]
        if art and art.get("schema_version") != SCHEMA_VERSION:
            note(f"{name}.schema_version != {SCHEMA_VERSION}")

    source_ids = {s["id"] for s in run["sources"]}
    obs_ids = {o["id"] for o in run["observations"]}
    activity_ids = {a["id"] for a in run["activities"]}

    # unique ids
    if len(source_ids) != len(run["sources"]):
        note("duplicate source ids")
    if len(obs_ids) != len(run["observations"]):
        note("duplicate observation ids")

    # referential integrity: every observation's source resolves
    for o in run["observations"]:
        if o["source_id"] not in source_ids:
            note(f"observation {o['id']} source_id {o['source_id']} unresolved")

    # provenance chain: every source's activity resolves (when activities exist)
    if activity_ids:
        for s in run["sources"]:
            if s.get("activity_id") and s["activity_id"] not in activity_ids:
                note(f"source {s['id']} activity_id {s['activity_id']} unresolved")

    # every claim's supporting/contradicting obs resolve; valid status
    for c in run["claims"]:
        if c.get("status") not in VALID_CLAIM_STATUSES:
            note(f"claim {c['id']} invalid status {c.get('status')}")
        for oid in c.get("supporting_observation_ids", []) + c.get(
            "contradicting_observation_ids", []
        ):
            if oid not in obs_ids:
                note(f"claim {c['id']} references unresolved obs {oid}")

    # all 10 competency questions present in model.json, each with a valid
    # answer_status and either items or an explicit unknown_reason
    model_q = run["model"].get("competency_questions", [])
    q_by_id = {q.get("question_id"): q for q in model_q}
    for qid in COMPETENCY_IDS:
        q = q_by_id.get(qid)
        if q is None:
            note(f"competency question {qid} absent from model.json")
            continue
        status = q.get("answer_status")
        if status not in ("ANSWERED", "UNKNOWN"):
            note(f"competency question {qid} has invalid answer_status {status!r}")
        elif status == "UNKNOWN" and not q.get("unknown_reason"):
            note(f"competency question {qid} UNKNOWN without unknown_reason")

    return {"passed": ok, "findings": findings}


# ── class 3: temporal ───────────────────────────────────────────────────────


def check_temporal(run: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    ok = True

    def note(msg: str) -> None:
        nonlocal ok
        ok = False
        findings.append(msg)

    # recorded_at never removed where present; valid_time qualifier explicit
    for o in run["observations"]:
        if "recorded_at" not in o:
            note(f"observation {o['id']} missing recorded_at key")
        vt = o.get("valid_time", {})
        if vt and vt.get("qualifier") not in ("instant", "interval", "open", "unknown"):
            note(f"observation {o['id']} invalid valid_time qualifier")

    # supersession preserves prior entries: every supersedes target still present
    claim_ids = {c["id"] for c in run["claims"]}
    for c in run["claims"]:
        sup = c.get("supersedes")
        if sup and sup not in claim_ids:
            note(f"claim {c['id']} supersedes missing entry {sup}")

    # identity supersession preserves prior entries too
    ident_ids = {r["id"] for r in run["identities"]}
    for r in run["identities"]:
        sup = r.get("supersedes")
        if sup and sup not in ident_ids:
            note(f"identity {r['id']} supersedes missing entry {sup}")

    return {"passed": ok, "findings": findings}


# ── class 4: mechanism-safety ───────────────────────────────────────────────


def check_mechanism_safety(run: dict[str, Any]) -> dict[str, Any]:
    """Causal records carry a typed basis; experimental basis needs a method.

    Causal records are OPTIONAL in a run; if absent this class is vacuously
    safe. Any causal record present must carry a non-empty basis, and a basis
    of 'experimental' or 'quasi_experimental' requires a non-empty method
    (textual repetition may not be labeled experimental). The basis is a typed
    evidence class, never a global rank — validity dimensions are separate.
    """
    findings: list[str] = []
    ok = True
    causal = run.get("causal") or []
    # causal records may be embedded in model.json under a 'causal' key
    causal = causal or run["model"].get("causal", [])
    for cr in causal:
        basis = cr.get("basis")
        if not basis:
            ok = False
            findings.append(f"causal {cr.get('id')} has no basis")
        if basis in ("experimental", "quasi_experimental") and not cr.get("method"):
            ok = False
            findings.append(f"causal {cr.get('id')} basis={basis} but method is empty")
    return {"passed": ok, "causal_records": len(causal), "findings": findings}


# ── critical §4.3 invariant ─────────────────────────────────────────────────


def check_no_design_as_implementation(run: dict[str, Any]) -> dict[str, Any]:
    """No 'supported' claim whose supporting observations are ALL declaration-facet.

    A claim resting only on declared/specified observations may be at most
    'proposed'/'unresolved' — never 'supported'. This is the single failure mode
    the spec exists to prevent (intent laundered into fact).
    """
    obs_by_id = {o["id"]: o for o in run["observations"]}
    violations: list[str] = []
    for c in run["claims"]:
        if c.get("status") != "supported":
            continue
        sup = c.get("supporting_observation_ids", [])
        if not sup:
            continue
        facets = [obs_by_id.get(oid, {}).get("maturity_facet") for oid in sup]
        facets = [f for f in facets if f is not None]
        if facets and all(f in DECLARATION_FACETS for f in facets):
            violations.append(c["id"])
    return {"passed": not violations, "violations": violations}


# ── convergence citation resolution ─────────────────────────────────────────


def check_convergence_citations(run: dict[str, Any]) -> dict[str, Any]:
    """Parse [namespace:hash] tokens from convergence.md and RESOLVE each
    against the actual ledgers. A syntactic heading never satisfies this, and
    neither does a pure-intent model: at least one cited record must be
    GROUNDED beyond declaration — an observation with an implementation or
    runtime maturity facet, or a mined (evidence-era) identity candidate."""
    conv_path = run["run_dir"] / "convergence.md"
    if not conv_path.is_file():
        return {
            "passed": False,
            "cited": 0,
            "resolved": 0,
            "grounded": 0,
            "unresolved": ["<missing convergence.md>"],
        }
    text = conv_path.read_text(encoding="utf-8")
    cited = _CITATION_RE.findall(text)
    known: set[str] = set()
    grounded_ids: set[str] = set()
    for o in run["observations"]:
        rid = o.get("id")
        if rid:
            known.add(rid)
            facet = o.get("maturity_facet")
            if facet and facet not in DECLARATION_FACETS:
                grounded_ids.add(rid)
    for r in run["identities"]:
        rid = r.get("id")
        if rid:
            known.add(rid)
            if str(r.get("candidate_basis", "")).startswith("mined:"):
                grounded_ids.add(rid)
    for coll in ("sources", "claims", "activities"):
        for rec in run[coll]:
            rid = rec.get("id")
            if rid:
                known.add(rid)
    unresolved = sorted({c for c in cited if c not in known})
    grounded = sum(1 for c in set(cited) if c in grounded_ids)
    passed = bool(cited) and not unresolved and grounded > 0
    return {
        "passed": passed,
        "cited": len(cited),
        "resolved": len(cited) - len(unresolved),
        "grounded": grounded,
        "unresolved": unresolved,
    }


# ── decision-usefulness (5 fixed questions) ─────────────────────────────────

DECISION_QUESTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "DQ1",
        "question": "What is the canonical mutation path?",
        "expect_claim_type": "canonical_owner",
    },
    {
        "id": "DQ2",
        "question": "What is the world-model implementation state?",
        "expect_observation_predicate": "world_model_entity",
    },
    {
        "id": "DQ3",
        "question": ("Can the model DISTINGUISH documented/configured state from runtime state?"),
        # Valid answers: mismatch found and evidenced, OR no mismatch found
        # within observed coverage — but the comparison must have had REAL
        # inputs: a model with zero configured subjects cannot answer this.
        "expect_check_performed": "deployment_configured_vs_running",
        "expect_min_compared": 1,
    },
    {
        "id": "DQ4",
        "question": "Is there a duplication/overlap finding?",
        # Seed fixtures are ALWAYS emitted, so their presence proves nothing.
        # A real finding is a mined candidate or an evidence-backed verdict.
        "expect_identity_grounded": True,
    },
    {
        "id": "DQ5",
        "question": "Is there a convergence verification requirement?",
        "expect_convergence_marker": "Verification requirements",
    },
)


def check_decision_usefulness(run: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    answered = 0
    claims = run["claims"]
    obs = run["observations"]
    checks = run["divergence"].get("checks_performed", [])
    idents = run["identities"]
    conv_path = run["run_dir"] / "convergence.md"
    conv_text = conv_path.read_text(encoding="utf-8") if conv_path.is_file() else ""

    for q in DECISION_QUESTIONS:
        ok_q = False
        if "expect_claim_type" in q:
            ok_q = any(c.get("claim_type") == q["expect_claim_type"] for c in claims)
        elif "expect_observation_predicate" in q:
            ok_q = any(o.get("predicate") == q["expect_observation_predicate"] for o in obs)
        elif "expect_check_performed" in q:
            ok_q = any(
                c.get("check") == q["expect_check_performed"]
                and c.get("status") == "performed"
                and c.get("compared_subjects", 0) >= q.get("expect_min_compared", 0)
                for c in checks
            )
        elif "expect_identity_grounded" in q:
            # Seed fixtures are always emitted — a real duplication finding is
            # a mined candidate or an evidence-backed verdict.
            ok_q = any(
                str(r.get("candidate_basis", "")).startswith("mined:")
                or r.get("supporting_evidence_ids")
                for r in idents
            )
        elif "expect_convergence_marker" in q:
            ok_q = q["expect_convergence_marker"] in conv_text
        if ok_q:
            answered += 1
        else:
            findings.append(f"{q['id']} unanswered: {q['question']}")
    return {
        "passed": answered == len(DECISION_QUESTIONS),
        "answered": answered,
        "total": len(DECISION_QUESTIONS),
        "findings": findings,
    }


# ── artifact-hash integrity ─────────────────────────────────────────────────


def verify_artifact_hashes(run_dir: str | Path) -> dict[str, Any]:
    """Recompute artifact hashes and compare with the manifest's recorded ones.

    Referential-integrity check, NOT cryptographic tamper proof (the manifest
    itself is writable). Absent artifact_hashes → not verifiable (recorded)."""
    rd = Path(run_dir)
    manifest = _read_json(rd, "manifest.json") or {}
    recorded = manifest.get("artifact_hashes")
    if not recorded:
        return {"verifiable": False, "passed": False, "mismatches": [], "checked": 0}
    mismatches: list[str] = []
    checked = 0
    for name, expected in sorted(recorded.items()):
        p = rd / name
        if not p.is_file():
            mismatches.append(f"{name}: recorded but missing")
            continue
        checked += 1
        actual = file_sha256(p)
        if actual != expected:
            mismatches.append(f"{name}: hash mismatch")
    return {
        "verifiable": True,
        "passed": not mismatches,
        "mismatches": mismatches,
        "checked": checked,
    }


# ── acceptance vector (§14) ─────────────────────────────────────────────────


def _scan_secrets(run_dir: Path) -> list[str]:
    hits: list[str] = []
    for p in sorted(run_dir.iterdir()):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.debug("secret scan could not read %s: %s", p, exc)
            continue
        for pat in _SECRET_PATTERNS:
            if pat.search(text):
                hits.append(f"{p.name}:{pat.pattern[:24]}")
    return hits


def acceptance_vector(run_dir: str | Path) -> dict[str, Any]:
    """Per-criterion PASS/FAIL/PARTIAL/N_A vector (§14).

    N/A is excluded from the denominator and never counted as a pass.
    """
    rd = Path(run_dir)
    run = load_run(rd)

    retrieval = check_retrieval(run)
    structural = check_structural(run)
    temporal = check_temporal(run)
    mech = check_mechanism_safety(run)
    no_design = check_no_design_as_implementation(run)
    usefulness = check_decision_usefulness(run)
    citations = check_convergence_citations(run)
    artifact_hashes = verify_artifact_hashes(rd)

    obs_ids = {o["id"] for o in run["observations"]}
    source_ids = {s["id"] for s in run["sources"]}

    # all_claims_evidenced_or_marked: supported claim needs supporting obs;
    # a claim with none must be a non-asserting status.
    claims = run["claims"]
    unevidenced = [
        c["id"]
        for c in claims
        if c.get("status") == "supported" and not c.get("supporting_observation_ids")
    ]

    # evidence_refs_resolve: every referenced obs/source id resolves
    refs_ok = all(
        oid in obs_ids
        for c in claims
        for oid in c.get("supporting_observation_ids", [])
        + c.get("contradicting_observation_ids", [])
    ) and all(o["source_id"] in source_ids for o in run["observations"])

    # provenance_integrity: every source has an activity_id; every observation a
    # source; every source's activity resolves when activities are recorded.
    activity_ids = {a["id"] for a in run["activities"]}
    prov_ok = all(s.get("activity_id") for s in run["sources"]) and all(
        o.get("source_id") for o in run["observations"]
    )
    if prov_ok and activity_ids:
        prov_ok = all(
            s["activity_id"] in activity_ids for s in run["sources"] if s.get("activity_id")
        )

    # ten questions answered-or-unknown (with valid answer_status)
    model_q = run["model"].get("competency_questions", [])
    q_by_id = {q.get("question_id"): q for q in model_q}
    ten_ok = all(
        q_by_id.get(qid, {}).get("answer_status") in ("ANSWERED", "UNKNOWN")
        for qid in COMPETENCY_IDS
    )

    secrets = _scan_secrets(rd)

    # gates_clean_flag / targeted_tests_flag: recorded in manifest via the
    # supported record_run_outcomes() mechanism; absent → N_A (excluded from
    # denominator, never a pass).
    manifest = run["manifest"]
    gates_flag = manifest.get("gates_clean")
    tests_flag = manifest.get("targeted_tests_passed")

    def verdict(passed: bool) -> str:
        return "PASS" if passed else "FAIL"

    criteria: dict[str, str] = {
        "all_claims_evidenced_or_marked": verdict(not unevidenced),
        "evidence_refs_resolve": verdict(refs_ok),
        "provenance_integrity": verdict(prov_ok),
        "append_preserving": verdict(temporal["passed"]),
        "no_design_as_implementation": verdict(no_design["passed"]),
        "no_basis_free_causal": verdict(mech["passed"]),
        "no_secrets_emitted": verdict(not secrets),
        "ten_questions_answered_or_unknown": verdict(ten_ok),
        "convergence_cites_ids": verdict(citations["passed"]),
        "gates_clean_flag": "N_A" if gates_flag is None else verdict(bool(gates_flag)),
        "targeted_tests_flag": "N_A" if tests_flag is None else verdict(bool(tests_flag)),
        # non-critical supporting criteria
        "retrieval": verdict(retrieval["passed"]),
        "structural": verdict(structural["passed"]),
        "artifact_hashes": (
            "N_A" if not artifact_hashes["verifiable"] else verdict(artifact_hashes["passed"])
        ),
        "decision_usefulness": "PARTIAL"
        if 0 < usefulness["answered"] < usefulness["total"]
        else verdict(usefulness["passed"]),
    }

    scored = [v for v in criteria.values() if v != "N_A"]
    passes = sum(1 for v in scored if v == "PASS")
    return {
        "schema_version": SCHEMA_VERSION,
        "criteria": criteria,
        "critical_criteria": list(CRITICAL_CRITERIA),
        "denominator": len(scored),
        "passes": passes,
        "not_applicable": [k for k, v in criteria.items() if v == "N_A"],
        "detail": {
            "retrieval": retrieval,
            "structural": structural,
            "temporal": temporal,
            "mechanism_safety": mech,
            "no_design_as_implementation": no_design,
            "decision_usefulness": usefulness,
            "convergence_citations": citations,
            "artifact_hashes": artifact_hashes,
            "secrets": secrets,
            "unevidenced_supported_claims": unevidenced,
        },
    }


def final_status(vector: dict[str, Any]) -> FinalStatus:
    """Terminal status from an acceptance vector (§14).

    - FAILED on any integrity/safety criterion FAIL.
    - OPERATIONAL only if ALL critical criteria PASS (N_A never counts as pass,
      so a critical criterion that is N_A blocks OPERATIONAL → PARTIAL).
    - INSUFFICIENT_EVIDENCE when declared decisions are unsupported (a
      declaration-only model: no runtime facets and structural is otherwise sound).
    - PARTIALLY_OPERATIONAL otherwise.
    """
    criteria: dict[str, str] = vector.get("criteria", {})

    # FAILED: integrity/safety violation.
    for name in _INTEGRITY_SAFETY_CRITERIA:
        if criteria.get(name) == "FAIL":
            return "FAILED"

    # OPERATIONAL: every critical criterion is explicitly PASS.
    if all(criteria.get(name) == "PASS" for name in CRITICAL_CRITERIA):
        return "OPERATIONAL"

    # INSUFFICIENT_EVIDENCE: sound structure but declared decisions unsupported —
    # i.e. no recorded gate/test outcomes (flags N_A) and unanswered decisions.
    detail = vector.get("detail", {})
    usefulness = detail.get("decision_usefulness", {})
    if (
        criteria.get("gates_clean_flag") == "N_A" or criteria.get("targeted_tests_flag") == "N_A"
    ) and usefulness.get("answered", 0) < usefulness.get("total", 5):
        return "INSUFFICIENT_EVIDENCE"

    return "PARTIALLY_OPERATIONAL"


def agent_eval_packet(run_dir: str | Path) -> str:
    """Human-readable acceptance summary (builder may emit alongside artifacts)."""
    vector = acceptance_vector(run_dir)
    status = final_status(vector)
    lines = [
        f"# Acceptance — {Path(run_dir).name}",
        "",
        f"Final status: **{status}**",
        "",
    ]
    for k, v in sorted(vector["criteria"].items()):
        crit = " (critical)" if k in CRITICAL_CRITERIA else ""
        lines.append(f"- {k}: {v}{crit}")
    lines.append("")
    lines.append(f"Passes {vector['passes']}/{vector['denominator']} scored criteria.")
    return "\n".join(lines) + "\n"
