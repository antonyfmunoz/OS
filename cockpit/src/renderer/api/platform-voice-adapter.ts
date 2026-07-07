/**
 * PlatformVoiceAdapter — desktop browser push-to-talk (P4S-31D-1).
 *
 * The ONE adapter interface from docs/VOICE_INTENT_CONTRACT.md, implemented for
 * the desktop browser over the seams that already ship:
 *
 *   capture/STT      -> voice-controller.ts (ws://:8096/voice PCM16 bridge)
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
import { ensureBrowserMicPermission } from './voice-ws'
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

function deviceRegistryId(): string {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useDeviceSessionStore } = require('../stores/deviceSessionStore')
    const routing = useDeviceSessionStore.getState().getRoutingMetadata() as Record<string, string>
    if (routing.source_device_id) return routing.source_device_id
  } catch {
    // device session store unavailable — fall through to role-based id
  }
  return 'desktop_browser'
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
  try {
    return await fetchApi<VoiceConsentState>('/voice/consent/grant', {
      method: 'POST',
      body: JSON.stringify({ device_registry_id: deviceRegistryId(), mode }),
    })
  } catch (e) {
    return { active: false, error: e instanceof Error ? e.message : 'consent grant failed' }
  }
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
  const vs = useVoiceStore.getState()

  // (1) Returning device: an active grant already exists — straight to capture.
  const consent = await getConsent('push_to_talk')
  if (consent.active) {
    vs.setConsentState('active')
    _rememberGrantId(consent)
    await startVoice()
    return
  }

  // (2) Fresh device: the mic tap authorizes both layers. Browser permission
  // first (its own user-gesture prompt), then the server grant automatically.
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
    } else {
      vs.setError('Browser does not support microphone capture')
      vs.setLastOutcome('MIC_DEVICE_UNAVAILABLE')
    }
    vs.setMicState('idle')
    throw err
  }

  // Browser permission granted → auto-request the UMH grant in the SAME flow.
  const granted = await grantPushToTalk()
  if (!granted.active) {
    // (3) SERVER grant failed → surface the explicit enable RETRY affordance.
    // grantPushToTalk already set consentState 'required' + the error text.
    vs.setLastOutcome('CONSENT_REQUIRED')
    vs.setMicState('idle')
    throw new ConsentRequiredError(
      granted.error || 'no active VoiceConsentGrant(push_to_talk) for this device',
    )
  }

  await startVoice()
}

/** Stop capture; a committed turn dispatches into chat via the controller. */
function stopCapture(): void {
  stopVoice()
}

/** Tear down the voice session (WS, timers, held messages). */
function closeSession(): void {
  destroyVoice()
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
}
