# Gateway CognitiveLoop Fallback Removal

## What is being removed

Lines 1062-1612 of `control_plane/runtime/gateway.py`: the try/except wrapper around ExecutionSpine and the entire CognitiveLoop fallback block. This includes:
- CognitiveLoop instantiation + named agent team routing (lines 1068-1384)
- Generic team routing via agent_teams (lines 1386-1401)
- Direct task routing with IntentRouter + hierarchy fallback (lines 1402-1485)
- Post-loop side effects: KnowledgeIntegrator, FeedbackLoop, AccountabilityEngine, DecisionLog, ConversationMemory store, QualityGate scoring (lines 1487-1612)

## Why it is safe now

ExecutionSpine already handles all agent types via the `_spine_agent` mapping (line 996-1007) which mirrors the CognitiveLoop's named teams. ContextBuilder (used by spine at line 1017) assembles the same 25+ context layers that CognitiveLoop.run() previously built inline (EA standards, CEO standards, portfolio standards, domain principles, patterns, memory, calendar, etc.). The spine's own memory writes (ConversationMemory + AgentMemory at steps 3a/3b) replace the post-loop cm.store() block. Authority validation is handled at spine step 1.

## Gaps identified (must resolve before applying)

1. **Post-response side effects missing from spine**: KnowledgeIntegrator, FeedbackLoop, AccountabilityEngine, DecisionLog are called after CognitiveLoop returns (lines 1497-1562) but have NO equivalent in ExecutionSpine. These must be added to ExecutionSpine (or a post-execution hook) before removal.
2. **Quality gate scoring**: Gateway runs `_validate_output()` after CognitiveLoop (line 1588). Spine returns hardcoded `quality_score: 0.5`. Need spine-level quality gate.
3. **Prompt enhancement**: CognitiveLoop._enhance_prompt() expands short prompts. Spine passes raw prompt. ContextBuilder does not enhance.
4. **Quality iteration loop**: CognitiveLoop retries up to 3x on quality failure. Spine runs once.
5. **Stage filter**: CognitiveLoop applies stage-appropriate correction (5b). Spine does not.
6. **Response footer**: CognitiveLoop appends model/cost/latency stats. Spine does not.
7. **Multimodal input**: CognitiveLoop handles MultimodalInput (voice/image/video via MediaProcessor). Spine accepts only text.
8. **Web search**: Performed before spine try-block, so this is fine.
9. **Martell leverage detection for DEX**: Done inside gateway CognitiveLoop branch (line 1330). ContextBuilder also does it (line 427) so this is covered.
10. **Portfolio data injection**: Done in CognitiveLoop path (line 1366). NOT in ContextBuilder. Gap.

## Rollback path

```bash
git revert <commit-sha>
```

Single commit, single file change. Clean revert.

## Verdict

NOT SAFE TO REMOVE YET. 7 functional gaps remain (items 1-7 and 10 above). The spine needs these capabilities added before the fallback can be deleted.
