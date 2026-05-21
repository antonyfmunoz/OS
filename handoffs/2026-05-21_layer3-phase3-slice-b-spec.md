# Layer 3 Phase 3 Slice B — LLM Capability Extraction

**Status:** SPEC COMPLETE — awaiting operator approval before execute  
**Branch (execute only):** `layer3-phase3-slice-b-llm-extraction`  
**Worktree (execute only):** `/opt/OS/.claude/worktrees/layer3-phase3-slice-b-llm-extraction`  
**Baseline:** 4291 tests collected, zero errors  
**Target:** 4291 + 8 unit + 1 integration = 4300 tests  

---

## 0. Locked Decisions

| ID | Decision | Detail |
|----|----------|--------|
| Q19 | Option D input | LLM consumes `ResearchArtifact.extracted_patterns` + first 12K chars of raw captures. Not raw HTML, not `fetch_plan()` output. |
| Q20 | LLM-minted `capability_id` | Regex-validated `^[a-z][a-z0-9-]+$`, kebab-case `{adapter_type}-{verb}-{noun}`. Non-determinism accepted. |
| Q21 | Hardcoded prompt | Prompt lives in orchestrator code, matching decomposer precedent. External template deferred. |
| Q22 | API-only this slice | `GoogleDriveAdapterV1` sole target. CU/GUI deferred to Slice C+. |
| Q23 | Single-shot extraction | One LLM call over consolidated content. No per-page dedup. |
| Q24 | No governance filtering | Store all extracted capabilities. Governance is runtime, not discovery. |
| Q25 | Heuristic confidence | `min(1.0, 0.1 + 0.2 * len(evidence))`. LLM self-assessment deferred. |

---

## 1. File Edit Plan

### Decision: inline vs. factored module

**Inline** — keep all extraction logic in `capability_discovery.py`.

Justification: the decomposer precedent (`understanding/perception/orchestrator.py`) keeps the prompt template, LLM call, and parser in the same file (lines 437–652, ~215 lines). This codebase treats the orchestrator as the single-file owner of its extraction logic. A second module adds import wiring and a public interface contract for a single internal caller. The extraction adds ~180 lines — well within single-file comfort for this codebase. Factor only if Slice C/D adds a second extraction pathway.

### Files edited

| File | Change | Risk |
|------|--------|------|
| `adapters/adapter_engine/capability_discovery.py` | Extend orchestrator: add prompt template, 7 private methods, modify `discover()` | LOW (new methods, one existing method extended) |
| `adapters/adapter_engine/capability_catalog.py` | No changes needed — Slice A fields are sufficient for population | N/A |
| `tests/test_capability_extraction_slice_b.py` | New file: 8 unit + 1 integration test | LOW |
| `tests/fixtures/capability_discovery/googledrive/artifact.json` | New: cached ResearchArtifact fixture | LOW |
| `tests/fixtures/capability_discovery/googledrive/raw_excerpt.txt` | New: representative raw capture slice | LOW |

### Detailed diffs

#### `adapters/adapter_engine/capability_discovery.py`

**OLD (lines 1–22, current imports + docstring):**
```python
"""Capability discovery orchestrator for the UMH substrate layer.

Drives the TME source discovery pipeline with adapter-focused output.
The orchestrator resolves adapter_id -> manifest -> vendor_docs_url and
passes it through TME's existing official_url parameter. No TME code is
modified — the existing API already handles the adapter case.

Layer 3 Unified Architecture §3.
UMH substrate subsystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from adapters.adapter_engine.adapter_manifest import AdapterManifest
from adapters.adapter_engine.capability_catalog import CapabilityCatalog
from composition.mastery.research.source_discovery import discover_sources
```

**NEW (lines 1–30, updated imports + module-level constants):**
```python
"""Capability discovery orchestrator for the UMH substrate layer.

Drives the TME source discovery pipeline and LLM capability extraction.
Slice A: empty catalogs from source discovery.
Slice B: populated catalogs via LLM extraction over TME research artifacts.

Layer 3 Unified Architecture §3.
UMH substrate subsystem.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from adapters.adapter_engine.adapter_manifest import AdapterManifest
from adapters.adapter_engine.capability_catalog import (
    CapabilityCatalog,
    CatalogEntry,
)
from adapters.adapter_engine.modality import ModalityType
from composition.mastery.research.source_discovery import discover_sources

_CAP_ID_RE = re.compile(r"^[a-z][a-z0-9-]+$")
_MAX_EVIDENCE_LEN = 500
_MAX_RAW_CHARS = 12000
```

