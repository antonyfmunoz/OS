# UMH Agent Runtime Architecture

**Phase:** 14.6B-UMH
**Status:** DRAFT

## Agent Hierarchy

### EOS Department Agents

10 department agents, each extending `DepartmentAgent` base class:

| Agent | Department |
|-------|-----------|
| CEO | Executive leadership |
| COO | Operations |
| CFO | Finance |
| CMO | Marketing |
| CTO | Technology |
| CPO | Product |
| CHRO | Human resources |
| CSO | Sales |
| CLO | Legal |
| CIO | Information |

### DepartmentAgent Base Class

Each department agent inherits:

- **Skill execution** -- routes to registered skills for the department
- **Permission tiers** -- authority level determines which actions require approval
- **Browser capabilities** -- agents can interact with web interfaces via browser adapters

## AgentRuntime Routing

`adapters/models/agent_runtime.py` routes agent calls based on `TaskType`:

| TaskType | Target Model | Use Case |
|----------|-------------|----------|
| FAST_RESPONSE | Haiku | Quick lookups, classification, validation |
| Strategic/CEO | Opus (via cc_sdk) | High-stakes decisions, synthesis |
| Default | Sonnet/Flash | Standard agent work |

### Rate Limiter

- **30 requests/minute** per agent
- **500 requests/hour** per agent
- Enforced at the AgentRuntime level before model dispatch

## Authority Engine Integration

- Each agent action is classified by `RiskClass` (LOW/MEDIUM/HIGH/CRITICAL)
- LOW actions execute autonomously
- MEDIUM+ actions require governance approval via the authority engine
- Approval flows through the accountability chain defined in `substrate/control_plane/governance.py`

## Fallback Chain

AgentRuntime uses `call_with_fallback()` from `adapters/models/model_router.py`:

```
cc_sdk (Opus 4.6) --> Gemini 2.5 Flash --> Groq --> Ollama
```

CEO/strategic agents force Opus via `agent_type='ceo'` or `force_opus=True`.
