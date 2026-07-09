/**
 * voiceMessageStore — P4S-31D1-B voice-MESSAGE rail (lanes C+D+E).
 *
 * Voice recording produces a reviewable VoiceMessageDraft, NEVER a chat
 * message. The ONLY path from a draft into Cockpit Chat is the explicit
 * operator send (sendDraft), which uploads the audio artifact through the
 * existing /chat/upload seam and then calls chatStore.addVoiceTranscript
 * → sendMessage(text, 'voice', …) → POST /advisor/converse.
 *
 * Contract: data/umh/voice/voice_message_contract.json (P4S-31D1-B).
 * Invariants enforced here:
 *  - draft.status transitions: recording → transcribing → ready →
 *    (sent | deleted); failed → (retry → transcribing) | deleted
 *  - transcript_partial is provisional display ONLY — it never reaches
 *    chatStore messages, setDraftMessage, or the input box
 *  - audio is NEVER discarded on STT failure (revokeObjectURL only on delete)
 *  - send is gated on transcript_status ∈ {final, edited} and status == ready
 *  - diagnostics carry timings and counts, never transcript text
 */

import { create } from 'zustand'
import { API_BASE, authHeader } from '../api/client'
import { useChatStore, type MediaAttachment } from './chatStore'

const log = (stage: string, ...args: unknown[]) =>
  console.log(`[VoiceMessage] ${stage}`, ...args)

// ── VadConfig (contract defaults; module-level, values overridable) ──────────

export interface VadConfig {
  /** Audio level below which a window counts as silence. */
  silence_threshold_level: number
  /** Minimum speech before a turn is accepted at all (else NO_SPEECH). */
  min_speech_ms: number
  /** Silences shorter than this are ignored (sentence-internal). */
  intra_utterance_pause_ms: number
  /** Continuous silence required before auto-FINALIZE (finalize != send). */
  min_silence_before_finalize_ms: number
  /** Hard cap; finalizes to review. */
  max_recording_ms: number
  /** Sending ALWAYS requires explicit operator action. No current mode permits true. */
  auto_send: boolean
}

export const VAD_CONFIG: VadConfig = {
  silence_threshold_level: 0.02,
  min_speech_ms: 400,
  intra_utterance_pause_ms: 1500,
  min_silence_before_finalize_ms: 2500,
  max_recording_ms: 120000,
  auto_send: false,
}

// ── Contract types ────────────────────────────────────────────────────────────

export type TranscriptStatus = 'pending' | 'partial' | 'final' | 'failed' | 'edited'
export type DraftStatus = 'recording' | 'transcribing' | 'ready' | 'sent' | 'failed' | 'deleted'
/**
 * Contract enum. The max-duration cap is a system-initiated finalize with no
 * dedicated enum value in the binding contract — it records 'silence_timeout'
 * (system-driven finalize bucket). Flagged in the packet report.
 */
export type FinalizedBy = 'manual_stop' | 'silence_timeout' | 'cancel' | null

export interface AudioArtifactRef {
  artifact_id: string
  url: string
  content_type: string
  size_bytes: number
  sha256: string
}

export interface SilenceWindow {
  start_ms: number
  end_ms: number
  /** true when this window triggered finalization; false when ignored. */
  finalizing: boolean
}

/** Timings and counts only — transcript content is NEVER stored here. */
export interface VoiceDiagnostics {
  speech_start: number | null
  speech_end: number | null
  silence_windows: SilenceWindow[]
  transcript_partial_events: number
  transcript_final_at: number | null
  finalized_by: FinalizedBy
  // P4S31 convergence: STT is local faster-whisper on the ONE governed runtime.
  // 'groq_whisper' is retained only so old persisted drafts still type-check.
  stt_engine: 'faster_whisper' | 'groq_whisper' | 'other'
}

export interface VoiceMessageDraft {
  /** vmd-<uuid> — client correlation id. */
  draft_id: string
  /** vt-<uuid> — threads capture → transcript → chat → loop. */
  voice_turn_id: string
  /** Recorded audio. NEVER null after recording stops; preserved on STT failure. */
  audioBlob: Blob | null
  /** Object URL for local playback (revoked ONLY on delete). */
  audioUrl: string | null
  audio_artifact: AudioArtifactRef | null
  /** Finalized text, editable by operator before send. */
  transcript: string
  /** Provisional display ONLY — MUST NEVER be committed as chat content. */
  transcript_partial: string
  transcript_status: TranscriptStatus
  confidence: number | null
  duration_ms: number
  device_registry_id: string
  session_id: string
  consent_grant_id: string
  created_at: string
  finalized_by: FinalizedBy
  status: DraftStatus
  diagnostics: VoiceDiagnostics
  error: string | null
}

