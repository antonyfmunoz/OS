"""
Notion → Neon Outcome Sync
Polls the Notion Pipeline database for stage changes and fires
log_standalone_outcome() into Neon when a lead reaches a terminal stage.

Run on a schedule — every 15 minutes via cron or nightly_maintenance.sh.

Terminal stages:
  Booked → positive outcome (call scheduled)
  Won    → positive outcome (deal closed)
  Lost   → negative outcome (deal lost)

Non-terminal stages (New Lead, Contacted, Replied, Qualifying) are ignored.
"""

import sys
import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')

NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_PIPELINE_ID = os.getenv('NOTION_LYFE_PIPELINE_ID')
STATE_FILE = Path('/opt/OS/scripts/notion_sync_state.json')

TERMINAL_STAGES = {
    'Booked': 'booked',
    'Won':    'closed',
    'Lost':   'lost',
}

HEADERS = {
    'Authorization': f'Bearer {NOTION_API_KEY}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}


def load_state() -> dict:
    """Load last sync state — tracks which page IDs we've already processed."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'processed': {}, 'last_sync': None}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def query_pipeline() -> list:
    """Fetch all pages from the Notion Pipeline database."""
    results = []
    has_more = True
    cursor = None

    while has_more:
        payload = {'page_size': 100}
        if cursor:
            payload['start_cursor'] = cursor

        resp = requests.post(
            f'https://api.notion.com/v1/databases/{NOTION_PIPELINE_ID}/query',
            headers=HEADERS,
            json=payload,
            timeout=15,
        )

        if resp.status_code != 200:
            print(f'[Notion Sync] Query failed: {resp.status_code} {resp.text}')
            break

        data = resp.json()
        results.extend(data.get('results', []))
        has_more = data.get('has_more', False)
        cursor = data.get('next_cursor')

    return results


def extract_page_data(page: dict) -> dict:
    """Extract relevant fields from a Notion page."""
    props = page.get('properties', {})

    # Name
    name_prop = props.get('Name', {})
    title_list = name_prop.get('title', [])
    name = title_list[0]['text']['content'] if title_list else 'Unknown'

    # Stage
    stage_prop = props.get('Stage', {})
    stage = stage_prop.get('select', {})
    stage_name = stage.get('name') if stage else None

    # Score
    score_prop = props.get('Score', {})
    score = score_prop.get('number')

    # Archetype
    archetype_prop = props.get('Archetype', {})
    archetype_list = archetype_prop.get('rich_text', [])
    archetype = archetype_list[0]['text']['content'] if archetype_list else None

    # Channel
    channel_prop = props.get('Channel', {})
    channel = channel_prop.get('select', {})
    channel_name = channel.get('name') if channel else None

    return {
        'page_id': page['id'],
        'last_edited': page['last_edited_time'],
        'name': name,
        'stage': stage_name,
        'score': score,
        'archetype': archetype,
        'channel': channel_name,
    }


def fire_outcome(page_data: dict, outcome_type: str):
    """Log outcome signal to Neon via AgentMemory."""
    try:
        from eos_ai.memory import AgentMemory
        mem = AgentMemory()
        mem.log_standalone_outcome(
            outcome_type=outcome_type,
            score=float(page_data['score']) if page_data['score'] is not None else None,
            notes=f"Lead {page_data['name']} reached stage {page_data['stage']} | archetype={page_data['archetype']} channel={page_data['channel']}",
            source='notion_pipeline_sync',
        )
        print(f"  [Outcome] {outcome_type} — {page_data['name']} → {page_data['stage']}")
        return True
    except Exception as e:
        print(f"  [Outcome] Failed for {page_data['name']}: {e}")
        return False


def run_sync():
    print(f"\n[Notion Sync] Starting — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    state = load_state()
    processed = state.get('processed', {})

    pages = query_pipeline()
    print(f"  Found {len(pages)} pages in pipeline")

    new_outcomes = 0
    for page in pages:
        data = extract_page_data(page)
        page_id = data['page_id']
        stage = data['stage']

        if not stage:
            continue

        # Check if this is a terminal stage
        outcome_type = TERMINAL_STAGES.get(stage)
        if not outcome_type:
            continue

        # Check if we already processed this page at this stage
        prev = processed.get(page_id, {})
        if prev.get('stage') == stage:
            # Already logged this outcome — skip
            continue

        # New terminal stage — fire outcome
        success = fire_outcome(data, outcome_type)
        if success:
            processed[page_id] = {
                'stage': stage,
                'outcome': outcome_type,
                'fired_at': datetime.now(timezone.utc).isoformat(),
                'lead_name': data['name'],
            }
            new_outcomes += 1

    state['processed'] = processed
    state['last_sync'] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    print(f"  New outcomes fired: {new_outcomes}")
    print(f"  Total tracked: {len(processed)}")
    print(f"[Notion Sync] Done\n")
    return new_outcomes


if __name__ == '__main__':
    run_sync()
