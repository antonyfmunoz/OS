# Phase 14.14A — Daily Driver Acceptance Protocol

**Date:** 2026-06-09
**Purpose:** Score real operating sessions against 15 daily-driver categories.

---

## Scoring Rubric

Each category is scored per session:

| Score | Meaning |
|-------|---------|
| PASS | Works as expected, no operator workaround needed |
| PARTIAL | Works with caveats or minor workarounds |
| FAIL | Forces operator back to external tool (ChatGPT/Termius/VS Code/browser) |
| NOT TESTED | Not attempted this session |

---

## Categories

### 1. Conversational Planning with DEX
- DEX responds conversationally to open-ended planning questions
- No JSON dumps in chat responses
- Suggested actions are useful
- Response quality reduces ChatGPT dependency

### 2. View-Context Awareness
- DEX references what the operator is looking at
- Context from cockpit panel/view is used in responses
- "What am I looking at?" gets a real answer

### 3. Voice Input/Output
- Voice WebSocket accepts connections
- STT transcribes operator speech
- TTS speaks responses
- Voice commands route correctly

### 4. Text Chat Reliability
- Chat messages always get a response
- No dropped messages
- No infinite loading
- Response within 10 seconds

### 5. Work Packet Creation
- "Create a work packet for X" produces a structured packet
- Has desired_end_state, acceptance_criteria, proof_required
- Packet is visible in command center

### 6. Work Packet Decomposition
- Complex tasks can be broken into sub-packets
- Dependencies between sub-packets are identified
- Decomposition is actionable, not generic

### 7. Claude Code / Coding Delegation
- "Send this to Claude Code" routes to a coding session
- Session bridge is used if available
- Failure is reported honestly (no fake success)
- Result includes diff/proof/test output

### 8. Beast App Control
- Native apps resolve and launch (Spotify, Discord, etc.)
- Browser targets open in Chrome
- "on Beast" qualifier is stripped before lookup
- Session 0 is never used for GUI work
- Screenshot/proof does not silently fail

### 9. VPS Command/Control
- Safe commands execute through governed catalog
- Natural phrasing classifies correctly
- Unsafe commands are blocked with explanation
- Real output is returned (not hallucinated)

### 10. Report Generation
- "Create a report" produces a real report
- Summary is in chat, full report is attached/linked
- No hallucinated session data

### 11. Proof Attachment
- Proofs (screenshots, test output, diffs) are attached
- Artifact paths are visible
- No silent failure on large attachments

### 12. Approval Handling
- Unsafe actions trigger approval_required
- Approval appears in UI with explanation
- No action executes before approval
- Risk metadata is included

### 13. Loop Completion Verification
- Tasks are not marked complete without proof
- Verifier determines completion
- Blocker reports exact reason
- Loop outcome is summarized

### 14. Blocker Recovery
- "What is blocked?" returns real blockers
- Blockers include reason and recommended fix
- DEX can suggest recovery actions

### 15. Session Summary Quality
- "Summarize what happened" produces useful summary
- Based on real session data, not hallucination
- Includes actions taken, results, and pending items

---

## Session Template

```markdown
## Session: [YYYY-MM-DD]

### Trials Run
| # | Category | Command | Score | Notes |
|---|----------|---------|-------|-------|
| 1 | Conversational Planning | "What should I do next?" | ? | |
| 2 | View-Context | "What am I looking at?" | ? | |
| ... | ... | ... | ? | |

### Failures Discovered
| ID | Surface | User Action | Expected | Actual | Severity | Blocks Daily Driver |
|----|---------|-------------|----------|--------|----------|---------------------|
| F1 | ... | ... | ... | ... | ... | ... |

### Readiness Score
PASS: X/15  PARTIAL: Y/15  FAIL: Z/15  NOT TESTED: W/15
```

---

## Acceptance Gate

UMH is daily-driver ready when:
- 0 FAIL scores across all 15 categories
- No more than 3 PARTIAL scores
- All PARTIAL scores have documented workarounds
- At least 3 complete sessions scored
