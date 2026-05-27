---
Check and update all Claude Code skills.
Reviews source documentation for changes and syncs to Neon.
---

python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
# claude_skill_registry: dormant — pending substrate migration
from substrate.state.context.context import load_context_from_env

ctx = load_context_from_env()
csrm = ClaudeSkillRegistryManager()

print(csrm.format_status())
print()

needs = csrm.check_for_updates()
print(f'Skills needing review: {len(needs)}')
for s in needs:
    skill = csrm.registry.get(s)
    if skill and skill.source_url:
        print(f'  {s}: {skill.source_url}')

print()
synced = csrm.sync_to_neon(ctx)
print(f'Synced {synced} skills to Neon')
"
