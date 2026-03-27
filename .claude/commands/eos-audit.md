Run a full EOS system audit and report what's working, what's broken, and what's missing.

Execute this exact audit pattern:

```python
import sys, os
sys.path.insert(0, '/opt/OS')

modules = [
    ('eos_ai.db',                 'get_conn'),
    ('eos_ai.memory',             'AgentMemory'),
    ('eos_ai.agent_runtime',      'AgentRuntime'),
    ('eos_ai.cognitive_loop',     'CognitiveLoop'),
    ('eos_ai.authority_engine',   'AuthorityEngine'),
    ('eos_ai.portfolio_advisor',  'PortfolioAdvisor'),
    ('eos_ai.orchestrator',       'EOSOrchestrator'),
    ('eos_ai.model_preferences',  'ModelPreferences'),
    ('eos_ai.media_processor',    'MediaProcessor'),
    ('eos_ai.principle_engine',   'PrincipleEngine'),
    ('eos_ai.identity_engine',    'IdentityEngine'),
    ('eos_ai.workflow_engine',    'WorkflowEngine'),
    ('eos_ai.strategy_engine',    'StrategyEngine'),
    ('eos_ai.reality_engine',     'RealityIntelligenceEngine'),
    ('eos_ai.knowledge_graph',    'KnowledgeGraph'),
    ('eos_ai.coordination_engine','CoordinationEngine'),
    ('eos_ai.skill_registry',     'SkillRegistry'),
    ('eos_ai.gws_connector',      'GWSConnector'),
]

results = {'pass': [], 'fail': []}
for module, cls in modules:
    try:
        m = __import__(module, fromlist=[cls])
        getattr(m, cls)
        results['pass'].append(module)
        print(f'  PASS {module}')
    except Exception as e:
        results['fail'].append((module, str(e)))
        print(f'  FAIL {module}: {e}')

print(f"\n{len(results['pass'])} passing, {len(results['fail'])} failing")
```

Then check Docker status:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Then check Telegram bot:
```bash
pgrep -f telegram_control && echo "Telegram: running" || echo "Telegram: stopped"
```

Then check skill registry:
```python
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.skill_registry import SkillRegistry
sr = SkillRegistry()
print(f"Skills loaded: {len(sr._skills)}")
for name in sorted(sr._skills.keys()):
    print(f"  - {name}")
```

Report format:
- WORKING: list of confirmed working components
- BROKEN: list of failed imports with root cause
- MISSING: components referenced in CLAUDE.md but not yet built
- NEXT ACTION: single most important fix to run first
