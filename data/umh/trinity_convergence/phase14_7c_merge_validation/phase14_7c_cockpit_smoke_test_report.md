# Phase 14.7C — Cockpit Smoke Test Report

## Safe Intent Smoke Test

### Step 1: Submit Intent
```
POST /api/umh/operator-loop/submit-intent
Body: {"user_intent": "Improve model routing latency", "desired_end_state": "Sub-100ms routing"}
Response: 200
Result: packet_id assigned, status=classified, domain=infrastructure, risk_class=low
```

### Step 2: Classify
- Classification: automatic on submit
- Domain: infrastructure
- Risk: LOW
- Approval gates: none (low risk)

### Step 3: Execute
```
POST /api/umh/operator-loop/execute
Body: {"packet_id": "<id>"}
Response: 200
Result: status=executing
```

### Step 4: Complete
```
POST /api/umh/operator-loop/complete
Body: {"packet_id": "<id>", "outcome_summary": "Routing latency improved"}
Response: 200
Result: status=completed
```

### Step 5: Audit Trail
```
GET /api/umh/operator-loop/audit-trail?packet_id=<id>
Response: 200
Result: Full lifecycle trace (submit → classify → execute → complete)
```

### Step 6: Proof
- Packet visible in active-packets (during execution)
- Packet completed and audit trail recorded
- Full lifecycle traceable end-to-end

**SAFE INTENT RESULT: PASS** — full lifecycle completed without governance blocks

## Risky Intent Smoke Test

### Step 1: Submit High-Risk Intent
```
POST /api/umh/operator-loop/submit-intent
Body: {"user_intent": "Deploy new auth system", "desired_end_state": "New auth live",
       "constraints": ["production_deployment", "security_sensitive"]}
Response: 200
Result: packet_id assigned, risk_class=high, approval_gates=["operator_approval","risk_review"]
```

### Step 2: Verify Execution Blocked
```
POST /api/umh/operator-loop/execute
Body: {"packet_id": "<id>"}
Response: 200
Result: execution BLOCKED — packet requires approval before execution
```

### Step 3: Verify Appears in Pending Approvals
```
GET /api/umh/operator-loop/pending-approvals
Response: 200
Result: High-risk packet appears in pending list with approval gates
```

### Step 4: Verify Audit Trace
```
GET /api/umh/operator-loop/audit-trail?packet_id=<id>
Response: 200
Result: Shows submit and blocked-execution events
```

**RISKY INTENT RESULT: PASS** — execution blocked, approval required, audit trail recorded

## Summary
| Test | Result |
|------|--------|
| Safe intent full lifecycle | PASS |
| Classification automatic | PASS |
| Low-risk execution unblocked | PASS |
| Completion recorded | PASS |
| Audit trail available | PASS |
| High-risk execution blocked | PASS |
| Approval gates enforced | PASS |
| Pending approvals visible | PASS |
| Audit trail for blocked exec | PASS |
