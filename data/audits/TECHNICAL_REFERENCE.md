# UMH Technical Reference — Code Patterns & APIs

**Quick Reference for Developers**

---

## PART 1: COMMON IMPORTS & PATTERNS

### Pattern 1: Working with Signals (Input)

```python
from substrate.types import SignalEnvelope, SignalSource, SignalUrgency, Modality

# Create a signal
signal = SignalEnvelope(
    source=SignalSource.USER,
    urgency=SignalUrgency.HIGH,
    modality=Modality.TEXT,
    content="Schedule a meeting with Alice",
    user_id="founder_1",
    organization_id="org_1",
    venture_id="company_1",
    authority_tier=5  # User has high authority
)

# Process it
from substrate.control_plane.runtime.cognitive_loop import CognitiveLoop
loop = CognitiveLoop(ctx)
result = await loop.run(
    input=signal.content,
    agent="calendar_agent"
)
print(result.output)  # AI response
print(result.approval_id)  # If needs approval
```

### Pattern 2: Working with Memory

```python
from substrate.state.memory.memory import AgentMemory
from substrate.types import MemoryType, MemoryEntry

memory = AgentMemory(org_id="org_1")

# Store a fact
memory.store(MemoryEntry(
    memory_type=MemoryType.FACT,
    content="Alice is the VP of Sales",
    tags=["people", "org-structure"],
    confidence=0.95,
    authority_tier=7
))

# Query facts
results = memory.query(
    query_text="Who is VP of Sales?",
    memory_types=[MemoryType.FACT],
    limit=5
)
for entry in results:
    print(f"{entry.content} (confidence: {entry.confidence})")
```

### Pattern 3: Governance Gate

```python
from substrate.governance.policy_engine import PolicyEngine
from substrate.governance.risk_classes import RiskClass
from substrate.types import GovernanceRequest

policy = PolicyEngine(
    safe_roots=["/home/user/Documents/safe_zone/"],
    allowed_shell_prefixes=["cat ", "ls ", "grep "]
)

request = GovernanceRequest(
    action="write_file",
    target="/home/user/Documents/safe_zone/notes.txt",
    content="Meeting notes",
    risk_class=RiskClass.SAFE_WRITE
)

verdict = policy.evaluate(
    risk_class=RiskClass.SAFE_WRITE,
    request=request,
    context={"target_path": "/home/user/Documents/safe_zone/notes.txt"}
)

if verdict.decision == "approve":
    # Safe to execute
    pass
elif verdict.decision == "defer":
    # Needs approval
    await approval_engine.request_approval(request)
elif verdict.decision == "deny":
    # Rejected
    print(f"Blocked: {verdict.rationale}")
```

### Pattern 4: Work Packet Execution

```python
from substrate.execution.executor import WorkPacketExecutor, ExecutionBundle
from substrate.types import WorkPacket

executor = WorkPacketExecutor()

# Create a work packet
packet = WorkPacket(
    intent="Send email to sales@example.com",
    risk_level="medium",
    execution_environment="agent",
    description="Follow up on lead"
)

# Bundle it with approvals
bundle = ExecutionBundle(
    packet=packet,
    approved_at=datetime.now(timezone.utc),
    approver_id="founder_1"
)

# Execute
result = await executor.execute(bundle)
print(result.status)  # SUCCESS, PARTIAL, FAILED
print(result.output)  # What happened
print(result.proof)   # Cryptographic proof
```

### Pattern 5: Agent-Specific Tasks

```python
from substrate.contracts.agent_types import TaskType
from substrate.control_plane.runtime.cognitive_loop import CognitiveLoop

loop = CognitiveLoop(ctx)

# Route to specific agent
result = await loop.run(
    input="Analyze this customer churn signal",
    agent="cs_agent",
    task_type=TaskType.ANALYZE,
    venture_id="company_1"
)

# or: route through hierarchy
result = await loop.run(
    input="What's our strategic priority for Q3?",
    agent="ceo_agent",
    task_type=TaskType.STRATEGIC_PLANNING
)
```

### Pattern 6: Business Stage Awareness

```python
from substrate.state.business.business_instance import BusinessInstanceSpec

# Load current business spec
bis = await db.get_business_instance_spec("company_1")
print(bis.stage)  # 1-6
print(bis.offer)  # What we sell
print(bis.icp)    # Who we sell to

# Filter advice by stage
if bis.stage == 1:
    # Stage 1: "move fast"
    autonomous_action_threshold = 0.6
elif bis.stage == 3:
    # Stage 3: "optimize"
    autonomous_action_threshold = 0.7
elif bis.stage == 5:
    # Stage 5: "scale"
    autonomous_action_threshold = 0.8

# Only approve if confidence exceeds threshold for stage
if confidence >= autonomous_action_threshold:
    execute()
else:
    escalate()
```

