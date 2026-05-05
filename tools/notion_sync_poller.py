"""
Notion Sync Poller — runs every 15 minutes via cron.

1. Pushes Neon tasks without a notion_page_id → Notion
2. Pulls Notion status changes back → Neon events table
   (delegates to notion_tasks_sync.sync_neon_to_notion)
"""

import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/umh/.env')

PDT = ZoneInfo('America/Los_Angeles')


def run():
    from umh.environments.system_context import load_context_from_env
    from umh.runtime_engine.notion_sync import push_all_ventures
    from scripts.notion_tasks_sync import sync_neon_to_notion

    ctx = load_context_from_env()
    now = datetime.now(PDT)
    print(f'[NotionPoller] {now.strftime("%Y-%m-%d %H:%M")} PDT')

    # 1. Push Neon tasks → Notion
    push_results = push_all_ventures(ctx)
    for vid, counts in push_results.items():
        print(f'  {vid}: pushed={counts["pushed"]}')

    # 2. Push Neon status changes → Notion pages
    synced_back = sync_neon_to_notion()
    print(f'  status_sync_back={synced_back}')

    print('[NotionPoller] Done.')


if __name__ == '__main__':
    run()
