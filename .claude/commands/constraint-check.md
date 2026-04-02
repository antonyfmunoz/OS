---
description: "Diagnose current binding constraint across all ventures. Shows what is blocking stage advancement and what the CEO agent recommends."
---

Run a constraint check across all ventures.

!`python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
try:
    from eos_ai.context import load_context_from_env
    from eos_ai.ceo_intelligence import CEOIntelligence
    ctx = load_context_from_env()
    intel = CEOIntelligence(ctx)
    diagnosis = intel.diagnose_constraint()
    print(diagnosis)
except Exception as e:
    print(f'Constraint diagnosis error: {e}')
"`

Based on the diagnosis above, answer:
1. What is the binding constraint right now?
2. What is the ONE objective that addresses it?
3. What would unlock stage advancement?
4. What should NOT be worked on today?
