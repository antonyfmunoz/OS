"""
NotebookLMSync — bidirectional sync between Neon and NotebookLM.

Data flows:
  Neon → NotebookLM: pipeline data, world pulse reports, founder profile docs
  NotebookLM → Neon: query results stored as notebooklm_insight events for DEX

Notebook IDs are stored in .env after manual creation:
    nlm notebook create "Lyfe Institute"

Usage:
    from runtime.context import load_context_from_env
    from runtime.notebooklm_sync import NotebookLMSync

    ctx = load_context_from_env()
    nls = NotebookLMSync(ctx)
    nls.sync_world_pulse_to_notebook(report_text)
"""

import json
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from runtime.context import EOSContext
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



@dataclass
class NotebookConfig:
    notebook_id: str
    name: str
    venture_id: str
    auto_sync: bool = True
    last_synced: datetime | None = None


class NotebookLMSync:

    def __init__(self, ctx: EOSContext):
        self.ctx = ctx
        # Notebook IDs stored in .env after: nlm notebook create "Name"
        self.notebooks: dict[str, str] = {
            'lyfe_institute':    os.getenv('NOTEBOOKLM_LYFE_ID', ''),
            'empyrean_creative': os.getenv('NOTEBOOKLM_EMPYREAN_ID', ''),
            'personal_brand':    os.getenv('NOTEBOOKLM_BRAND_ID', ''),
            'world_pulse':       os.getenv('NOTEBOOKLM_PULSE_ID', ''),
        }

    # ── helpers ───────────────────────────────────────────────────────────────

    def _nlm_source_add(self, notebook_id: str, file_path: str) -> bool:
        """Run nlm source add and return success."""
        try:
            result = subprocess.run(
                ['nlm', 'source', 'add', notebook_id, '--file', file_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except Exception as e:
            print(f'[NotebookLMSync] nlm source add failed: {e}')
            return False

    def _write_tmp(self, content: str, suffix: str = '.txt') -> str:
        """Write content to a temp file and return its path."""
        tmp = tempfile.mktemp(suffix=suffix)
        Path(tmp).write_text(content)
        return tmp

    # ── Neon → NotebookLM ────────────────────────────────────────────────────

    def sync_pipeline_to_notebook(
        self,
        venture_id: str = 'lyfe_institute',
    ) -> bool:
        """
        Export pipeline data from Neon and upload to the venture's notebook.
        Called manually or via check_and_update() on Saturdays.
        """
        try:
            from state.storage.db import get_conn

            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    '''
                    SELECT
                        payload_json->>'name'    AS name,
                        payload_json->>'stage'   AS stage,
                        payload_json->>'notes'   AS notes,
                        payload_json->>'channel' AS channel,
                        created_at
                    FROM events
                    WHERE org_id = %s
                      AND event_type = 'pipeline_entry'
                      AND payload_json->>'venture_id' = %s
                    ORDER BY created_at DESC
                    LIMIT 50
                    ''',
                    (self.ctx.org_id, venture_id),
                )
                rows = cur.fetchall()

            if not rows:
                print(f'[NotebookLMSync] No pipeline data for {venture_id}')
                return False

            lines = [
                f'# {venture_id} Pipeline Data',
                f'Exported: {datetime.now().strftime("%Y-%m-%d")}',
                f'Total entries: {len(rows)}',
                '',
            ]
            for row in rows:
                lines.extend([
                    f'## {row[0] or "Unknown"}',
                    f'Stage: {row[1] or "—"}',
                    f'Channel: {row[3] or "—"}',
                    f'Notes: {row[2] or "—"}',
                    f'Date: {str(row[4])[:10]}',
                    '',
                ])

            notebook_id = self.notebooks.get(venture_id, '')
            if not notebook_id:
                print(f'[NotebookLMSync] No notebook ID for {venture_id}')
                return False

            tmp = self._write_tmp('\n'.join(lines))
            success = self._nlm_source_add(notebook_id, tmp)
            Path(tmp).unlink(missing_ok=True)

            if success:
                print(f'[NotebookLMSync] Pipeline synced: {venture_id}')
            return success

        except Exception as e:
            print(f'[NotebookLMSync] Pipeline sync failed: {e}')
            return False

    def sync_world_pulse_to_notebook(self, report: str) -> bool:
        """
        Upload a world pulse report to the world_pulse notebook.
        Called by WorldPulse.run_pulse_scan() after each Saturday scan.
        """
        try:
            notebook_id = self.notebooks.get('world_pulse', '')
            if not notebook_id:
                print('[NotebookLMSync] NOTEBOOKLM_PULSE_ID not set')
                return False

            date_str = datetime.now().strftime('%Y-%m-%d')
            content = f'# World Pulse Report — {date_str}\n\n{report}'
            tmp = self._write_tmp(content)
            success = self._nlm_source_add(notebook_id, tmp)
            Path(tmp).unlink(missing_ok=True)

            if success:
                print(f'[NotebookLMSync] World pulse report synced: {date_str}')
            return success

        except Exception as e:
            print(f'[NotebookLMSync] Pulse sync failed: {e}')
            return False

    def sync_founder_profile(self) -> bool:
        """
        Upload founder profile and brand docs to all venture notebooks.
        Keeps NotebookLM current with latest context docs from /opt/OS/data/.
        """
        docs = [
            f'{_ROOT}/data/founder_profile.md',
            f'{_ROOT}/data/brand_identity.md',
            f'{_ROOT}/data/funnel_strategy.md',
            f'{_ROOT}/data/workbook_framework.md',
            f'{_ROOT}/data/gws_context.md',
        ]

        synced = 0
        for venture_id, notebook_id in self.notebooks.items():
            if not notebook_id or venture_id == 'world_pulse':
                continue
            for doc_path in docs:
                if not Path(doc_path).exists():
                    continue
                if self._nlm_source_add(notebook_id, doc_path):
                    synced += 1

        print(f'[NotebookLMSync] Founder profile synced — {synced} uploads')
        return synced > 0

    # ── NotebookLM → Neon ────────────────────────────────────────────────────

    def query_for_context(self, venture_id: str, question: str) -> str:
        """
        Query a NotebookLM notebook via nlm CLI.
        Stores the answer in Neon as a notebooklm_insight event for DEX.
        Returns the answer string.
        """
        notebook_id = self.notebooks.get(venture_id, '')
        if not notebook_id:
            return ''

        try:
            result = subprocess.run(
                ['nlm', 'notebook', 'query', notebook_id, '--question', question],
                capture_output=True,
                text=True,
                timeout=90,
            )
            answer = result.stdout.strip() if result.returncode == 0 else ''

            if answer:
                from state.storage.db import get_conn
                with get_conn(self.ctx.org_id) as cur:
                    cur.execute(
                        '''
                        INSERT INTO events
                            (id, org_id, event_type, payload_json, created_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        ''',
                        (
                            str(uuid.uuid4()),
                            self.ctx.org_id,
                            'notebooklm_insight',
                            json.dumps({
                                'venture_id': venture_id,
                                'question':   question,
                                'answer':     answer[:2000],
                                'source':     'notebooklm',
                            }),
                        ),
                    )
                print(f'[NotebookLMSync] Query stored: {question[:50]}')

            return answer

        except Exception as e:
            print(f'[NotebookLMSync] Query failed: {e}')
            return ''

    def get_recent_insights(
        self,
        venture_id: str = '',
        limit: int = 5,
    ) -> list[dict]:
        """
        Retrieve recent NotebookLM insights from Neon for DEX context injection.
        """
        try:
            from state.storage.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                if venture_id:
                    cur.execute(
                        '''
                        SELECT payload_json, created_at
                        FROM events
                        WHERE org_id = %s
                          AND event_type = 'notebooklm_insight'
                          AND payload_json->>'venture_id' = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        ''',
                        (self.ctx.org_id, venture_id, limit),
                    )
                else:
                    cur.execute(
                        '''
                        SELECT payload_json, created_at
                        FROM events
                        WHERE org_id = %s
                          AND event_type = 'notebooklm_insight'
                        ORDER BY created_at DESC
                        LIMIT %s
                        ''',
                        (self.ctx.org_id, limit),
                    )
                rows = cur.fetchall()

            results = []
            for row in rows:
                data = row[0]
                if isinstance(data, str):
                    data = json.loads(data)
                results.append(data)
            return results

        except Exception as e:
            print(f'[NotebookLMSync] get_recent_insights failed: {e}')
            return []

    # ── cross-reference ───────────────────────────────────────────────────────

    def check_and_update(self) -> dict:
        """
        Full cross-reference: sync founder profile and venture pipelines to NotebookLM.
        Called by WorldPulse.run_pulse_scan() on Saturdays.
        """
        results: dict[str, bool] = {}

        results['founder_profile'] = self.sync_founder_profile()

        for venture_id in ('lyfe_institute', 'empyrean_creative'):
            results[f'pipeline_{venture_id}'] = self.sync_pipeline_to_notebook(
                venture_id
            )

        print(f'[NotebookLMSync] Cross-reference complete: {results}')
        return results
