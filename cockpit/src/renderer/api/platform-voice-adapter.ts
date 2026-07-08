/**
 * PlatformVoiceAdapter — desktop browser push-to-talk (P4S-31D-1).
 *
 * The ONE adapter interface from docs/VOICE_INTENT_CONTRACT.md, implemented for
 * the desktop browser over the seams that already ship:
 *
 *   capture/STT      -> voice-controller.ts (governed /api/umh/voice/ws, PCM16)
 *   review + send    -> recording produces a reviewable VoiceMessageDraft; the
 *                       operator's explicit send is voiceMessageStore.sendDraft
 *                       -> chatStore.addVoiceTranscript
 *                       -> sendMessage(text, 'voice', ...) -> POST /advisor/converse
 *
 * Contract invariants this module enforces:
 * - Output is ALWAYS a chat message via source='voice' (delegated to the draft
 *   send seam). This adapter never calls the intent classifier,
 *   the intent-loop submit endpoint, governed mutations, or any provider.
 * - Fail-closed consent: capture opens ONLY behind an active
 *   VoiceConsentGrant(mode) read from the server (GET /voice/consent). Missing,
 *   revoked, or unreadable consent -> typed CONSENT_REQUIRED refusal, mic never
 *   opens. The browser mic permission is the second, independent layer.
 * - No identity: the operator principal is resolved server-side from the
 *   authenticated session; this adapter sends only device + mode.
 * - No audio persistence; audio buffers live in the WS client only.
 */

import { fetchApi } from './client'
import { startVoice, stopVoice, destroyVoice } from './voice-controller'
import { ensureBrowserMicPermission, releaseGestureStream } from './voice-ws'
import { useVoiceStore } from '../stores/voiceStore'
import { useVoiceMessageStore } from '../stores/voiceMessageStore'

/** Thread the active grant id (vcg-…) into the draft store for stamping. */
function _rememberGrantId(consent: VoiceConsentState): void {
  const grant = consent.grant as Record<string, unknown> | null | undefined
  const id = grant && typeof grant.grant_id === 'string' ? grant.grant_id : ''
  if (id) useVoiceMessageStore.getState().setActiveConsentGrantId(id)
}

export type VoiceActivationMode = 'push_to_talk' | 'wake_word' | 'always_on'

export interface VoiceConsentState {
  active: boolean
  grant?: Record<string, unknown> | null
  error?: string | null
  code?: string
}

export class ConsentRequiredError extends Error {
  code = 'CONSENT_REQUIRED'
  constructor(message: string) {
    super(message)
    this.name = 'ConsentRequiredError'
  }
}

// P5 — synchronous re-entrancy claim. Set at the VERY TOP of startCapture, BEFORE
// any await, and released in a finally. The React-side handleMicToggle guard reads
// a STALE micState closure, so a fast double-tap can slip two startCapture calls
// into the pre-await window and spawn two recorders + two drafts. This module-level
// boolean is checked/set synchronously, so the second tap can never pass.
let captureClaimed = false

function deviceRegistryId(): string {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useDeviceSessionStore } = require('../stores/deviceSessionStore')
    const routing = useDeviceSessionStore.getState().getRoutingMetadata() as Record<string, string>
    if (routing.source_device_id) return routing.source_device_id
  } catch {
    // device session store unavailable — fall through to a runtime-derived id
  }
  // P4S31: no hardcoded 'desktop_browser' — derive the fallback device id from
  // the actual runtime platform so native/mobile aren't mislabeled as desktop.
  return `${currentVoiceSource()}_device`
}

async function getConsent(mode: VoiceActivationMode): Promise<VoiceConsentState> {
  try {
    const device = encodeURIComponent(deviceRegistryId())
    return await fetchApi<VoiceConsentState>(
      `/voice/consent?device_registry_id=${device}&mode=${mode}`,
    )
  } catch (e) {
    // Fail-closed: unreachable consent surface means NO consent.
    return { active: false, error: e instanceof Error ? e.message : 'consent read failed' }
  }
}

