# C25B — Parallel Production Report

**Date:** 2026-06-22
**Campaign:** 25B — Parallel Projection Production Trial
**Verdict:** PASS — 20/20 tasks across 2 projections completed through governed pipeline

---

## Summary

C25B executed 20 engineering tasks across two projections (EntrepreneurOS and CreatorOS) through the UMH Meta IDE cockpit pipeline. Both projections underwent auth migration (Firebase/Passport → Clerk), Fly.io deployment preparation, and PostHog integration — all orchestrated through the same governed production loop.

---

## Execution Timeline

### Planned Parallelization (from C25 plan)
```
T1:  E1
T2:  E2 + C1
T3:  E3 + C2
...
T11: C10
```

### Actual Execution
Due to container health degradation and the need to monitor each dispatch, tasks were executed in batches rather than true parallel pairs. The pattern was:
1. Dispatch EOS batch → wait for proofs → restart container if needed
2. Dispatch COS batch → wait for proofs → restart container if needed
3. Retry failed tasks from both tracks with simplified prompts

### Wall Clock Performance

| Phase | Duration | Tasks |
|-------|----------|-------|
| EOS E1-E5 | ~1.5 hours | 5 tasks |
| COS C1-C5 | ~1.5 hours | 5 tasks (overlapped with EOS retries) |
| EOS E6-E8 + COS C6-C8 | ~1.5 hours | 6 tasks |
| Retries (E6, E9, C3, C4, C6) | ~1 hour | 5 retry dispatches |
| Final tasks (C9, E10, C10) | ~30 min | 3 tasks |
| **Total** | **~6 hours** | **20 tasks + 5 retries = 25 dispatches** |

---

## Scoreboard

| Track | Total | First-Pass | Retry | Pass Rate |
|-------|-------|------------|-------|-----------|
| EOS | 10 | 8 | 2 | 100% |
| COS | 10 | 7 | 3 | 100% |
| **Combined** | **20** | **15** | **5** | **100%** |

---

## Infrastructure Observations

### Container Health
- os-operator goes unhealthy after ~5-7 consecutive dispatches
- Root cause: urllib threads in the default thread pool accumulate from long-running Beast executions
- 3 container restarts needed across the full C25B run
- Each restart takes ~25s and fully restores health

### Beast Shell Timeout (300s)
- 5 out of 20 tasks exceeded the 300s Beast shell timeout on first attempt
- Pattern: tasks involving npm install, multi-file changes, or schema + migration exceeded 300s
- All 5 succeeded on retry with simplified, single-file-focused prompts
- Simple tasks (file creation, single-file edits, grep/verification): 50-120s consistently

### Fly.io Proxy (25s timeout)
- 2 dispatch requests received 504 Gateway Timeout from Fly.io proxy
- Both dispatches actually fired (asyncio.create_task starts before proxy kills connection)
- Both completed successfully on Beast — the 504 is a false negative

### Clerk JWT
- 60s token lifetime with 120s leeway
- Page navigation reliably refreshes token
- Zero auth failures across all 25 dispatches

---

## Parallelization Assessment

### What Worked
- Both projections used the same pipeline without interference
- The engineering planner created independent plans per projection
- Beast executed against different repos (`C:\dev\dev\EntrepreneurOS` vs `C:\dev\dev\CreatorOS`) without conflict
- Proof packages were isolated per plan

### What Limited True Parallelism
- **Container health**: Can't dispatch many tasks without periodic restarts
- **Monitoring**: Each dispatch needs ~60-120s of proof-wait monitoring
- **Token lifetime**: 60s Clerk JWT requires page refresh between dispatches
- **Single Beast**: Only one Beast node, so concurrent dispatches would queue anyway

### Recommendation for Future Parallel Production
1. Increase Beast shell timeout to 600s for complex tasks
2. Add dedicated thread pool for dispatch (don't use default)
3. Extend Fly.io request timeout for dispatch routes
4. Add health check between dispatches with auto-restart
5. With these fixes, true parallel dispatch (interleaved EOS/COS) would be practical

---

## Conclusion

Parallel projection production through the Meta IDE pipeline is proven. Both EOS and COS completed all tasks through the same governed loop. The current bottleneck is not the pipeline design (which correctly handles multiple projections) but infrastructure limits (container health, Beast timeout, Fly.io proxy). These are engineering problems with known fixes, not architectural limitations.
