"""
Sunday Portfolio Brief — runs at 6am every Sunday.
Scans all ventures, identifies binding constraint,
posts to Discord #general + creates Notion page.
"""

import os
import sys
import json
import asyncio
import discord
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

PDT = ZoneInfo('America/Los_Angeles')
GENERAL_CHANNEL_ID = 1486289444830056540


def post_to_notion(brief: str, ventures: list) -> str | None:
    """Create a Notion page with the weekly portfolio brief."""
    try:
        token = os.getenv('NOTION_API_KEY')
        root_id = os.getenv('NOTION_ROOT_ID', '32eda8b9-6e4f-8071-b299-fef02dcb1b8c')
        if not token:
            return None

        headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json',
        }
        now = datetime.now(PDT)
        title = f'Portfolio Brief — {now.strftime("%B %d, %Y")}'

        # Build blocks from brief
        blocks = []
        for line in brief.split('\n'):
            line = line.strip()
            if not line:
                continue
            block_text = line.replace('**', '').replace('━', '').replace('░', '').replace('█', '')
            if block_text:
                blocks.append({
                    'object': 'block',
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [{'type': 'text', 'text': {'content': block_text[:2000]}}]
                    }
                })

        payload = {
            'parent': {'type': 'page_id', 'page_id': root_id},
            'properties': {
                'title': [{'type': 'text', 'text': {'content': title}}]
            },
            'children': blocks[:100],
        }
        resp = requests.post(
            'https://api.notion.com/v1/pages',
            headers=headers,
            json=payload,
            timeout=15,
        )
        return resp.json().get('id')
    except Exception as e:
        print(f'[PortfolioBrief] Notion post failed: {e}')
        return None


async def run_portfolio_brief():
    sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
    from runtime.context import load_context_from_env
    from control_plane.strategy.portfolio_advisor import PortfolioAdvisor as PortfolioAgent

    ctx = load_context_from_env()
    pa = PortfolioAgent(ctx)

    ventures = pa.scan_all_ventures()
    brief = pa.generate_portfolio_brief(ventures)
    binding = pa.identify_binding_constraint(ventures)

    now = datetime.now(PDT)
    header = (
        f'## 📊 Weekly Portfolio Brief\n'
        f'{now.strftime("%A, %B %d %Y")}\n\n'
    )
    full_message = header + brief

    # Post to Notion
    notion_id = post_to_notion(full_message, ventures)
    if notion_id:
        print(f'[PortfolioBrief] Notion page: {notion_id}')

    # Post to Discord
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if channel:
            # Split if over 2000 chars
            chunks = [full_message[i:i+1900] for i in range(0, len(full_message), 1900)]
            for chunk in chunks:
                await channel.send(chunk)

            # Send binding constraint as separate highlighted message
            if binding:
                alert = (
                    f'🎯 **This week\'s binding constraint:**\n'
                    f'**{binding.name}** — {binding.binding_constraint}\n\n'
                    f'{binding.recommendation}'
                )
                await channel.send(alert)
        await client.close()

    await client.start(os.getenv('DISCORD_BOT_TOKEN'))


if __name__ == '__main__':
    asyncio.run(run_portfolio_brief())
