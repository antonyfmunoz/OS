"""
Person Recognition — central module for identifying known people
across all channels: email, Discord, Calendly, Calendar.

The Martell Rule: never auto-respond to a recognized person with
a template. Route to ANTONY immediately. Flag it.
"""

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def create_lead_file(
    name: str,
    email: str = '',
    company: str = '',
    source: str = 'auto',
    venture: str = '',
    notes: str = '',
) -> str:
    """Auto-create a CRM lead file when a new person is recognized."""
    try:
        import re
        import os

        now = datetime.now(PDT)

        # Sanitize filename
        safe_name = re.sub(r'[^a-z0-9_]', '_', name.lower().replace(' ', '_'))
        filename = f'{_ROOT}/03_CRM/Leads/lead_{safe_name}.md'

        # Don't overwrite existing
        if os.path.exists(filename):
            return filename

        content = f"""# Lead: {name}

## Contact
- **Email:** {email or 'Unknown'}
- **Company:** {company or 'Unknown'}
- **Source:** {source}
- **Venture:** {venture or 'Unknown'}
- **Created:** {now.strftime('%Y-%m-%d')}

## Status
- **kanban_stage:** New
- **status:** Active

## Notes
{notes or 'Auto-created by DEX person recognition.'}

## Interaction Log
- {now.strftime('%Y-%m-%d')} — Lead created automatically via {source}
"""
        with open(filename, 'w') as f:
            f.write(content)

        logger.info(f'[PersonRecognition] Lead file created: {filename}')
        return filename
    except Exception as e:
        logger.warning(f'[PersonRecognition] create_lead_file failed: {e}')
        return ''


