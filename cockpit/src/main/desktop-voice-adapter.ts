/**
 * desktop-voice-adapter — P4S-31D-3 SCAFFOLD (flag-disabled, no activation).
 *
 * Electron main-process shell for the desktop-app PlatformVoiceAdapter from
 * docs/VOICE_INTENT_CONTRACT.md, mirroring the shape of the shipped desktop
 * BROWSER adapter (cockpit/src/renderer/api/platform-voice-adapter.ts, PR #230).
 *
 * THIS FILE IS A SCAFFOLD. It implements the full PlatformVoiceAdapter method
 * surface (requestConsent / openSession / startCapture / stopCapture /
 * closeSession) but EVERY method returns a typed DISABLED refusal while
 * DESKTOP_VOICE_ENABLED is false. There is:
 *   - NO microphone capture (no media capture API, no native audio path)
 *   - NO wake-word runtime (no on-device detector, no always-on listener)
 *   - NO IPC registration (nothing in index.ts imports or activates this)
 *
 * Flag discipline: DESKTOP_VOICE_ENABLED is a hard build-time constant, false.
 * It is deliberately NOT read from the environment, config files, IPC
 * messages, or any renderer/client input — the only way to enable it is a code
 * change shipped in the P4S-31D-3 implementation packet. This is the
 * mechanical guard against premature activation.
 *
 * Contract invariants this scaffold binds to (VoiceIntentContract §Non-bypass):
 * - Output of the future implementation is ONLY a chat message via
 *   chatStore.sendMessage(text, source='voice', routing, voice_turn_id)
 *   -> POST /advisor/converse. The voice path NEVER calls the deterministic
 *   intent classifier directly, never posts to the intent-loop submit route,
 *   never invokes a governed mutation, and never calls any model provider.
 *   Voice's entire job is to put a transcript into the existing chat seam.
 * - Fail-closed consent: capture opens ONLY behind an active
 *   VoiceConsentGrant(mode) (substrate/workstation/voice_consent.py).
 *   push_to_talk is the first grantable mode; wake_word becomes grantable in
 *   the P4S-31D-3 implementation packet, always_on only in P4S-31D-6.
 *   OS mic permission (macOS TCC / Windows privacy) is the second,
 *   independent layer — both required, either missing = refusal.
 * - No identity: the operator principal is resolved server-side from the
 *   authenticated Clerk session. This adapter sends only device + mode.
 * - No audio persistence, transcript-only transit: audio buffers live and die
 *   in-process; only TranscriptEvent text ever crosses the chat seam.
 * - CPU Gate Law: any future on-device wake runtime runs CPU-budgeted and
 *   NEVER on the orchestrator-role node (no mic on the VPS).
 */

/**
 * Hard build-time flag. Default (and only possible value in this scaffold)
 * is false. Not overridable by env, config, IPC, or any client input.
 */
export const DESKTOP_VOICE_ENABLED: boolean = false

export type VoiceActivationMode = 'push_to_talk' | 'wake_word' | 'always_on'

/** Typed refusal returned by every method while the scaffold flag is off. */
export interface DesktopVoiceRefusal {
  ok: false
  code: 'DESKTOP_VOICE_DISABLED'
  platform: 'desktop_app'
  method: string
  reason: string
}

/** Union result type: the implementation packet adds the success arms. */
export type DesktopVoiceResult = DesktopVoiceRefusal

function disabledRefusal(method: string): DesktopVoiceRefusal {
  return {
    ok: false,
    code: 'DESKTOP_VOICE_DISABLED',
    platform: 'desktop_app',
    method,
    reason:
      'desktop app voice is a flag-disabled scaffold (P4S-31D-3 not started); ' +
      'no capture, no wake runtime, no consent surface is active',
  }
}

/**
 * Request a UMH VoiceConsentGrant(mode) for this device.
 * Scaffold: refuses. Implementation will POST the governed consent grant
 * (voice_consent_grant MutationSpec) exactly like the browser adapter — and
 * will additionally require the OS microphone permission before any capture.
 */
export async function requestConsent(
  _mode: VoiceActivationMode,
): Promise<DesktopVoiceResult> {
  return disabledRefusal('requestConsent')
}

/**
 * Open a VoiceSession (consent_pending -> consent_granted -> mic_opening ...).
 * Scaffold: refuses. Implementation binds device_session_id + activation_mode
 * and verifies an ACTIVE VoiceConsentGrant for that exact mode, fail-closed.
 */
export async function openSession(
  _mode: VoiceActivationMode,
): Promise<DesktopVoiceResult> {
  return disabledRefusal('openSession')
}

/**
 * Begin push-to-talk capture. Scaffold: refuses — there is no capture code in
 * this module at all. When activated it will be a THIN edge on the ONE governed
 * voice WS (/api/umh/voice/ws), exactly like the browser + CLI edges: capture
 * PCM16 locally, stream via the GAP F protocol, and exit through
 * sendMessage(text, 'voice', routing, voice_turn_id). No separate STT engine.
 */
export async function startCapture(): Promise<DesktopVoiceResult> {
  return disabledRefusal('startCapture')
}

/**
 * Stop capture; a committed turn would dispatch into chat as a verbatim
 * transcript. Scaffold: refuses (nothing is ever capturing).
 */
export async function stopCapture(): Promise<DesktopVoiceResult> {
  return disabledRefusal('stopCapture')
}

/** Tear down the voice session. Scaffold: refuses (no session can exist). */
export async function closeSession(): Promise<DesktopVoiceResult> {
  return disabledRefusal('closeSession')
}

export const desktopAppVoiceAdapter = {
  platform: 'desktop_app' as const,
  enabled: DESKTOP_VOICE_ENABLED,
  requestConsent,
  openSession,
  startCapture,
  stopCapture,
  closeSession,
}