---

## PART 2: CRITICAL DATA STRUCTURES

### ExecutionContext (What the AI sees)

```python
from substrate.types import ExecutionContext

ctx = ExecutionContext(
    signal_id=signal.id,
    identity=Identity(
        user_id="founder_1",
        organization_id="org_1",
        venture_id="company_1",
        ai_name="Aria",
        ai_personality="strategic, direct",
        autonomy_level=3,  # 0-5, user sets this
        business_stage="stage_3",
        permission_tier="execute"
    ),
    session_id="session_abc123",
    conversation_history=[...],  # Last 10 messages
    relevant_memories=[...],      # Top 5 matching memories
    active_goals=[...],            # Current OKRs
    business_context={
        "stage": 3,
        "monthly_revenue": 45000,
        "customer_count": 12,
        "churn_rate": 0.08
    },
    assembled_at=datetime.now(timezone.utc)
)
```

### GovernanceDecision (What gets approved/denied)

```python
from substrate.types import GovernanceDecision, PipelineGovernanceVerdict

verdict = PipelineGovernanceVerdict(
    request_id=request.id,
    decision=GovernanceDecision.APPROVE,  # APPROVE|DEFER|DENY|ESCALATE
    decision_path="autonomous",  # autonomous|approved|escalated
    authority_required="autonomous",  # What tier is needed
    rationale="Read-only query of customer data",
    conditions=[],  # If any conditions must be met
    verified_at=datetime.now(timezone.utc),
    verifier_id="policy_engine"
)
```

### MemoryEntry (How facts are stored)

```python
from substrate.types import MemoryEntry, MemoryType

entry = MemoryEntry(
    memory_type=MemoryType.FACT,  # FACT|BELIEF|DECISION|OBSERVATION|COMMITMENT
    content="Customer ABC Corp renewed contract for $500K/year",
    source_signal_id=signal.id,  # Where this came from
    source_trace_id=execution_trace.id,  # Which execution produced it
    authority_tier=7,  # 1-9, higher = more certain
    confidence=0.92,   # 0.0-1.0
    tags=["revenue", "renewal", "ABC Corp"],
    created_at=datetime.now(timezone.utc),
    metadata={
        "contract_id": "contract_xyz",
        "renewal_date": "2026-06-20"
    }
)
```

### TraceRecord (Immutable audit trail)

```python
from substrate.types import TraceRecord, TraceEventType

trace = TraceRecord(
    id=uuid4(),
    signal_id=signal.id,
    events=[
        TraceEvent(
            event_type=TraceEventType.SIGNAL_RECEIVED,
            timestamp=datetime.now(timezone.utc),
            detail={"source": "discord", "user": "founder_1"}
        ),
        TraceEvent(
            event_type=TraceEventType.GOVERNANCE_EVALUATED,
            timestamp=...,
            detail={"decision": "approve", "risk_class": "safe_write"}
        ),
        TraceEvent(
            event_type=TraceEventType.EXECUTION_STARTED,
            timestamp=...,
            detail={"executor": "browser_agent"}
        ),
        TraceEvent(
            event_type=TraceEventType.EXECUTION_COMPLETED,
            timestamp=...,
            detail={"status": "success", "proof_hash": "abc123..."}
        )
    ]
)
```

---

## PART 3: DATABASE ACCESS PATTERNS

### Get Database Connection

```python
from substrate.state.storage.db import get_conn

# Per-org connection
with get_conn(org_id="org_1") as conn:
    conn.execute("SELECT * FROM memories WHERE org_id = %s", (org_id,))
    rows = conn.fetchall()
    for row in rows:
        print(row)

# Or async
async with get_conn_async(org_id="org_1") as conn:
    await conn.execute("SELECT * FROM interactions WHERE ...")
```

### Common Queries

```python
# Recent interactions
conn.execute("""
    SELECT * FROM interactions
    WHERE org_id = %s
    ORDER BY created_at DESC
    LIMIT 10
""", (org_id,))

# Pending approvals
conn.execute("""
    SELECT * FROM approvals
    WHERE org_id = %s AND status = 'pending'
    ORDER BY created_at ASC
""", (org_id,))

# Memory by tag
conn.execute("""
    SELECT * FROM memories
    WHERE org_id = %s AND %s = ANY(tags)
    ORDER BY confidence DESC
""", (org_id, "revenue"))

# Cost today
conn.execute("""
    SELECT SUM((tokens_json->>'prompt')::int) as input,
           SUM((tokens_json->>'completion')::int) as output
    FROM interactions
    WHERE org_id = %s
    AND created_at >= date_trunc('day', NOW() AT TIME ZONE 'UTC')
""", (org_id,))
```

