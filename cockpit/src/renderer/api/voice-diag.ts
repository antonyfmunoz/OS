/**
 * Voice client-side diagnostic collector (P4S-VOICE-CLIENT-DIAG).
 *
 * The server logs cannot see a client-side stall that never opens a WS — which is
 * exactly the class of failure that survived four voice fixes. This records the
 * ordered `[VoicePipeline]` stage markers for ONE mic tap (stage label + ms since
 * tap start + a short detail) and flushes them to POST /api/umh/voice/diag when the
 * chain reaches a terminal state (idle / recording / error). NO audio, transcript,
 * or token content — stage labels + relative timings only.
 *
 * Best-effort and non-blocking: collection never throws, and the flush is
 * fire-and-forget so it can never itself stall the voice chain.
 */
import { API_BASE } from './client'

interface DiagEvent {
  stage: string
  t_ms: number
  detail: string
}

let _tapId = ''
let _t0 = 0
let _events: DiagEvent[] = []
let _armed = false

/** Monotonic-ish ms without Date.now flakiness across the app (performance.now is
 *  fine in the browser). */
function _now(): number {
  return typeof performance !== 'undefined' && performance.now
    ? performance.now()
    : 0
}

/** Begin a fresh diagnostic capture for one mic tap. */
export function diagStartTap(tapId: string): void {
  _tapId = tapId
  _t0 = _now()
  _events = []
  _armed = true
  diagStage('tap_start')
}

/** Record a stage marker (no-op if no tap is armed). */
export function diagStage(stage: string, detail: unknown = ''): void {
  if (!_armed) return
  try {
    const d =
      detail === '' || detail == null
        ? ''
        : typeof detail === 'string'
          ? detail
          : String(detail)
    _events.push({ stage, t_ms: Math.round(_now() - _t0), detail: d.slice(0, 200) })
    if (_events.length > 100) _events.shift()
  } catch {
    /* diagnostics must never throw */
  }
}

/** Flush the collected timeline to the server and disarm. Fire-and-forget. */
export function diagFlush(reason: string): void {
  if (!_armed) return
  diagStage('flush', reason)
  const payload = {
    tap_id: _tapId,
    ua: typeof navigator !== 'undefined' ? navigator.userAgent : '',
    events: _events.slice(),
  }
  _armed = false
  _events = []
  try {
    // keepalive so it still sends if the page/JS is tearing down; never awaited.
    void fetch(`${API_BASE}/voice/diag`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {})
  } catch {
    /* ignore */
  }
}