async function requestConsent(mode: VoiceActivationMode): Promise<VoiceConsentState> {
  // P4S31 mobile: the browser mic approval IS the authorizing gesture — the UMH
  // grant must land reliably right after it, not fail into a button. Clerk's
  // getToken() can transiently return null/stale on mobile Safari on the call
  // right after the GET, so retry the POST a few times before giving up, and
  // surface the REAL error (status + detail) instead of a generic message.
  const device = deviceRegistryId()
  let lastErr = ''
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const out = await fetchApi<VoiceConsentState>('/voice/consent/grant', {
        method: 'POST',
        body: JSON.stringify({ device_registry_id: device, mode }),
      })
      if (out.active) return out
      lastErr = out.error || `grant returned active=false (${JSON.stringify(out).slice(0, 120)})`
    } catch (e) {
      lastErr = e instanceof Error ? e.message : 'consent grant failed'
    }
    await new Promise((r) => setTimeout(r, 400 * (attempt + 1)))
  }
  return { active: false, error: lastErr || 'consent grant failed' }
}

async function revokeConsent(mode: VoiceActivationMode): Promise<VoiceConsentState> {
  try {
    const out = await fetchApi<VoiceConsentState>('/voice/consent/revoke', {
      method: 'POST',
      body: JSON.stringify({ device_registry_id: deviceRegistryId(), mode }),
    })
    if (mode === 'push_to_talk') useVoiceStore.getState().setConsentState('required')
    return out
  } catch (e) {
    return { active: false, error: e instanceof Error ? e.message : 'consent revoke failed' }
  }
}

/**
 * Explicit inline grant flow for push-to-talk (Lane A UX). Server truth only:
 * the store state flips to 'active' ONLY when the governed grant route
 * confirms an active grant — never faked client-side, never auto-granted.
 */
async function grantPushToTalk(): Promise<VoiceConsentState> {
  const vs = useVoiceStore.getState()
  vs.setConsentState('granting')
  const out = await requestConsent('push_to_talk')
  if (out.active) {
    vs.setConsentState('active')
    vs.setError(null)
    vs.setLastOutcome(null)
    _rememberGrantId(out)
  } else {
    vs.setConsentState('required')
    vs.setError(out.error || 'Consent grant failed — try again')
  }
  return out
}

/**
 * Open push-to-talk capture behind the fail-closed consent gate — P4S-31D1-E
 * SINGLE-GESTURE flow (fixes the mobile-Safari double-consent).
 *
 * One user tap on the mic drives the whole sequence:
 *   1. If an active VoiceConsentGrant(push_to_talk) already exists for this
 *      device → go straight to capture (returning device, no grant round-trip).
 *   2. Otherwise the mic tap IS the authorizing gesture: prompt the BROWSER mic
 *      permission first (ensureBrowserMicPermission → getUserMedia). On its
 *      success, AUTOMATICALLY request the UMH push_to_talk grant IN THE SAME
 *      handler — no second "Enable Push-to-Talk" tap on the happy path. This is
 *      a REAL server round-trip (requestConsent → governed grant route); the
 *      store flips to 'active' only when the server confirms an active grant.
 *   3. Only if the SERVER grant fails (VoiceConsentRefused / network) do we set
 *      consentState 'required' + throw ConsentRequiredError, so the UI surfaces
 *      the explicit "Enable Push-to-Talk" RETRY affordance — off the happy path.
 *   4. If the BROWSER permission is denied, that's the mic layer, not consent:
 *      map to the typed mic outcome (no server grant is attempted).
 *
 * The browser permission and the UMH grant remain two independent fail-closed
 * layers; this only removes the extra user gesture between them.
 */
async function startCapture(): Promise<void> {
  // P5: claim synchronously BEFORE any await. A fast double-tap's second call sees
  // captureClaimed===true and bails here — no second recorder/draft can spawn.
  if (captureClaimed) {
    console.log('[VoicePipeline] start_capture_ignored_already_claimed')
    return
  }
  captureClaimed = true
  try {
    await _startCaptureInner()
  } finally {
    captureClaimed = false
  }
}