---

## PART 4: TESTING PATTERNS

### Unit Test Template

```python
import pytest
from substrate.governance.policy_engine import PolicyEngine
from substrate.governance.risk_classes import RiskClass
from substrate.types import GovernanceRequest, GovernanceDecision

class TestPolicyEngine:
    @pytest.fixture
    def policy(self):
        return PolicyEngine(
            safe_roots=["/home/safe/"],
            allowed_shell_prefixes=["cat ", "ls "]
        )
    
    def test_read_only_is_autonomous(self, policy):
        """Read-only operations should not require approval."""
        verdict = policy.evaluate(
            risk_class=RiskClass.READ_ONLY,
            request=GovernanceRequest(action="read"),
            context={}
        )
        assert verdict.decision == GovernanceDecision.APPROVE
    
    def test_irreversible_write_denied(self, policy):
        """Financial operations should be denied by default."""
        verdict = policy.evaluate(
            risk_class=RiskClass.FINANCIAL,
            request=GovernanceRequest(action="send_money"),
            context={"amount": 10000}
        )
        assert verdict.decision == GovernanceDecision.DENY
```

### Integration Test Template

```python
import pytest
from substrate.organism.organism_loop import OrganismLoopEngine, OrganismLoopResult
from substrate.control_plane.runtime.cognitive_loop import CognitiveLoop

class TestOrganismLoop:
    @pytest.fixture
    async def loop(self):
        return OrganismLoopEngine()
    
    @pytest.mark.asyncio
    async def test_full_loop_cycle(self, loop):
        """Test full organism loop: intent → execution → memory."""
        result = await loop.execute_intent(
            intent="Send followup email to alice@example.com",
            desired_end_state="Email sent and logged",
            constraints=[]
        )
        
        assert result.final_status == "completed"
        assert result.work_packet_id
        assert result.governance_decision_id
        assert result.execution_bundle_id
        assert result.memory_write_receipt_id
        assert len(result.event_ids) > 0
```

### Test Governance

```python
def test_governance_cannot_be_bypassed():
    """Governance gate must always be applied."""
    # This should NOT be possible:
    result = executor.execute(packet)  # Error: packet not approved!
    
    # Always must flow through:
    verdict = policy.evaluate(packet)
    if verdict.decision == "approve":
        result = executor.execute(packet)
```

---

## PART 5: ERROR HANDLING

### Expected Errors to Catch

```python
from substrate.execution.executor import ExecutionError
from substrate.governance.policy_engine import PolicyViolation
from substrate.state.storage.db import DatabaseError

try:
    result = await executor.execute(packet)
except ExecutionError as e:
    print(f"Execution failed: {e}")  # Work failed, but didn't crash
except PolicyViolation as e:
    print(f"Governance blocked: {e}")  # Action not allowed
except DatabaseError as e:
    print(f"Persistence failed: {e}")  # DB is unavailable
```

### Fallback Pattern

```python
def fallback_response(intent: str) -> str:
    """Deterministic response when LLM fails."""
    # Pattern match on intent
    if "schedule" in intent.lower():
        return "I've noted your scheduling request. I'll process it once AI is back online."
    elif "analyze" in intent.lower():
        return "Analysis requires AI, which is temporarily offline. I'll process this when systems reconnect."
    else:
        return "I've logged your request. Full capability will be restored when AI is available."

# Use fallback
try:
    result = await cognitive_loop.run(...)
except LLMUnavailableError:
    result = fallback_response(signal.content)
```

---

## PART 6: LOGGING & DEBUGGING

### Structured Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Memory query executed", extra={
    "query": "Who is VP of Sales?",
    "results_count": 3,
    "duration_ms": 45
})

logger.info("Governance verdict issued", extra={
    "risk_class": "reversible_write",
    "decision": "approve",
    "authority_tier": 3
})

logger.warning("LLM request retry", extra={
    "attempt": 2,
    "max_attempts": 3,
    "error": "timeout"
})

logger.error("Executor failed to complete work", extra={
    "packet_id": "wp-123",
    "error": "browser_timeout",
    "duration_ms": 30000
})
```

### Query Execution Traces

```bash
# Get full trace of an interaction
python3 scripts/query_trace.py {interaction_id}

# Get governance decisions for a time range
python3 scripts/query_decisions.py --after 2026-06-20 --before 2026-06-21

# Find slow operations
python3 scripts/query_traces.py --min-duration-ms 5000

# Search for errors
python3 scripts/search_logs.py "Executor failed" --date 2026-06-20
```

---

## PART 7: CONFIGURATION REFERENCE

### Environment Variables

```bash
# LLM Routing
CC_SDK_API_KEY=sk-proj-...
GEMINI_API_KEY=...
GROQ_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434

