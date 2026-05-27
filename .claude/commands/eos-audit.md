Run a full EOS system audit and report what's working, what's broken, and what's missing.

Execute this exact audit pattern:

```python
import sys, os
sys.path.insert(0, '/opt/OS')

modules = [
    ('substrate.state.storage.db', 'get_conn'),
    ('substrate.state.memory.memory', 'AgentMemory'),
    ('adapters.models.agent_runtime', 'AgentRuntime'),
    ('substrate.control_plane.runtime.cognitive_loop', 'CognitiveLoop'),
    ('substrate.governance.policy.authority_engine', 'AuthorityEngine'),
    ('substrate.control_plane.strategy.portfolio_advisor', 'PortfolioAdvisor'),
    ('substrate.control_plane.orchestrator.orchestrator', 'EOSOrchestrator'),
    ('substrate.state.preferences.model_preferences', 'ModelPreferences'),
    ('substrate.execution.media.media_processor', 'MediaProcessor'),
    ('substrate.governance.quality.principle_engine', 'PrincipleEngine'),
    ('substrate.control_plane.identity.identity_engine', 'IdentityEngine'),
    ('substrate.execution.workflows.workflow_engine', 'WorkflowEngine'),
    ('substrate.control_plane.strategy.strategy_engine', 'StrategyEngine'),
    ('substrate.understanding.intelligence.input_intelligence', 'InputIntelligence'),
    ('substrate.understanding.knowledge.knowledge_integrator', 'KnowledgeIntegrator'),
    ('substrate.control_plane.events.event_manager', 'EventManager'),
    ('substrate.state.registries.skill_registry', 'SkillRegistry'),
    ('adapters.google_workspace.gws_connector', 'GWSConnector'),
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
from substrate.state.registries.skill_registry import SkillRegistry
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