async function _startCaptureInner(): Promise<void> {
  const vs = useVoiceStore.getState()

  // Instant feedback + concurrent-reentry guard: flip micState OUT of 'idle'
  // synchronously up front (the handleMicToggle guard is micState==='idle').
  vs.setError(null)
  vs.setMicState('requesting_permission')
  // Clear any stale 'required' left by a prior failed attempt: the mic tap always
  // drives a fresh auto-grant flow, so the separate "Enable Push-to-Talk" button
  // never lingers on the happy path. It only reappears if THIS attempt's grant
  // is genuinely refused (server fail-closed).
  if (vs.consentState === 'required') vs.setConsentState('granting')

  // BROWSER MIC PROMPT FIRST. The browser getUserMedia permission dialog must
  // fire synchronously inside the user gesture. Awaiting a SERVER round-trip
  // (getConsent) before it delays the prompt and breaks the gesture-context
  // requirement — the dialog then appears late or not at all (the button just
  // reads "Requesting mic…" with no OS prompt). So call the browser layer first;
  // do ALL UMH server consent work AFTER the user has allowed the mic. Browser
  // permission is origin-cached, so a returning device sees no dialog and this
  // path stays instant either way.
  try {
    await ensureBrowserMicPermission()
  } catch (err) {
    // Browser mic layer denied/unavailable — NOT a consent-grant failure.
    const error = err as Error & { name?: string }
    if (error.name === 'NotAllowedError') {
      vs.setError('Microphone permission denied — check browser settings')
      vs.setLastOutcome('MIC_PERMISSION_DENIED')
    } else if (error.name === 'NotFoundError') {
      vs.setError('No microphone found')
      vs.setLastOutcome('MIC_DEVICE_UNAVAILABLE')
    } else if (error.name === 'MicAcquireTimeout') {
      // P4S31 mobile: getUserMedia stalled (iOS held the audio session). Fast,
      // typed failure instead of a forever "Requesting mic…" button.
      vs.setError('Microphone did not open — close other mic apps/tabs and try again')
      vs.setLastOutcome('MIC_ACQUIRE_TIMEOUT')
    } else {
      vs.setError('Browser does not support microphone capture')
      vs.setLastOutcome('MIC_DEVICE_UNAVAILABLE')
    }
    vs.setMicState('idle')
    throw err
  }

  // The server consent + WS-open work below goes through the SSH tunnel to the
  // VPS. If that tunnel is momentarily down the API 502s and fetchApi retries
  // with backoff (up to ~60s) — pinning the button at 'requesting_permission'
  // the whole time (the "hangs forever on Requesting mic…" symptom). Race the
  // whole consent→capture chain against a short watchdog so a flaky/down tunnel
  // degrades to a fast, typed "Voice server unreachable" instead of a dead
  // button. Any throw here resets micState to 'idle' (no stuck window).
  // P4: an AbortController lets the watchdog CANCEL the in-flight chain. Without it,
  // _withTimeout rejected but _consentAndStart→startVoice kept running and installed
  // a recorder over the just-torn-down mic (the "resurrected zombie recording after
  // Voice server unreachable" bug). startVoice checks signal.aborted after each await.
  const abort = new AbortController()
  try {
    await _withTimeout(_consentAndStart(abort.signal), CONSENT_START_TIMEOUT_MS, abort)
  } catch (err) {
    if (err instanceof ConsentRequiredError) {
      // Server grant refused (not a timeout) — the inline "Enable Push-to-Talk"
      // retry affordance already showing. Re-throw so handleMicToggle no-ops.
      throw err
    }
    // Aborting before capture handed off the stream to the recorder — release
    // the gesture mic so iOS doesn't hold a leaked session / lit mic indicator.
    releaseGestureStream()
    const timedOut = err instanceof Error && err.name === 'VoiceStartTimeout'
    vs.setError(
      timedOut
        ? 'Voice server unreachable — check connection and try again'
        : 'Could not start voice — try again',
    )
    vs.setLastOutcome(timedOut ? 'VOICE_START_TIMEOUT' : 'VOICE_START_FAILED')
    vs.setMicState('idle')
    throw err
  }
}

/** ~8s ceiling on the consent→capture chain — well under fetchApi's 60s, so a
 * down tunnel surfaces fast instead of a minute-long dead button. */
const CONSENT_START_TIMEOUT_MS = 8000

/** Reject with a VoiceStartTimeout if `p` does not settle within `ms`. On timeout,
 *  ALSO abort the passed controller so the raced chain cancels itself (P4) instead
 *  of running on and resurrecting a torn-down capture. */
