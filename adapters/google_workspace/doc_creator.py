"""
Document Creator — generates briefing docs, board updates,
investor updates, proposals, and presentation outlines using
LLM + Google Drive.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def create_briefing_doc(
    title: str,
    topic: str,
    context: str = '',
    audience: str = 'Antony',
    doc_type: str = 'briefing',
    ctx=None,
) -> dict:
    """
    Generate a briefing document using LLM and save to Google Drive.
    doc_type: briefing | board_update | investor_update | proposal
    Returns dict with content, drive_file, title, type.
    """
    try:
        from substrate.execution.runtime.model_router import get_router, TaskType
        from adapters.google_workspace.gws_connector import GWSConnector
        router = get_router()

        templates = {
            'briefing': f"""Create a concise executive briefing document.

Title: {title}
Topic: {topic}
Context: {context}
Audience: {audience}

Format:
# {title}
**Date:** {datetime.now(PDT).strftime('%B %d, %Y')}
**Prepared by:** DEX

## Executive Summary
[2-3 sentence summary]

## Background
[Context and relevance]

## Key Points
[3-5 bullet points]

## Recommendations
[1-3 specific actions]

## Next Steps
[What needs to happen and by when]

Keep it under 400 words. Direct. No fluff.""",

            'board_update': f"""Create a board update document.

Company context: Munoz Conglomerate — Lyfe Institute,
Empyrean Creative, Personal Brand
Topic: {topic}
Context: {context}

Format:
# Board Update — {datetime.now(PDT).strftime('%B %Y')}

## Performance Highlights
[Key metrics and wins]

## Portfolio Status
[Each venture: status, revenue, key metric]

## Challenges & Risks
[Top 3 challenges]

## Strategic Priorities
[Next 90 days focus]

## Asks from the Board
[What support is needed]

Keep it under 500 words. Numbers over narrative.""",

            'investor_update': f"""Create a monthly investor update.

Context: {context}
Topic: {topic}

Format:
# Investor Update — {datetime.now(PDT).strftime('%B %Y')}

## The One-Line Summary
[What happened this month in one sentence]

## Progress
[What moved forward]

## Revenue
[Numbers]

## Key Learnings
[What you learned]

## Ask
[What you need from investors/network]