def recognize_person(
    name: str = '',
    email: str = '',
    ctx=None,
) -> dict:
    """
    Check if a person is known across all memory sources.

    Checks in order:
    1. Semantic memory search (recent conversations)
    2. CRM lead files (03_CRM/Leads/)
    3. Meetings database (Notion)
    4. Neon interactions/events

    Returns:
    {
        'known': bool,
        'confidence': 'high' | 'medium' | 'low',
        'sources': ['memory', 'crm', 'meetings'],
        'context': str,  # what we know about them
        'last_seen': str,  # ISO date
        'warning': str,   # if Martell rule applies
    }
    """
    try:
        from state.context.context import load_context_from_env
        ctx = ctx or load_context_from_env()

        results = {
            'known': False,
            'confidence': 'low',
            'sources': [],
            'context': '',
            'last_seen': '',
            'warning': '',
        }

        context_parts = []

        # 1. Semantic memory search
        if name or email:
            try:
                from state.memory.memory import AgentMemory
                mem = AgentMemory()
                query = f'{name} {email}'.strip()
                hits = mem.semantic_search(query=query, limit=5, min_similarity=0.5)
                if hits:
                    results['sources'].append('memory')
                    for h in hits[:3]:
                        output = str(h.get('output_summary') or '')[:200]
                        if output:
                            context_parts.append(output)
                    latest = max(
                        (str(h.get('created_at', '')) for h in hits),
                        default='',
                    )
                    if latest:
                        results['last_seen'] = latest
            except Exception as e:
                logger.warning(f'[PersonRecognition] Memory search failed: {e}')

        # 2. CRM lead files
        if name or email:
            try:
                import glob as _glob
                lead_files = _glob.glob(f'{_ROOT}/03_CRM/Leads/lead_*.md')
                name_lower = name.lower()
                email_lower = email.lower()
                for lf in lead_files:
                    with open(lf) as f:
                        content = f.read()
                    content_lower = content.lower()
                    if (name_lower and name_lower in content_lower) or \
                       (email_lower and email_lower in content_lower):
                        results['sources'].append('crm')
                        for line in content.split('\n')[:20]:
                            if any(k in line.lower() for k in ['stage', 'status', 'company', 'note']):
                                context_parts.append(line.strip())
                        break
            except Exception as e:
                logger.warning(f'[PersonRecognition] CRM search failed: {e}')

        # 3. Meetings database (Notion)
        if name or email:
            try:
                import requests
                from dotenv import load_dotenv
                load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
                token = os.getenv('NOTION_API_KEY')
                db_id = os.getenv('NOTION_MEETINGS_ID')
                if token and db_id:
                    headers = {
                        'Authorization': f'Bearer {token}',
                        'Notion-Version': '2022-06-28',
                        'Content-Type': 'application/json',
                    }
                    filter_clause: dict = {'or': []}
                    if name:
                        filter_clause['or'].append(
                            {'property': 'Person', 'rich_text': {'contains': name}}
                        )
                    if email:
                        filter_clause['or'].append(
                            {'property': 'Email', 'email': {'equals': email}}
                        )
                    if filter_clause['or']:
                        resp = requests.post(
                            f'https://api.notion.com/v1/databases/{db_id}/query',
                            headers=headers,
                            json={'filter': filter_clause, 'page_size': 5},
                            timeout=10,
                        )
                        meeting_results = resp.json().get('results', [])
                        if meeting_results:
                            results['sources'].append('meetings')
                            for m in meeting_results[:2]:
                                props = m.get('properties', {})
                                date = props.get('Date', {}).get('date', {}).get('start', '')
                                status = props.get('Status', {}).get('select', {}).get('name', '')
                                outcomes = props.get('Outcomes', {}).get('rich_text', [{}])[0].get('plain_text', '')
                                if date:
                                    context_parts.append(f'Met {date[:10]}: {status}')
                                if outcomes:
                                    context_parts.append(f'Outcome: {outcomes[:100]}')
                                if date and not results['last_seen']:
                                    results['last_seen'] = date
            except Exception as e:
                logger.warning(f'[PersonRecognition] Meetings search failed: {e}')

        # 4. Neon pipeline events
        if name or email:
            try:
                from state.storage.db import get_conn
                with get_conn(ctx.org_id) as cur:
                    cur.execute('''
                        SELECT payload_json, created_at
                        FROM events
                        WHERE org_id = %s
                          AND event_type = 'pipeline_entry'
                        ORDER BY created_at DESC
                        LIMIT 100
                    ''', (ctx.org_id,))
                    rows = cur.fetchall()
                    name_lower = name.lower()
                    email_lower = email.lower()
                    for row in rows:
                        data = row['payload_json']
                        if isinstance(data, str):
                            data = json.loads(data)
                        p_email = data.get('email', '').lower()
                        p_name = data.get('name', '').lower().strip()
                        matched = False
                        if email_lower and p_email and p_email == email_lower:
                            matched = True
                        if name_lower and p_name and len(p_name) > 5:
                            parts = p_name.split()
                            if len(parts) >= 2 and parts[0] in name_lower and parts[-1] in name_lower:
                                matched = True
                        if matched:
                            results['sources'].append('neon')
                            stage = data.get('stage', '')
                            if stage:
                                context_parts.append(f'Pipeline stage: {stage}')
                            ts = str(row.get('created_at', ''))[:10]
                            if ts and not results['last_seen']:
                                results['last_seen'] = ts
                            break
            except Exception as e:
                logger.warning(f'[PersonRecognition] Neon search failed: {e}')

        # Determine confidence
        source_count = len(set(results['sources']))
        if source_count >= 2:
            results['known'] = True
            results['confidence'] = 'high'
        elif source_count == 1:
            results['known'] = True
            results['confidence'] = 'medium'

        results['context'] = '\n'.join(context_parts[:5]) if context_parts else ''

        # Martell rule warning
        if results['known'] and results['confidence'] in ('high', 'medium'):
            results['warning'] = (
                f'⚠️ Known person: {name or email}. '
                f'Do not auto-respond with template. '
                f'Sources: {", ".join(set(results["sources"]))}.'
            )

        # Auto-create lead file for new people
        if not results['known'] and name:
            try:
                create_lead_file(
                    name=name,
                    email=email,
                    source='auto_recognition',
                )
            except Exception:
                pass

        return results

    except Exception as e:
        logger.error(f'[PersonRecognition] recognize_person failed: {e}')
        return {
            'known': False,
            'confidence': 'low',
            'sources': [],
            'context': '',
            'last_seen': '',
            'warning': '',
        }