---

**ADD after `_now_iso()` function (current line 25), before the class definition (current line 28):**

```python
_EXTRACTION_SYSTEM = (
    "You are a structured data extraction engine. Return only valid JSON."
)

_EXTRACTION_PROMPT = """\
Extract API capabilities from the documentation below for an adapter.

ADAPTER CONTEXT:
- adapter_id: {adapter_id}
- adapter_type: {adapter_type}
- vendor_docs_url: {vendor_docs_url}

PRE-EXTRACTED PATTERNS (high-confidence signals from documentation):
{patterns_block}

RAW DOCUMENTATION EXCERPT:
---
{raw_excerpt}
---

RULES:
- Extract every distinct API capability you can identify.
- capability_id: kebab-case, pattern {{adapter_type}}-{{verb}}-{{noun}}. Examples: google_drive-list-files, google_drive-get-file, google_drive-create-folder. Must match regex ^[a-z][a-z0-9_-]+$.
- action_type: UPPER_SNAKE_CASE verb. Examples: LIST_FILES, GET_FILE, CREATE_FOLDER.
- description: one sentence, ≤300 chars, what the capability does.
- evidence: list of verbatim quotes from the documentation (each ≤500 chars). These MUST be exact text spans, not paraphrases.
- gotchas: list of caveats, rate limits, auth requirements, or known issues.
- Do NOT invent capabilities not supported by evidence in the documentation.
- Do NOT filter by usefulness — extract ALL capabilities you find evidence for.

Return ONLY valid JSON matching this schema:
{{
  "capabilities": [
    {{
      "capability_id": "<kebab-case-id>",
      "action_type": "<UPPER_SNAKE>",
      "description": "<what it does, ≤300 chars>",
      "evidence": ["<verbatim quote 1>", "<verbatim quote 2>"],
      "gotchas": ["<caveat 1>"]
    }}
  ]
}}
"""
```

---

**OLD `discover()` method (lines 34–70):**
```python
    def discover(self, manifest: AdapterManifest) -> CapabilityCatalog:
        """Run capability discovery for a single adapter.

        Slice A: resolves vendor docs, calls source_discovery, writes
        empty catalog. Slice B adds LLM extraction to populate capabilities.
        """
        vendor_url = manifest.vendor_docs_url
        if not vendor_url:
            catalog = CapabilityCatalog(
                adapter_id=manifest.adapter_id,
                adapter_type=manifest.adapter_type,
                source_plan_notes=[
                    "no vendor_docs_url on manifest; discovery skipped",
                ],
                discovery_timestamp=_now_iso(),
            )
            self._write(catalog)
            return catalog

        plan = discover_sources(
            tool_slug=manifest.adapter_type,
            official_url=vendor_url,
        )

        catalog = CapabilityCatalog(
            adapter_id=manifest.adapter_id,
            adapter_type=manifest.adapter_type,
            vendor_docs_url=vendor_url,
            capabilities=[],
            gotchas=[],
            source_plan_notes=list(plan.notes),
            discovery_timestamp=_now_iso(),
            discovery_version="slice-a",
        )

        self._write(catalog)
        return catalog
```

