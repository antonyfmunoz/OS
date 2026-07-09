"""
GWSDocumentScanner — reads Google Docs the founder owns,
extracts business context, and ingests it into EOS knowledge layers.

The assistant knows everything written about the businesses.

Features:
  - AI-based document understanding (not just keyword filtering)
  - Deduplication — skips unchanged docs on incremental runs
  - Chunked ingestion — large docs split into 3000-char chunks
  - Venture routing — maps each doc to the right company

Usage:
    from substrate.state.context.context import load_context_from_env
    from adapters.google_workspace.gws_scanner import GWSDocumentScanner

    ctx = load_context_from_env()
    scanner = GWSDocumentScanner(ctx)
    docs = scanner.scan_all(limit=200, incremental=False)
    scanner.ingest_to_eos(docs)
    scanner.save_context_summary(docs)
"""

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from substrate.execution.cpu_gate import gated_subprocess_run, gated_popen
from datetime import datetime
from pathlib import Path

from substrate.state.context.context import EntrepreneurOSContext
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



@dataclass
class GWSDocument:
    id: str
    name: str
    content: str
    doc_type: str       # 'doc', 'sheet', 'slide'
    modified: str
    url: str
    relevance: str      # 'high', 'medium', 'low'
    venture_id: str     # which company it relates to
    summary: str = ''
    key_context: str = ''
    tags: list[str] = field(default_factory=list)


