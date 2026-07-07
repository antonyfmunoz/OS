/**
 * PlatformVoiceAdapter — desktop browser push-to-talk (P4S-31D-1).
 *
 * The ONE adapter interface from docs/VOICE_INTENT_CONTRACT.md, implemented for
 * the desktop browser over the seams that already ship:
 *
 *   capture/STT      -> voice-controller.ts (ws://:8096/voice PCM16 bridge)
 *   transcript exit  -> _dispatchCommittedTurn -> chatStore.addVoiceTranscript
 *                       -> sendMessage(text, 'voice', ...) -> POST /advisor/converse
 *
 * Contract invariants this module enforces:
 * - Output is ALWAYS a chat message via source='voice' (delegated to the
 *   controller's dispatch). This adapter never calls the intent classifier,
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
import { useVoiceStore } from '../stores/voiceStore'

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
  } else {
    vs.setConsentState('required')
    vs.setError(out.error || 'Consent grant failed — try again')
  }
  return out
}

/**
 * Open push-to-talk capture behind the fail-closed consent gate.
 * Throws ConsentRequiredError (and sets the typed VoiceOutcome + consentState
 * 'required' so the UI renders the inline enable control) when no active
 * VoiceConsentGrant(push_to_talk) exists for this device.
 */
async function startCapture(): Promise<void> {
  const consent = await getConsent('push_to_talk')
  const vs = useVoiceStore.getState()
  if (!consent.active) {
    vs.setConsentState('required')
    vs.setError('Voice consent required — enable push-to-talk for this device')
    vs.setLastOutcome('CONSENT_REQUIRED')
    vs.setMicState('idle')
    throw new ConsentRequiredError(
      consent.error || 'no active VoiceConsentGrant(push_to_talk) for this device',
    )
  }
  vs.setConsentState('active')
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