// ── RecordingSessionState machine (contract) ─────────────────────────────────

export type RecordingSessionState =
  | 'idle'
  | 'requesting_consent'
  | 'requesting_permission'
  | 'recording'
  | 'paused_speech_gap'
  | 'finalizing'
  | 'transcribing'
  | 'review'
  | 'sending'
  | 'sent'
  | 'failed'
  | 'cancelled'

const RECORDING_STATE_TRANSITIONS: Record<RecordingSessionState, RecordingSessionState[]> = {
  idle: ['requesting_consent', 'requesting_permission', 'recording'],
  requesting_consent: ['requesting_permission', 'idle', 'failed'],
  requesting_permission: ['recording', 'idle', 'failed'],
  // paused_speech_gap is INTERNAL: short silences render a paused indicator
  // at most; they never finalize by themselves.
  recording: ['paused_speech_gap', 'finalizing', 'cancelled', 'failed'],
  paused_speech_gap: ['recording', 'finalizing', 'cancelled', 'failed'],
  finalizing: ['transcribing', 'failed', 'cancelled'],
  transcribing: ['review', 'failed', 'cancelled'],
  // review is mandatory before sending (auto_send default false).
  review: ['sending', 'transcribing', 'cancelled', 'failed'],
  sending: ['sent', 'failed'],
  sent: ['idle'],
  failed: ['transcribing', 'cancelled', 'idle'],
  cancelled: ['idle'],
}