# Database
DATABASE_URL=postgresql://user:pass@neon.tech/dbname

# Discord
DISCORD_TOKEN=...
DISCORD_COMMAND_PREFIX=!

# Spend Limits
DAILY_SPEND_LIMIT_USD=10
MONTHLY_SPEND_LIMIT_USD=300

# Governance
SAFE_ROOTS=/home/user/safe/:/opt/safe/
ALLOWED_SHELL_PREFIXES=cat,ls,grep

# Logging
LOG_LEVEL=INFO
SENTRY_DSN=...
```

### Policy Configuration

```python
# In policy_engine.py or config
SAFE_ROOTS = [
    "/home/user/Documents/safe_zone/",
    "/opt/project/src/",
    "/tmp/scratch/"
]

ALLOWED_SHELL_PREFIXES = [
    "cat ",           # Read files
    "ls ",            # List directories
    "grep ",          # Search
    "find ",          # Find files
    "ps ",            # Process listing
    "whoami ",        # Current user
]

# Risk class defaults (no approval needed for these)
AUTONOMOUS_RISK_CLASSES = [
    RiskClass.READ_ONLY,
    RiskClass.DEBUGGING
]

# Risk classes that need user approval
REQUIRES_APPROVAL = [
    RiskClass.SAFE_WRITE,
    RiskClass.REVERSIBLE_WRITE
]

# Risk classes that are denied
ALWAYS_DENY = [
    RiskClass.IRREVERSIBLE_WRITE,
    RiskClass.FINANCIAL,
    RiskClass.EXTERNAL_COMMUNICATION
]
```

---

## PART 8: PERFORMANCE TUNING

### Memory Query Optimization

```python
# SLOW: Queries all 10,000 memories
memories = memory.query(query_text="revenue", limit=10000)

# FAST: Limit scope with tags
memories = memory.query(
    query_text="revenue",
    tags=["financial"],  # Pre-filter by tag
    memory_types=[MemoryType.FACT],  # Only facts, not beliefs
    authority_tier_max=9,  # Confidence > 0.7
    limit=10  # Get top 10
)
```

### Batch Operations

```python
# SLOW: Write 100 memories one at a time
for entry in entries:
    memory.store(entry)  # 100 round-trips

# FAST: Batch write
memory.store_batch(entries)  # 1 round-trip
```

### Connection Pooling

```python
# Configured automatically, but be aware:
from substrate.state.storage.db import get_conn

# Gets connection from pool
with get_conn(org_id) as conn:
    # Use it
    pass
# Automatically returned to pool

# Pool size is limited. Don't hold connections:
# WRONG: Opens 100 connections, holds them
for i in range(100):
    conn = get_conn(org_id)  # Doesn't return until end of loop
    # ... do work
```

---

## PART 9: DEBUGGING CHECKLIST

When something breaks:

```
1. Check logs
   docker logs os-discord | grep ERROR

2. Verify database
   python3 scripts/verify_knowledge_system.py

3. Test governance
   pytest tests/test_governance_routes.py -v

4. Check recent interactions
   python3 scripts/query_trace.py {interaction_id}

5. Verify permissions
   SELECT * FROM permissions WHERE user_id = 'xyz'

6. Check memory conflicts
   SELECT * FROM memories WHERE tags = 'conflicting'

7. Test LLM routing
   python3 scripts/test_llm_routing.py

8. Check spend
   curl http://localhost:8000/spend

9. Verify runtime availability
   curl http://localhost:8000/runtime-status

10. Restart if stuck
    docker restart os-discord
```

---

## PART 10: API ENDPOINTS (Cockpit)

### Status Endpoints

```bash
# System health
GET /health
→ { "status": "ready", "version": "1.0" }

# Current spend
GET /spend
→ { "today": 2.45, "month": 47.32, "all_time": 127.50 }

# Runtime status
GET /runtime-status
→ { "workstations": 3, "browsers": 1, "agents": 5 }

# Memory stats
GET /memory-stats
→ { "total_entries": 5432, "by_type": { "fact": 3000, "belief": 2000 } }
```

### Action Endpoints

```bash
# Send message
POST /message
{
  "content": "Schedule a meeting",
  "user_id": "xyz",
  "venture_id": "company_1"
}
→ { "status": "received", "interaction_id": "int-123" }

# Approve pending action
POST /approve/{approval_id}
{
  "approve": true,
  "reason": "Looks good"
}
→ { "status": "approved", "execution_started": true }

# Get interaction history
GET /interactions?user_id=xyz&limit=10
→ [ { id, timestamp, input, output, model, tokens }, ... ]
```

---

End of Technical Reference