def format_person_context(recognition: dict, name: str = '') -> str:
    """Format recognition result for injection into prompts."""
    if not recognition.get('known'):
        return ''

    lines = [f'## Known Person: {name}']
    if recognition.get('last_seen'):
        lines.append(f'Last seen: {recognition["last_seen"][:10]}')
    lines.append(f'Sources: {", ".join(set(recognition.get("sources", [])))}')
    if recognition.get('context'):
        lines.append(f'\nContext:\n{recognition["context"]}')
    if recognition.get('warning'):
        lines.append(f'\n{recognition["warning"]}')
    return '\n'.join(lines)


# ─── Human Intelligence Profile ───────────────────────────────────────────────

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HumanIntelligenceProfile:
    name: str
    email: str = ''
    company: str = ''
    role: str = ''
    communication_style: str = ''  # direct/formal/casual/analytical
    decision_style: str = ''       # fast/deliberate/consensus/data-driven
    motivations: list = field(default_factory=list)
    concerns: list = field(default_factory=list)
    preferences: list = field(default_factory=list)
    relationship_history: str = ''
    deal_stage: str = ''
    venture: str = ''
    last_contact: str = ''
    confidence: str = 'low'        # low/medium/high
    source: str = ''
    notes: str = ''


def build_intelligence_profile(
    name: str,
    email: str = '',
    company: str = '',
    ctx=None,
) -> HumanIntelligenceProfile:
    """
    Build a full human intelligence profile by aggregating
    all available data sources and using LLM to synthesize.
    """
    try:
        from state.context.context import load_context_from_env
        ctx = ctx or load_context_from_env()

        profile = HumanIntelligenceProfile(name=name, email=email, company=company)

        # 1. Run base recognition
        recognition = recognize_person(name=name, email=email, ctx=ctx)
        profile.confidence = recognition.get('confidence', 'low')
        profile.last_contact = recognition.get('last_seen', '')
        raw_context = recognition.get('context', '')

        # 2. Pull meeting history from Notion
        try:
            import requests as _req
            from dotenv import load_dotenv
            load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
            token = os.getenv('NOTION_API_KEY')
            db_id = os.getenv('NOTION_MEETINGS_ID')
            if token and db_id:
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Notion-Version': '2022-06-28',
                    'Content-Type': 'application/json',
                }
                filter_clause: dict = {'or': []}
                if name:
                    filter_clause['or'].append(
                        {'property': 'Person', 'rich_text': {'contains': name}}
                    )
                if email:
                    filter_clause['or'].append(
                        {'property': 'Email', 'email': {'equals': email}}
                    )
                if filter_clause['or']:
                    resp = _req.post(
                        f'https://api.notion.com/v1/databases/{db_id}/query',
                        headers=headers,
                        json={'filter': filter_clause, 'page_size': 10},
                        timeout=10,
                    )
                    meetings = resp.json().get('results', [])
                    history_parts = []
                    for m in meetings:
                        props = m.get('properties', {})
                        date = props.get('Date', {}).get('date', {}).get('start', '')
                        status = props.get('Status', {}).get('select', {}).get('name', '')
                        outcomes_list = props.get('Outcomes', {}).get('rich_text', [])
                        outcomes = outcomes_list[0].get('plain_text', '') if outcomes_list else ''
                        venture = props.get('Venture', {}).get('select', {}).get('name', '')
                        if date:
                            history_parts.append(f'{date[:10]}: {status} — {outcomes[:100]}')
                        if venture and not profile.venture:
                            profile.venture = venture
                    profile.relationship_history = '\n'.join(history_parts)
        except Exception as e:
            logger.warning(f'[PersonRecognition] Meeting history failed: {e}')

        # 3. LLM synthesis from all available context
        if raw_context or profile.relationship_history:
            try:
                from execution.runtime.model_router import get_router, TaskType
                router = get_router()
                model = router.route(TaskType.ANALYSIS)

                synthesis_prompt = (
                    f'You are DEX, EA to Antony Munoz.\n'
                    f'Build a human intelligence profile for {name} based on all available context.\n\n'
                    f'Available context:\n{raw_context}\n\n'
                    f'Meeting history:\n{profile.relationship_history}\n\n'
                    f'Return JSON only:\n'
                    f'{{\n'
                    f'  "communication_style": "direct|formal|casual|analytical|unknown",\n'
                    f'  "decision_style": "fast|deliberate|consensus|data-driven|unknown",\n'
                    f'  "motivations": ["list", "of", "key", "motivations"],\n'
                    f'  "concerns": ["list", "of", "likely", "concerns"],\n'
                    f'  "preferences": ["list", "of", "known", "preferences"],\n'
                    f'  "deal_stage": "current deal stage if applicable",\n'
                    f'  "notes": "key insight for Antony in one sentence"\n'
                    f'}}'
                )

                result = router.call(model, synthesis_prompt).strip()
                if '```' in result:
                    result = result.split('```')[1].replace('json', '').strip()
                import json as _json
                synthesized = _json.loads(result)
                profile.communication_style = synthesized.get('communication_style', '')
                profile.decision_style = synthesized.get('decision_style', '')
                profile.motivations = synthesized.get('motivations', [])
                profile.concerns = synthesized.get('concerns', [])
                profile.preferences = synthesized.get('preferences', [])
                profile.deal_stage = synthesized.get('deal_stage', '')
                profile.notes = synthesized.get('notes', '')
            except Exception as e:
                logger.warning(f'[PersonRecognition] LLM synthesis failed: {e}')

        # 4. Append intelligence profile section to lead file if it exists
        try:
            import glob as _glob
            safe_name = name.lower().replace(' ', '_')
            lead_files = _glob.glob(f'{_ROOT}/03_CRM/Leads/lead_{safe_name}*.md')
            if lead_files:
                lf = lead_files[0]
                with open(lf) as f:
                    content = f.read()
                if '## Intelligence Profile' not in content:
                    profile_section = (
                        f'\n## Intelligence Profile\n'
                        f'- **Communication Style:** {profile.communication_style}\n'
                        f'- **Decision Style:** {profile.decision_style}\n'
                        f'- **Motivations:** {", ".join(profile.motivations)}\n'
                        f'- **Concerns:** {", ".join(profile.concerns)}\n'
                        f'- **Deal Stage:** {profile.deal_stage}\n'
                        f'- **Key Insight:** {profile.notes}\n'
                        f'- **Last Updated:** {datetime.now(PDT).strftime("%Y-%m-%d")}\n'
                    )
                    with open(lf, 'a') as f:
                        f.write(profile_section)
        except Exception as e:
            logger.warning(f'[PersonRecognition] Lead file update failed: {e}')

        return profile

    except Exception as e:
        logger.error(f'[PersonRecognition] build_intelligence_profile failed: {e}')
        return HumanIntelligenceProfile(name=name, email=email, company=company)