**NEW `discover()` method (replaces lines 34–70):**
```python
    def discover(self, manifest: AdapterManifest) -> CapabilityCatalog:
        """Run capability discovery for a single adapter.

        Flow: discover_sources -> research agent -> LLM extraction -> catalog.
        Any failure in research or extraction -> empty capabilities, valid
        catalog still written.
        """
        log = logging.getLogger(__name__)
        vendor_url = manifest.vendor_docs_url

        if not vendor_url:
            catalog = CapabilityCatalog(
                adapter_id=manifest.adapter_id,
                adapter_type=manifest.adapter_type,
                source_plan_notes=[
                    "no vendor_docs_url on manifest; discovery skipped",
                ],
                discovery_timestamp=_now_iso(),
            )
            self._write(catalog)
            return catalog

        plan = discover_sources(
            tool_slug=manifest.adapter_type,
            official_url=vendor_url,
        )

        capabilities: list[CatalogEntry] = []
        extraction_notes: list[str] = []
        drop_log: list[str] = []

        try:
            artifact_data, raw_excerpt = self._run_research(
                manifest.adapter_type, vendor_url
            )
            if artifact_data is not None:
                capabilities, drop_log = self._extract_capabilities(
                    manifest, artifact_data, raw_excerpt
                )
                if capabilities:
                    extraction_notes.append(
                        f"llm extracted {len(capabilities)} capabilities"
                    )
                else:
                    extraction_notes.append("llm returned no valid capabilities")
            else:
                extraction_notes.append("research agent returned no artifact")
        except Exception as exc:
            log.warning(
                "[capability_discovery] extraction failed for %s: %s",
                manifest.adapter_id,
                exc,
            )
            extraction_notes.append(f"extraction error: {type(exc).__name__}")

        catalog = CapabilityCatalog(
            adapter_id=manifest.adapter_id,
            adapter_type=manifest.adapter_type,
            vendor_docs_url=vendor_url,
            capabilities=capabilities,
            gotchas=[],
            source_plan_notes=list(plan.notes) + extraction_notes + drop_log,
            discovery_timestamp=_now_iso(),
            discovery_version="slice-b",
        )

        self._write(catalog)
        return catalog
```

---

**ADD — 7 private methods after existing `_write()` method (after current line 81):**

