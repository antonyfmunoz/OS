Read the broken module, diagnose the root cause, fix it, test it, confirm it imports clean.

Argument: $ARGUMENTS (module name or description of what's broken)

Protocol — follow this exact order, no shortcuts:

1. READ the broken file first — never assume what's in it
   ```bash
   cat /opt/OS/substrate/$ARGUMENTS.py
   ```

2. DIAGNOSE by running the import and capturing the full traceback:
   ```python
   import sys, traceback
   sys.path.insert(0, '/opt/OS')
   try:
       import substrate.$ARGUMENTS
   except Exception:
       traceback.print_exc()
   ```

3. CHECK dependencies — if the error is an import error, read the imported module too

4. FIX — make the minimal change that resolves the root cause
   - Do not refactor surrounding code
   - Do not add features
   - Do not change working logic

5. TEST — confirm the import is clean:
   ```python
   import sys; sys.path.insert(0, '/opt/OS')
   from substrate.$ARGUMENTS import [ClassName]
   print('import ok')
   ```

6. CONFIRM — state exactly what was broken and what was changed

Risk class reminder:
- HIGH: gateway, cognitive_loop, agent_runtime, memory, authority_engine
- MEDIUM: all other existing modules
- LOW: new files, new methods

For HIGH risk changes: run the validator before touching anything:
```python
import sys; sys.path.insert(0, '/opt/OS')
from substrate.state.context.context import load_context_from_env
from substrate.state.context.context import EntrepreneurOSContext as SystemContext
ctx = load_context_from_env()
sc = SystemContext(ctx, 'claude_code')
result = sc.validate_architectural_change('[describe change]')
print(result)
```
