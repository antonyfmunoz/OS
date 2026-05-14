"""
VoiceInterface — dedicated voice conversation and meeting intelligence layer.

Wraps MediaProcessor synthesis/transcription into a clean interface for:
  - Full voice conversation turns (transcribe → CognitiveLoop → synthesize)
  - Meeting session capture (accumulate transcript without synthesis)
  - Meeting analysis (structured extraction via CognitiveLoop ANALYZE)

Usage:
    from runtime.context import load_context_from_env
    from runtime.voice_interface import VoiceInterface

    ctx = load_context_from_env()
    vi  = VoiceInterface(ctx)

    # One voice turn
    result = vi.process_voice_turn('/tmp/audio.wav')

    # Meeting session
    session_id = vi.start_meeting_session('Weekly Review')
    vi.process_meeting_audio('/tmp/chunk1.wav', session_id)
    vi.process_meeting_audio('/tmp/chunk2.wav', session_id)
    summary = vi.end_meeting_session(session_id)
"""

import os
import re
import time
import uuid

from runtime.context import EOSContext
from runtime.media_processor import MediaProcessor
from control_plane.runtime.cognitive_loop import CognitiveLoop
from execution.runtime.agent_runtime import TaskType


class VoiceInterface:

    # ─── Meeting type context map ──────────────────────────────────────────────

    MEETING_CONTEXTS: dict[str, dict] = {
        'sales_call': {
            'pre_brief_agent': 'sales_agent',
            'during_agent': 'sales_agent',
            'post_agent': 'sales_agent',
            'pre_brief_prompt': (
                'Generate a sales call brief: lead overview, ICP fit, '
                'likely objections, recommended opener, and close script.'
            ),
            'post_action': 'log outcome and draft follow-up message',
            'agenda_items': [
                'Lead overview and ICP score',
                'Likely objections',
                'Recommended opener',
                'Close script reminder',
            ],
        },
        'content_planning': {
            'pre_brief_agent': 'marketing_agent',
            'during_agent': 'marketing_agent',
            'post_agent': 'content_agent',
            'pre_brief_prompt': (
                'Generate top ICP signals from last 7 days, '
                'hook concepts to test, and content priorities.'
            ),
            'post_action': 'create content calendar with selected hooks',
            'agenda_items': [
                'Top signals from last 7 days',
                'Hook concepts to test',
                'Content priorities this week',
                'Distribution plan',
            ],
        },
        'ops_review': {
            'pre_brief_agent': 'operations_agent',
            'during_agent': 'operations_agent',
            'post_agent': 'operations_agent',
            'pre_brief_prompt': (
                'Identify current bottlenecks, process completion rates, '
                'and automation opportunities.'
            ),
            'post_action': 'create optimization tasks in Neon',
            'agenda_items': [
                'Current bottleneck',
                'Process completion rates',
                'What to eliminate this week',
                'Automation opportunities',
            ],
        },
        'finance_review': {
            'pre_brief_agent': 'finance_agent',
            'during_agent': 'finance_agent',
            'post_agent': 'finance_agent',
            'pre_brief_prompt': (
                'Generate financial summary: revenue vs target, '
                'cash position, unit economics status.'
            ),
            'post_action': 'update BIS financial data and model',
            'agenda_items': [
                'Revenue vs target',
                'Cash position',
                'Unit economics status',
                'Next financial milestone',
            ],
        },
        'team_standup': {
            'pre_brief_agent': 'ceo_agent',
            'during_agent': 'ceo_agent',
            'post_agent': 'operations_agent',
            'pre_brief_prompt': (
                'Generate standup agenda: completions, in-progress, '
                'blockers, and today\'s priorities.'
            ),
            'post_action': 'update tasks and blockers in Neon',
            'agenda_items': [
                'What was completed',
                'What is in progress today',
                'Any blockers',
                'Priorities alignment',
            ],
        },
        'weekly_review': {
            'pre_brief_agent': 'portfolio_advisor',
            'during_agent': 'portfolio_advisor',
            'post_agent': 'strategy_engine',
            'pre_brief_prompt': (
                'Generate weekly review: KPIs vs targets, wins and losses, '
                'binding constraint, next week priorities.'
            ),
            'post_action': 'update strategy and priorities for next week',
            'agenda_items': [
                'KPIs vs targets',
                'This week wins and losses',
                'Binding constraint',
                'Next week priorities',
                'Strategic decisions pending',
            ],
        },
        'strategy_session': {
            'pre_brief_agent': 'ceo_agent',
            'during_agent': 'ceo_agent',
            'post_agent': 'strategy_engine',
            'pre_brief_prompt': (
                'Prepare strategic context: current stage, north star gap, '
                'pending decisions, and market position.'
            ),
            'post_action': 'document decisions and update strategy',
            'agenda_items': [
                'Current stage and north star gap',
                'Strategic options on the table',
                'Key decisions to make',
                'Next 90-day priorities',
            ],
        },
        'vendor_call': {
            'pre_brief_agent': 'operations_agent',
            'during_agent': 'operations_agent',
            'post_agent': 'operations_agent',
            'pre_brief_prompt': (
                'Prepare vendor brief: what we need, our leverage, '
                'pricing benchmarks, and negotiation priorities.'
            ),
            'post_action': 'document agreement and create follow-up tasks',
            'agenda_items': [
                'What we need from this vendor',
                'Our leverage in this negotiation',
                'Pricing benchmarks',
                'Non-negotiables',
            ],
        },
        'investor_update': {
            'pre_brief_agent': 'finance_agent',
            'during_agent': 'finance_agent',
            'post_agent': 'finance_agent',
            'pre_brief_prompt': (
                'Prepare investor update: traction metrics, milestones hit, '
                'ask, and forward projections.'
            ),
            'post_action': 'send follow-up and update investor tracker',
            'agenda_items': [
                'Traction and metrics',
                'Milestones since last update',
                'Current ask or update',
                'Forward projections',
            ],
        },
        'coaching_session': {
            'pre_brief_agent': 'ceo_agent',
            'during_agent': 'ceo_agent',
            'post_agent': 'ceo_agent',
            'pre_brief_prompt': (
                'Prepare coaching context: current challenges, goals, '
                'patterns from recent interactions.'
            ),
            'post_action': 'log session insights and update action items',
            'agenda_items': [
                'Current state and challenges',
                'Goals for this session',
                'Key insights or patterns',
                'Commitments for next session',
            ],
        },
        'research_session': {
            'pre_brief_agent': 'research_agent',
            'during_agent': 'research_agent',
            'post_agent': 'research_agent',
            'pre_brief_prompt': (
                'Prepare research context: knowledge gaps, recent signals, '
                'and questions to answer.'
            ),
            'post_action': 'document findings and update knowledge base',
            'agenda_items': [
                'Research questions to answer',
                'Current knowledge gaps',
                'Signal sources to check',
                'Hypothesis to test',
            ],
        },
    }

    def __init__(self, ctx: EOSContext) -> None:
        self.ctx = ctx
        self.processor = MediaProcessor()
        self.loop = CognitiveLoop(ctx)
        self._session_transcript: list[dict] = []
        self._active_meeting_type: str = 'sales_call'

    # ─── Transcription ────────────────────────────────────────────────────────

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file to text via local Whisper.
        Logs the entry to session transcript.
        Returns transcript text.
        """
        text = self.processor._local_transcribe(audio_path)
        self._session_transcript.append({
            'role': 'user',
            'text': text,
            'audio_path': audio_path,
            'ts': time.time(),
        })
        return text

    # ─── Synthesis ────────────────────────────────────────────────────────────

    def synthesize(
        self,
        text: str,
        output_path: str | None = None,
    ) -> str | None:
        """
        Convert text to speech. Markdown stripping is handled inside
        MediaProcessor.synthesize_speech(). Returns path to audio or None.
        """
        return self.processor.synthesize_speech(text, output_path)

    # ─── Full voice turn ──────────────────────────────────────────────────────

    def process_voice_turn(
        self,
        audio_path: str,
        agent: str = 'ceo_agent',
        venture_id: str = 'lyfe_institute',
    ) -> dict:
        """
        Full voice conversation turn:
          1. transcribe(audio_path) → text
          2. Route text through CognitiveLoop
          3. synthesize response audio
          4. Log to session transcript

        Returns:
            {
                transcript: str,
                response_text: str,
                response_audio_path: str | None,
                model_used: str,
                cost_usd: float,
                duration_ms: int,
            }
        """
        start_ms = int(time.monotonic() * 1000)

        # 1. Transcribe
        transcript = self.transcribe(audio_path)

        # 2. Route through CognitiveLoop (pure text — transcription already done)
        cognitive_result = self.loop.run(
            input=transcript,
            agent=agent,
            task_type=TaskType.ANALYZE,
            venture_id=venture_id,
        )
        response_text = cognitive_result.output or ''

        # 3. Synthesize response
        response_audio_path = self.synthesize(response_text)

        # 4. Log response to session transcript
        self._session_transcript.append({
            'role': 'assistant',
            'text': response_text,
            'audio_path': response_audio_path,
            'ts': time.time(),
        })

        duration_ms = int(time.monotonic() * 1000) - start_ms

        from execution.runtime.agent_runtime import calculate_cost
        cost_usd = calculate_cost(
            cognitive_result.model_used,
            cognitive_result.tokens_used,
        )

        return {
            'transcript': transcript,
            'response_text': response_text,
            'response_audio_path': response_audio_path,
            'model_used': cognitive_result.model_used,
            'cost_usd': cost_usd,
            'duration_ms': duration_ms,
        }

    # ─── Type-aware meeting methods ───────────────────────────────────────────

    def get_meeting_brief(
        self,
        meeting_type: str,
        venture_id: str,
        attendee_context: dict | None = None,
    ) -> str:
        """
        Generate a type-appropriate pre-meeting brief using the correct dept agent.
        Injects BIS context and returns a formatted brief for Telegram.
        """
        ctx_map = self.MEETING_CONTEXTS.get(meeting_type, self.MEETING_CONTEXTS['sales_call'])
        agent   = ctx_map['pre_brief_agent']
        agenda  = '\n'.join(f'  {i+1}. {item}' for i, item in enumerate(ctx_map['agenda_items']))

        # BIS context injection
        bis_context = ''
        try:
            from runtime.business_instance import BusinessInstanceManager
            bim = BusinessInstanceManager(self.ctx)
            bis_context = bim.get_context_for_agents(venture_id) or ''
        except Exception:
            pass

        attendee_str = ''
        if attendee_context:
            attendee_str = '\n'.join(f'{k}: {v}' for k, v in attendee_context.items())

        prompt = (
            f'{ctx_map["pre_brief_prompt"]}\n\n'
            f'Meeting type: {meeting_type}\n'
            f'Venture: {venture_id}\n'
            f'{bis_context}'
            + (f'\nAttendee context:\n{attendee_str}' if attendee_str else '')
        )

        try:
            result = self.loop.run(
                input=prompt,
                agent=agent,
                task_type=TaskType.ANALYZE,
                venture_id=venture_id,
            )
            brief = result.output or ''
        except Exception as e:
            brief = f'Brief generation failed: {e}'

        return (
            f'PRE-MEETING BRIEF — {meeting_type.replace("_", " ").upper()}\n\n'
            f'AGENDA:\n{agenda}\n\n'
            f'{brief[:1200]}'
        )

    def get_during_meeting_context(
        self,
        meeting_type: str,
        query: str,
        session_id: str,
        venture_id: str = 'lyfe_institute',
    ) -> str:
        """
        Answer real-time queries during a meeting — text only, silent to call.
        Routes common shortcut queries to fast answers.
        """
        q = query.lower().strip()

        # Fast non-AI shortcuts
        if q in ('score', 'icp score', 'icp'):
            try:
                from runtime.business_instance import BusinessInstanceManager
                bim = BusinessInstanceManager(self.ctx)
                bis = bim.get_bis(venture_id)
                return f'ICP target: {bis.icp_description}' if bis else 'No BIS loaded'
            except Exception as e:
                return f'ICP error: {e}'

        if q in ('stage', 'current stage'):
            try:
                from runtime.business_instance import BusinessInstanceManager
                bim = BusinessInstanceManager(self.ctx)
                g = bim.get_stage_guidance(venture_id)
                return f'Stage {g["current_stage"]}/6 — {g["stage_name"]}\nFocus: {g["focus"]}'
            except Exception as e:
                return f'Stage error: {e}'

        if q in ('numbers', 'kpis', 'metrics', 'revenue'):
            try:
                from runtime.business_instance import BusinessInstanceManager
                bim = BusinessInstanceManager(self.ctx)
                bis = bim.get_bis(venture_id)
                if bis:
                    return (
                        f'Revenue: ${bis.monthly_revenue:,.0f} / '
                        f'${bis.monthly_target:,.0f} target\n'
                        f'Stage: {bis.current_stage}/6 — {bis.stage_name}'
                    )
                return 'No BIS loaded'
            except Exception as e:
                return f'Numbers error: {e}'

        if q in ('price', 'offer', 'anchor'):
            try:
                from runtime.business_instance import BusinessInstanceManager
                bim = BusinessInstanceManager(self.ctx)
                bis = bim.get_bis(venture_id)
                if bis:
                    return (
                        f'Offer: {bis.offer_name}\n'
                        f'Price: ${bis.offer_price:,.0f}\n'
                        f'Anchor: quote value delivered, not time invested'
                    )
                return 'No BIS loaded'
            except Exception as e:
                return f'Price error: {e}'

        if q in ('constraint', 'bottleneck', 'binding'):
            try:
                from runtime.business_instance import BusinessInstanceManager
                bim = BusinessInstanceManager(self.ctx)
                g = bim.get_stage_guidance(venture_id)
                return (
                    f'Stage {g["current_stage"]}/6 — {g["stage_name"]}\n'
                    f'Binding constraint: {g["focus"]}\n'
                    f'Next action: {g.get("next_action", "see /bis for details")}'
                )
            except Exception as e:
                return f'Constraint error: {e}'

        if q in ('tasks', 'todo', 'action items'):
            try:
                from state.storage.db import get_conn
                with get_conn(self.ctx.org_id) as cur:
                    cur.execute(
                        """
                        SELECT title, status, priority
                        FROM tasks
                        WHERE org_id = %s AND status NOT IN ('done','cancelled')
                        ORDER BY priority DESC, created_at DESC
                        LIMIT 5
                        """,
                        (self.ctx.org_id,),
                    )
                    rows = cur.fetchall()
                if not rows:
                    return 'No active tasks'
                lines = ['Active tasks:']
                for r in rows:
                    lines.append(f'  [{r["priority"] or "—"}] {r["title"]} ({r["status"]})')
                return '\n'.join(lines)
            except Exception as e:
                return f'Tasks error: {e}'

        if q in ('signals', 'intel', 'market'):
            try:
                from state.memory.memory import AgentMemory
                mem = AgentMemory()
                events = mem.get_recent_events(
                    org_id=self.ctx.org_id,
                    event_type='signal',
                    limit=5,
                )
                if not events:
                    return 'No recent signals'
                lines = ['Recent signals:']
                for e in events[:5]:
                    payload = e.get('payload', {})
                    summary = payload.get('summary') or payload.get('content', '')
                    lines.append(f'  • {summary[:100]}')
                return '\n'.join(lines)
            except Exception as e:
                return f'Signals error: {e}'

        if q in ('objections', 'objection', 'pushback'):
            prompt = (
                'List the 3 most likely objections for this meeting type '
                f'({meeting_type}) and the one-line reframe for each. '
                'Be concise — mobile format.'
            )
            try:
                result = self.loop.run(
                    input=prompt,
                    agent='sales_agent',
                    task_type=TaskType.ANALYZE,
                    venture_id=venture_id,
                )
                return result.output or 'No objections generated.'
            except Exception as e:
                return f'Objections error: {e}'

        if q in ('history', 'background', 'context'):
            prompt = (
                f'Summarize the key interaction history relevant to this '
                f'{meeting_type} session. Include: last touchpoint, any '
                f'commitments made, and open items. Max 4 lines.'
            )
            try:
                result = self.loop.run(
                    input=prompt,
                    agent='sales_agent',
                    task_type=TaskType.ANALYZE,
                    venture_id=venture_id,
                )
                return result.output or 'No history found.'
            except Exception as e:
                return f'History error: {e}'

        # AI-powered queries
        ctx_map = self.MEETING_CONTEXTS.get(meeting_type, self.MEETING_CONTEXTS['sales_call'])
        agent   = ctx_map['during_agent']
        prompt  = (
            f'During a {meeting_type} meeting, quickly answer this query: {query}\n'
            f'Be concise — response will be read on mobile. Max 3 sentences.'
        )
        try:
            result = self.loop.run(
                input=prompt,
                agent=agent,
                task_type=TaskType.ANALYZE,
                venture_id=venture_id,
            )
            return result.output or 'No answer generated.'
        except Exception as e:
            return f'Query error: {e}'

    def end_meeting_with_actions(
        self,
        session_id: str,
        meeting_type: str,
        venture_id: str,
    ) -> dict:
        """
        End meeting and run type-appropriate post-meeting actions.
        Wraps end_meeting_session() and routes to correct dept agent.
        """
        # Core analysis
        result = self.end_meeting_session(session_id)
        ctx_map = self.MEETING_CONTEXTS.get(meeting_type, self.MEETING_CONTEXTS['sales_call'])

        # Type-specific post-actions
        post_action = ctx_map['post_action']
        agent       = ctx_map['post_agent']

        if meeting_type == 'finance_review' and result.get('decisions'):
            # Update BIS financial data from decisions
            try:
                from runtime.business_instance import BusinessInstanceManager
                bim = BusinessInstanceManager(self.ctx)
                bis = bim.get_bis(venture_id)
                if bis:
                    # Log meeting as a venture event
                    from state.memory.memory import AgentMemory
                    mem = AgentMemory()
                    mem.log_event(
                        org_id=self.ctx.org_id,
                        event_type='finance_review_complete',
                        payload={
                            'session_id': session_id,
                            'venture_id': venture_id,
                            'decisions': result.get('decisions', []),
                            'action_items': result.get('action_items', []),
                        },
                    )
            except Exception as e:
                print(f'[VoiceInterface] finance BIS update failed: {e}')

        result['meeting_type']  = meeting_type
        result['post_action']   = post_action
        result['post_agent']    = agent
        return result

    # ─── Meeting session ──────────────────────────────────────────────────────

    def start_meeting_session(self, meeting_name: str) -> str:
        """
        Create a new meeting session. Clears any prior transcript.
        Logs meeting_start event to Neon.
        Returns session_id.
        """
        session_id = str(uuid.uuid4())
        self.clear_session()

        try:
            from state.memory.memory import AgentMemory
            mem = AgentMemory()
            mem.log_event(
                org_id=self.ctx.org_id,
                event_type='meeting_start',
                payload={
                    'session_id': session_id,
                    'meeting_name': meeting_name,
                },
            )
        except Exception as e:
            print(f'[VoiceInterface] meeting_start log failed: {e}')

        return session_id

    def process_meeting_audio(
        self,
        audio_path: str,
        session_id: str,
    ) -> dict:
        """
        Transcribe an audio chunk and add to session transcript.
        Does NOT synthesize a response — capture only.

        Returns:
            {transcript: str, session_id: str}
        """
        transcript = self.processor._local_transcribe(audio_path)
        self._session_transcript.append({
            'role': 'meeting',
            'text': transcript,
            'session_id': session_id,
            'ts': time.time(),
        })
        return {
            'transcript': transcript,
            'session_id': session_id,
        }

    def end_meeting_session(self, session_id: str) -> dict:
        """
        Analyze the full session transcript via CognitiveLoop ANALYZE.
        Logs the meeting to Neon as interaction type 'meeting'.
        Creates tasks in Neon for all action items via CoordinationEngine.

        Returns:
            {
                summary: str,
                decisions: list[str],
                action_items: list[dict],
                next_steps: list[str],
            }
        """
        full_text = '\n'.join(
            entry['text']
            for entry in self._session_transcript
            if entry.get('text')
        ).strip()

        if not full_text:
            return {
                'summary': 'No transcript captured.',
                'decisions': [],
                'action_items': [],
                'next_steps': [],
            }

        prompt = (
            "Extract from this meeting transcript:\n"
            "1. Decisions made\n"
            "2. Action items with owners\n"
            "3. Key insights\n"
            "4. Open questions\n"
            "5. Next steps\n\n"
            "Format your response EXACTLY as:\n\n"
            "SUMMARY:\n[2-3 sentence summary]\n\n"
            "DECISIONS:\n- [decision 1]\n- [decision 2]\n\n"
            "ACTION ITEMS:\n- [owner]: [action]\n\n"
            "INSIGHTS:\n- [insight]\n\n"
            "OPEN QUESTIONS:\n- [question]\n\n"
            "NEXT STEPS:\n- [step]\n\n"
            f"TRANSCRIPT:\n{full_text[:4000]}"
        )

        cognitive_result = self.loop.run(
            input=prompt,
            agent='ceo_agent',
            task_type=TaskType.ANALYZE,
            venture_id='lyfe_institute',
        )

        output = cognitive_result.output or ''

        # Parse structured sections from output
        summary       = self._extract_section(output, 'SUMMARY')
        decisions     = self._extract_list(output, 'DECISIONS')
        action_raw    = self._extract_list(output, 'ACTION ITEMS')
        next_steps    = self._extract_list(output, 'NEXT STEPS')

        # Normalise action items to {owner, action} dicts
        action_items: list[dict] = []
        for item in action_raw:
            if ':' in item:
                owner, action = item.split(':', 1)
                action_items.append({
                    'owner':  owner.strip().lstrip('- '),
                    'action': action.strip(),
                })
            else:
                action_items.append({'owner': 'unassigned', 'action': item.strip()})

        # Log to Neon as 'meeting' event
        try:
            from state.memory.memory import AgentMemory
            mem = AgentMemory()
            mem.log_event(
                org_id=self.ctx.org_id,
                event_type='meeting',
                payload={
                    'session_id':     session_id,
                    'summary':        summary,
                    'decisions':      decisions,
                    'action_items':   action_items,
                    'next_steps':     next_steps,
                    'interaction_id': cognitive_result.interaction_id,
                },
            )
        except Exception as e:
            print(f'[VoiceInterface] meeting log failed: {e}')

        # Create tasks in Neon for all action items via CoordinationEngine
        if action_items:
            try:
                from runtime.coordination_engine import CoordinationEngine
                ce = CoordinationEngine(self.ctx)
                action_text = '\n'.join(
                    f"- {a['owner']}: {a['action']}"
                    for a in action_items
                )
                ce.ceo_delegate(
                    company_objective=(
                        f"Action items from meeting session {session_id[:8]}:\n"
                        f"{action_text}"
                    ),
                    venture_id='lyfe_institute',
                )
            except Exception as e:
                print(f'[VoiceInterface] task creation failed: {e}')

        return {
            'summary':      summary,
            'decisions':    decisions,
            'action_items': action_items,
            'next_steps':   next_steps,
        }

    # ─── Session management ───────────────────────────────────────────────────

    def get_session_transcript(self) -> list[dict]:
        return self._session_transcript

    def clear_session(self) -> None:
        self._session_transcript = []

    # ─── Private: parsing helpers ─────────────────────────────────────────────

    def _extract_section(self, text: str, section: str) -> str:
        """Extract the content block under a named section header."""
        pattern = (
            rf'{re.escape(section)}[:\s]*\n(.*?)'
            rf'(?=\n[A-Z][A-Z ]+[:\n]|─{{3,}}|$)'
        )
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Fallback: section header inline with content
        pattern2 = rf'{re.escape(section)}:\s*(.+?)(?=\n[A-Z][A-Z ]+:|$)'
        match2 = re.search(pattern2, text, re.DOTALL | re.IGNORECASE)
        if match2:
            return match2.group(1).strip()
        return ''

    def _extract_list(self, text: str, section: str) -> list[str]:
        """Return list of items from a named section."""
        block = self._extract_section(text, section)
        if not block:
            return []
        items = []
        for line in block.split('\n'):
            line = re.sub(r'^[\-•\*]\s*', '', line.strip())
            if line:
                items.append(line)
        return items
