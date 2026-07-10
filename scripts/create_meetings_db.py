import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

token = os.getenv('NOTION_API_KEY')
PARENT_PAGE_ID = os.getenv("NOTION_ROOT_ID", "")

headers = {
    'Authorization': f'Bearer {token}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}

# Venture select options are built from the tenant's ventures (BIS) at runtime,
# never hardcoded — a fixed list would seed one tenant's ventures into every seat.
_VENTURE_COLORS = ['green', 'orange', 'purple', 'blue', 'yellow', 'pink', 'red']
def _venture_options() -> list:
    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.business.business_instance import get_ventures
        opts = []
        for i, v in enumerate(get_ventures(load_context_from_env())):
            name = v.get('name') or v.get('id', '')
            if name:
                opts.append({"name": name, "color": _VENTURE_COLORS[i % len(_VENTURE_COLORS)]})
        return opts
    except Exception:
        return []

payload = {
    "parent": {"type": "page_id", "page_id": PARENT_PAGE_ID},
    "title": [{"type": "text", "text": {"content": "Meetings"}}],
    "properties": {
        "Name": {"title": {}},
        "Person": {"rich_text": {}},
        "Email": {"email": {}},
        "Company": {"rich_text": {}},
        "Date": {"date": {}},
        "Status": {"select": {"options": [
            {"name": "Scheduled", "color": "blue"},
            {"name": "Completed", "color": "green"},
            {"name": "Cancelled", "color": "red"},
            {"name": "No-show", "color": "gray"},
        ]}},
        "Type": {"select": {"options": [
            {"name": "Discovery", "color": "purple"},
            {"name": "Sales Call", "color": "orange"},
            {"name": "Follow-up", "color": "yellow"},
            {"name": "Internal", "color": "blue"},
            {"name": "Other", "color": "gray"},
        ]}},
        "Venture": {"select": {"options": _venture_options()}},
        "Prep Notes": {"rich_text": {}},
        "Outcomes": {"rich_text": {}},
        "Open Loops": {"rich_text": {}},
        "Source": {"select": {"options": [
            {"name": "Calendly", "color": "blue"},
            {"name": "Manual", "color": "gray"},
            {"name": "Google Calendar", "color": "green"},
        ]}},
        "Meet Link": {"url": {}},
        "Calendly Event ID": {"rich_text": {}},
        "Recording Link": {"url": {}},
    }
}

if not PARENT_PAGE_ID:
    raise SystemExit('NOTION_ROOT_ID not set — cannot create Meetings DB')

resp = requests.post(
    'https://api.notion.com/v1/databases',
    headers=headers,
    json=payload,
)
result = resp.json()
db_id = result.get('id')
if db_id:
    print(f'Meetings DB created: {db_id}')
else:
    print(f'Error: {result}')