```python
    # ── Slice B: research + LLM extraction ──────────────────────────

    def _run_research(
        self, adapter_type: str, vendor_url: str
    ) -> tuple[dict | None, str]:
        """Run TME research agent. Returns (artifact_data, raw_excerpt)."""
        from composition.mastery.research.agent import run as research_run
        from composition.mastery.research.models import (
            ResearchMode,
            ResearchRequest,
            ResearchStatus,
        )

        request = ResearchRequest(
            tool_slug=adapter_type,
            mode=ResearchMode.RESEARCH,
            official_url=vendor_url,
        )
        result = research_run(request)

        if result.status is ResearchStatus.NO_SOURCES:
            return None, ""

        if not result.artifact_path:
            return None, ""

        artifact_path = Path(result.artifact_path)
        if not artifact_path.exists():
            return None, ""

        artifact_data = json.loads(artifact_path.read_text(encoding="utf-8"))

        raw_excerpt = self._load_raw_excerpt(Path(result.run_dir))
        return artifact_data, raw_excerpt

    def _load_raw_excerpt(self, run_dir: Path) -> str:
        """Load first N chars from raw captures under run_dir/raw/."""
        raw_dir = run_dir / "raw"
        if not raw_dir.exists():
            return ""
        parts: list[str] = []
        total = 0
        for f in sorted(raw_dir.iterdir()):
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            remaining = _MAX_RAW_CHARS - total
            if remaining <= 0:
                break
            parts.append(text[:remaining])
            total += len(parts[-1])
        return "\n---\n".join(parts)

    def _render_patterns(self, artifact_data: dict) -> str:
        """Render extracted_patterns from artifact as structured text block."""
        patterns = artifact_data.get("extracted_patterns", {})
        lines: list[str] = []
        for kind in ("usage", "api", "workflows"):
            items = patterns.get(kind, [])
            if not items:
                continue
            lines.append(f"[{kind.upper()}]")
            for p in items[:20]:
                excerpt = str(p.get("excerpt", ""))[:300]
                lines.append(f"  - {excerpt}")
        return "\n".join(lines) if lines else "(no pre-extracted patterns)"

    def _extract_capabilities(
        self,
        manifest: AdapterManifest,
        artifact_data: dict,
        raw_excerpt: str,
    ) -> tuple[list[CatalogEntry], list[str]]:
        """LLM extraction -> validated CatalogEntry list + drop log."""
        log = logging.getLogger(__name__)

        patterns_block = self._render_patterns(artifact_data)
        prompt = _EXTRACTION_PROMPT.format(
            adapter_id=manifest.adapter_id,
            adapter_type=manifest.adapter_type,
            vendor_docs_url=manifest.vendor_docs_url or "",
            patterns_block=patterns_block,
            raw_excerpt=raw_excerpt[:_MAX_RAW_CHARS],
        )

        for attempt in range(2):
            try:
                from execution.runtime.model_router import (
                    TaskType,
                    call_with_fallback,
                )

                result = call_with_fallback(
                    prompt=prompt,
                    system=_EXTRACTION_SYSTEM,
                    task_type=TaskType.ANALYSIS,
                )
                raw_output = result.output.strip()
                entries, drops = self._parse_extraction(
                    raw_output, manifest
                )
                if entries is not None:
                    return entries, drops
                log.warning(
                    "[capability_discovery] LLM output failed validation "
                    "(attempt %d)",
                    attempt + 1,
                )
            except Exception as exc:
                log.warning(
                    "[capability_discovery] LLM call failed (attempt %d): %s",
                    attempt + 1,
                    exc,
                )

        return [], ["drop: all extraction attempts failed"]

    def _parse_extraction(
        self, raw_output: str, manifest: AdapterManifest
    ) -> tuple[list[CatalogEntry] | None, list[str]]:
        """Parse LLM JSON -> CatalogEntry list. Returns None on structural failure."""
        text = raw_output
        if "```" in text:
            start = text.find("```")
            first_nl = text.find("\n", start)
            end = text.find("```", first_nl)
            if first_nl != -1 and end != -1:
                text = text[first_nl + 1 : end]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None, ["drop: json parse failed"]

        if not isinstance(data, dict) or "capabilities" not in data:
            return None, ["drop: missing capabilities key"]

        raw_caps = data["capabilities"]
        if not isinstance(raw_caps, list):
            return None, ["drop: capabilities is not a list"]

        entries: list[CatalogEntry] = []
        drops: list[str] = []

        for item in raw_caps:
            entry, reason = self._validate_entry(item, manifest)
            if entry is not None:
                entries.append(entry)
            else:
                drops.append(f"drop: {reason}")

        return entries, drops

    def _validate_entry(
        self, item: dict, manifest: AdapterManifest
    ) -> tuple[CatalogEntry | None, str]:
        """Validate + build a single CatalogEntry from LLM output."""
        cap_id = str(item.get("capability_id", "")).strip()
        if not cap_id or not _CAP_ID_RE.match(cap_id):
            return None, f"invalid capability_id: {cap_id!r}"

        action_type = str(item.get("action_type", "")).strip()
        if not action_type:
            return None, f"empty action_type for {cap_id}"

        description = str(item.get("description", ""))[:300].strip()

        raw_evidence = item.get("evidence", [])
        if not isinstance(raw_evidence, list):
            raw_evidence = []
        evidence = [str(e)[:_MAX_EVIDENCE_LEN] for e in raw_evidence]

        raw_gotchas = item.get("gotchas", [])
        if not isinstance(raw_gotchas, list):
            raw_gotchas = []
        gotchas = [str(g) for g in raw_gotchas]

        confidence = min(1.0, 0.1 + 0.2 * len(evidence))

        requires_auth = self._infer_requires_auth(manifest)
        requires_gui = self._infer_requires_gui(manifest)

        source_urls: list[str] = []
        artifact_sources = item.get("source_urls", [])
        if isinstance(artifact_sources, list):
            source_urls = [str(u) for u in artifact_sources]

        return CatalogEntry(
            capability_id=cap_id,
            action_type=action_type,
            description=description,
            evidence=evidence,
            source_urls=source_urls,
            confidence=confidence,
            gotchas=gotchas,
            requires_auth=requires_auth,
            requires_gui=requires_gui,
        ), ""

    @staticmethod
    def _infer_requires_auth(manifest: AdapterManifest) -> bool | None:
        """Heuristic: EXTERNAL adapters require auth; ECOSYSTEM do not."""
        if manifest.participant_type.value == "external":
            return True
        return None

    @staticmethod
    def _infer_requires_gui(manifest: AdapterManifest) -> bool | None:
        """Heuristic: API-only -> False, COMPUTER_USE -> True, else None."""
        modalities = {m.value for m in manifest.modalities}
        if modalities == {"api"}:
            return False
        if "computer_use" in modalities:
            return True
        return None
