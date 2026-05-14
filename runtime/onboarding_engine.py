"""
OnboardingEngine — conversational onboarding for new EOS founders.

A new founder runs !onboard in Discord. DEX asks 15 questions across
6 topic areas. When all questions are answered the engine:
  1. Uses the LLM to extract structured business data from free-form answers
  2. Creates the BusinessInstance (BIS) in Neon via create_from_wizard()
  3. Generates a personalised EA soul doc
  Discord structure provisioning is handled by the caller (discord_bot.py).

Session state is held in a module-level dict so it survives across
multiple on_message calls within a single container lifetime.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



# ─── Session state ────────────────────────────────────────────────────────────

class OnboardingStep(Enum):
    WELCOME         = 'welcome'
    FOUNDER_PROFILE = 'founder_profile'
    COMPANY_BASICS  = 'company_basics'
    OFFER_ICP       = 'offer_icp'
    CHANNEL_STAGE   = 'channel_stage'
    NORTH_STAR      = 'north_star'
    AI_SETUP        = 'ai_setup'
    PROVISIONING    = 'provisioning'
    COMPLETE        = 'complete'


@dataclass
class OnboardingSession:
    org_id:           str
    user_id:          str
    current_step:     OnboardingStep = OnboardingStep.WELCOME
    answers:          dict           = field(default_factory=dict)
    started_at:       datetime       = field(default_factory=datetime.now)
    completed:        bool           = False
    pending_question: str            = ''   # last question asked
    question_index:   int            = 0    # index within current step


# Module-level session store — persists across on_message calls
_SESSIONS: dict[str, OnboardingSession] = {}


# ─── OnboardingEngine ─────────────────────────────────────────────────────────

class OnboardingEngine:

    QUESTIONS: dict[OnboardingStep, list[str]] = {
        OnboardingStep.FOUNDER_PROFILE: [
            'What is your name?',
            'What is your role or title?',
            'What timezone are you in?',
        ],
        OnboardingStep.COMPANY_BASICS: [
            'What is your company name?',
            'What type of business is it? (coaching, agency, SaaS, ecommerce, content, other)',
            'Describe what you do in one sentence.',
        ],
        OnboardingStep.OFFER_ICP: [
            'What is your primary offer? (what do you sell and at what price?)',
            'Who is your ideal customer? (be specific — age, situation, pain point)',
        ],
        OnboardingStep.CHANNEL_STAGE: [
            'What channel are you using to find customers? '
            '(Instagram DMs, LinkedIn, cold email, referrals, content, ads, other)',
            'How many paying customers do you have right now?',
            'What is your current monthly revenue?',
        ],
        OnboardingStep.NORTH_STAR: [
            'What is your revenue goal for the next 12 months?',
            'What is the ONE thing that would change everything for your business right now?',
        ],
        OnboardingStep.AI_SETUP: [
            'What should your AI assistant be named?',
            'How do you prefer to communicate? (direct/blunt, coaching/questions, analytical/data-driven)',
        ],
    }

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    # ── Session management ────────────────────────────────────────────────────

    def start_session(self, org_id: str, user_id: str) -> OnboardingSession:
        session = OnboardingSession(org_id=org_id, user_id=user_id)
        _SESSIONS[org_id] = session
        return session

    def get_session(self, org_id: str) -> Optional[OnboardingSession]:
        return _SESSIONS.get(org_id)

    def clear_session(self, org_id: str) -> None:
        _SESSIONS.pop(org_id, None)

    # ── Messaging ─────────────────────────────────────────────────────────────

    def get_welcome_message(self) -> str:
        return (
            '**Welcome to EntrepreneurOS.**\n\n'
            'I am going to ask you a few questions to set up your operating system. '
            'This takes about 5 minutes.\n\n'
            'Be specific — the more context you give me, the better I can serve you.\n\n'
            'Let\'s start.'
        )

    # ── Question flow ─────────────────────────────────────────────────────────

    def get_next_question(self, session: OnboardingSession) -> Optional[str]:
        """
        Return the next question to ask, advancing steps as needed.
        Returns None when all questions are answered (triggers provisioning).
        Sets session.pending_question to the returned question.
        """
        steps = list(OnboardingStep)

        while True:
            step = session.current_step

            if step in (OnboardingStep.PROVISIONING, OnboardingStep.COMPLETE):
                return None

            questions = self.QUESTIONS.get(step, [])

            if session.question_index < len(questions):
                q = questions[session.question_index]
                session.pending_question = q
                return q

            # Advance to next step
            idx = steps.index(step)
            if idx + 1 >= len(steps):
                return None

            session.current_step   = steps[idx + 1]
            session.question_index = 0

    def store_answer(self, session: OnboardingSession, answer: str) -> None:
        """Store the answer to session.pending_question and advance index."""
        if not session.pending_question:
            return
        key = f'{session.current_step.value}_{session.question_index}'
        session.answers[key] = {
            'question': session.pending_question,
            'answer':   answer,
        }
        session.question_index  += 1
        session.pending_question = ''

    # ── Provisioning ──────────────────────────────────────────────────────────

    async def analyze_and_provision(
        self,
        session: OnboardingSession,
    ) -> dict:
        """
        AI analyses all answers and provisions the complete system.

        Returns:
            {
                'data':    dict  — structured business data extracted by LLM
                'stage':   int   — determined stage (1-6)
                'results': dict  — provisioning step → 'created' | 'error: ...'
            }

        Discord structure provisioning is intentionally left to the caller
        to avoid a circular import between this module and discord_bot.py.
        """
        # Build context string from all answers
        all_answers = '\n'.join(
            f'Q: {v["question"]}\nA: {v["answer"]}'
            for v in session.answers.values()
        )

        # ── Step 1: LLM extracts structured data ─────────────────────────────
        data: dict = {}
        try:
            from execution.runtime.agent_runtime import AgentRuntime, TaskType

            rt     = AgentRuntime(self.ctx)
            loop   = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: rt.run(
                    task_type=TaskType.ANALYZE,
                    prompt=(
                        f'Analyze these onboarding answers and extract structured data.\n\n'
                        f'{all_answers}\n\n'
                        f'Return valid JSON only — no commentary:\n'
                        f'{{\n'
                        f'  "founder_name": "",\n'
                        f'  "company_name": "",\n'
                        f'  "company_type": "",\n'
                        f'  "offer_name": "",\n'
                        f'  "offer_price": 0,\n'
                        f'  "icp_description": "",\n'
                        f'  "primary_channel": "",\n'
                        f'  "current_revenue": 0,\n'
                        f'  "client_count": 0,\n'
                        f'  "north_star": "",\n'
                        f'  "ai_name": "",\n'
                        f'  "communication_style": "",\n'
                        f'  "biggest_constraint": ""\n'
                        f'}}'
                    ),
                    agent='executive_assistant',
                    max_tokens=500,
                ),
            )
            output = result.output or '{}'
            match  = re.search(r'\{.*\}', output, re.DOTALL)
            if match:
                data = json.loads(match.group(), strict=False)
        except Exception as e:
            print(f'[Onboarding] LLM analysis failed: {e}')

        # ── Stage determination ───────────────────────────────────────────────
        revenue = float(data.get('current_revenue', 0) or 0)
        clients = int(data.get('client_count', 0) or 0)
        if revenue > 50000:
            stage = 3
        elif revenue > 5000 or clients >= 5:
            stage = 2
        else:
            stage = 1
        data['stage'] = stage

        results: dict = {}

        # ── Step 2: Create BIS in Neon ────────────────────────────────────────
        try:
            from state.business.business_instance import BusinessInstanceManager

            bim = BusinessInstanceManager(self.ctx)

            company_slug = (
                data.get('company_name', 'new_venture')
                .lower()
                .replace(' ', '_')
                .replace('-', '_')
            )

            wizard_data = {
                'venture_id':      company_slug,
                'name':            data.get('company_name', 'New Venture'),
                'industry':        data.get('company_type', 'service'),
                'business_model':  data.get('company_type', 'service'),
                'current_stage':   stage,
                'offer_name':      data.get('offer_name', ''),
                'offer_price':     float(data.get('offer_price', 0) or 0),
                'icp_description': data.get('icp_description', ''),
                'primary_channel': data.get('primary_channel', ''),
                'monthly_revenue': revenue,
                'founder_name':    data.get('founder_name', ''),
                'north_star':      data.get('north_star', ''),
                'ai_name':         data.get('ai_name', 'DEX'),
            }

            loop = asyncio.get_event_loop()
            bis  = await loop.run_in_executor(
                None, lambda: bim.create_from_wizard(wizard_data)
            )
            results['bis'] = 'created'
            print(f'[Onboarding] BIS created: {bis.venture_id} stage={stage}')
        except Exception as e:
            results['bis'] = f'error: {e}'
            print(f'[Onboarding] BIS failed: {e}')

        # ── Step 3: Generate EA soul doc ──────────────────────────────────────
        try:
            from runtime.setup_wizard import generate_ea_soul_doc

            ai_name = data.get('ai_name', 'DEX') or 'DEX'
            soul_doc = generate_ea_soul_doc(
                ai_name=ai_name,
                founder_name=data.get('founder_name', 'Founder'),
                north_star=data.get('north_star', ''),
                current_stage=stage,
                offer_name=data.get('offer_name', ''),
                primary_channel=data.get('primary_channel', ''),
            )

            if soul_doc:
                path = Path(f'{_ROOT}/agents/{ai_name.lower()}_ea.md')
                path.write_text(soul_doc, encoding='utf-8')
                results['soul_doc'] = 'created'
                print(f'[Onboarding] Soul doc: {path}')
            else:
                results['soul_doc'] = 'error: template missing'
        except Exception as e:
            results['soul_doc'] = f'error: {e}'
            print(f'[Onboarding] Soul doc failed: {e}')

        session.completed    = True
        session.current_step = OnboardingStep.COMPLETE

        return {'data': data, 'stage': stage, 'results': results}

    # ── Completion message ────────────────────────────────────────────────────

    def get_completion_message(self, data: dict, results: dict) -> str:
        name       = data.get('founder_name', 'Founder')
        ai_name    = data.get('ai_name', 'DEX') or 'DEX'
        stage      = data.get('stage', 1)
        company    = data.get('company_name', '')
        offer      = data.get('offer_name', '')
        channel    = data.get('primary_channel', '')
        icp        = data.get('icp_description', '')
        north_star = data.get('north_star', '')

        provisioned = [k for k, v in results.items() if 'error' not in str(v)]
        failed      = [k for k, v in results.items() if 'error' in str(v)]

        lines = [
            f'**{company} is live on EOS.**',
            '',
            f'**{name}** — Stage {stage}',
            f'AI: {ai_name}',
        ]
        if offer:
            lines.append(f'Offer: {offer}')
        if channel:
            lines.append(f'Channel: {channel}')
        if icp:
            lines.append(f'ICP: {icp}')
        if north_star:
            lines.append(f'North star: {north_star}')
        lines.append('')
        lines.append(f'Provisioned: {", ".join(provisioned)}')
        if failed:
            lines.append(f'Skipped: {", ".join(failed)}')
        lines.extend([
            '',
            f'**Your operating system is running.**',
            f'Type anything to talk to {ai_name}.',
            '',
            f'— {ai_name}',
        ])

        return '\n'.join(lines)