def format_intelligence_profile(profile: HumanIntelligenceProfile) -> str:
    """Format profile for injection into prompts and Discord."""
    lines = [f'**Intelligence Profile: {profile.name}**']
    if profile.company:
        lines.append(f'🏢 {profile.company}')
    if profile.communication_style and profile.communication_style != 'unknown':
        lines.append(f'💬 Communication: {profile.communication_style}')
    if profile.decision_style and profile.decision_style != 'unknown':
        lines.append(f'🧠 Decision style: {profile.decision_style}')
    if profile.motivations:
        lines.append(f'🎯 Motivated by: {", ".join(profile.motivations[:3])}')
    if profile.concerns:
        lines.append(f'⚠️ Concerns: {", ".join(profile.concerns[:2])}')
    if profile.deal_stage:
        lines.append(f'📊 Stage: {profile.deal_stage}')
    if profile.notes:
        lines.append(f'💡 {profile.notes}')
    if profile.relationship_history:
        lines.append(f'\n**History:**\n{profile.relationship_history[:300]}')
    return '\n'.join(lines)


def score_relationship_health(
    name: str,
    email: str = '',
    ctx=None,
) -> dict:
    """
    Score relationship health for a contact.

    Factors: days since last contact, meetings, no-shows, outcomes.
    Returns score 0-1 and status label.
    """
    try:
        import requests as _req
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
        from state.context.context import load_context_from_env
        ctx = ctx or load_context_from_env()

        now = datetime.now(PDT)
        score = 0.5
        factors = []

        token = os.getenv('NOTION_API_KEY')
        db_id = os.getenv('NOTION_MEETINGS_ID')
        meetings = []

        if token and db_id:
            headers = {
                'Authorization': f'Bearer {token}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json',
            }
            filter_clause: dict = {'or': []}
            if name:
                filter_clause['or'].append(
                    {'property': 'Person', 'rich_text': {'contains': name}}
                )
            if email:
                filter_clause['or'].append(
                    {'property': 'Email', 'email': {'equals': email}}
                )
            if filter_clause['or']:
                resp = _req.post(
                    f'https://api.notion.com/v1/databases/{db_id}/query',
                    headers=headers,
                    json={'filter': filter_clause, 'page_size': 10},
                    timeout=10,
                )
                meetings = resp.json().get('results', [])

        total_meetings = len(meetings)
        completed = sum(
            1 for m in meetings
            if m.get('properties', {}).get('Status', {})
               .get('select', {}).get('name') == 'Completed'
        )
        no_shows = sum(
            1 for m in meetings
            if m.get('properties', {}).get('Status', {})
               .get('select', {}).get('name') == 'No-show'
        )

        last_contact_date = None
        for m in meetings:
            date_str = (
                m.get('properties', {})
                 .get('Date', {})
                 .get('date', {})
                 .get('start', '')
            )
            if date_str:
                try:
                    dt = datetime.fromisoformat(date_str).replace(tzinfo=PDT)
                    if last_contact_date is None or dt > last_contact_date:
                        last_contact_date = dt
                except Exception:
                    pass

        days_since = (now - last_contact_date).days if last_contact_date else 999

        if days_since <= 7:
            score += 0.2
            factors.append('Recent contact')
        elif days_since <= 30:
            score += 0.1
            factors.append('Active')
        elif days_since <= 60:
            score -= 0.1
            factors.append('Going cold')
        else:
            score -= 0.2
            factors.append('Cold')

        if total_meetings >= 3:
            score += 0.1
            factors.append('Multiple touchpoints')
        if no_shows > 0:
            score -= 0.1 * no_shows
            factors.append(f'{no_shows} no-show(s)')
        if completed > 0:
            score += 0.05 * min(completed, 3)

        score = max(0.0, min(1.0, score))

        if score >= 0.7:
            status = 'Strong'
        elif score >= 0.5:
            status = 'Active'
        elif score >= 0.3:
            status = 'At risk'
        else:
            status = 'Cold'

        return {
            'score': round(score, 2),
            'status': status,
            'days_since_contact': days_since,
            'total_meetings': total_meetings,
            'completed_meetings': completed,
            'no_shows': no_shows,
            'factors': factors,
            'last_contact': last_contact_date.strftime('%Y-%m-%d') if last_contact_date else 'Never',
        }
    except Exception as e:
        logger.warning(f'[PersonRecognition] score_relationship_health failed: {e}')
        return {'score': 0.5, 'status': 'Unknown', 'factors': []}