```

---

## 2. LLM Extraction Design

### Module location
All extraction logic: private methods on `CapabilityDiscoveryOrchestrator` in `adapters/adapter_engine/capability_discovery.py`.

### Public interface
No new public interface. Existing `discover(manifest: AdapterManifest) -> CapabilityCatalog` is the only entry point. Callers see the same signature; return value now has populated `capabilities`.

### System message
```
"You are a structured data extraction engine. Return only valid JSON."
```
Exact match with `understanding/perception/orchestrator.py:547`.

### User prompt template
See `_EXTRACTION_PROMPT` in Section 1 diff. Key design choices:

| Element | Design |
|---------|--------|
| Literal JSON braces | `{{` / `}}` matching decomposer convention |
| Adapter metadata block | Grounds the LLM with `adapter_id`, `adapter_type`, `vendor_docs_url` |
| Pre-extracted patterns | TME's regex-validated signals (Option D — standing on shoulders) |
| Raw excerpt | Capped at 12K chars matching `orchestrator.py:531` |
| Output schema | Explicit JSON matching CatalogEntry fields |
| capability_id instruction | Kebab-case + regex constraint + examples |
| Evidence instruction | "MUST be exact text spans, not paraphrases" + ≤500 char note |
| No-governance instructions | "Do NOT filter by usefulness" (Q24) |

### Output parsing
1. Markdown fence strip — same algorithm as `orchestrator.py:569-575`
2. `json.loads()` — structural validation (`capabilities` key exists, is list)
3. Per-entry validation via `_validate_entry()`:
   - `capability_id` must match `^[a-z][a-z0-9-]+$` — drop if invalid
   - `action_type` must be non-empty — drop if empty
   - `description` truncated to 300 chars
   - `evidence` entries each truncated to 500 chars
   - `gotchas` accepted as-is (list of strings)
   - Confidence computed via heuristic formula, NOT from LLM output
4. Structural failure (bad JSON, missing key) → returns `(None, drops)` → triggers retry
5. Per-entry failure → that entry dropped with reason, other entries kept
6. Both retry attempts fail → returns `([], ["drop: all extraction attempts failed"])`

### LLM call pattern
```python
from execution.runtime.model_router import TaskType, call_with_fallback

result = call_with_fallback(
    prompt=prompt,
    system=_EXTRACTION_SYSTEM,
    task_type=TaskType.ANALYSIS,
)
```
- `TaskType.ANALYSIS` → Opus (cc_sdk) first, Gemini Flash fallback
- 2-attempt retry loop matching decomposer (`orchestrator.py:541`)
- Lazy import inside loop body matching decomposer pattern (`orchestrator.py:543`)
- Returns `RoutingResult` with `.output: str`, `.provider: str`, `.model: str`

---

## 3. Orchestrator Flow Extension

### Before (Slice A)
```
discover(manifest)
  └─ vendor_url missing? → skip catalog → _write → return
  └─ discover_sources(adapter_type, vendor_url) → SourcePlan
  └─ CapabilityCatalog(capabilities=[]) → _write → return
```

### After (Slice B)
```
discover(manifest)
  └─ vendor_url missing? → skip catalog → _write → return  [unchanged]
  └─ discover_sources(adapter_type, vendor_url) → SourcePlan
  └─ _run_research(adapter_type, vendor_url)
  │    └─ research.agent.run(ResearchRequest) → ResearchResult
  │    └─ load artifact JSON from result.artifact_path
  │    └─ _load_raw_excerpt(run_dir) → first 12K chars from raw/
  │    └─ return (artifact_data, raw_excerpt)
  └─ _extract_capabilities(manifest, artifact_data, raw_excerpt)
  │    └─ _render_patterns(artifact_data) → structured text block
  │    └─ _EXTRACTION_PROMPT.format(...) → full prompt
  │    └─ call_with_fallback(prompt, system, TaskType.ANALYSIS) [×2 retry]
  │    └─ _parse_extraction(raw_output, manifest)
  │    │    └─ fence strip → json.loads → structural checks
  │    │    └─ per item: _validate_entry(item, manifest) → CatalogEntry | drop
  │    └─ return (list[CatalogEntry], list[str] drop_log)
  └─ CapabilityCatalog(capabilities=entries, discovery_version="slice-b")
  └─ _write(catalog) → return
