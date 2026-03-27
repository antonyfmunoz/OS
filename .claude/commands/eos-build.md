Read the canonical spec in CLAUDE.md, validate the requested feature against the architecture, build it, wire it to the gateway and Telegram, test it.

Argument: $ARGUMENTS (description of what to build)

Protocol:

1. READ CLAUDE.md for architecture context:
   ```bash
   cat /opt/OS/.claude/CLAUDE.md
   ```

2. READ the relevant existing modules before touching anything

3. VALIDATE — does this feature fit the architecture?
   - Does it belong in eos_ai/ (intelligence layer) or 13_Scripts/ (automation)?
   - Does it need a new module or does it extend an existing one?
   - What are the risk classes for any files being modified?

4. CHECK session state — what phase are we in?
   ```python
   import sys; sys.path.insert(0, '/opt/OS')
   from eos_ai.session_state import SessionState
   print(SessionState.get_resume_context())
   ```

5. BUILD — real code only, no placeholders, no pseudocode
   - New files: LOW risk — build freely
   - Modifying existing: MEDIUM/HIGH — read first, change minimally

6. WIRE — connect to gateway and Telegram if applicable:
   - Gateway: check /opt/OS/eos_ai/gateway.py for routing pattern
   - Telegram: check /opt/OS/13_Scripts/telegram_control.py for command registration

7. TEST — import check + functional test:
   ```python
   import sys; sys.path.insert(0, '/opt/OS')
   from eos_ai.[module] import [Class]
   print('import ok')
   ```

8. SAVE STATE:
   ```python
   import sys; sys.path.insert(0, '/opt/OS')
   from eos_ai.session_state import SessionState
   SessionState.save(
       phase='[current phase]',
       last_completed='[what was just built]',
       in_progress=None,
       next_steps=['[logical next step]'],
       files_modified=['[files changed]']
   )
   ```