class GWSDocumentScanner:
    """
    Scans all Google Docs owned by the founder.
    Uses AI to understand every document. Deduplicates against Neon.
    Ingests with chunking. Saves context summary for cognitive loop.
    """

    def __init__(self, ctx: EntrepreneurOSContext):
        self.ctx = ctx
        self._scan_skipped = 0  # set by scan_all() for reporting

    # ── CLI runner ────────────────────────────────────────────────────────────

    def _run(self, *args, params: dict | None = None) -> dict | list | None:
        """Run a gws CLI command and return parsed JSON, or None on error."""
        cmd = ['npx', '@googleworkspace/cli'] + list(args)
        if params:
            cmd += ['--params', json.dumps(params)]
        try:
            result = gated_subprocess_run(
                cmd, capture_output=True, text=True, timeout=60
            )
            output = result.stdout
            clean = '\n'.join(
                l for l in output.split('\n')
                if not l.startswith('Using keyring')
            ).strip()
            if not clean:
                return None
            return json.loads(clean)
        except Exception as e:
            print(f'[GWS] Command failed: {e}')
            return None

    # ── Drive operations ──────────────────────────────────────────────────────

    def list_all_docs(self, limit: int = 200) -> list[dict]:
        """List all Google Docs in Drive."""
        data = self._run(
            'drive', 'files', 'list',
            params={
                'q':        "mimeType='application/vnd.google-apps.document'",
                'pageSize': limit,
                'fields':   'files(id,name,mimeType,modifiedTime,webViewLink)',
            },
        )
        if not data or not isinstance(data, dict):
            return []
        return data.get('files', [])

    def read_doc(self, doc_id: str) -> str:
        """
        Read plain-text content of a Google Doc.

        The gws CLI export command saves to a file and returns JSON metadata
        with the saved_file path. We read that file then clean up.
        """
        import tempfile
        import os
        import shutil
        tmp_dir = tempfile.mkdtemp()
        try:
            result = gated_subprocess_run(
                [
                    'npx', '@googleworkspace/cli', 'drive', 'files', 'export',
                    '--params',
                    json.dumps({'fileId': doc_id, 'mimeType': 'text/plain'}),
                ],
                capture_output=True, text=True, timeout=60,
                cwd=tmp_dir,
            )
            stdout = result.stdout
            clean = '\n'.join(
                l for l in stdout.split('\n')
                if not l.startswith('Using keyring')
            ).strip()

            try:
                meta = json.loads(clean)
                saved_file = meta.get('saved_file', '')
                if saved_file:
                    file_path = os.path.join(tmp_dir, saved_file)
                    if os.path.exists(file_path):
                        return Path(file_path).read_text(errors='replace').strip()
            except (json.JSONDecodeError, TypeError):
                return clean

            return ''
        except Exception as e:
            print(f'[GWS] Read doc failed: {e}')
            return ''
        finally:
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    # ── Deduplication ─────────────────────────────────────────────────────────

    def get_already_ingested(self) -> dict:
        """
        Returns doc_id → modified_time for docs already in Neon.
        Queries the events table where KnowledgeIntegrator logs metadata.
        """
        try:
            from substrate.state.storage.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT
                        payload_json->'metadata'->>'doc_id'       AS doc_id,
                        payload_json->'metadata'->>'modified'      AS modified
                    FROM events
                    WHERE org_id = %s
                    AND payload_json->>'source' = 'google_docs'
                    AND payload_json->'metadata'->>'doc_id' IS NOT NULL
                    GROUP BY
                        payload_json->'metadata'->>'doc_id',
                        payload_json->'metadata'->>'modified'
                    """,
                    (self.ctx.org_id,),
                )
                rows = cur.fetchall()
                return {
                    row['doc_id']: row['modified'] or ''
                    for row in rows
                    if row['doc_id']
                }
        except Exception as e:
            print(f'[GWS] get_already_ingested failed: {e}')
            return {}

    def is_new_or_modified(
        self,
        doc_id: str,
        modified_time: str,
        already_ingested: dict,
    ) -> bool:
        if doc_id not in already_ingested:
            return True
        prev = already_ingested[doc_id]
        if not prev:
            return True
        return modified_time > prev

    # ── AI understanding ──────────────────────────────────────────────────────

    def understand_doc(self, name: str, content: str) -> dict:
        """
        Use Claude Haiku to understand every document properly.
        Falls back to keyword scoring if AI call fails.
        """
        if not content.strip():
            return {
                'relevance_score': 0,
                'venture_id': 'none',
                'summary': 'empty document',
                'key_context': '',
                'keep': False,
            }

        try:
            from adapters.models.agent_runtime import AgentRuntime, TaskType
            from substrate.state.business.business_instance import (
                get_founder_name,
                get_ventures,
            )
            rt = AgentRuntime(self.ctx)

            # Founder + venture roster come from the tenant's BIS at runtime.
            _founder = get_founder_name(self.ctx, default='the owner')
            _ventures = get_ventures(self.ctx)
            if _ventures:
                _owner_lines = '\n'.join(f'- {v["name"]}' for v in _ventures)
                _venture_enum = '|'.join(
                    f'"{v["id"]}"' for v in _ventures
                ) + '|"general"|"irrelevant"'
                _owns = f'This belongs to {_founder} who runs:\n{_owner_lines}\n\n'
            else:
                _venture_enum = '"general"|"irrelevant"'
                _owns = f'This belongs to {_founder}.\n\n'

            result = rt.run(
                task_type=TaskType.ANALYZE,
                prompt=(
                    f'Document: "{name}"\n\n'
                    f'Content (first 1500 chars):\n'
                    f'{content[:1500]}\n\n'
                    f'{_owns}'
                    f'Return ONLY valid JSON:\n'
                    f'{{\n'
                    f'  "relevance_score": <1-10>,\n'
                    f'  "venture_id": <{_venture_enum}>,\n'
                    f'  "summary": <one sentence>,\n'
                    f'  "key_context": <most important 150 chars>,\n'
                    f'  "keep": <true|false>\n'
                    f'}}'
                ),
                agent='executive_assistant',
                max_tokens=300,
            )

            output = result.output or ''
            match = re.search(r'\{[^{}]*\}', output, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                if 'relevance_score' in parsed:
                    return parsed

        except Exception as e:
            print(f'[GWS] AI understand failed: {e}')

        return self._keyword_assess(name, content)

    def _keyword_assess(self, name: str, content: str) -> dict:
        """Keyword-based fallback when AI is unavailable."""
        text = (name + ' ' + content).lower()
        # Generic business-relevance vocabulary (projection-agnostic).
        keywords = [
            'business', 'offer', 'strategy', 'plan', 'goal', 'revenue',
            'client', 'sales', 'marketing', 'brand', 'content', 'coaching',
            'product', 'service', 'personal', 'creator', 'audience',
            'outreach', 'mission', 'vision', 'system', 'process', 'workflow',
            'build', 'phase', 'roadmap', 'milestone', 'notes', 'ideas',
            'brainstorm', 'life', 'health', 'habits', 'growth', 'instagram',
            'linkedin', 'tiktok', 'launch', 'funnel', 'icp', 'kpi',
        ]
        # Tenant identity keywords (founder name + venture names) from BIS.
        from substrate.state.business.business_instance import (
            get_founder_name,
            get_ventures,
        )
        _ventures = get_ventures(self.ctx)
        _founder = get_founder_name(self.ctx, default='')
        identity_kw = [w for w in _founder.lower().split() if len(w) > 2]
        for _v in _ventures:
            identity_kw.extend(w for w in _v['name'].lower().split() if len(w) > 2)
            identity_kw.append(_v['id'].replace('_', ' '))
        hits = sum(1 for k in keywords + identity_kw if k in text)

        # Assign the best-matching tenant venture by its name tokens, else general.
        venture_id = 'general'
        for _v in _ventures:
            _tokens = [w for w in _v['name'].lower().split() if len(w) > 2]
            if _tokens and any(t in text for t in _tokens):
                venture_id = _v['id']
                break

        score = min(hits * 1.5, 10)

        return {
            'relevance_score': score,
            'venture_id': venture_id,
            'summary': f'{name} — {hits} relevant keywords',
            'key_context': content[:150],
            'keep': score >= 2 or hits >= 1,
        }

    # ── Full scan ─────────────────────────────────────────────────────────────

    def scan_all(
        self,
        limit: int = 200,
        incremental: bool = False,
    ) -> list[GWSDocument]:
        """
        Scan all Google Docs. Every doc is read and AI-assessed.
        incremental=True skips docs already in Neon that haven't changed.
        """
        print('[GWS] Starting scan...')
        print(f'[GWS] Mode: {"incremental" if incremental else "full"}')

        already_ingested = self.get_already_ingested()
        print(f'[GWS] Already in Neon: {len(already_ingested)} docs')

        docs_list = self.list_all_docs(limit)
        print(f'[GWS] In Drive: {len(docs_list)} docs')
        print()

        documents: list[GWSDocument] = []
        skipped = 0
        empty = 0

        for i, doc_meta in enumerate(docs_list):
            doc_id   = doc_meta.get('id', '')
            name     = doc_meta.get('name', '')
            modified = doc_meta.get('modifiedTime', '')
            url      = doc_meta.get('webViewLink', '')

            # Skip unchanged docs in incremental mode
            if incremental and not self.is_new_or_modified(
                doc_id, modified, already_ingested
            ):
                skipped += 1
                continue

            print(f'[GWS] [{i+1}/{len(docs_list)}] {name[:55]}')

            content = self.read_doc(doc_id)

            if not content.strip():
                empty += 1
                print('[GWS]   Empty — skipped')
                continue

            # AI understands the document
            time.sleep(0.3)  # rate limit
            understanding = self.understand_doc(name, content)

            score      = understanding.get('relevance_score', 0)
            keep       = understanding.get('keep', True)
            venture_id = understanding.get('venture_id', 'general')
            summary    = understanding.get('summary', name)
            key_ctx    = understanding.get('key_context', '')

            print(
                f'[GWS]   Score: {score}/10 | {venture_id} | Keep: {keep}'
            )

            # Only discard confirmed noise (score 0-2 AND keep=False)
            if score < 3 and not keep:
                print('[GWS]   Discarded as noise')
                continue

            relevance = (
                'high'   if score >= 7
                else 'medium' if score >= 4
                else 'low'
            )

            documents.append(GWSDocument(
                id=doc_id,
                name=name,
                content=content,
                doc_type='doc',
                modified=modified,
                url=url,
                relevance=relevance,
                venture_id=venture_id,
                summary=summary,
                key_context=key_ctx,
                tags=[venture_id, relevance],
            ))

        self._scan_skipped = skipped  # expose for WorldPulse report

        print()
        print('[GWS] Scan complete:')
        print(f'  To ingest:          {len(documents)}')
        print(f'  Skipped (unchanged): {skipped}')
        print(f'  Empty:              {empty}')
        print()

        # Show breakdown by venture
        by_venture: dict[str, list[GWSDocument]] = {}
        for doc in documents:
            by_venture.setdefault(doc.venture_id, []).append(doc)
        for venture, vdocs in sorted(by_venture.items()):
            print(f'  {venture}: {len(vdocs)} docs')
            for d in vdocs:
                print(f'    [{d.relevance}] {d.name[:55]}')

        return documents

    # ── EOS ingestion ─────────────────────────────────────────────────────────

    def ingest_to_eos(self, documents: list[GWSDocument]) -> int:
        """
        Store document knowledge in EOS via KnowledgeIntegrator.
        Large docs are split into 3000-char chunks.
        Returns count of docs ingested.
        """
        ingested = 0
        try:
            from substrate.understanding.knowledge.knowledge_integrator import KnowledgeIntegrator
            ki = KnowledgeIntegrator(self.ctx)

            for doc in documents:
                if not doc.content:
                    continue

                chunk_size = 3000
                chunks = [
                    doc.content[i:i + chunk_size]
                    for i in range(0, len(doc.content), chunk_size)
                ]

                for j, chunk in enumerate(chunks):
                    ki.integrate(
                        content=(
                            f'Google Doc: {doc.name}\n'
                            f'Venture: {doc.venture_id}\n'
                            f'Relevance: {doc.relevance}\n'
                            f'Summary: {doc.summary}\n'
                            f'Part {j+1}/{len(chunks)}:\n'
                            f'{chunk}'
                        ),
                        source='google_docs',
                        category='business_insight',
                        metadata={
                            'doc_id':       doc.id,
                            'doc_name':     doc.name,
                            'modified':     doc.modified,
                            'relevance':    doc.relevance,
                            'venture_id':   doc.venture_id,
                            'summary':      doc.summary,
                            'chunk':        j + 1,
                            'total_chunks': len(chunks),
                            'url':          doc.url,
                        },
                    )

                ingested += 1
                print(
                    f'[GWS] Ingested: {doc.name[:50]} '
                    f'({len(chunks)} chunk{"s" if len(chunks) > 1 else ""})'
                )

        except Exception as e:
            print(f'[GWS] Ingest failed: {e}')

        return ingested

    # ── Context summary ───────────────────────────────────────────────────────

    def _complete_if_truncated(
        self,
        text: str,
        rt: object,
        context: str,
    ) -> str:
        """Request continuation if text ends mid-sentence."""
        if not text:
            return text

        text = text.strip()

        ends_complete = (
            text.endswith('.')
            or text.endswith('!')
            or text.endswith('?')
            or text.endswith('*')
            or text.endswith('"')
            or text[-1].isdigit()
        )

        if not ends_complete:
            try:
                from adapters.models.agent_runtime import TaskType
                continuation = rt.run(
                    task_type=TaskType.GENERATE,
                    prompt=(
                        f'Complete this sentence (continue from where it was '
                        f'cut off, do not repeat what was already said):\n\n'
                        f'...{text[-200:]}'
                    ),
                    agent='executive_assistant',
                    max_tokens=200,
                )
                if continuation.output:
                    last_words = ' '.join(text.split()[-5:])
                    cont = continuation.output
                    if last_words.lower() in cont.lower():
                        idx = cont.lower().find(last_words.lower())
                        cont = cont[idx + len(last_words):]
                    return text + cont
            except Exception:
                pass

        return text

    def generate_founder_profile(
        self,
        documents: list[GWSDocument],
    ) -> str:
        """
        Generate a per-venture profile of what was learned from all docs.
        Sections: one per tenant venture, plus Other Projects and Founder Patterns.
        Saves to /opt/OS/data/founder_profile.md for cognitive loop injection.
        """
        if not documents:
            return 'No documents to profile.'

        from substrate.state.business.business_instance import (
            get_ai_name,
            get_founder_name,
            get_ventures,
        )

        _founder = get_founder_name(self.ctx, default='the founder')
        _ai = get_ai_name() or 'the assistant'

        # Group high/medium docs by venture — buckets built from the tenant roster.
        _roster = get_ventures(self.ctx)
        by_venture: dict[str, list[str]] = {v['id']: [] for v in _roster}
        for _extra in ('eos_platform', 'general'):
            by_venture.setdefault(_extra, [])
        for doc in documents:
            if doc.relevance in ('high', 'medium'):
                entry = (
                    f'[{doc.name}]\n'
                    f'Summary: {doc.summary or ""}\n'
                    f'Context: {doc.key_context or ""}\n'
                    f'Content: {doc.content[:800]}\n'
                )
                by_venture.setdefault(doc.venture_id, []).append(entry)

        from adapters.models.agent_runtime import AgentRuntime, TaskType
        rt = AgentRuntime(self.ctx)
        sections: list[str] = []

        # ── One profile section per tenant venture (roster-driven, no hardcoding) ─
        for _v in _roster:
            _vname = _v['name']
            _vcontent = '\n'.join(by_venture.get(_v['id'], [])[:5])
            if not _vcontent:
                continue
            print(f'[GWS] Profiling: {_vname}...')
            result = rt.run(
                task_type=TaskType.ANALYZE,
                prompt=(
                    f'Based on these docs about {_vname}:\n\n'
                    f'{_vcontent[:2500]}\n\n'
                    f'What was learned about this business? Cover:\n'
                    f'1. The exact offer and pricing\n'
                    f'2. Current stage and progress\n'
                    f'3. ICP / target client profile\n'
                    f'4. Current strategy\n'
                    f'5. What has been tried or built vs planned\n'
                    f'6. Gaps or missing pieces\n'
                    f'Be specific. 200 words max.'
                ),
                agent='executive_assistant',
                max_tokens=800,
            )
            output = self._complete_if_truncated(
                result.output or '', rt, _v['id']
            )
            sections.append(f'## {_vname}\n{output or "No data"}')

        # ── Section 3: Other projects ─────────────────────────────────────────
        eos_content = '\n'.join(by_venture.get('eos_platform', [])[:3])
        gen_content = '\n'.join(by_venture.get('general', [])[:3])
        other_content = (eos_content + '\n' + gen_content).strip()
        if other_content:
            print('[GWS] Profiling: Other projects...')
            result = rt.run(
                task_type=TaskType.ANALYZE,
                prompt=(
                    f'Based on these docs:\n\n'
                    f'{other_content[:2500]}\n\n'
                    f'What other projects and ideas did EOS find? Cover:\n'
                    f'1. EntrepreneurOS — what stage, what was planned\n'
                    f'2. CreatorOS — what was planned\n'
                    f'3. LYFEOS — what was planned\n'
                    f'4. Any other projects mentioned\n'
                    f'5. Ideas not yet acted on\n'
                    f'Be specific. 200 words max.'
                ),
                agent='executive_assistant',
                max_tokens=800,
            )
            output = self._complete_if_truncated(
                result.output or '', rt, 'other_projects'
            )
            sections.append(f'## Other Projects\n{output or "No data"}')

        # ── Section 4: Founder patterns ───────────────────────────────────────
        all_entries = [
            entry
            for venture_docs in by_venture.values()
            for entry in venture_docs[:2]
        ]
        all_content = '\n'.join(all_entries)
        if all_content:
            print('[GWS] Profiling: Founder patterns...')
            result = rt.run(
                task_type=TaskType.ANALYZE,
                prompt=(
                    f'Based on all these docs from {_founder}:\n\n'
                    f'{all_content[:2500]}\n\n'
                    f'What patterns emerge about how they think and operate?\n'
                    f'1. Core philosophy and values\n'
                    f'2. Recurring frameworks he uses\n'
                    f'3. Strengths evident in the docs\n'
                    f'4. Gaps or blind spots noticed\n'
                    f'5. What he cares most about\n'
                    f'Be specific and honest. 200 words max.'
                ),
                agent='executive_assistant',
                max_tokens=800,
            )
            output = self._complete_if_truncated(
                result.output or '', rt, 'founder_patterns'
            )
            sections.append(f'## Founder Patterns\n{output or "No data"}')

        profile = (
            f'# What the Assistant Learned from Your Docs\n'
            f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n'
            f'Based on: {len(documents)} documents\n\n'
            + '\n\n'.join(sections)
        )

        profile_path = Path(_ROOT) / "data" / "founder_profile.md"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(profile)
        print(f'[GWS] Full profile saved: {profile_path}')

        # Post to Discord
        try:
            from transports.discord.discord_utils import post_to_webhook
            post_to_webhook(
                profile,
                title='📊 LEARNING REPORT',
                username=_ai,
            )
            print('[GWS] Profile posted to Discord')
        except Exception as _e:
            print(f'[GWS] Discord post failed: {_e}')

        return profile

    def save_context_summary(self, documents: list[GWSDocument]) -> None:
        """
        Save a markdown summary of all scanned docs.
        Written to /opt/OS/data/gws_context.md — injected into cognitive loop.
        """
        summary_path = Path(_ROOT) / "data" / "gws_context.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            '# GWS Document Context',
            f'Last scanned: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            f'Total documents: {len(documents)}',
            '',
        ]

        by_venture: dict[str, list[GWSDocument]] = {}
        for doc in documents:
            by_venture.setdefault(doc.venture_id, []).append(doc)

        for venture, docs in sorted(by_venture.items()):
            lines.append(f'## {venture}')
            for doc in docs:
                lines.append(f'### {doc.name}')
                lines.append(f'Relevance: {doc.relevance}')
                if doc.summary:
                    lines.append(f'Summary: {doc.summary}')
                if doc.key_context:
                    lines.append(f'Key: {doc.key_context[:200]}')
                lines.append('')

        summary_path.write_text('\n'.join(lines))
        print(f'[GWS] Context saved: {summary_path}')