```

### Error containment matrix

| Failure point | Behavior | Catalog written? |
|---------------|----------|------------------|
| `_run_research()` raises any Exception | Caught in `discover()`, extraction_notes records error type | Yes, capabilities=[] |
| `research.agent.run()` returns `NO_SOURCES` | `_run_research` returns `(None, "")`, extraction skipped | Yes, capabilities=[] |
| `result.artifact_path` missing or doesn't exist | `_run_research` returns `(None, "")` | Yes, capabilities=[] |
| `call_with_fallback` raises Exception (both attempts) | Caught in retry loop, returns `([], [drop_msg])` | Yes, capabilities=[] |
| LLM returns invalid JSON (both attempts) | `_parse_extraction` returns `(None, drops)`, retry exhausted | Yes, capabilities=[] |
| Individual entry fails `_validate_entry` | Entry dropped, others kept, drop reason logged | Yes, with remaining entries |
| All entries fail validation | Returns `([], drops)` | Yes, capabilities=[] |

**Every path converges on `self._write(catalog)` — a valid catalog is always written.**

### HARD CONSTRAINT: TME zero-touch
Zero files under `composition/mastery/` are edited. The orchestrator imports `discover_sources` and `research.agent.run` as read-only consumers. TME's honesty boundary (no LLM in TME) is preserved.

Verification command: `git diff --stat composition/mastery/` must show zero files at merge time.

---

## 4. CatalogEntry Field Population Strategy

| Field | Source | Rule | Example |
|-------|--------|------|---------|
| `capability_id` | LLM-minted | Regex `^[a-z][a-z0-9-]+$`. Drop entry if invalid. | `google_drive-list-files` |
| `action_type` | LLM-extracted | Non-empty string. Drop entry if empty. | `LIST_FILES` |
| `description` | LLM-extracted | Truncated to ≤300 chars. | `"List files and folders in a Drive directory"` |
| `evidence` | LLM-extracted | List of verbatim quotes. Each truncated to ≤500 chars. | `["Use the files.list method to..."]` |
| `source_urls` | LLM pass-through | If LLM includes `source_urls` in output, pass through. Otherwise empty list. LLM is not explicitly instructed to produce these. | `[]` |
| `confidence` | Heuristic | `min(1.0, 0.1 + 0.2 * len(evidence))` | 0 ev→0.1, 1→0.3, 2→0.5, 3→0.7, 4→0.9, 5+→1.0 |
| `gotchas` | LLM-extracted | List of strings, accepted as-is. | `["Rate limited to 1000 queries per 100 seconds"]` |
| `requires_auth` | Manifest heuristic | `True` if `manifest.participant_type == "external"`, else `None`. All external adapters require some form of auth. | `True` (Google Drive) |
| `requires_gui` | Manifest heuristic | `False` if modalities is exactly `{"api"}`. `True` if `"computer_use"` in modalities. `None` otherwise. | `False` (Google Drive) |

---

## 5. Test Scope

**Test file:** `tests/test_capability_extraction_slice_b.py`  
**Baseline:** 4291  
**Target:** 4291 + 8 unit + 1 integration = 4300

### Unit tests (8)

**1. `test_valid_json_parse`**  
Feed well-formed JSON with 2 capabilities through `_parse_extraction()`. Assert 2 `CatalogEntry` objects returned with correct fields.

**2. `test_invalid_capability_id_rejected`**  
Feed JSON with one valid entry (`google_drive-list-files`) and one invalid (`has spaces`). Assert valid kept, invalid dropped, drop log contains reason.

**3. `test_evidence_truncation`**  
Feed entry with a 600-char evidence string. Assert stored evidence is exactly 500 chars.

**4. `test_empty_artifact_handling`**  
Call `_extract_capabilities()` with empty `extracted_patterns` and empty raw excerpt. Mock `call_with_fallback` to return valid JSON. Assert patterns block renders as `"(no pre-extracted patterns)"` and capabilities are populated from mock.

**5. `test_llm_failure_returns_empty`**  
Mock `call_with_fallback` to raise `Exception`. Assert `_extract_capabilities()` returns `([], ["drop: all extraction attempts failed"])`.

**6. `test_full_orchestrator_mocked`**  
Mock both `composition.mastery.research.agent.run` (return fake ResearchResult with artifact path pointing to tmp_path fixture) and `call_with_fallback` (return valid JSON). Assert `discover()` returns `CapabilityCatalog` with populated capabilities, `discovery_version == "slice-b"`, catalog JSON written to disk at `catalog_root/adapter_id/catalog.json`.

**7. `test_research_agent_failure`**  
Mock `_run_research` to raise `RuntimeError`. Assert `discover()` returns valid catalog with empty capabilities. Assert `source_plan_notes` contains `"extraction error: RuntimeError"`.

**8. `test_confidence_formula`**  
Create entries with 0, 1, 3, 5, 10 evidence items via `_validate_entry()`. Assert confidence values: 0.1, 0.3, 0.7, 1.0, 1.0.

### Integration test (1)

**9. `test_integration_google_drive_extraction`**  
- Load cached fixture from `tests/fixtures/capability_discovery/googledrive/`
- Mock `_run_research` to return fixture data (skip real network for research stage)
- Call real `call_with_fallback` (real LLM call)
- Assert:
  - At least 3 capabilities extracted
  - All `capability_id` values match `^[a-z][a-z0-9-]+$`
  - At least one `action_type` contains `LIST` or `GET` or `CREATE`
  - All confidence values are `> 0.0` and `<= 1.0`
  - All evidence lists are non-empty
- Marked with `@pytest.mark.integration` for optional skip in fast suite

---

## 6. Cached Fixture Policy

### Paths
```
tests/fixtures/capability_discovery/googledrive/artifact.json
tests/fixtures/capability_discovery/googledrive/raw_excerpt.txt
```

### Generation
During execute phase first-run protocol (Section 7):
1. Run `research.agent.run()` against GoogleDriveAdapterV1 (real network)
2. Load artifact JSON from `result.artifact_path`
3. Load raw captures from `result.run_dir/raw/` (first ~8K chars)
4. Save to fixture paths

### Sanitization checklist
- [ ] Google Drive API docs are public — no PII expected, but verify
- [ ] Scan for: API keys, OAuth tokens, session cookies, email addresses, user-specific file IDs
- [ ] Replace `fetched_at` timestamps with `"2026-01-01T00:00:00+00:00"`
- [ ] Replace `run_dir` absolute paths with placeholder `"/tmp/research_fixture"`
- [ ] Replace any `generated_at` with `"2026-01-01T00:00:00+00:00"`
- [ ] Verify fixture is self-contained: `json.loads()` succeeds without filesystem context
- [ ] Raw excerpt truncated to ~8K chars (not full captures)

### Fixture loading pattern (used by integration test)
```python
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "capability_discovery" / "googledrive"