function _withTimeout<T>(p: Promise<T>, ms: number, abort?: AbortController): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const t = setTimeout(() => {
      abort?.abort()
      reject(Object.assign(new Error('voice start timed out'), { name: 'VoiceStartTimeout' }))
    }, ms)
    p.then(
      (v) => { clearTimeout(t); resolve(v) },
      (e) => { clearTimeout(t); reject(e) },
    )
  })
}

/** The capture chain, raced against the watchdog above.
 *
 * DURABLE consent model: the governed voice WS AUTO-GRANTS for the authenticated
 * principal on connect. So the client-side consent GET/POST are NO LONGER in the
 * critical path — they run FIRE-AND-FORGET purely to (a) refresh the local
 * grant-id for draft stamping and (b) keep the "disable" affordance accurate. We
 * go straight to startVoice() so a slow/flaky consent round-trip through the SSH
 * tunnel can never (i) trip the 8s watchdog into a false "Voice server unreachable"
 * nor (ii) flash "consent not granted". The WS is the real, fail-closed gate. */
async function _consentAndStart(signal?: AbortSignal): Promise<void> {
  const vs = useVoiceStore.getState()
  vs.setConsentState('active')

  // fire-and-forget: refresh local grant id, never block or error the capture.
  void (async () => {
    try {
      const consent = await getConsent('push_to_talk')
      if (consent.active) { _rememberGrantId(consent); return }
      const granted = await grantPushToTalk()
      if (granted.active) _rememberGrantId(granted)
    } catch {
      // WS auto-grants for the authenticated principal — nothing to surface.
    }
  })()

  // P4: pass the abort signal so startVoice can bail after its awaits if the
  // watchdog fired mid-flight (no recorder installed over a torn-down mic).
  await startVoice(signal)
}

/** Stop capture; a committed turn dispatches into chat via the controller. */
function stopCapture(): void {
  stopVoice()
}

/** Tear down the voice session (WS, timers, held messages). */
function closeSession(): void {
  destroyVoice()
}

/**
 * P4S31 Voice Convergence: the capture context the governed voice WS control
 * frame needs — the active push-to-talk grant id, this surface's device id, and
 * a source label. Returns an empty grant id when no live grant exists (the WS
 * will then refuse with CONSENT_DENIED — server truth, never faked client-side).
 */
export async function voiceConsentForCapture(): Promise<{
  source: string
  deviceRegistryId: string
  consentGrantId: string
}> {
  const device = deviceRegistryId()
  let consentGrantId = ''
  try {
    const state = await getConsent('push_to_talk')
    if (state.active && state.grant && typeof state.grant.grant_id === 'string') {
      consentGrantId = state.grant.grant_id as string
    }
  } catch {
    // fail-closed: no grant id → the WS refuses capture.
  }
  return { source: currentVoiceSource(), deviceRegistryId: device, consentGrantId }
}

/**
 * The capture surface label sent as `source` on the control frame. Derived from
 * the platform at RUNTIME (never hardcoded) so web / mobile-web / iOS / android /
 * Electron are distinguishable in the one ledger. Capacitor native reports its
 * real platform ('ios' / 'android'); Electron reports 'electron'; browsers
 * report 'web' / 'mobile_web'.
 */
function currentVoiceSource(): string {
  // Capacitor native shell (iOS / Android) — the real device platform.
  const cap = (window as Record<string, unknown>).Capacitor as
    | { getPlatform?: () => string; isNativePlatform?: () => boolean }
    | undefined
  try {
    if (cap?.isNativePlatform?.() && cap.getPlatform) {
      const p = cap.getPlatform() // 'ios' | 'android' | 'web'
      if (p === 'ios' || p === 'android') return p
    }
  } catch {
    // fall through to web detection
  }
  try {
    const isElectron = Boolean((window as Record<string, unknown>).cockpit)
    if (isElectron) return 'electron'
    const ua = navigator.userAgent || ''
    if (/Mobi|Android|iPhone|iPad/i.test(ua)) return 'mobile_web'
    return 'web'
  } catch {
    return 'web'
  }
}

export const desktopBrowserVoiceAdapter = {
  platform: 'desktop_browser' as const,
  activationMode: 'push_to_talk' as const,
  getConsent,
  requestConsent,
  revokeConsent,
  grantPushToTalk,
  startCapture,
  stopCapture,
  closeSession,
  voiceConsentForCapture,
}