## Next Month
[What you're focused on]

Keep it conversational and honest. Under 400 words.""",

            'proposal': f"""Create a business proposal.

Title: {title}
Topic: {topic}
Context: {context}
Audience: {audience}

Format:
# {title}

## The Situation
[Problem or opportunity]

## Our Solution
[What we're proposing]

## How It Works
[Process/approach]

## Investment
[Pricing and terms]

## Why Us
[Credibility and fit]

## Next Steps
[Call to action]

Keep it under 500 words. Client-facing quality.""",
        }

        prompt = templates.get(doc_type, templates['briefing'])
        content = router.call_with_fallback(TaskType.ANALYSIS, prompt).strip()

        # Save to Google Drive
        gws = GWSConnector()
        drive_result = gws.create_document(
            title=f'{title} — {datetime.now(PDT).strftime("%Y-%m-%d")}',
            content=content,
        )

        # Log to Neon
        try:
            from substrate.state.context.context import load_context_from_env
            from substrate.state.memory.memory import AgentMemory
            ctx = ctx or load_context_from_env()
            AgentMemory().log_event(
                org_id=str(ctx.org_id),
                event_type='document_created',
                payload={
                    'title': title,
                    'type': doc_type,
                    'drive_id': drive_result.get('id', ''),
                    'created_at': datetime.now(PDT).isoformat(),
                },
                handled_by='dex_doc_creator',
            )
        except Exception:
            pass

        return {
            'content': content,
            'drive_file': drive_result,
            'title': title,
            'type': doc_type,
        }
    except Exception as e:
        logger.warning(f'[DocCreator] create_briefing_doc failed: {e}')
        return {'content': '', 'error': str(e)}


def create_presentation_outline(
    title: str,
    topic: str,
    slides: int = 10,
    audience: str = '',
    ctx=None,
) -> dict:
    """
    Generate a presentation outline with slide content.
    Returns dict with slides (structured data) and drive_file.
    """
    try:
        from substrate.execution.runtime.model_router import get_router, TaskType
        from adapters.google_workspace.gws_connector import GWSConnector
        import json as _json
        router = get_router()

        raw = router.call_with_fallback(TaskType.ANALYSIS, f"""Create a {slides}-slide presentation outline.

Title: {title}
Topic: {topic}
Audience: {audience or 'Business audience'}

For each slide provide:
- Slide number
- Title
- Key message (one sentence)
- 3 bullet points max
- Speaker note (what to say)

Format as JSON:
{{
  "presentation_title": "{title}",
  "slides": [
    {{
      "number": 1,
      "title": "slide title",
      "key_message": "one sentence",
      "bullets": ["point 1", "point 2", "point 3"],
      "speaker_note": "what to say"
    }}
  ]
}}""").strip()

        if '```' in raw:
            raw = raw.split('```')[1].replace('json', '').strip()

        slides_data = _json.loads(raw)

        # Build doc content for Drive
        doc_content = f'# {title}\n\n'
        for slide in slides_data.get('slides', []):
            doc_content += f'## Slide {slide["number"]}: {slide["title"]}\n'
            doc_content += f'**Key message:** {slide["key_message"]}\n\n'
            for bullet in slide.get('bullets', []):
                doc_content += f'- {bullet}\n'
            doc_content += f'\n*Speaker note: {slide.get("speaker_note", "")}*\n\n'

        gws = GWSConnector()
        drive_result = gws.create_document(
            title=f'{title} — Presentation Outline',
            content=doc_content,
        )

        return {
            'slides': slides_data,
            'drive_file': drive_result,
            'slide_count': len(slides_data.get('slides', [])),
        }
    except Exception as e:
        logger.warning(f'[DocCreator] create_presentation_outline failed: {e}')
        return {'slides': {}, 'error': str(e)}


def fact_check(claim: str, ctx=None) -> dict:
    """
    Fact-check a claim using LLM knowledge.
    Returns dict with verdict, explanation, confidence, verify.
    """
    try:
        from substrate.execution.runtime.model_router import get_router, TaskType
        import json as _json
        router = get_router()

        raw = router.call_with_fallback(TaskType.ANALYSIS, f"""Fact-check this claim.

Claim: {claim}

Return JSON only:
{{"verdict": "TRUE|FALSE|PARTIALLY TRUE|UNVERIFIABLE",
  "explanation": "why",
  "confidence": "high|medium|low",
  "verify": ["thing to check 1", "thing to check 2"]}}""").strip()

        if '```' in raw:
            raw = raw.split('```')[1].replace('json', '').strip()
        return _json.loads(raw)
    except Exception as e:
        return {'verdict': 'UNVERIFIABLE', 'explanation': str(e), 'confidence': 'low', 'verify': []}


def draft_announcement(
    topic: str,
    audience: str,
    key_message: str,
    context: str = '',
    announcement_type: str = 'internal',
    ctx=None,
) -> str:
    """
    Draft an announcement or memo.
    announcement_type: internal|team|public|press_release
    """
    try:
        from substrate.execution.runtime.model_router import get_router, TaskType
        router = get_router()

        templates = {
            'internal': 'internal team announcement',
            'team': 'team memo',
            'public': 'public announcement',
            'press_release': 'press release',
        }

        return router.call_with_fallback(TaskType.FAST_RESPONSE, f"""Draft a {templates.get(announcement_type, 'announcement')}.

Topic: {topic}
Audience: {audience}
Key message: {key_message}
Context: {context}
Author: Antony Munoz

Voice: direct, warm, clear. No corporate speak.
Include: what's happening, why it matters, what people need to do or know.
Keep it concise and actionable. Format appropriately for the type.""").strip()
    except Exception as e:
        return f'Announcement draft unavailable: {e}'


def draft_crisis_communication(
    situation: str,
    affected_parties: str,
    what_happened: str,
    what_we_are_doing: str,
    ctx=None,
) -> str:
    """Draft crisis communication following acknowledge-factual-action structure."""
    try:
        from substrate.execution.runtime.model_router import get_router, TaskType
        router = get_router()

        return router.call_with_fallback(TaskType.FAST_RESPONSE, f"""Draft a crisis communication.

Situation: {situation}
Affected parties: {affected_parties}
What happened: {what_happened}
What we are doing: {what_we_are_doing}

Guidelines:
1. Acknowledge first — no deflection
2. Be factual — no speculation
3. State what you know and what you don't know
4. State concrete next steps with timeline
5. Provide contact for questions
6. Antony's voice — direct, accountable, calm

Format:
Subject: [clear subject line]

[Body — structured, under 200 words]

[Antony Munoz]""").strip()
    except Exception as e:
        return f'Crisis communication unavailable: {e}'
