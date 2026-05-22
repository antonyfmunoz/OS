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

_CAP_ID_RE = re.compile(r"^[a-z][a-z0-9_-]+$")
_MAX_EVIDENCE_LEN = 500
_MAX_RAW_CHARS = 12000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_EXTRACTION_SYSTEM = "You are a structured data extraction engine. Return only valid JSON."

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
- capability_id: kebab-case, pattern {{adapter_type}}-{{verb}}-{{noun}}. \
Examples: google_drive-list-files, google_drive-get-file, \
google_drive-create-folder. Must match regex ^[a-z][a-z0-9_-]+$.
- action_type: UPPER_SNAKE_CASE verb. Examples: LIST_FILES, GET_FILE, \
CREATE_FOLDER.
- description: one sentence, ≤300 chars, what the capability does.
- evidence: list of verbatim quotes from the documentation (each ≤500 \
chars). These MUST be exact text spans, not paraphrases.
- gotchas: list of caveats, rate limits, auth requirements, or known issues.
- Do NOT invent capabilities not supported by evidence in the documentation.
- Do NOT filter by usefulness — extract ALL capabilities you find evidence \
for.

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


@dataclass
class CapabilityDiscoveryOrchestrator:
    """Discovers adapter capabilities by driving the TME source pipeline."""

    catalog_root: Path = Path("data/runtime/catalogs")

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
            artifact_data, raw_excerpt = self._run_research(manifest.adapter_type, vendor_url)
            if artifact_data is not None:
                capabilities, drop_log = self._extract_capabilities(
                    manifest, artifact_data, raw_excerpt
                )
                if capabilities:
                    extraction_notes.append(f"llm extracted {len(capabilities)} capabilities")
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

    def _write(self, catalog: CapabilityCatalog) -> Path:
        out_dir = self.catalog_root / catalog.adapter_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "catalog.json"
        out_path.write_text(
            json.dumps(catalog.to_dict(), indent=2),
            encoding="utf-8",
        )
        return out_path

    # ── Slice B: research + LLM extraction ──────────────────────────

    def _run_research(self, adapter_type: str, vendor_url: str) -> tuple[dict | None, str]:
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
                entries, drops = self._parse_extraction(raw_output, manifest)
                if entries is not None:
                    return entries, drops
                log.warning(
                    "[capability_discovery] LLM output failed validation (attempt %d)",
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
