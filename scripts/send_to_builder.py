#!/usr/bin/env python3
"""Send a file to the EOS Discord builder channel."""
import os
import sys
import requests
from dotenv import load_dotenv
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


load_dotenv(os.path.join(_ROOT, 'services', '.env'))

token = os.getenv('DISCORD_BOT_TOKEN')
channel_id = os.getenv('EOS_DISCORD_BUILDER_CHANNELS', '1491648663221567499')

filepath = sys.argv[1] if len(sys.argv) > 1 else f'{_ROOT}/docs/system/phase968bh_codebase_truth_map.md'
message = sys.argv[2] if len(sys.argv) > 2 else f'**W0 CODEBASE TRUTH MAP — Phase 96.8BH**\nFull forensic audit of {_ROOT}.'

url = f'https://discord.com/api/v10/channels/{channel_id}/messages'
headers = {'Authorization': f'Bot {token}'}

with open(filepath, 'rb') as f:
    resp = requests.post(
        url,
        headers=headers,
        data={'content': message},
        files={'files[0]': (os.path.basename(filepath), f, 'text/markdown')},
        timeout=15,
    )

print(f'Status: {resp.status_code}')
if resp.status_code in (200, 201):
    print('Sent successfully')
else:
    print(resp.text[:500])
