Run the full sync — reload skill registry, update user model, sync harness profile, refresh domain registry, re-profile CRM leads. Same as the /sync Telegram command but from Claude Code.

Protocol:

1. RELOAD skill registry:
   ```python
   import sys; sys.path.insert(0, '/opt/OS')
   from eos_ai.skill_registry import SkillRegistry
   sr = SkillRegistry()
   sr.reload()
   print(f"Skills loaded: {len(sr._skills)}")
   for name in sorted(sr._skills.keys()):
       print(f"  - {name}")
   ```

2. UPDATE user model if available:
   ```python
   import sys; sys.path.insert(0, '/opt/OS')
   try:
       from eos_ai.user_model import UserModel
       from eos_ai.context import load_context_from_env
       ctx = load_context_from_env()
       um = UserModel(ctx)
       profile = um.get_profile()
       print(f"User model: {profile}")
   except Exception as e:
       print(f"User model sync skipped: {e}")
   ```

3. RE-PROFILE CRM leads — scan for unqualified leads and score them:
   ```bash
   ls /opt/OS/03_CRM/Leads/ | head -20
   ```
   Then for each unqualified lead file: run the Qualify Lead skill

4. CHECK inbox for unprocessed signals:
   ```bash
   ls /opt/OS/01_Inbox/raw_signals/ | wc -l
   ```
   If count > 0: run process_signal_queue skill to clear the queue

5. VERIFY session state is current:
   ```python
   import sys; sys.path.insert(0, '/opt/OS')
   from eos_ai.session_state import SessionState
   print(SessionState.get_resume_context())
   ```

6. REPORT sync summary:
   - Skills reloaded: N
   - CRM leads profiled: N
   - Inbox signals processed: N
   - Any errors encountered

Note: For MCP server sync (Slack, Notion, Miro), those require separate auth flows. Check `claude mcp list` to see connection status.