def _load_fixture() -> tuple[dict, str]:
    artifact = json.loads((FIXTURE_DIR / "artifact.json").read_text(encoding="utf-8"))
    raw = (FIXTURE_DIR / "raw_excerpt.txt").read_text(encoding="utf-8")
    return artifact, raw
```

---

## 7. First-Run Protocol (CRITICAL — CC Pause Point)

This is a wet operation with real network calls and real LLM inference.

### Execution sequence

```
1. Implement all methods in capability_discovery.py
2. Write all 8 unit tests, run them, confirm pass
3. ── WET OPERATION ──────────────────────────────────────
   Run research.agent.run() against GoogleDriveAdapterV1.MANIFEST
   (real network: fetches Google Drive docs)
   (real LLM: call_with_fallback with TaskType.ANALYSIS)
4. ── CC HARD STOP ───────────────────────────────────────
   Print to operator:
     a. Raw LLM output (full JSON string)
     b. Parsed CatalogEntry list (capability_id, action_type, confidence)
     c. Drop log (any rejected entries with reasons)
     d. Provider used (Opus/Gemini)
5. Wait for operator decision:
     APPROVE → sanitize output, commit fixture, write integration test
     REFINE  → iterate prompt, re-run from step 3
6. Do NOT commit fixture before operator approval
   ──────────────────────────────────────────────────────
