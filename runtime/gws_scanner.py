"""
GWSDocumentScanner — reads Google Docs the founder owns,
extracts business context, and ingests it into EOS knowledge layers.

DEX knows everything written about the businesses.

Features:
  - AI-based document understanding (not just keyword filtering)
  - Deduplication — skips unchanged docs on incremental runs
  - Chunked ingestion — large docs split into 3000-char chunks
  - Venture routing — maps each doc to the right company

Usage:
    from runtime.context import load_context_from_env
    from runtime.gws_scanner import GWSDocumentScanner

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
from datetime import datetime
from pathlib import Path

from runtime.context import EOSContext
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

    def __init__(self, ctx: EOSContext):
        self.ctx = ctx
        self._scan_skipped = 0  # set by scan_all() for reporting

    # ── CLI runner ────────────────────────────────────────────────────────────

    def _run(self, *args, params: dict | None = None) -> dict | list | None:
        """Run a gws CLI command and return parsed JSON, or None on error."""
        cmd = ['npx', '@googleworkspace/cli'] + list(args)
        if params:
            cmd += ['--params', json.dumps(params)]
        try:
            result = subprocess.run(
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
            result = subprocess.run(
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
            from state.storage.db import get_conn
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
            from execution.runtime.agent_runtime import AgentRuntime, TaskType
            rt = AgentRuntime(self.ctx)

            result = rt.run(
                task_type=TaskType.ANALYZE,
                prompt=(
                    f'Document: "{name}"\n\n'
                    f'Content (first 1500 chars):\n'
                    f'{content[:1500]}\n\n'
                    f'This belongs to Antony Munoz who runs:\n'
                    f'- Lyfe Institute (coaching, $750 Initiate Arena)\n'
                    f'- Empyrean Creative (B2B AI services)\n'
                    f'- Personal Brand (content business)\n'
                    f'- EntrepreneurOS (AI OS platform)\n\n'
                    f'Return ONLY valid JSON:\n'
                    f'{{\n'
                    f'  "relevance_score": <1-10>,\n'
                    f'  "venture_id": <"lyfe_institute"|"empyrean_creative"|"personal_brand"|"eos_platform"|"general"|"irrelevant">,\n'
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
        keywords = [
            'entrepreneur', 'eos', 'lyfe', 'empyrean', 'initiate', 'business',
            'offer', 'strategy', 'plan', 'goal', 'revenue', 'client', 'sales',
            'marketing', 'brand', 'content', 'coaching', 'product', 'service',
            'personal', 'antony', 'afm', 'munoz', 'creator', 'audience',
            'outreach', 'mission', 'vision', 'system', 'process', 'workflow',
            'build', 'phase', 'roadmap', 'milestone', 'notes', 'ideas',
            'brainstorm', 'life', 'health', 'habits', 'growth', 'instagram',
            'linkedin', 'tiktok', 'launch', 'funnel', 'icp', 'kpi',
        ]
        hits = sum(1 for k in keywords if k in text)

        venture_id = 'general'
        if any(k in text for k in ['lyfe', 'initiate', 'coaching', 'arena']):
            venture_id = 'lyfe_institute'
        elif any(k in text for k in ['empyrean', 'b2b', 'agency', 'retainer']):
            venture_id = 'empyrean_creative'
        elif any(k in text for k in ['personal brand', 'creator', 'audience', 'content']):
            venture_id = 'personal_brand'
        elif any(k in text for k in ['eos', 'entrepreneur os', 'entrepreneuros', 'harness', 'operating system']):
            venture_id = 'eos_platform'

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
            from runtime.knowledge_integrator import KnowledgeIntegrator
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
                from execution.runtime.agent_runtime import TaskType
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
        Generate a four-section profile of what EOS learned from all docs.
        Sections: Lyfe Institute, Empyrean Creative, Other Projects, Founder Patterns.
        Saves to /opt/OS/data/founder_profile.md for cognitive loop injection.
        """
        if not documents:
            return 'No documents to profile.'

        # Group high/medium docs by venture
        by_venture: dict[str, list[str]] = {
            'lyfe_institute':    [],
            'empyrean_creative': [],
            'eos_platform':      [],
            'personal_brand':    [],
            'general':           [],
        }
        for doc in documents:
            if doc.relevance in ('high', 'medium'):
                entry = (
                    f'[{doc.name}]\n'
                    f'Summary: {doc.summary or ""}\n'
                    f'Context: {doc.key_context or ""}\n'
                    f'Content: {doc.content[:800]}\n'
                )
                by_venture.setdefault(doc.venture_id, []).append(entry)

        from execution.runtime.agent_runtime import AgentRuntime, TaskType
        rt = AgentRuntime(self.ctx)
        sections: list[str] = []

        # ── Section 1: Lyfe Institute ─────────────────────────────────────────
        lyfe_content = '\n'.join(by_venture.get('lyfe_institute', [])[:5])
        if lyfe_content:
            print('[GWS] Profiling: Lyfe Institute...')
            result = rt.run(
                task_type=TaskType.ANALYZE,
                prompt=(
                    f'Based on these docs about Lyfe Institute:\n\n'
                    f'{lyfe_content[:2500]}\n\n'
                    f'What did EOS learn about this business? Cover:\n'
                    f'1. The exact offer and pricing\n'
                    f'2. Current stage and progress\n'
                    f'3. ICP description\n'
                    f'4. Current strategy\n'
                    f'5. What has been tried\n'
                    f'6. Gaps or missing pieces\n'
                    f'Be specific. 200 words max.'
                ),
                agent='executive_assistant',
                max_tokens=800,
            )
            output = self._complete_if_truncated(
                result.output or '', rt, 'lyfe_institute'
            )
            sections.append(f'## Lyfe Institute\n{output or "No data"}')

        # ── Section 2: Empyrean Creative ──────────────────────────────────────
        emp_content = '\n'.join(by_venture.get('empyrean_creative', [])[:5])
        if emp_content:
            print('[GWS] Profiling: Empyrean Creative...')
            result = rt.run(
                task_type=TaskType.ANALYZE,
                prompt=(
                    f'Based on these docs about Empyrean Creative:\n\n'
                    f'{emp_content[:2500]}\n\n'
                    f'What did EOS learn about this business? Cover:\n'
                    f'1. What services are offered\n'
                    f'2. Target client profile\n'
                    f'3. Current stage and progress\n'
                    f'4. What has been built vs planned\n'
                    f'5. Current strategy\n'
                    f'6. Gaps or missing pieces\n'
                    f'Be specific. 200 words max.'
                ),
                agent='executive_assistant',
                max_tokens=800,
            )
            output = self._complete_if_truncated(
                result.output or '', rt, 'empyrean_creative'
            )
            sections.append(f'## Empyrean Creative\n{output or "No data"}')

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
                    f'Based on all these docs from Antony Munoz:\n\n'
                    f'{all_content[:2500]}\n\n'
                    f'What patterns emerge about how he thinks and operates?\n'
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
            f'# What EOS Learned from Your Docs\n'
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
            from runtime.discord_utils import post_to_webhook
            post_to_webhook(
                profile,
                title='📊 EOS LEARNING REPORT',
                username='DEX',
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
