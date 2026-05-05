import os
import requests
from dotenv import load_dotenv

load_dotenv('/opt/OS/eos_ai/.env')
load_dotenv('/opt/OS/services/.env')

token = os.getenv('NOTION_API_KEY')

headers = {
    'Authorization': f'Bearer {token}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}

payload = {
    "parent": {"type": "page_id", "page_id": "32eda8b9-6e4f-8071-b299-fef02dcb1b8c"},
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
        "Venture": {"select": {"options": [
            {"name": "Lyfe Institute", "color": "green"},
            {"name": "Empyrean Creative", "color": "orange"},
            {"name": "Personal Brand", "color": "purple"},
        ]}},
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
