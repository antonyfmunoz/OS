"""Grounded Self-Model builder (DOMAIN_RECONSTRUCTION_SPEC §11-12).

Assembles a run-scoped, evidence-graded reconstruction of the UMH codebase from
three evidence layers — declared/specified (docs + compose config), implemented
(source inventory + organism world-model extraction), and runtime (probes) —
into an append-preserving claim ledger + observation/source/identity logs, then
derives divergence classes, competency answers, and convergence artifacts.

The single load-bearing invariant (§4.3): a declared/specified assertion is a
CLAIM, never an observation that the thing exists. Configuration is intent;
running is observed reality. This module NEVER promotes a declaration facet or a
`deployment_configured` config block into a runtime facet.

Build ordering is load-bearing: repository HEAD is resolved in a bounded
preflight BEFORE any repository-backed SourceRecord exists (frozen records
cannot be backfilled); every artifact acceptance evaluates (model, coverage,
divergence, convergence, report, initial manifest) is written BEFORE the
acceptance vector is computed; acceptance.json (including final_status) is
written next; the manifest is then finalized with per-artifact SHA-256 hashes.

Contract-only in v1 (declared, not silently skipped):
  - test-evidence acquisition (unit_tested/integration_tested facets, CQ5) —
    a test file referencing a module is NEVER proof of component correctness,
    and v1 does not run tests inside a build, so the tested facet is recorded
    as an explicit evidence gap;
  - ContradictionEngine integration — the engine is negation-pair lexical and
    its outputs would be candidates, never adjudicated contradictions; v1 does
    not call it and does not claim to.

Deterministic: given the same repo state + the same injected inventory/probe
results, every produced record hashes identically (record ids are content
hashes from the data layer). The builder spawns NO subprocess itself — the
inventory/probe seams own all gated process access.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from substrate.understanding.reconstruction.competency_questions import (
    COMPETENCY_QUESTIONS,
)
from substrate.understanding.reconstruction.contracts import (
    ClaimLedgerEntry,
    IdentityResolution,
    ObservationRecord,
    RUNTIME_FACETS,
    SCHEMA_VERSION,
    SourceRecord,
    ValidTime,
)
from substrate.understanding.reconstruction.identity import (
    IdentityResolutionLog,
    candidate_pair,
)
from substrate.understanding.reconstruction.ledger import ClaimLedger
from substrate.understanding.reconstruction.provenance import (
    ActivityRecord,
    RUN_ARTIFACTS,
    RunLayout,
    atomic_write_json,
    content_hash,
    file_sha256,
)

logger = logging.getLogger(__name__)

CODE_VERSION = "adl-builder-v1"

# Component-status taxonomy declared in .claude/CLAUDE.md.
_COMPONENT_STATUSES: tuple[str, ...] = (
    "CONFIRMED_RUNTIME",
    "PARTIALLY_VERIFIED",
    "UNVERIFIED",
    "PROOF_ONLY",
    "DORMANT",
    "DEPRECATED",
)
# `- <path>  — <STATUS> (<desc>)`  (em-dash U+2014; desc optional, may nest parens)
_COMPONENT_LINE_RE = re.compile(
    r"^-\s+(?P<path>\S+)\s+—\s+(?P<status>" + "|".join(_COMPONENT_STATUSES) + r")\b\s*(?P<desc>.*)$"
)
_COMPONENT_BLOCK_RE = re.compile(r"^## Component status.*?(?=^## )", re.MULTILINE | re.DOTALL)
# Canonical-ownership declaration rule: DELIBERATELY narrow — only a row whose
# description literally declares "the one canonical <thing> runtime" asserts
# ownership. "NOT the canonical ..." never matches. Ownership is an explicit
# claim_type="canonical_owner" entry, never mined from uncertainty text.
_CANONICAL_DECL_RE = re.compile(
    r"declares the one canonical\s+(?P<concern>[a-z]+)\s+runtime", re.IGNORECASE
)

# The three known same-name module pairs (§11.3) — SEED FIXTURES only, not the
# complete identity pass (deterministic mining below adds candidates).
# remain_separate ONLY where a rule documents the concerns as distinct;
# otherwise the verdict is unresolved.
_KNOWN_SAME_NAME_PAIRS: tuple[tuple[str, str, Optional[str], str], ...] = (
    (
        "substrate/organism/world_model.py",
        "substrate/understanding/world_model/world_model.py",
        ".claude/rules/ontology-layers.md",
        "organism self-model vs domain-knowledge world model — documented "
        "distinct concerns, must not be merged",
    ),
    (
        "substrate/organism/projection_port.py",
        "substrate/sockets/projection_port.py",
        ".claude/rules/projection-boundary.md",
        "organism state-broadcast port (OrganismStatePort) vs canonical "
        "projection registration port — documented different concern",
    ),
    (
        "substrate/organism/council.py",
        "substrate/understanding/deliberation/council.py",
        None,  # no documented separation evidence → unresolved
        "same module name; no rule documents these as distinct — insufficient evidence to resolve",
    ),
)

# Basenames too generic to be meaningful duplicate-identity candidates.
_MINING_BASENAME_EXCLUDES: frozenset[str] = frozenset(
    {
        "__init__.py",
        "__main__.py",
        "types.py",
        "utils.py",
        "config.py",
        "base.py",
        "models.py",
        "constants.py",
        "errors.py",
        "helpers.py",
    }
)

# The nine divergence classes (§11.4). v1 computes a subset; the rest are
# explicitly recorded as not-computable (tested facet is contract-only).
DIVERGENCE_CLASSES: tuple[str, ...] = (
    "specified_but_source_absent",
    "source_present_but_untested",
    "tested_but_not_known_deployed",
    "deployment_configured_but_not_observed_running",
    "running_but_not_declared_canonical",
    "multiple_claimed_canonical_owners",
    "feature_gated_disabled_by_default",
    "documentation_stale_vs_source",
    "status_unknown",
)
_NOT_COMPUTABLE_V1: dict[str, str] = {
    "source_present_but_untested": "tested-facet acquisition is contract-only in v1",
    "tested_but_not_known_deployed": "tested-facet acquisition is contract-only in v1",
}


@dataclass(frozen=True)
class SelfModelBuildResult:
    """Outcome of a build: identity + counts + acceptance + terminal status."""

    run_id: str
    run_dir: str
    counts: dict[str, int]
    acceptance: dict[str, Any]
    status: str


# ── injectable seam defaults (lazy — keep module import-clean before siblings land)


def _default_inventory_fn(repo_root: Path, run_id: str, activity_id: str) -> Any:
    from substrate.understanding.reconstruction.repository_inventory import (
        inventory_repository,
    )

    return inventory_repository(repo_root, run_id, activity_id)


def _default_probes_fn(run_id: str, activity_id: str, repo_root: str) -> Any:
    from substrate.understanding.reconstruction.runtime_probes import (
        collect_runtime_observations,
    )

    return collect_runtime_observations(run_id, activity_id, repo_root=repo_root)


def _default_preflight_fn(repo_root: Path) -> tuple[Optional[str], str, Optional[bool]]:
    from substrate.understanding.reconstruction.repository_inventory import (
        resolve_repository_commit,
    )

    return resolve_repository_commit(repo_root)


def _default_world_model_fn(repo_root: Path) -> Any:
    from substrate.organism.world_model import extract_world_model

    return extract_world_model(str(repo_root))


# ── internal build accumulator ──────────────────────────────────────────────


@dataclass
class _BuildState:
    run_id: str
    layout: RunLayout
    now: str
    repo_commit: Optional[str]
    repo_commit_status: str
    working_tree_dirty: Optional[bool]
    ledger: ClaimLedger
    identity_log: IdentityResolutionLog
    sources: dict[str, SourceRecord] = field(default_factory=dict)
    observations: dict[str, ObservationRecord] = field(default_factory=dict)
    activities: list[ActivityRecord] = field(default_factory=list)
    causal: list[Any] = field(default_factory=list)
    omissions: list[dict[str, Any]] = field(default_factory=list)
    thin_areas: list[str] = field(default_factory=list)

    # appenders (bound in build_self_model)
    src_app: Any = None
    obs_app: Any = None
    act_app: Any = None
    claim_app: Any = None

    def record_source(self, src: SourceRecord) -> str:
        if src.id not in self.sources:
            self.sources[src.id] = src
            self.src_app.append(src.to_dict())
        return src.id

    def record_observation(self, obs: ObservationRecord) -> str:
        if obs.id not in self.observations:
            self.observations[obs.id] = obs
            self.obs_app.append(obs.to_dict())
        return obs.id

    def record_claim(self, entry: ClaimLedgerEntry) -> ClaimLedgerEntry:
        self.ledger.append(entry)
        self.claim_app.append(entry.to_dict())
        return entry

    def record_identity(self, res: IdentityResolution) -> IdentityResolution:
        # IdentityResolutionLog validates (merge needs evidence) + appends to file.
        return self.identity_log.append(res)


class _ActivityScope:
    """Append-only activity lifecycle: the id is stable before outputs exist;
    the COMPLETED record (same id, lineage populated) is what lands in
    activities.jsonl — so the PROV chain carries real used/generated lineage.
    """

    def __init__(self, state: _BuildState, kind: str, agent_id: str) -> None:
        self._state = state
        self._proto = ActivityRecord(
            activity_kind=kind,
            agent_id=agent_id,
            run_id=state.run_id,
            code_version=CODE_VERSION,
            started_at=state.now,
        )
        self.used: list[str] = []
        self.generated: list[str] = []

    @property
    def id(self) -> str:
        return self._proto.id

    def finish(self) -> ActivityRecord:
        done = ActivityRecord(
            activity_kind=self._proto.activity_kind,
            agent_id=self._proto.agent_id,
            run_id=self._proto.run_id,
            code_version=self._proto.code_version,
            started_at=self._proto.started_at,
            ended_at=self._state.now,
            used_source_ids=tuple(sorted(set(self.used))),
            generated_record_ids=tuple(sorted(set(self.generated))),
        )
        if done.id != self._proto.id:  # lineage must never change identity
            raise RuntimeError(
                "activity id changed when lineage was added — identity_fields "
                "must exclude used/generated"
            )
        self._state.activities.append(done)
        self._state.act_app.append(done.to_dict())
        return done


# ── step 1: declared / specified evidence ───────────────────────────────────


def _parse_component_status(claude_md_text: str) -> list[dict[str, str]]:
    """Parse the `## Component status` block into per-component rows.

    Returns [{path, status, desc}]. Deterministic ordering (file order).
    """
    m = _COMPONENT_BLOCK_RE.search(claude_md_text)
    if not m:
        return []
    rows: list[dict[str, str]] = []
    for line in m.group(0).splitlines():
        lm = _COMPONENT_LINE_RE.match(line.strip())
        if lm:
            rows.append(
                {
                    "path": lm.group("path"),
                    "status": lm.group("status"),
                    "desc": lm.group("desc").strip(),
                }
            )
    return rows


def _parse_compose_services(compose_text: str) -> list[str]:
    """Extract top-level service names from a docker-compose file.

    Dependency-light: service names are the 2-space-indented keys directly under
    the top-level `services:` mapping. Avoids a hard PyYAML dependency and stays
    deterministic.
    """
    services: list[str] = []
    in_services = False
    for raw in compose_text.splitlines():
        if raw.rstrip() == "services:" or raw.rstrip() == "services :":
            in_services = True
            continue
        if not in_services:
            continue
        if raw and not raw[0].isspace():
            break  # left the services block (next top-level key)
        m = re.match(r"^  (?P<name>[A-Za-z0-9][\w.\-]*):\s*$", raw)
        if m:
            services.append(m.group("name"))
    return services


def _read_file_source(
    state: _BuildState,
    act: "_ActivityScope",
    rel_path: str,
    repo_root: Path,
    modality: str,
) -> Optional[tuple[str, str]]:
    """Acquire a repository file as ONE SourceRecord whose source_content_hash
    is the hash of the ACTUAL file bytes. Returns (source_id, text) or None."""
    fpath = repo_root / rel_path
    if not fpath.is_file():
        return None
    body = fpath.read_bytes()
    src = SourceRecord(
        subject_path=rel_path,
        source_kind="repository_file",
        modality=modality,  # type: ignore[arg-type]
        source_content_hash=content_hash(body),
        activity_id=act.id,
        run_id=state.run_id,
        repository_commit=state.repo_commit,
        repository_commit_status=state.repo_commit_status,  # type: ignore[arg-type]
        acquisition_context="declared-evidence acquisition",
        recorded_at=state.now,
        acquired_at=state.now,
    )
    sid = state.record_source(src)
    act.generated.append(sid)
    return sid, body.decode("utf-8", errors="replace")


def _step_declared(state: _BuildState, repo_root: Path) -> None:
    act = _ActivityScope(state, "extraction", "script:builder/declared")

    acquired = _read_file_source(state, act, ".claude/CLAUDE.md", repo_root, "document")
    rows: list[dict[str, str]] = []
    claude_sid = ""
    if acquired is not None:
        claude_sid, text = acquired
        act.used.append(claude_sid)
        rows = _parse_component_status(text)

    for row in rows:
        obs = ObservationRecord(
            subject=f"file:{row['path']}",
            predicate="declared_status",
            value=row["status"],
            observation_kind="maturity",
            maturity_facet="declared",
            source_id=claude_sid,
            run_id=state.run_id,
            scope="component_status",
            recorded_at=state.now,
            support={"desc": row["desc"], "extraction": "component-status block"},
        )
        oid = state.record_observation(obs)
        act.generated.append(oid)
        # A component_status declaration is a CLAIM, supported only by a
        # declaration-facet observation → status 'proposed' (§4.3: a declaration
        # can never make a claim 'supported').
        entry = state.record_claim(
            ClaimLedgerEntry(
                proposition=f"{row['path']} has declared status {row['status']}",
                claim_type="component_status",
                scope=f"file:{row['path']}",
                status="proposed",
                run_id=state.run_id,
                supporting_observation_ids=(oid,),
                valid_time=ValidTime(qualifier="unknown"),
                recorded_at=state.now,
                support_factors={"directness": 0.4, "source_authority": 0.6},
                uncertainty_reasons=("declaration-only evidence",),
            )
        )
        act.generated.append(entry.id)
        # Canonical ownership: EXPLICIT claim type, narrow declaration rule.
        cm = _CANONICAL_DECL_RE.search(row["desc"])
        if cm:
            owner_entry = state.record_claim(
                ClaimLedgerEntry(
                    proposition=(
                        f"{row['path']} is declared the canonical "
                        f"{cm.group('concern').lower()} runtime"
                    ),
                    claim_type="canonical_owner",
                    scope=f"{cm.group('concern').lower()}_runtime",
                    object_ref=row["path"],
                    status="proposed",
                    run_id=state.run_id,
                    supporting_observation_ids=(oid,),
                    recorded_at=state.now,
                    support_factors={"directness": 0.5, "source_authority": 0.6},
                    uncertainty_reasons=("declaration-only evidence",),
                )
            )
            act.generated.append(owner_entry.id)

    # docker-compose service blocks: CONFIG, never running. Subjects are
    # normalized to service:<name> so they intersect with probe observations.
    compose = _read_file_source(state, act, "docker-compose.yml", repo_root, "config")
    if compose is not None:
        compose_sid, ctext = compose
        act.used.append(compose_sid)
        for svc in _parse_compose_services(ctext):
            obs = ObservationRecord(
                subject=f"service:{svc}",
                predicate="deployment_configured",
                value=True,
                observation_kind="maturity",
                maturity_facet="deployment_configured",
                source_id=compose_sid,
                run_id=state.run_id,
                scope="docker-compose",
                recorded_at=state.now,
                support={"note": "compose block is config, not a running process"},
            )
            oid = state.record_observation(obs)
            act.generated.append(oid)
            entry = state.record_claim(
                ClaimLedgerEntry(
                    proposition=f"service {svc} is configured in docker-compose",
                    claim_type="deployment_configured",
                    scope=f"service:{svc}",
                    status="supported",  # config presence is directly observed
                    run_id=state.run_id,
                    supporting_observation_ids=(oid,),
                    recorded_at=state.now,
                    support_factors={"directness": 0.9, "runtime_verification": None},
                    uncertainty_reasons=("configured != running",),
                )
            )
            act.generated.append(entry.id)

    act.finish()


# ── step 2: implemented evidence ────────────────────────────────────────────


def _step_implemented(
    state: _BuildState, repo_root: Path, inventory_fn: Callable, world_model_fn: Callable
) -> Any:
    act = _ActivityScope(state, "acquisition", "script:builder/inventory")
    inv = inventory_fn(repo_root, state.run_id, act.id)
    for src in getattr(inv, "sources", ()):  # type: ignore[union-attr]
        sid = state.record_source(src)
        act.generated.append(sid)
    for obs in getattr(inv, "observations", ()):  # type: ignore[union-attr]
        oid = state.record_observation(obs)
        act.generated.append(oid)
        if obs.maturity_facet == "source_present" and obs.observation_kind == "maturity":
            entry = state.record_claim(
                ClaimLedgerEntry(
                    proposition=f"{obs.subject} is present in source",
                    claim_type="source_presence",
                    scope=obs.subject,
                    status="supported",
                    run_id=state.run_id,
                    supporting_observation_ids=(oid,),
                    recorded_at=state.now,
                    support_factors={"directness": 0.85},
                )
            )
            act.generated.append(entry.id)
    act.finish()

    # organism world-model extraction — entities, capabilities, gaps.
    wact = _ActivityScope(state, "extraction", "organism_world_model_extractor")
    try:
        wm = world_model_fn(repo_root)
    except Exception as exc:  # extractor unavailable → recorded omission, not fatal
        state.omissions.append({"omission": "world_model_extraction_failed", "detail": str(exc)})
        wm = None

    if wm is not None:
        entity_ids = sorted((getattr(wm, "entities", {}) or {}).keys())
        wm_payload_hash = content_hash({"entity_ids": entity_ids})
        wsrc = SourceRecord(
            subject_path="substrate/organism/world_model.py::extract_world_model",
            source_kind="derived_artifact",
            modality="derived",
            source_content_hash="",
            extraction_hash=wm_payload_hash,
            derivation_key=wm_payload_hash,
            derivation_activity_id=wact.id,
            activity_id=wact.id,
            run_id=state.run_id,
            repository_commit=state.repo_commit,
            repository_commit_status=state.repo_commit_status,  # type: ignore[arg-type]
            acquisition_context="organism world-model extraction",
            recorded_at=state.now,
            metadata={"content_recorded": False, "entity_count": len(entity_ids)},
        )
        wsid = state.record_source(wsrc)
        wact.generated.append(wsid)
        _absorb_world_model(state, wact, wm, wsid)
    wact.finish()
    return inv


def _absorb_world_model(state: _BuildState, act: "_ActivityScope", wm: Any, source_id: str) -> None:
    """Wrap world-model entities/capabilities/gaps as observations + omissions."""
    entities = getattr(wm, "entities", {}) or {}
    for eid, ent in entities.items():
        subject = getattr(ent, "module_path", "") or getattr(ent, "name", eid)
        obs = ObservationRecord(
            subject=subject,
            predicate="world_model_entity",
            value={
                "name": getattr(ent, "name", ""),
                "category": _enum_value(getattr(ent, "category", "")),
                "status": _enum_value(getattr(ent, "status", "")),
            },
            observation_kind="maturity",
            maturity_facet="source_present",
            source_id=source_id,
            run_id=state.run_id,
            scope="world_model",
            recorded_at=state.now,
        )
        act.generated.append(state.record_observation(obs))
        for cap in getattr(ent, "capabilities", []) or []:
            cobs = ObservationRecord(
                subject=getattr(cap, "provided_by", subject),
                predicate="provides_capability",
                value=getattr(cap, "name", ""),
                observation_kind="capability_extraction",
                maturity_facet="source_present",
                source_id=source_id,
                run_id=state.run_id,
                scope="capability",
                recorded_at=state.now,
            )
            oid = state.record_observation(cobs)
            act.generated.append(oid)
            entry = state.record_claim(
                ClaimLedgerEntry(
                    proposition=f"{getattr(cap, 'provided_by', subject)} provides "
                    f"capability {getattr(cap, 'name', '')}",
                    claim_type="capability_claimed",
                    scope=getattr(cap, "name", ""),
                    status="proposed",
                    run_id=state.run_id,
                    supporting_observation_ids=(oid,),
                    recorded_at=state.now,
                    support_factors={"directness": 0.5},
                )
            )
            act.generated.append(entry.id)
    # WorldGaps → recorded omissions (desired-state-without-implementation).
    for gap in getattr(wm, "gaps", []) or []:
        state.omissions.append(
            {
                "omission": getattr(gap, "description", "") or "world_gap",
                "entity_id": getattr(gap, "entity_id", ""),
                "severity": _enum_value(getattr(gap, "severity", "")),
                "source": "organism_world_model",
            }
        )


def _enum_value(v: Any) -> Any:
    return getattr(v, "value", v)


# ── step 3: runtime evidence ────────────────────────────────────────────────


def _step_runtime(state: _BuildState, repo_root: Path, probes_fn: Callable) -> Any:
    act = _ActivityScope(state, "acquisition", "script:builder/probes")
    probes = probes_fn(state.run_id, act.id, str(repo_root))
    for src in getattr(probes, "sources", ()):  # type: ignore[union-attr]
        act.generated.append(state.record_source(src))
    runtime_obs = 0
    for obs in getattr(probes, "observations", ()):  # type: ignore[union-attr]
        oid = state.record_observation(obs)
        act.generated.append(oid)
        if obs.maturity_facet in RUNTIME_FACETS:
            runtime_obs += 1
            entry = state.record_claim(
                ClaimLedgerEntry(
                    proposition=(f"{obs.subject} observed at runtime facet {obs.maturity_facet}"),
                    claim_type="runtime_observed",
                    scope=obs.subject,
                    status="supported",
                    run_id=state.run_id,
                    supporting_observation_ids=(oid,),
                    recorded_at=state.now,
                    support_factors={
                        "directness": 0.9,
                        "runtime_verification": 1.0,
                    },
                )
            )
            act.generated.append(entry.id)
    act.finish()
    # Missing/unavailable probes → thin runtime coverage, never fabricated.
    results = getattr(probes, "probe_results", ()) or ()
    unavailable = [r.get("name", "?") for r in results if not r.get("available", False)]
    if runtime_obs == 0:
        state.thin_areas.append("runtime: no runtime-facet observations collected")
    if unavailable:
        state.thin_areas.append("runtime: unavailable probes → " + ", ".join(sorted(unavailable)))
    return probes


# ── step 4: identity — deterministic mining + seed fixtures ─────────────────


def _mine_duplicate_basenames(inv: Any) -> list[tuple[str, ...]]:
    """Deterministic candidate mining: repeated non-generic .py basenames among
    inventoried substrate/ sources. Candidates only — verdicts need evidence."""
    by_basename: dict[str, list[str]] = {}
    for src in getattr(inv, "sources", ()) or ():
        path = getattr(src, "subject_path", "")
        if not path.endswith(".py") or not path.startswith("substrate/"):
            continue
        base = path.rsplit("/", 1)[-1]
        if base in _MINING_BASENAME_EXCLUDES:
            continue
        by_basename.setdefault(base, []).append(path)
    pairs: list[tuple[str, ...]] = []
    for base in sorted(by_basename):
        paths = sorted(set(by_basename[base]))
        if 2 <= len(paths) <= 4:
            for i in range(len(paths)):
                for j in range(i + 1, len(paths)):
                    pairs.append(candidate_pair(paths[i], paths[j]))
    return pairs


def _default_import_evidence_fn(
    repo_root: Path, candidate_paths: list[str], run_id: str, activity_id: str
) -> Any:
    from substrate.understanding.reconstruction.import_evidence import (
        scan_import_evidence,
    )

    return scan_import_evidence(repo_root, candidate_paths, run_id, activity_id)


def _verdict_from_evidence(
    path_a: str,
    path_b: str,
    ev_by_path: dict[str, dict[str, Any]],
    hash_by_path: dict[str, str],
) -> tuple[str, tuple[str, ...], str, dict[str, Any]]:
    """Council verdict rules over formal-dependency evidence.

    Returns (verdict, evidence_observation_ids, rationale, metadata).
    - link            — proven dependency (cross-import) or identical content
                        (coordinated duplicate copies);
    - remain_separate — both live with provably different dependency positions
                        (distinct non-identical importer sets, no cross-import,
                        different content);
    - unresolved      — everything else, evidence attached. `merge` is NEVER
                        emitted in v1.1: it requires shared-identity evidence
                        this packet does not collect. A removal CANDIDATE flag
                        (never a deletion) requires zero static references +
                        zero registry ownership + zero literal dynamic-import
                        evidence + zero doc references + zero test/tooling
                        references — and still carries explicit limitations
                        (opaque dynamic imports, runtime paths unassessed).
    """
    ea = ev_by_path.get(path_a, {})
    eb = ev_by_path.get(path_b, {})
    obs_ids = tuple(
        sorted(
            set(ea.get("observation_ids", {}).values())
            | set(eb.get("observation_ids", {}).values())
        )
    )
    imp_a = set(ea.get("static_importers", []))
    imp_b = set(eb.get("static_importers", []))
    meta: dict[str, Any] = {
        "importer_count_a": len(imp_a),
        "importer_count_b": len(imp_b),
    }

    ha, hb = hash_by_path.get(path_a, ""), hash_by_path.get(path_b, "")
    if ha and ha == hb:
        return (
            "link",
            obs_ids,
            "identical source content — coordinated duplicate copies "
            "(convergence decision needed, not asserted here)",
            meta,
        )
    cross = path_a in imp_b or path_b in imp_a
    if cross:
        return (
            "link",
            obs_ids,
            "proven formal dependency — one candidate statically imports the other",
            meta,
        )
    if imp_a and imp_b and imp_a != imp_b:
        return (
            "remain_separate",
            obs_ids,
            f"both modules are live with distinct dependency positions "
            f"({len(imp_a)} vs {len(imp_b)} static importers, no cross-import, "
            f"different content)",
            meta,
        )

    def _no_evidence(e: dict[str, Any]) -> bool:
        return (
            not e.get("static_importers")
            and not e.get("registries")
            and e.get("dynamic_import_count", 0) == 0
            and not e.get("doc_references")
            and e.get("qualified_reference_count", 0) == 0
            and e.get("test_reference_count", 0) == 0
        )

    removal_candidates = [p for p, e in ((path_a, ea), (path_b, eb)) if e and _no_evidence(e)]
    if removal_candidates:
        meta["removal_candidate"] = removal_candidates
        meta["removal_candidate_limitations"] = [
            "static/textual absence only — opaque dynamic imports exist repo-wide",
            "runtime execution paths not assessed in v1.1",
            "removal is a human decision, never performed by this subsystem",
        ]
        return (
            "unresolved",
            obs_ids,
            f"no static/registry/dynamic/doc/test references found for "
            f"{', '.join(removal_candidates)} — REMOVAL CANDIDATE (flag only; "
            f"absence is not proof, see limitations)",
            meta,
        )
    if imp_a and imp_b:
        return (
            "unresolved",
            obs_ids,
            "both imported by identical importer sets — dependency positions "
            "indistinguishable from static evidence",
            meta,
        )
    return (
        "unresolved",
        obs_ids,
        "one-sided or ambiguous dependency evidence — insufficient to resolve",
        meta,
    )


def _step_identity(
    state: _BuildState, repo_root: Path, inv: Any, import_evidence_fn: Callable
) -> Any:
    act = _ActivityScope(state, "evaluation", "script:builder/identity")
    seeded_ruled: dict[tuple[str, ...], tuple[str, str]] = {}
    seeded_unruled: dict[tuple[str, ...], str] = {}

    for path_a, path_b, evidence_rule, rationale in _KNOWN_SAME_NAME_PAIRS:
        pair = candidate_pair(path_a, path_b)
        if evidence_rule is not None:
            seeded_ruled[pair] = (evidence_rule, rationale)
        else:
            seeded_unruled[pair] = rationale

    # Candidate mining generates CANDIDATES only — verdicts come from evidence.
    mined = [
        p
        for p in _mine_duplicate_basenames(inv)
        if p not in seeded_ruled and p not in seeded_unruled
    ]
    all_pairs = list(seeded_ruled) + list(seeded_unruled) + mined
    candidate_paths = sorted({p for pair in all_pairs for p in pair})

    # Formal-dependency evidence pass (injectable seam).
    ev = import_evidence_fn(repo_root, candidate_paths, state.run_id, act.id)
    for src in getattr(ev, "sources", ()) or ():
        act.generated.append(state.record_source(src))
    for obs in getattr(ev, "observations", ()) or ():
        act.generated.append(state.record_observation(obs))
    for cr in getattr(ev, "causal_records", ()) or ():
        state.causal.append(cr)
    ev_by_path = getattr(ev, "evidence_by_path", {}) or {}

    hash_by_path: dict[str, str] = {}
    for src in getattr(inv, "sources", ()) or ():
        h = getattr(src, "source_content_hash", "")
        if h:
            hash_by_path[getattr(src, "subject_path", "")] = h

    # Rule-documented seeds: keep the documented verdict, enriched with the
    # formal-dependency observations.
    for pair, (evidence_rule, rationale) in sorted(seeded_ruled.items()):
        acquired = _read_file_source(state, act, evidence_rule, repo_root, "document")
        import_obs = tuple(
            sorted(
                oid
                for p in pair
                for oid in ev_by_path.get(p, {}).get("observation_ids", {}).values()
            )
        )
        if acquired is not None:
            eid, _ = acquired
            verdict = "remain_separate"
            evidence_ids: tuple[str, ...] = (eid,) + import_obs
        else:
            verdict = "unresolved"
            evidence_ids = import_obs
            rationale += " (documenting rule file not found at build time)"
        res = state.record_identity(
            IdentityResolution(
                candidate_entity_ids=pair,
                verdict=verdict,  # type: ignore[arg-type]
                run_id=state.run_id,
                candidate_basis="seed_fixture",
                supporting_evidence_ids=evidence_ids,
                rationale=rationale,
                recorded_at=state.now,
            )
        )
        act.generated.append(res.id)

    # Evidence-rule verdicts for the unruled seed + every mined candidate.
    for pair, basis in sorted(
        [(p, "seed_fixture") for p in seeded_unruled]
        + [(p, "mined:duplicate_basename") for p in mined]
    ):
        verdict, evidence_ids, rationale, meta = _verdict_from_evidence(
            pair[0], pair[1], ev_by_path, hash_by_path
        )
        res = state.record_identity(
            IdentityResolution(
                candidate_entity_ids=pair,
                verdict=verdict,  # type: ignore[arg-type]
                run_id=state.run_id,
                candidate_basis=basis,
                supporting_evidence_ids=evidence_ids,
                support_score=None,
                rationale=rationale
                + (
                    f" [removal_candidate: {', '.join(meta['removal_candidate'])}]"
                    if meta.get("removal_candidate")
                    else ""
                ),
                recorded_at=state.now,
            )
        )
        act.generated.append(res.id)
    act.finish()
    return ev


# ── step 5: divergence classes ──────────────────────────────────────────────


def _step_divergence(state: _BuildState) -> dict[str, Any]:
    obs = list(state.observations.values())
    subjects_by_facet: dict[str, set[str]] = {}
    for o in obs:
        if o.maturity_facet:
            subjects_by_facet.setdefault(o.maturity_facet, set()).add(o.subject)

    declared = subjects_by_facet.get("specified", set()) | subjects_by_facet.get("declared", set())
    source_present = subjects_by_facet.get("source_present", set())
    configured = subjects_by_facet.get("deployment_configured", set())
    running: set[str] = set()
    for f in RUNTIME_FACETS:
        running |= subjects_by_facet.get(f, set())

    # map (subject, facet) → representative observation id for citation
    obs_id_for: dict[tuple[str, str], str] = {}
    subjects_with_obs: set[str] = set()
    for o in obs:
        subjects_with_obs.add(o.subject)
        if o.maturity_facet:
            obs_id_for.setdefault((o.subject, o.maturity_facet), o.id)

    def cite_obs(subject: str, facets: tuple[str, ...]) -> list[str]:
        out = []
        for f in facets:
            oid = obs_id_for.get((subject, f))
            if oid:
                out.append(oid)
        return out

    # claims by scope for citing claim ids
    claims = state.ledger.entries
    claim_ids_for_scope: dict[str, list[str]] = {}
    for c in claims:
        claim_ids_for_scope.setdefault(c.scope, []).append(c.id)

    divergences: list[dict[str, Any]] = []

    def emit(
        dclass: str,
        subject: str,
        claim_ids: list[str],
        observation_ids: list[str],
        detail: str,
        required: str,
        closing_evidence: str,
    ) -> None:
        divergences.append(
            {
                "class": dclass,
                "subject": subject,
                "claim_ids": claim_ids,
                "observation_ids": observation_ids,
                "detail": detail,
                "required_change_or_investigation": required,
                "closing_evidence": closing_evidence,
            }
        )

    for s in sorted(declared - source_present):
        emit(
            "specified_but_source_absent",
            s,
            claim_ids_for_scope.get(s, []),
            cite_obs(s, ("specified", "declared")),
            "declared/specified but no source_present observation",
            f"verify whether {s} exists in source or retire the declaration",
            f"an ObservationRecord(maturity_facet='source_present') for {s}",
        )
    for s in sorted(configured - running):
        emit(
            "deployment_configured_but_not_observed_running",
            s,
            claim_ids_for_scope.get(s, []),
            cite_obs(s, ("deployment_configured",)),
            "compose-configured but no running observation",
            f"probe the runtime for {s} or record why it is intentionally down",
            f"an ObservationRecord(maturity_facet='running') for {s}",
        )
    for s in sorted(running - (declared | configured)):
        emit(
            "running_but_not_declared_canonical",
            s,
            claim_ids_for_scope.get(s, []),
            cite_obs(s, tuple(sorted(RUNTIME_FACETS))),
            "observed running but neither declared nor configured",
            f"declare {s} in component status / compose or investigate the process",
            f"a declaration source covering {s}",
        )

    # multiple_claimed_canonical_owners: EXPLICIT canonical_owner claims only.
    owners_by_concern: dict[str, list[ClaimLedgerEntry]] = {}
    for c in claims:
        if c.claim_type == "canonical_owner":
            owners_by_concern.setdefault(c.scope, []).append(c)
    for concern in sorted(owners_by_concern):
        entries = owners_by_concern[concern]
        distinct_owners = sorted({e.object_ref for e in entries})
        if len(distinct_owners) > 1:
            emit(
                "multiple_claimed_canonical_owners",
                concern,
                [e.id for e in entries],
                [],
                f"{len(distinct_owners)} distinct declared owners of {concern}: "
                + ", ".join(distinct_owners),
                f"adjudicate the single canonical owner of {concern}",
                "a superseding canonical_owner claim leaving one owner",
            )

    # feature_gated / documentation_stale — surfaced by observation support flags
    for o in obs:
        if o.support.get("feature_gated_disabled_by_default"):
            emit(
                "feature_gated_disabled_by_default",
                o.subject,
                claim_ids_for_scope.get(o.subject, []),
                [o.id],
                "feature gated off by default",
                f"decide whether {o.subject} should be enabled",
                "a runtime observation with the gate enabled",
            )
        if o.support.get("documentation_stale_vs_source"):
            emit(
                "documentation_stale_vs_source",
                o.subject,
                claim_ids_for_scope.get(o.subject, []),
                [o.id],
                "documentation diverges from observed source",
                f"update the documentation for {o.subject}",
                "a fresh declaration matching observed source",
            )

    # status_unknown — claims with zero supporting observations
    for c in claims:
        if c.scope and not c.supporting_observation_ids and c.scope not in subjects_with_obs:
            emit(
                "status_unknown",
                c.scope,
                [c.id],
                [],
                "claim exists with no supporting observation",
                f"acquire any observation for {c.scope}",
                f"at least one ObservationRecord for {c.scope}",
            )

    checks_performed = [
        {
            "check": "specified_vs_source_present",
            "status": "performed",
            "compared_subjects": len(declared),
        },
        {
            "check": "deployment_configured_vs_running",
            "status": "performed",
            "compared_subjects": len(configured),
        },
        {
            "check": "running_vs_declared",
            "status": "performed",
            "compared_subjects": len(running),
        },
        {
            "check": "canonical_owner_multiplicity",
            "status": "performed",
            "compared_subjects": len(owners_by_concern),
        },
        {
            "check": "status_unknown_sweep",
            "status": "performed",
            "compared_subjects": len(claims),
        },
    ] + [
        {"check": name, "status": f"not_computable:{reason}"}
        for name, reason in sorted(_NOT_COMPUTABLE_V1.items())
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "divergences": divergences,
        "checks_performed": checks_performed,
    }


# ── step 6: competency answers ──────────────────────────────────────────────


def _step_competency(state: _BuildState, divergence: dict[str, Any]) -> list[dict[str, Any]]:
    obs = list(state.observations.values())
    claims = state.ledger.entries
    divergences = divergence["divergences"]

    answers: dict[str, dict[str, Any]] = {}

    def ans(
        qid: str,
        items: list[dict[str, Any]],
        cited: list[str],
        *,
        unknown_reason: str = "",
        summary: Optional[dict[str, Any]] = None,
        unknown_regions: Optional[list[str]] = None,
    ) -> None:
        status = "UNKNOWN" if unknown_reason and not items else "ANSWERED"
        answers[qid] = {
            "question_id": qid,
            "answer_status": status,
            "items": items,
            "summary": summary or {"item_count": len(items)},
            "cited_record_ids": sorted(set(cited)),
            "unknown_reason": unknown_reason if status == "UNKNOWN" else "",
            "unknown_regions": unknown_regions or [],
        }

    # CQ1 — declared components (structured, with record ids)
    cq1_items = []
    for c in claims:
        if c.claim_type == "component_status":
            cq1_items.append(
                {
                    "subject": c.scope,
                    "declared_status": c.proposition.rsplit(" ", 1)[-1],
                    "claim_id": c.id,
                    "observation_ids": list(c.supporting_observation_ids),
                }
            )
    ans(
        "CQ1",
        cq1_items,
        [i["claim_id"] for i in cq1_items],
        unknown_reason="no declaration source acquired",
    )

    # CQ2 — observed running (entities with runtime facets + their obs ids)
    running_by_subject: dict[str, dict[str, Any]] = {}
    for o in obs:
        if o.maturity_facet in RUNTIME_FACETS:
            entry = running_by_subject.setdefault(
                o.subject,
                {"subject": o.subject, "facets": set(), "observation_ids": []},
            )
            entry["facets"].add(o.maturity_facet)
            entry["observation_ids"].append(o.id)
    cq2_items = [
        {
            "subject": v["subject"],
            "facets": sorted(v["facets"]),
            "observation_ids": sorted(v["observation_ids"]),
        }
        for v in sorted(running_by_subject.values(), key=lambda x: x["subject"])
    ]
    ans(
        "CQ2",
        cq2_items,
        [oid for i in cq2_items for oid in i["observation_ids"]],
        unknown_reason="no runtime probe established a runtime facet",
    )

    # CQ3 — claimed capabilities
    cq3_items = []
    for c in claims:
        if c.claim_type == "capability_claimed":
            cq3_items.append(
                {
                    "capability": c.scope,
                    "provider": c.proposition.split(" provides ")[0],
                    "claim_id": c.id,
                    "observation_ids": list(c.supporting_observation_ids),
                }
            )
    ans(
        "CQ3",
        cq3_items,
        [i["claim_id"] for i in cq3_items],
        unknown_reason="no capability source acquired",
    )

    # CQ4 — present in source: package aggregates + full per-file id list
    cq4_pkgs = []
    cq4_file_obs_ids = []
    for o in obs:
        if o.observation_kind == "aggregate_count" and o.predicate == "python_files_present":
            cq4_pkgs.append({"package": o.subject, "python_files": o.value, "observation_id": o.id})
        elif o.maturity_facet == "source_present" and o.predicate == "source_present":
            cq4_file_obs_ids.append(o.id)
    cq4_items = sorted(cq4_pkgs, key=lambda x: x["package"])
    ans(
        "CQ4",
        cq4_items,
        [i["observation_id"] for i in cq4_items] + sorted(cq4_file_obs_ids),
        unknown_reason="inventory produced no source_present observations",
        summary={
            "package_count": len(cq4_items),
            "per_file_observations": len(cq4_file_obs_ids),
        },
    )

    # CQ5 — tested: contract-only in v1, an explicit evidence gap.
    tested_items = []
    for o in obs:
        if o.maturity_facet in ("unit_tested", "integration_tested"):
            tested_items.append(
                {
                    "subject": o.subject,
                    "facet": o.maturity_facet,
                    "proves": o.value,
                    "observation_id": o.id,
                }
            )
    ans(
        "CQ5",
        tested_items,
        [i["observation_id"] for i in tested_items],
        unknown_reason=(
            "test-evidence acquisition is contract-only in v1; no "
            "unit_tested/integration_tested observations were recorded — a test "
            "file referencing a module is never proof of component correctness"
        ),
        unknown_regions=["tested_facet"],
    )

    # CQ6 — canonical ownership: EXPLICIT canonical_owner claims only.
    cq6_items = []
    for c in claims:
        if c.claim_type == "canonical_owner":
            cq6_items.append(
                {
                    "concern": c.scope,
                    "declared_owner": c.object_ref,
                    "claim_id": c.id,
                    "observation_ids": list(c.supporting_observation_ids),
                }
            )
    ans(
        "CQ6",
        cq6_items,
        [i["claim_id"] for i in cq6_items],
        unknown_reason="no source declares canonical ownership",
    )

    # CQ7 — overlap/duplication: identity resolutions (all verdicts are answers)
    cq7_items = [
        {
            "candidates": list(r.candidate_entity_ids),
            "verdict": r.verdict,
            "candidate_basis": r.candidate_basis,
            "resolution_id": r.id,
            "evidence_ids": list(r.supporting_evidence_ids),
        }
        for r in state.identity_log.entries
    ]
    ans(
        "CQ7",
        cq7_items,
        [i["resolution_id"] for i in cq7_items],
        unknown_reason="no duplicate candidates found",
    )

    # CQ8 — desired state without implementation evidence
    cq8_items = []
    for c in claims:
        if c.claim_type in ("component_status", "capability_claimed") and c.status == "proposed":
            cq8_items.append(
                {
                    "subject": c.scope,
                    "claim_type": c.claim_type,
                    "claim_id": c.id,
                }
            )
    for om in state.omissions:
        cq8_items.append(
            {
                "subject": om.get("entity_id", "") or om.get("omission", ""),
                "claim_type": "recorded_omission",
                "detail": om.get("omission", ""),
            }
        )
    ans("CQ8", cq8_items, [i["claim_id"] for i in cq8_items if "claim_id" in i])

    # CQ9 — what must change to converge (per divergence entry, with ids)
    cq9_items = [
        {
            "subject": d["subject"],
            "divergence": d["class"],
            "required_change_or_investigation": d["required_change_or_investigation"],
            "claim_ids": d["claim_ids"],
            "observation_ids": d["observation_ids"],
        }
        for d in divergences
    ]
    not_computable = [
        c["check"]
        for c in divergence["checks_performed"]
        if str(c["status"]).startswith("not_computable")
    ]
    ans(
        "CQ9",
        cq9_items,
        [cid for i in cq9_items for cid in i["claim_ids"]],
        unknown_reason="no divergence computable (no claims or observations)",
        unknown_regions=not_computable,
    )

    # CQ10 — the exact evidence that would prove convergence, per gap
    cq10_items = [
        {
            "subject": d["subject"],
            "divergence": d["class"],
            "closing_evidence": d["closing_evidence"],
            "claim_ids": d["claim_ids"],
        }
        for d in divergences
    ]
    ans(
        "CQ10",
        cq10_items,
        [cid for i in cq10_items for cid in i["claim_ids"]],
        unknown_reason="divergence set empty — nothing to converge",
        unknown_regions=not_computable,
    )

    # Ensure every one of the 10 ids present (unknown WITH gap named if missing).
    ordered: list[dict[str, Any]] = []
    for q in COMPETENCY_QUESTIONS:
        if q.id in answers:
            ordered.append(answers[q.id])
        else:
            ordered.append(
                {
                    "question_id": q.id,
                    "answer_status": "UNKNOWN",
                    "items": [],
                    "summary": {"item_count": 0},
                    "cited_record_ids": [],
                    "unknown_reason": "not derivable from current records",
                    "unknown_regions": [],
                }
            )
    return ordered


# ── build orchestration ─────────────────────────────────────────────────────


def build_self_model(
    repo_root: Path,
    output_root: Path,
    run_id: str,
    now: Optional[str] = None,
    inventory_fn: Callable = _default_inventory_fn,
    probes_fn: Callable = _default_probes_fn,
    preflight_fn: Callable = _default_preflight_fn,
    world_model_fn: Callable = _default_world_model_fn,
    import_evidence_fn: Callable = _default_import_evidence_fn,
    resume: bool = False,
) -> SelfModelBuildResult:
    """Build a run-scoped grounded self-model.

    output_root is the self-model root (canonically
    <repo>/data/world_models/self); the run lands at output_root/runs/<run_id>.

    Deterministic given the same repo state + the same inventory/probe results.
    inventory_fn/probes_fn/preflight_fn/world_model_fn are injectable (tests
    pass fakes); they default to the real seam functions.
    """
    repo_root = Path(repo_root)
    now = now or ""  # caller-supplied for determinism; empty = unknown-time seed
    layout = RunLayout(run_id, self_model_root=Path(output_root))
    layout.create(resume=resume)

    # PREFLIGHT: resolve HEAD before ANY record exists — frozen records cannot
    # be backfilled with a commit learned later.
    head, head_status, dirty = preflight_fn(repo_root)

    state = _BuildState(
        run_id=run_id,
        layout=layout,
        now=now,
        repo_commit=head,
        repo_commit_status=head_status,
        working_tree_dirty=dirty,
        ledger=ClaimLedger(appender=None),
        identity_log=IdentityResolutionLog(appender=layout.appender("identity_resolutions.jsonl")),
    )
    state.src_app = layout.appender("sources.jsonl")
    state.obs_app = layout.appender("observations.jsonl")
    state.act_app = layout.appender("activities.jsonl")
    state.claim_app = layout.appender("claims.jsonl")

    # Pipeline.
    _step_declared(state, repo_root)
    inv = _step_implemented(state, repo_root, inventory_fn, world_model_fn)
    _step_runtime(state, repo_root, probes_fn)
    _step_identity(state, repo_root, inv, import_evidence_fn)
    divergence = _step_divergence(state)
    competency = _step_competency(state, divergence)

    counts = {
        "sources": len(state.sources),
        "observations": len(state.observations),
        "claims": len(state.ledger.entries),
        "activities": len(state.activities),
        "identities": len(state.identity_log.entries),
        "divergences": len(divergence["divergences"]),
        "omissions": len(state.omissions),
    }

    # ORDERING: every artifact acceptance evaluates exists BEFORE evaluation.
    manifest = {
        "run_id": run_id,
        "repository_commit": state.repo_commit,
        "repository_commit_status": state.repo_commit_status,
        "working_tree_dirty": state.working_tree_dirty,
        "code_version": CODE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "generated_at": now,
        "counts": counts,
    }
    atomic_write_json(layout.path("manifest.json"), manifest)
    atomic_write_json(
        layout.path("model.json"), _build_model_json(state, competency, run_id, layout)
    )
    atomic_write_json(layout.path("coverage.json"), _build_coverage(state, inv))
    atomic_write_json(layout.path("divergence.json"), divergence)
    _write_convergence(layout.path("convergence.md"), state, divergence, competency)
    _write_report(layout.path("report.md"), run_id, counts)

    # Finalize manifest hashes BEFORE acceptance so the stored vector actually
    # verifies them (referential integrity, not cryptographic tamper proof).
    # acceptance.json is excluded from the hash set — it is the evaluation OF
    # the artifacts, and covering it would need a fixpoint.
    _finalize_manifest(layout)

    # Acceptance runs over the complete artifact set; final_status is stored in
    # acceptance.json itself.
    from substrate.understanding.reconstruction.evaluation import (
        acceptance_vector,
        final_status,
    )

    vector = acceptance_vector(layout.run_dir)
    status = final_status(vector)
    vector["final_status"] = status
    atomic_write_json(layout.path("acceptance.json"), vector)
    layout.update_latest_pointer()

    return SelfModelBuildResult(
        run_id=run_id,
        run_dir=str(layout.run_dir),
        counts=counts,
        acceptance=vector,
        status=status,
    )


def _finalize_manifest(layout: RunLayout) -> None:
    """Add per-artifact SHA-256 hashes + previous-run manifest chain link."""
    manifest_path = layout.path("manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes: dict[str, str] = {}
    for name in RUN_ARTIFACTS:
        # manifest can't hash itself; acceptance is the evaluation OF the
        # artifacts and is written after the hashes it verifies.
        if name in ("manifest.json", "acceptance.json"):
            continue
        p = layout.run_dir / name
        if p.is_file():
            hashes[name] = file_sha256(p)
    manifest["artifact_hashes"] = hashes

    prev_hash = None
    latest = layout.self_root / "latest.json"
    if latest.is_file():
        try:
            info = json.loads(latest.read_text(encoding="utf-8"))
            prev_manifest = Path(info.get("run_dir", "")) / "manifest.json"
            if prev_manifest.is_file() and prev_manifest != manifest_path:
                prev_hash = file_sha256(prev_manifest)
        except Exception as exc:
            logger.debug("previous-run manifest hash unavailable: %s", exc)
            prev_hash = None
    manifest["previous_run_manifest_hash"] = prev_hash
    atomic_write_json(manifest_path, manifest)


def record_run_outcomes(
    run_dir: str | Path,
    gates_clean: Optional[bool] = None,
    targeted_tests_passed: Optional[bool] = None,
) -> dict[str, Any]:
    """SUPPORTED mechanism for recording gate/test outcomes in the manifest.

    Never edit run artifacts by hand — this updates the manifest atomically,
    re-computes the acceptance vector + final status over the updated run, and
    re-finalizes the artifact hashes so integrity stays coherent.
    """
    rd = Path(run_dir)
    manifest_path = rd / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if gates_clean is not None:
        manifest["gates_clean"] = bool(gates_clean)
    if targeted_tests_passed is not None:
        manifest["targeted_tests_passed"] = bool(targeted_tests_passed)
    atomic_write_json(manifest_path, manifest)

    # Re-finalize hashes first so the recomputed acceptance verifies them.
    layout = RunLayout(rd.name, self_model_root=rd.parent.parent)
    _finalize_manifest(layout)

    from substrate.understanding.reconstruction.evaluation import (
        acceptance_vector,
        final_status,
    )

    vector = acceptance_vector(rd)
    status = final_status(vector)
    vector["final_status"] = status
    atomic_write_json(rd / "acceptance.json", vector)
    return vector


# ── artifact writers ────────────────────────────────────────────────────────


def _build_model_json(
    state: _BuildState,
    competency: list[dict[str, Any]],
    run_id: str,
    layout: RunLayout,
) -> dict[str, Any]:
    """model.json holds references/indexes/derived projections; claims.jsonl is
    the AUTHORITATIVE ledger and is referenced by artifact hash, never
    duplicated in full."""
    beliefs = [b.to_dict() for b in state.ledger.belief_state()]
    identities = [r.to_dict() for r in state.identity_log.entries]
    entities = sorted(
        {o.subject for o in state.observations.values() if o.maturity_facet == "source_present"}
    )
    claim_index: dict[str, list[str]] = {}
    status_index: dict[str, list[str]] = {}
    for c in state.ledger.entries:
        claim_index.setdefault(c.lineage_id(), []).append(c.id)
        status_index.setdefault(c.status, []).append(c.id)
    claims_path = layout.path("claims.jsonl")
    ledger_hash = file_sha256(claims_path) if claims_path.is_file() else ""
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "entities": entities,
        "claim_index": claim_index,
        "claim_status_index": {k: sorted(v) for k, v in sorted(status_index.items())},
        "ledger_artifact": {"path": "claims.jsonl", "sha256": ledger_hash},
        "beliefs": beliefs,
        "identities": identities,
        "causal": [c.to_dict() for c in state.causal],
        "competency_questions": competency,
        "omissions": state.omissions,
    }


def _build_coverage(state: _BuildState, inv: Any) -> dict[str, Any]:
    per_facet: dict[str, int] = {}
    per_kind: dict[str, int] = {}
    for o in state.observations.values():
        if o.maturity_facet:
            per_facet[o.maturity_facet] = per_facet.get(o.maturity_facet, 0) + 1
        per_kind[o.observation_kind] = per_kind.get(o.observation_kind, 0) + 1
    accounting = getattr(inv, "accounting", {}) or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "per_facet_observation_counts": per_facet,
        "per_kind_observation_counts": per_kind,
        "accounting": accounting,
        "thin_areas": state.thin_areas,
        "omissions": state.omissions,
        "contract_only_regions": sorted(_NOT_COMPUTABLE_V1),
    }


def _write_convergence(
    path: Path,
    state: _BuildState,
    divergence: dict[str, Any],
    competency: list[dict[str, Any]],
) -> None:
    """Human-readable reconstruction. Every material finding cites resolvable
    record ids inline as [claimentry:...] / [obs:...] / [identityentry:...] —
    acceptance parses and RESOLVES these tokens against the ledgers."""
    facets: dict[str, int] = {}
    for o in state.observations.values():
        if o.maturity_facet:
            facets[o.maturity_facet] = facets.get(o.maturity_facet, 0) + 1
    divergences = divergence["divergences"]
    lines: list[str] = []
    a = lines.append
    a(f"# Grounded Self-Model — run {state.run_id}")
    a("")
    a(f"- repository commit: {state.repo_commit or 'unknown'} ({state.repo_commit_status})")
    a(f"- working tree dirty: {state.working_tree_dirty}")
    a("")
    a("## Coverage summary (evidence facets)")
    for f in sorted(facets):
        a(f"- {f}: {facets[f]}")
    a("")
    a("## Component / capability inventory")
    entities = {
        o.subject for o in state.observations.values() if o.maturity_facet == "source_present"
    }
    a(f"- entities in source: {len(entities)}")
    a(f"- claim entries: {len(state.ledger.entries)}")
    a(f"- beliefs: {len(state.ledger.belief_state())}")
    a("")
    a("## Duplication / identity matrix")
    for r in state.identity_log.entries:
        a(
            f"- {list(r.candidate_entity_ids)} → **{r.verdict}** "
            f"({r.candidate_basis}) [{r.id}] — {r.rationale}"
        )
    a("")
    a("## Divergence report")
    if not divergences:
        a("- none computed within observed coverage")
    for d in divergences:
        cites = " ".join(f"[{cid}]" for cid in d["claim_ids"] + d["observation_ids"])
        a(f"- [{d['class']}] {d['subject']} — {d['detail']} {cites}")
        a(f"  - required: {d['required_change_or_investigation']}")
        a(f"  - closing evidence: {d['closing_evidence']}")
    a("")
    a("## Not-computable checks (contract-only regions)")
    for c in divergence["checks_performed"]:
        if str(c["status"]).startswith("not_computable"):
            a(f"- {c['check']}: {c['status']}")
    a("")
    a("## PROPOSED canonical ownership (PROPOSAL — not asserted fact)")
    owner_claims = [c for c in state.ledger.entries if c.claim_type == "canonical_owner"]
    if not owner_claims:
        a("- no canonical ownership declared by any acquired source")
    for c in owner_claims:
        a(
            f"- PROPOSAL: {c.scope} = {c.object_ref} [{c.id}] "
            f"(declaration-only; verify with a runtime observation before ratifying)"
        )
    a("")
    a("## Unknowns")
    for area in state.thin_areas:
        a(f"- {area}")
    for om in state.omissions:
        a(f"- omission: {om.get('omission')}")
    unknown_qs = [q for q in competency if q.get("answer_status") == "UNKNOWN"]
    for q in unknown_qs:
        a(f"- {q['question_id']} unknown: {q.get('unknown_reason', '')}")
    a("")
    a("## Convergence sequence")
    a("1. Acquire runtime observations for deployment_configured services.")
    a("2. Resolve unresolved identity candidates with documented evidence.")
    a("3. Implement the tested-facet acquisition seam (contract-only in v1).")
    a("")
    a("## Verification requirements")
    a("- Each divergence resolves only when its named closing evidence exists.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_report(path: Path, run_id: str, counts: dict[str, int]) -> None:
    lines = [
        f"# Self-model run {run_id}",
        "",
        "Status: recorded in acceptance.json (final_status)",
        "",
        "## Counts",
    ]
    for k in sorted(counts):
        lines.append(f"- {k}: {counts[k]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
