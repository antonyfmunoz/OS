# Client-Failure Observability Law (NON-NEGOTIABLE)

This law exists because a mobile-voice bug took a full day and SIX wrong fixes
(2026-07-09). The failure was 100% client-side and NEVER reached the server, so
`docker logs` showed nothing and every fix was a plausible guess at the wrong layer.
The real cause (`unlockAudioForIOS()`'s `audio.play()` hanging on iOS 18.7 Safari) was
found in ONE user tap the moment a client→server diagnostic beacon was added.

## The law

**When a user-facing failure cannot be seen in server logs, STOP writing fixes and
INSTRUMENT the client FIRST.** A diagnostic that makes an invisible failure visible is
worth more than any number of plausible fixes. Never ship a second speculative fix for a
client-side symptom that survived the first — build the beacon instead.

### 1. Instrument before the second fix
If a client-side symptom survives even ONE fix, the next change MUST be a diagnostic
beacon, not another fix. The beacon is cheap (~60 lines) and permanent.

Reference implementation (keep it, don't delete as "scaffolding"):
- Collector: `cockpit/src/renderer/api/voice-diag.ts` — `diagStartTap(id)` /
  `diagStage(stage, detail)` / `diagFlush(reason)`. Records ordered
  `{stage, ms_since_action_start, short_detail}`. NO tokens / audio / transcript / PII.
- Ingest: `POST /api/umh/voice/diag` (`transports/api/voice.py`) → logs
  `[VoiceClientDiag] tap=… ua=… | stage@ms → stage@ms → …`. Auth-free, bounded,
  never raises.
- Wiring: mirror the surface's existing `log()`/console stages into the collector, and
  add an explicit `stage` marker immediately BEFORE and AFTER every awaited step on the
  user-blocking critical path. The gap between an `X_await` marker and its `X_ok` marker
  is exactly where a hang lives. Flush on EVERY terminal exit (success AND each failure).

To read it: `docker logs <container> | grep <DiagTag> | tail -3`. The stage whose
`_await` has no following marker (or `flush@<~budget>ms/…_timeout` right after it) is the
bug.

### 2. Never await a non-essential call on a user-blocking path
Any awaited call on a path that blocks the user (mic start, first paint, submit) that is
NOT strictly required for THAT path is a latent hang. Make it fire-and-forget AND
internally bound it (`Promise.race` with a timeout). `unlockAudioForIOS()` — a TTS
autoplay nicety with nothing to do with recording — was awaited before the mic and hung
the whole chain. If a step's result isn't needed to complete the current user action,
it must not be able to block that action.

### 3. An error string names a SYMPTOM, not the layer that failed
A timeout/"unreachable"/"unavailable" banner means "some watchdog fired," not "the thing
it names failed." Before fixing, establish WHICH timer fired and whether an unbounded
upstream `await` stole the budget. Prefer typed, layer-specific outcomes over generic
strings so the banner can't lie about the boundary.

## Scope

Governs client-heavy cockpit surfaces (voice, TTS playback, vision, desktop/browser WS)
— anywhere a failure can occur entirely in the browser and never hit the backend.
Generalize the beacon pattern to a surface the first time it produces a
server-invisible failure; do not preemptively instrument every surface.

## Enforcement

Partially enforced by Gate 14 (`scripts/check_voice_runtime_divergence.py`): the voice
diag beacon must exist and be wired, and the known-hang audio-unlock call must not be
awaited on the voice-start critical path. The broader law is a review discipline —
reviewers reject a second speculative client-side fix that lacks a diagnostic beacon.