```

### Why this pause exists
- LLM output quality determines whether the prompt design is sound
- First real extraction reveals calibration issues invisible in mocked unit tests
- Fixture committed without review could enshrine bad extraction patterns
- Operator may want to adjust prompt framing based on actual Google Drive API structure

---

## 8. Verification Gate (post-execute, pre-merge)

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | py_compile | `python3 -m py_compile adapters/adapter_engine/capability_discovery.py` | exit 0 |
| 2 | ruff format | `ruff format --check adapters/adapter_engine/capability_discovery.py tests/test_capability_extraction_slice_b.py` | 0 reformatted |
| 3 | Unit tests | `python3 -m pytest tests/test_capability_extraction_slice_b.py -k 'not integration' -v` | 8/8 pass |
| 4 | Integration | `python3 -m pytest tests/test_capability_extraction_slice_b.py -k integration -v` | 1/1 pass (or operator skip) |
| 5 | Collection | `python3 -m pytest --collect-only -q 2>/dev/null \| tail -1` | 4300 tests collected |
| 6 | Full suite | `python3 -m pytest -x -q` | 0 errors, 0 failures |
| 7 | Sovereignty | `scripts/sovereignty-grep.sh` | 20 DATA hits, no system-text additions |
| 8 | TME zero-touch | `git diff --stat composition/mastery/` | 0 files changed |
| 9 | First extraction | Reviewed in CC output during first-run protocol | Operator-approved |

---

## 9. Branch / Worktree (execute phase only)

**Do NOT create during spec phase.**

| Item | Value |
|------|-------|
| Branch | `layer3-phase3-slice-b-llm-extraction` |
| Base | HEAD of `layer3-phase3-slice-a-capability-catalog` |
| Worktree | `/opt/OS/.claude/worktrees/layer3-phase3-slice-b-llm-extraction` |

---

## 10. Risks

### Token budget
Option D pre-condenses via TME regex — the LLM sees `extracted_patterns` (structured, compact list) + raw excerpt capped at 12K chars. Worst case for Google Drive: ~15K tokens input. Well within Opus (200K) and Gemini Flash (1M) context windows. The 12K raw cap is the safety valve for future adapters with massive docs.

### Determinism
`capability_id` and `description` will vary across LLM runs. Unit tests use mocked LLM output for full determinism. Integration test asserts structural properties (regex match, non-empty, sensible action types) not exact strings. Snapshot tests are explicitly avoided.

### TME integrity
Zero-touch contract is load-bearing. Verified by `git diff --stat composition/mastery/` in gate #8. The orchestrator is a consumer of TME APIs (`discover_sources`, `research.agent.run`), never a modifier. This boundary is the architectural reason extraction lives in `adapters/adapter_engine/`, not `composition/mastery/`.

### Research agent side effects
`research.agent.run()` writes to `data/runtime/research_log/` and queues a Control Plane author action via `_queue_author_action()`. During first-run protocol these side effects are expected and harmless: research logs are append-only, author action fails gracefully if CP is unavailable. No cleanup needed.

### Model routing fallback
If cc_sdk (Opus) is unavailable, `call_with_fallback` falls through to Gemini Flash. Extraction quality may differ. The validation pipeline (regex check, truncation, per-field validation) is model-agnostic — it catches bad output regardless of provider. Integration test should pass on either.

---

## 11. Open Questions

None. All design decisions locked (Q19–Q25). The first-run protocol (Section 7) is the remaining decision gate, and it is explicitly operator-controlled.

---

## 12. STOP

Spec written to `/opt/OS/handoffs/2026-05-21_layer3-phase3-slice-b-spec.md`.  
Awaiting operator review before execute phase.
