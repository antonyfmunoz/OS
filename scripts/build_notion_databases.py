"""Create the 9 databases that failed in the first build pass."""
import sys
sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')

from notion_client import Client
import os

client = Client(auth=os.getenv('NOTION_API_KEY'))

company_ids = {
    'Empyrean Creative': os.getenv('NOTION_EMPYREAN_CREATIVE_ID'),
    'Lyfe Institute':    os.getenv('NOTION_LYFE_INSTITUTE_ID'),
    'Personal Brand':    os.getenv('NOTION_PERSONAL_BRAND_ID'),
}


def create_database(parent_id, title, icon='', properties=None):
    try:
        kwargs = {
            'parent': {'type': 'page_id', 'page_id': parent_id},
            'title': [{'type': 'text', 'text': {'content': title}}],
            'properties': properties or {'Name': {'title': {}}},
        }
        if icon:
            kwargs['icon'] = {'type': 'emoji', 'emoji': icon}
        result = client.databases.create(**kwargs)
        print(f'  ✅ DB: {title}: {result["id"]}')
        return result['id']
    except Exception as e:
        print(f'  ❌ DB: {title}: {e}')
        return None


for company_name, company_id in company_ids.items():
    if not company_id:
        print(f'❌ No ID for {company_name}')
        continue
    print(f'\nBuilding databases for {company_name}...')

    create_database(
        company_id, '⚙️ Workflows', icon='⚙️',
        properties={
            'Name': {'title': {}},
            'Status': {'select': {'options': [
                {'name': 'Draft', 'color': 'gray'},
                {'name': 'Active', 'color': 'green'},
                {'name': 'Paused', 'color': 'yellow'},
                {'name': 'Completed', 'color': 'blue'},
            ]}},
            'Department': {'select': {'options': [
                {'name': 'Sales', 'color': 'red'},
                {'name': 'Marketing', 'color': 'pink'},
                {'name': 'Operations', 'color': 'orange'},
                {'name': 'Product', 'color': 'purple'},
            ]}},
            'AI Assisted': {'checkbox': {}},
            'Steps': {'number': {}},
            'Owner': {'rich_text': {}},
            'Last Run': {'date': {}},
        }
    )

    create_database(
        company_id, '✅ Tasks', icon='✅',
        properties={
            'Name': {'title': {}},
            'Status': {'select': {'options': [
                {'name': 'Backlog', 'color': 'gray'},
                {'name': 'In Progress', 'color': 'blue'},
                {'name': 'Waiting', 'color': 'yellow'},
                {'name': 'Done', 'color': 'green'},
                {'name': 'Blocked', 'color': 'red'},
            ]}},
            'Priority': {'select': {'options': [
                {'name': 'Critical', 'color': 'red'},
                {'name': 'High', 'color': 'orange'},
                {'name': 'Medium', 'color': 'yellow'},
                {'name': 'Low', 'color': 'gray'},
            ]}},
            'Due Date': {'date': {}},
            'Linked Workflow': {'rich_text': {}},
            'Linked Role': {'rich_text': {}},
            'AI Generated': {'checkbox': {}},
        }
    )

    create_database(
        company_id, '🎯 Pipeline', icon='🎯',
        properties={
            'Name': {'title': {}},
            'Stage': {'select': {'options': [
                {'name': 'New Lead', 'color': 'blue'},
                {'name': 'Contacted', 'color': 'yellow'},
                {'name': 'Conversation Active', 'color': 'orange'},
                {'name': 'Call Booked', 'color': 'purple'},
                {'name': 'Proposal Sent', 'color': 'pink'},
                {'name': 'Closed Won', 'color': 'green'},
                {'name': 'Closed Lost', 'color': 'red'},
            ]}},
            'Channel': {'select': {'options': [
                {'name': 'Instagram DM', 'color': 'pink'},
                {'name': 'LinkedIn', 'color': 'blue'},
                {'name': 'Referral', 'color': 'green'},
                {'name': 'Cold Email', 'color': 'yellow'},
                {'name': 'Other', 'color': 'gray'},
            ]}},
            'Value': {'number': {'format': 'dollar'}},
            'Last Contact': {'date': {}},
            'Notes': {'rich_text': {}},
            'AI Qualified': {'checkbox': {}},
        }
    )

print('\nDone.')