function _uuid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 14)}`
}

async function _sha256Hex(blob: Blob): Promise<string> {
  try {
    const buf = await blob.arrayBuffer()
    const digest = await crypto.subtle.digest('SHA-256', buf)
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')
  } catch {
    // crypto.subtle unavailable (non-secure context) — integrity hash skipped.
    return ''
  }
}

function _normalizeAudioContentType(t: string): string {
  const base = (t || 'audio/webm').split(';')[0].trim()
  if (!base.startsWith('audio/')) return 'audio/webm'
  // iOS Safari records audio/mp4 (AAC); some engines report audio/x-m4a.
  if (base === 'audio/x-m4a' || base === 'audio/m4a' || base === 'audio/aac') return 'audio/mp4'
  return base
}

/** Server-agreed extension for a normalized audio content type. Must stay in
 * lockstep with the upload seam's accept-list (_AUDIO_EXT in
 * transports/api/cockpit_chat_routes.py). iOS mp4 → .m4a. */
function _audioExtFor(contentType: string): string {
  switch (contentType) {
    case 'audio/wav':
      return '.wav'
    case 'audio/mp4':
      return '.m4a'
    case 'audio/ogg':
      return '.ogg'
    default:
      return '.weba' // audio/webm — matches server _AUDIO_EXT (.weba, not .webm)
  }
}

interface CreateDraftInput {
  voiceTurnId: string
  deviceRegistryId: string
  sessionId: string
}

interface VoiceMessageState {
  drafts: VoiceMessageDraft[]
  activeDraftId: string | null
  recordingState: RecordingSessionState
  /** vcg-<id> of the active VoiceConsentGrant(push_to_talk); set by the adapter. */
  activeConsentGrantId: string
  /**
   * Live client-computed capture RMS (0..1) for the active recording, written
   * by the controller's ~10Hz meter poll from client.clientRms. The recording
   * card reads THIS field — it does not run its own audio loop. 0 when idle.
   */
  captureRms: number
  /** Peak captureRms seen this session — powers the "mic appears silent" hint. */
  captureRmsPeak: number
  /** ms the current recording has run with peak RMS still ~0 (silence hint gate). */
  captureSilentMs: number

  setActiveConsentGrantId: (id: string) => void
  /** Meter poll writes the live RMS + rolling peak + silent-duration here. */
  setCaptureRms: (rms: number, silentMs: number) => void
  /** Reset meter state (recording start / stop). */
  resetCaptureMeter: () => void
  transitionRecordingState: (to: RecordingSessionState) => void
  /** ROOT A: unconditional escape to a terminal state (teardown only). */
  _forceState: (to: RecordingSessionState) => void

  createDraft: (input: CreateDraftInput) => VoiceMessageDraft
  updateActivePartial: (text: string) => void
  setActiveTranscriptPreview: (text: string) => void
  markSpeechStart: (ts: number) => void
  recordSilenceWindow: (window: SilenceWindow) => void
  finalizeActiveDraft: (
    finalizedBy: Exclude<FinalizedBy, null>,
    durationMs: number,
    speechStart: number | null,
    speechEnd: number | null,
  ) => void
  attachAudio: (blob: Blob) => void
  completeActiveTranscript: (text: string, confidence?: number | null) => void
  markNoSpeech: () => void
  markTranscriptFailed: (error: string) => void
  // ROOT F: draft-id-PARAMETERIZED completion. The controller captures the draft id
  // at finalize time and passes it here, so a concurrent delete/new-recording that
  // nulls (or rebinds) activeDraftId mid-flight can never make the returning
  // transcript land on the WRONG draft. The active-* variants above stay for
  // callers that legitimately target the live draft.
  completeTranscript: (draftId: string | null, text: string, confidence?: number | null) => void
  markFailed: (draftId: string | null, error: string) => void

  editTranscript: (draftId: string, text: string) => void
  beginRetry: (draftId: string) => void
  updateRetryPartial: (draftId: string, text: string) => void
  completeRetry: (draftId: string, text: string, engine?: VoiceDiagnostics['stt_engine']) => void
  markRetryFailed: (draftId: string, error: string) => void
  retryDraft: (draftId: string) => void

  sendDraft: (draftId: string) => Promise<void>
  deleteDraft: (draftId: string) => void
}

export const useVoiceMessageStore = create<VoiceMessageState>((set, get) => {
  const _update = (
    draftId: string | null,
    fn: (d: VoiceMessageDraft) => Partial<VoiceMessageDraft>,
  ): void => {
    if (!draftId) return
    set((s) => ({
      drafts: s.drafts.map((d) => (d.draft_id === draftId ? { ...d, ...fn(d) } : d)),
    }))
  }

  const _get = (draftId: string | null): VoiceMessageDraft | undefined =>
    get().drafts.find((d) => d.draft_id === draftId)

  return {
    drafts: [],
    activeDraftId: null,
    recordingState: 'idle',
    activeConsentGrantId: '',
    captureRms: 0,
    captureRmsPeak: 0,
    captureSilentMs: 0,

    setActiveConsentGrantId: (id) => set({ activeConsentGrantId: id }),

    setCaptureRms: (rms, silentMs) =>
      set((s) => ({
        captureRms: rms,
        captureRmsPeak: rms > s.captureRmsPeak ? rms : s.captureRmsPeak,
        captureSilentMs: silentMs,
      })),

    resetCaptureMeter: () => set({ captureRms: 0, captureRmsPeak: 0, captureSilentMs: 0 }),

    transitionRecordingState: (to) => {
      const from = get().recordingState
      if (from === to) return
      const allowed = RECORDING_STATE_TRANSITIONS[from] || []
      if (!allowed.includes(to)) {
        // ROOT A: a legal app-transition that isn't in the table is a bug worth a
        // log — BUT teardown/terminal transitions (idle/cancelled) must NEVER be
        // silently dropped, or the machine strands (retry-from-idle, delete-during-
        // finalize). Teardown uses _forceState(); this path stays strict for
        // genuine app transitions and just records the ignore.
        log('recording_state_transition_ignored', `${from} -> ${to}`)
        return
      }
      log('recording_state', `${from} -> ${to}`)
      set({ recordingState: to })
    },

    // ROOT A: unconditional escape to a terminal state. teardownCapture / abort /
    // delete route through this so the machine can ALWAYS reach 'idle' (or
    // 'cancelled') no matter the current state — a stuck recordingState can never
    // block the next capture. Not for ordinary app transitions (use
    // transitionRecordingState); reserved for terminal teardown.
    _forceState: (to) => {
      const from = get().recordingState
      if (from === to) return
      log('recording_state_forced', `${from} -> ${to}`)
      set({ recordingState: to })
    },

    createDraft: (input) => {
      const draft: VoiceMessageDraft = {
        draft_id: `vmd-${_uuid()}`,
        voice_turn_id: input.voiceTurnId,
        audioBlob: null,
        audioUrl: null,
        audio_artifact: null,
        transcript: '',
        transcript_partial: '',
        transcript_status: 'pending',
        confidence: null,
        duration_ms: 0,
        device_registry_id: input.deviceRegistryId,
        session_id: input.sessionId,
        consent_grant_id: get().activeConsentGrantId,
        created_at: new Date().toISOString(),
        finalized_by: null,
        status: 'recording',
        diagnostics: {
          speech_start: null,
          speech_end: null,
          silence_windows: [],
          transcript_partial_events: 0,
          transcript_final_at: null,
          finalized_by: null,
          stt_engine: 'faster_whisper',
        },
        error: null,
      }
      set((s) => ({
        drafts: [...s.drafts, draft],
        activeDraftId: draft.draft_id,
        recordingState: 'recording',
      }))
      log('draft_created', draft.draft_id, draft.voice_turn_id)
      return draft
    },

    // Provisional display ONLY. Diagnostics count the event; the content is
    // never stored in diagnostics and never leaves this store toward chat.
    updateActivePartial: (text) => {
      _update(get().activeDraftId, (d) => ({
        transcript_partial: text,
        transcript_status: d.transcript_status === 'pending' ? 'partial' : d.transcript_status,
        diagnostics: {
          ...d.diagnostics,
          transcript_partial_events: d.diagnostics.transcript_partial_events + 1,
        },
      }))
    },

    setActiveTranscriptPreview: (text) => {
      _update(get().activeDraftId, () => ({
        transcript: text,
        transcript_partial: '',
        transcript_status: 'partial',
      }))
    },

    markSpeechStart: (ts) => {
      _update(get().activeDraftId, (d) =>
        d.diagnostics.speech_start === null
          ? { diagnostics: { ...d.diagnostics, speech_start: ts } }
          : {},
      )
    },

    recordSilenceWindow: (window) => {
      _update(get().activeDraftId, (d) => ({
        diagnostics: {
          ...d.diagnostics,
          silence_windows: [...d.diagnostics.silence_windows, window],
        },
      }))
    },

    finalizeActiveDraft: (finalizedBy, durationMs, speechStart, speechEnd) => {
      get().transitionRecordingState('finalizing')
      _update(get().activeDraftId, (d) => ({
        status: 'transcribing',
        finalized_by: finalizedBy,
        duration_ms: durationMs,
        diagnostics: {
          ...d.diagnostics,
          finalized_by: finalizedBy,
          speech_start: d.diagnostics.speech_start ?? speechStart,
          speech_end: speechEnd,
        },
      }))
    },

    // Audio is NEVER discarded — attached even when STT already failed.
    attachAudio: (blob) => {
      const draftId = get().activeDraftId
      const existing = _get(draftId)
      if (!existing) return
      const url = URL.createObjectURL(blob)
      _update(draftId, () => ({ audioBlob: blob, audioUrl: url }))
      log('audio_attached', draftId, `bytes=${blob.size}`)
    },

    completeActiveTranscript: (text, confidence = null) => {
      const draftId = get().activeDraftId
      get().transitionRecordingState('review')
      _update(draftId, (d) => ({
        transcript: text,
        transcript_partial: '',
        transcript_status: 'final',
        confidence,
        status: 'ready',
        diagnostics: { ...d.diagnostics, transcript_final_at: Date.now() },
      }))
      set({ activeDraftId: null })
      log('draft_ready', draftId)
    },

    // NO_SPEECH: recoverable draft with retry affordance — never a chat message.
    markNoSpeech: () => {
      const draftId = get().activeDraftId
      get().transitionRecordingState('failed')
      _update(draftId, () => ({
        status: 'failed',
        transcript_status: 'failed',
        error: 'NO_SPEECH',
      }))
      set({ activeDraftId: null })
      log('draft_no_speech', draftId)
    },

    // STT failure path: draft kept, audio kept (no revoke, no discard).
    markTranscriptFailed: (error) => {
      const draftId = get().activeDraftId
      get().transitionRecordingState('failed')
      _update(draftId, () => ({
        status: 'failed',
        transcript_status: 'failed',
        error,
      }))
      set({ activeDraftId: null })
      log('draft_transcript_failed', draftId, error)
    },

    // ROOT F — draft-id-parameterized completion. Writes to the PASSED draft id
    // (captured at finalize time), never the live activeDraftId. Only clears
    // activeDraftId if it still points at THIS draft — so a concurrent new
    // recording that already rebound activeDraftId is left untouched (no cross-
    // draft transcript write, no marking the wrong live draft ready).
    completeTranscript: (draftId, text, confidence = null) => {
      if (!draftId) return
      if (!_get(draftId)) return // draft deleted mid-flight — drop the late result
      get().transitionRecordingState('review')
      _update(draftId, (d) => ({
        transcript: text,
        transcript_partial: '',
        transcript_status: 'final',
        confidence,
        status: 'ready',
        diagnostics: { ...d.diagnostics, transcript_final_at: Date.now() },
      }))
      if (get().activeDraftId === draftId) set({ activeDraftId: null })
      log('draft_ready', draftId)
    },

    markFailed: (draftId, error) => {
      if (!draftId) return
      if (!_get(draftId)) return // draft deleted mid-flight — nothing to mark
      get().transitionRecordingState('failed')
      _update(draftId, () => ({
        status: 'failed',
        transcript_status: 'failed',
        error,
      }))
      if (get().activeDraftId === draftId) set({ activeDraftId: null })
      log('draft_transcript_failed', draftId, error)
    },

    editTranscript: (draftId, text) => {
      _update(draftId, (d) =>
        d.status === 'ready' ? { transcript: text, transcript_status: 'edited' } : {},
      )
    },

    beginRetry: (draftId) => {
      get().transitionRecordingState('transcribing')
      _update(draftId, () => ({
        status: 'transcribing',
        transcript_status: 'pending',
        transcript_partial: '',
        error: null,
      }))
    },

    updateRetryPartial: (draftId, text) => {
      _update(draftId, (d) => ({
        transcript_partial: text,
        diagnostics: {
          ...d.diagnostics,
          transcript_partial_events: d.diagnostics.transcript_partial_events + 1,
        },
      }))
    },

    completeRetry: (draftId, text, engine = 'faster_whisper') => {
      get().transitionRecordingState('review')
      _update(draftId, (d) => ({
        transcript: text,
        transcript_partial: '',
        transcript_status: 'final',
        status: 'ready',
        error: null,
        diagnostics: { ...d.diagnostics, transcript_final_at: Date.now(), stt_engine: engine },
      }))
      log('retry_complete', draftId)
    },

    // Typed retry failure: audio kept (no revoke, no discard).
    markRetryFailed: (draftId, error) => {
      get().transitionRecordingState('failed')
      _update(draftId, () => ({
        status: 'failed',
        transcript_status: 'failed',
        error,
      }))
      log('retry_failed', draftId, error)
    },

    retryDraft: (draftId) => {
      // Lane E: re-run STT against the preserved audio. The controller owns
      // the WS transport; lazy require avoids a module cycle.
      try {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const controller = require('../api/voice-controller')
        controller.retryDraftTranscription(draftId)
      } catch (e) {
        get().markRetryFailed(draftId, 'RETRY_UNAVAILABLE')
        log('retry_dispatch_failed', e)
      }
    },

    sendDraft: async (draftId) => {
      const draft = _get(draftId)
      if (!draft) return
      // Send gate (contract ux_states.operator_actions.send): only when
      // transcript_status ∈ {final, edited} and status == ready. Explicit
      // operator action is the ONLY way a draft becomes a chat message.
      if (draft.status !== 'ready') {
        log('send_refused_status', draftId, draft.status)
        return
      }
      if (draft.transcript_status !== 'final' && draft.transcript_status !== 'edited') {
        log('send_refused_transcript_status', draftId, draft.transcript_status)
        return
      }
      if (!draft.transcript.trim()) {
        log('send_refused_empty_transcript', draftId)
        return
      }

      // Re-entrancy latch: flip status OUT of 'ready' SYNCHRONOUSLY before any await.
      // The send gate above requires status==='ready', so a second (double-click) call
      // now hits send_refused_status and no-ops. Previously status was flipped to
      // 'transcribing' then IMMEDIATELY back to 'ready', so it stayed 'ready' across the
      // whole upload await and a double-tap sent TWICE (field test 2026-07-08). We hold
      // 'transcribing' (a valid non-'ready' DraftStatus) for the whole send; the failure
      // paths below reset to 'failed' so a failed send can still be retried/deleted.
      get().transitionRecordingState('sending')
      _update(draftId, () => ({ status: 'transcribing' }))
      log('send_start', draftId)

      // 1. Upload the audio artifact through the EXISTING /chat/upload seam.
      let artifact: AudioArtifactRef | null = draft.audio_artifact
      let media: MediaAttachment | null = null
      if (draft.audioBlob) {
        try {
          const contentType = _normalizeAudioContentType(draft.audioBlob.type)
          const ext = _audioExtFor(contentType)
          const file = new File([draft.audioBlob], `voice-message-${draft.draft_id}${ext}`, {
            type: contentType,
          })
          const form = new FormData()
          form.append('file', file)
          const res = await fetch(`${API_BASE}/chat/upload`, {
            method: 'POST',
            body: form,
            headers: await authHeader(), // operator-gated route — send Clerk bearer or 403
          })
          if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`)
          const uploaded = (await res.json()) as MediaAttachment
          media = uploaded
          artifact = {
            artifact_id: uploaded.id,
            url: uploaded.url,
            content_type: uploaded.content_type || contentType,
            size_bytes: uploaded.size ?? draft.audioBlob.size,
            sha256: await _sha256Hex(draft.audioBlob),
          }
          _update(draftId, () => ({ audio_artifact: artifact }))
        } catch (e) {
          // Upload failure: draft failed, audio preserved for retry.
          get().transitionRecordingState('failed')
          _update(draftId, () => ({
            status: 'failed',
            error: e instanceof Error ? e.message : 'AUDIO_UPLOAD_FAILED',
          }))
          log('send_upload_failed', draftId)
          return
        }
      }

      // 2. Explicit send — the ONLY caller of the chat seam for voice.
      try {
        useChatStore.getState().addVoiceTranscript(draft.transcript, draft.voice_turn_id, {
          media: media ? [media] : [],
          meta: {
            draft_id: draft.draft_id,
            artifact_id: artifact?.artifact_id ?? null,
            artifact_url: artifact?.url ?? null,
            duration_ms: draft.duration_ms,
            transcript_status: draft.transcript_status,
            consent_grant_id: draft.consent_grant_id,
          },
        })
      } catch (e) {
        get().transitionRecordingState('failed')
        _update(draftId, () => ({
          status: 'failed',
          error: e instanceof Error ? e.message : 'CHAT_SEND_FAILED',
        }))
        log('send_chat_failed', draftId)
        return
      }

      get().transitionRecordingState('sent')
      _update(draftId, () => ({ status: 'sent' }))
      get().transitionRecordingState('idle')
      log('send_complete', draftId)

      // Voice-response presentation (TTS reveal) — same machinery as before,
      // now armed by the explicit send instead of an auto-dispatch.
      try {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const controller = require('../api/voice-controller')
        controller.notifyVoiceMessageSent(draft.voice_turn_id)
      } catch {
        // presentation wiring is optional — the message is already sent
      }
    },

    // Delete: discard draft + blob; no chat trace. The ONLY path that revokes
    // the blob URL — failure paths always preserve audio.
    deleteDraft: (draftId) => {
      const draft = _get(draftId)
      if (!draft || draft.status === 'sent') return
      if (draft.draft_id === get().activeDraftId) {
        // Cancel an in-flight recording session first (mic + recorder down,
        // finalized_by=cancel, no chat trace).
        try {
          // eslint-disable-next-line @typescript-eslint/no-var-requires
          const controller = require('../api/voice-controller')
          controller.abortActiveRecording()
        } catch {
          // controller unavailable — still remove the draft below
        }
        set({ activeDraftId: null })
        // ROOT A: FORCE the terminal transition — a delete must always land the
        // machine at idle regardless of the current recordingState (transcribing,
        // review, failed…). The old transitionRecordingState pair was silently
        // dropped from states that don't legally reach 'cancelled', stranding
        // recordingState and blocking the next capture.
        get()._forceState('cancelled')
        get()._forceState('idle')
      }
      if (draft.audioUrl) URL.revokeObjectURL(draft.audioUrl)
      set((s) => ({ drafts: s.drafts.filter((d) => d.draft_id !== draftId) }))
      log('draft_deleted', draftId)
    },
  }
})
