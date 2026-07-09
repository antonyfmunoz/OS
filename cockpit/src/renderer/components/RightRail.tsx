import { clsx } from 'clsx'
import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Pencil, Check, Download, Mic, MicOff, Paperclip, X, ChevronDown, ChevronRight, Loader2, Play, Pause } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChatStore, type ChatMessage, type Provenance, type Attachment, type MediaAttachment } from '../stores/chatStore'
import { usePolling } from '../hooks/usePolling'
import { useConfigStore } from '../stores/configStore'
import { useViewContextStore } from '../stores/viewContextStore'
import { useVoiceStore } from '../stores/voiceStore'
import { useVoiceMessageStore, type VoiceMessageDraft } from '../stores/voiceMessageStore'
import { desktopBrowserVoiceAdapter, ConsentRequiredError } from '../api/platform-voice-adapter'
import { getApiKey, fetchApi, API_BASE } from '../api/client'
import type { SuggestedAction } from '../stores/chatStore'
import { useCockpitStore } from '../stores/cockpitStore'
import { useExecutionSummaryStore } from '../stores/executionSummaryStore'


// ROOT E: the ONLY VoiceOutcomes whose error text is shown to the operator. These
// are genuine terminal dead-ends where the mic gave up and the user needs to know
// why. Consent-flow transients (requesting/granting) and recoverable states are
// deliberately excluded so the field-test consent-noise silence is preserved.
const VOICE_TERMINAL_OUTCOMES = new Set<string>([
  'MIC_PERMISSION_DENIED',
  'MIC_DEVICE_UNAVAILABLE',
  'MIC_ACQUIRE_TIMEOUT',
  'VOICE_WS_UNAVAILABLE',
  'VOICE_START_TIMEOUT',
  'VOICE_START_FAILED',
  'STT_FAILED',
  'TIMEOUT',
  // P4S-VOICE-WS-AUTH-PREFLIGHT-001: canonical typed voice-WS failures are all
  // terminal (the mic returned to idle with a real reason) → render their banner.
  'VOICE_WS_AUTH_TOKEN_MISSING',
  'VOICE_WS_AUTH_TOKEN_TIMEOUT',
  'VOICE_WS_AUTH_FAILED',
  'VOICE_WS_UPGRADE_FAILED',
  'VOICE_WS_PROXY_FAILED',
  'VOICE_RUNTIME_TIMEOUT',
  'VOICE_RUNTIME_UNAVAILABLE',
  'VOICE_RUNTIME_NOT_MOUNTED',
])

function safeUrl(url: string): string {
  return /^https?:\/\//i.test(url) ? url : ''
}

const markdownComponents = {
  a: ({ href, children, ...rest }: React.ComponentPropsWithoutRef<'a'>) => (
    <a href={href ?? ''} target="_blank" rel="noopener noreferrer nofollow" {...rest}>{children}</a>
  ),
  img: () => null,
}

export function RightRail() {
  const rightPanelView = useCockpitStore((s) => s.rightPanelView)

  return (
    <div className="flex flex-col w-full h-full bg-surface">
      <div className="flex-1 overflow-y-auto p-3">
        {rightPanelView === 'chat' && <ChatSection />}
        {rightPanelView === 'context' && <ContextSection />}
        {rightPanelView === 'execution' && <ExecutionSection />}
      </div>
    </div>
  )
}

function ProvenanceLine({ provenance }: { provenance: Provenance }) {
  const parts: string[] = []
  if (provenance.node) parts.push(provenance.node)
  if (provenance.harness) parts.push(provenance.harness)
  if (provenance.session) parts.push(`session ${provenance.session}`)
  if (provenance.phase) parts.push(`Phase ${provenance.phase}`)
  if (provenance.pr) parts.push(`PR #${provenance.pr}`)
  if (provenance.task) parts.push(provenance.task)
  if (parts.length === 0) return null

  return (
    <div
      className="flex flex-wrap gap-x-1 gap-y-1 mt-1 mb-2 py-1 px-2 rounded text-[9px] font-mono"
      style={{
        background: 'var(--color-surface)',
        borderLeft: '2px solid var(--color-cyan)',
        color: 'var(--color-text-tertiary)',
      }}
    >
      {parts.map((p, i) => (
        <span key={i}>
          {i > 0 && <span style={{ opacity: 0.4 }}> · </span>}
          {p}
        </span>
      ))}
    </div>
  )
}

function AttachmentLink({ attachment }: { attachment: Attachment }) {
  const handleDownload = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault()
    const url = `${API_BASE}/chat/attachment?path=${encodeURIComponent(attachment.path)}`
    const headers: Record<string, string> = {}
    const key = getApiKey()
    if (key) headers['X-API-Key'] = key
    const res = await fetch(url, { headers })
    if (!res.ok) return
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = attachment.filename
    a.click()
    URL.revokeObjectURL(a.href)
  }, [attachment])

  return (
    <button
      type="button"
      onClick={handleDownload}
      className="flex items-center gap-2 mt-2 py-1 px-2 rounded text-[10px] font-mono transition-colors cursor-pointer w-full text-left"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        color: 'var(--color-cyan)',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-cyan)' }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
    >
      <Download size={10} />
      <span className="truncate flex-1">{attachment.filename}</span>
      <span style={{ color: 'var(--color-text-tertiary)' }}>DOWNLOAD</span>
    </button>
  )
}

/**
 * P4S31 voice message — a playable audio bubble (iMessage / Instagram / Telegram
 * style) for the operator's REAL recorded audio. Play/pause + a scrubbable
 * progress bar + elapsed/total duration. The blob is already captured, uploaded,
 * and attached to the message as an 'audio' MediaAttachment; this just renders it.
 */
function VoiceMessagePlayer({ src }: { src: string }) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [current, setCurrent] = useState(0)

  const fmt = (s: number) => {
    if (!isFinite(s) || s < 0) s = 0
    const m = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  const toggle = useCallback(() => {
    const a = audioRef.current
    if (!a) return
    if (a.paused) { a.play().catch(() => { /* autoplay/gesture guard */ }) }
    else { a.pause() }
  }, [])

  const seek = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const a = audioRef.current
    if (!a || !duration) return
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
    a.currentTime = ratio * duration
  }, [duration])

  const pct = duration > 0 ? (current / duration) * 100 : 0

  return (
    <div
      className="flex items-center gap-1.5 mt-1 px-1.5 py-1 rounded w-full max-w-[180px]"
      style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
    >
      <audio
        ref={audioRef}
        src={src}
        preload="metadata"
        playsInline
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => { setPlaying(false); setCurrent(0) }}
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration || 0)}
        onTimeUpdate={(e) => setCurrent(e.currentTarget.currentTime || 0)}
      />
      <button
        type="button"
        onClick={toggle}
        className="shrink-0 flex items-center justify-center cursor-pointer transition-colors"
        style={{ color: 'var(--color-cyan)' }}
        title={playing ? 'Pause' : 'Play'}
      >
        {playing ? <Pause size={11} /> : <Play size={11} />}
      </button>
      <div className="flex-1 min-w-0">
        <div
          onClick={seek}
          className="h-1 rounded-full cursor-pointer relative"
          style={{ background: 'var(--color-border)' }}
        >
          <div
            className="h-full rounded-full absolute left-0 top-0"
            style={{ width: `${pct}%`, background: 'var(--color-cyan)' }}
          />
        </div>
      </div>
      <span className="shrink-0 text-[8px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
        {fmt(playing || current > 0 ? current : duration)}
      </span>
    </div>
  )
}

function MediaGrid({ media }: { media: MediaAttachment[] }) {
  const apiUrl = API_BASE
  return (
    <div className="flex flex-wrap gap-1 mt-1.5">
      {media.map((m) => {
        const src = m.url.startsWith('/') ? `${apiUrl.replace(/\/api\/umh$/, '')}${m.url}` : m.url
        const previewSrc = m.previewUrl || src
        if (m.media_type === 'video') {
          return (
            <video
              key={m.id}
              src={src}
              controls
              className="rounded max-w-full"
              style={{ maxHeight: 200 }}
            />
          )
        }
        if (m.media_type === 'audio') {
          return <VoiceMessagePlayer key={m.id} src={src} />
        }
        if (m.media_type === 'file') {
          return (
            <a
              key={m.id}
              href={src}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 px-2 py-1.5 rounded bg-surface-raised border border-border text-[10px] font-mono text-text-secondary hover:border-cyan transition-colors"
            >
              <Download size={10} />
              <span className="truncate">{m.filename}</span>
            </a>
          )
        }
        return (
          <a key={m.id} href={src} target="_blank" rel="noopener noreferrer">
            <img
              src={previewSrc}
              alt={m.filename}
              className="rounded cursor-pointer hover:opacity-80 transition-opacity"
              style={{ maxHeight: 200, maxWidth: '100%', objectFit: 'cover' }}
            />
          </a>
        )
      })}
    </div>
  )
}

function MessageBubble({ msg, aiName, onAction }: { msg: ChatMessage; aiName: string; onAction?: (a: SuggestedAction) => void }) {
  if (msg.sender === 'operator') {
    return (
      <div className="px-2 py-2 rounded text-[11px] bg-surface-raised text-text-primary ml-4">
        <div className="flex items-center gap-1 font-mono text-[9px] text-text-tertiary mb-1">
          <span>YOU</span>
          {msg.source === 'voice' && (
            <span className="text-[8px] px-1 rounded bg-surface text-text-tertiary">
              <Mic size={8} className="inline" /> voice
            </span>
          )}
          {msg.media && msg.media.length > 0 && (
            <span className="text-[8px] px-1 rounded bg-surface text-text-tertiary">
              {msg.media.length} media
            </span>
          )}
        </div>
        {msg.content && <p className="whitespace-pre-wrap">{msg.content}</p>}
        {msg.media && msg.media.length > 0 && <MediaGrid media={msg.media} />}
      </div>
    )
  }

  const isReport = msg.intent === 'report'

  return (
    <div className="px-2 py-2 rounded text-[11px] bg-surface-raised text-text-secondary mr-4">
      <div className="flex items-center gap-2 mb-1">
        <span className="font-mono text-[9px] text-text-tertiary">{aiName}</span>
        {isReport && (
          <span
            className="text-[8px] font-mono px-1 rounded uppercase"
            style={{ color: 'var(--color-ok)', background: 'rgba(0,255,136,0.08)' }}
          >
            report
          </span>
        )}
        {msg.intent && msg.intent !== 'report' && msg.intent !== 'dex_response' && (
          <span className="text-[8px] font-mono px-1 rounded uppercase text-text-tertiary bg-surface">
            {msg.intent}
          </span>
        )}
        {msg.metadata?.target_node && (
          <span
            className="text-[8px] font-mono px-1 rounded uppercase"
            style={{
              color: msg.metadata.target_node === 'vps' ? 'var(--color-warn)'
                : msg.metadata.target_node === 'beast_windows' ? 'var(--color-cyan)'
                : 'var(--color-ok)',
              background: msg.metadata.target_node === 'vps' ? 'rgba(255,204,0,0.08)'
                : msg.metadata.target_node === 'beast_windows' ? 'rgba(0,255,255,0.08)'
                : 'rgba(0,255,136,0.08)',
            }}
          >
            {msg.metadata.target_node === 'beast_windows' ? 'beast' : String(msg.metadata.target_node)}
          </span>
        )}
        <span className="text-[9px] text-text-tertiary ml-auto flex items-center gap-1">
          {msg.metadata?.model_tier && msg.metadata.model_tier !== 'deterministic' && (
            <span className="text-[8px] font-mono px-1 rounded bg-surface text-text-tertiary">
              via {String(msg.metadata.model_tier)}
            </span>
          )}
          {msg.metadata?.model_tier === 'deterministic' && (
            <span className="text-[8px] font-mono px-1 rounded bg-warn/10 text-warn/70">
              offline
            </span>
          )}
          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      {isReport && msg.title && (
        <div
          className="font-mono text-[10px] tracking-wide uppercase mb-1 pb-1"
          style={{ color: 'var(--color-cyan)', borderBottom: '1px solid var(--color-border)' }}
        >
          {msg.title}
        </div>
      )}
      {msg.provenance && <ProvenanceLine provenance={msg.provenance} />}
      <div className="chat-markdown leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} urlTransform={safeUrl} components={markdownComponents}>{msg.content}</ReactMarkdown>
      </div>
      {msg.attachment && <AttachmentLink attachment={msg.attachment} />}
      {msg.suggested_actions && msg.suggested_actions.length > 0 && onAction && (() => {
        const filtered = msg.suggested_actions!.filter(
          (a) => a.action !== 'approve_engineering_plan' && a.action !== 'reject_engineering_plan'
        )
        return filtered.length > 0 ? (
          <div className="flex flex-wrap gap-1 mt-1.5 pt-1.5 border-t border-border/50">
            {filtered.map((action, i) => (
              <button
                key={i}
                onClick={() => onAction(action)}
                className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-cyan/30 text-cyan hover:bg-cyan-glow transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
        ) : null
      })()}
    </div>
  )
}

const DRAFT_STATUS_LABEL: Record<VoiceMessageDraft['status'], string> = {
  recording: 'recording',
  transcribing: 'transcribing',
  ready: 'ready to send',
  sent: 'sent',
  failed: 'failed',
  deleted: 'deleted',
}

/**
 * Precise failure reasons — P4S-31D1-C. Maps every server + client capture
 * error code to a DISTINCT human string. A mic-silent or decode failure must
 * NEVER collapse to a bare "No speech detected": that message caused the
 * original mis-diagnosis (suspended capture AudioContext read as no-speech).
 * Each code here maps to its own line so the operator sees the real cause.
 */
const VOICE_FAILURE_REASON: Record<string, string> = {
  // Server error taxonomy (umh/voice_server.py)
  EMPTY_AUDIO_BLOB: 'No audio captured — mic sent no bytes',
  SILENT_AUDIO: 'Mic appears silent — no audio energy detected',
  UNSUPPORTED_AUDIO_FORMAT: 'Unsupported audio format for this browser',
  DECODE_FAILED: 'Audio could not be decoded',
  VAD_NO_SPEECH: 'No speech found in the recording',
  STT_FAILED: 'Transcription failed — try again',
  // Client-side capture / VAD taxonomy
  NO_SPEECH: 'No speech detected before the pause',
  // Retry / transport / send taxonomy
  RETRY_NO_AUDIO: 'No stored audio to retry',
  RETRY_WS_UNAVAILABLE: 'Voice server unavailable — retry later',
  RETRY_DECODE_FAILED: 'Stored audio could not be decoded for retry',
  RETRY_STT_FAILED: 'Retry transcription failed',
  RETRY_TIMEOUT: 'Retry timed out — server did not respond',
  RETRY_UNAVAILABLE: 'Retry could not start',
  AUDIO_UPLOAD_FAILED: 'Audio upload failed — send again',
  CHAT_SEND_FAILED: 'Could not deliver to chat — send again',
  // P4S-31D1-E artifact-binding taxonomy — the ONE canonical local vocabulary
  // (voicenote_artifact_binding_contract.json). The local blob is the source of
  // truth for transcription; these codes distinguish precisely why transcription
  // of a PRESENT blob could not complete — NONE claims the audio was never
  // received. The earlier off-canon UI names (TRANSCRIPT_BINDING_* /
  // UPLOAD_PRESENT_TRANSCRIPT_MISSING) were folded into these so the controller
  // and UI share one vocabulary.
  LOCAL_AUDIO_PRESENT_UPLOAD_MISSING: 'Audio recorded but nothing reached the server — retry',
  LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY: 'Audio recorded but the server saw no bytes — retry',
  AUDIO_ARTIFACT_REF_NOT_FOUND: 'Recorded audio could not be located — retry',
  MISSING_AUDIO_FIELD: 'No audio was captured for this note',
}

/** Resolve a draft error code to its precise human reason (never a bare fallback). */
function voiceFailureReason(code: string | null): string {
  if (!code) return 'Transcription failed'
  return VOICE_FAILURE_REASON[code] ?? `Transcription failed (${code})`
}

/**
 * Live audio-level meter — P4S-31D1-C. Reads the client-computed capture RMS
 * the controller mirrors into the store at ~10Hz. This is the VISIBLE proof of
 * capture: the bar moves when the user speaks. If capture stays flat at 0 past
 * the grace window, a subtle "mic appears silent" hint appears. No audio loop
 * lives here — the card only reads a store field.
 */
function CaptureMeter() {
  const rms = useVoiceMessageStore((s) => s.captureRms)
  const silentMs = useVoiceMessageStore((s) => s.captureSilentMs)
  // Perceptual scale: sqrt lifts quiet speech into a visible range, clamped 0..1.
  const level = Math.min(1, Math.sqrt(Math.max(0, rms)) * 1.6)
  const pct = Math.round(level * 100)
  const silent = silentMs > 0
  return (
    <div className="mt-1" aria-label="capture level meter" data-testid="capture-meter">
      <div className="h-1.5 w-full rounded bg-surface overflow-hidden border border-border">
        <div
          className={clsx('h-full transition-[width] duration-75', silent ? 'bg-danger' : 'bg-cyan')}
          style={{ width: `${pct}%` }}
        />
      </div>
      {silent && (
        <p className="text-[9px] font-mono text-danger mt-0.5">
          mic appears silent — check input device
        </p>
      )}
    </div>
  )
}

/** Live-updating recorded duration in seconds while a draft is recording. */
function useRecordingSeconds(active: boolean): number {
  const [secs, setSecs] = useState(0)
  const startRef = useRef<number>(0)
  useEffect(() => {
    if (!active) { setSecs(0); return }
    startRef.current = Date.now()
    setSecs(0)
    const t = setInterval(() => setSecs((Date.now() - startRef.current) / 1000), 200)
    return () => clearInterval(t)
  }, [active])
  return secs
}

/**
 * Human status shown in the transcript-section header — P4S-31D1-E.
 * Derived from transcript_status so the operator always knows the transcript's
 * lifecycle state (transcribing / ready / edited / failed) without opening the
 * body. Distinct from DRAFT_STATUS_LABEL, which describes the draft as a whole.
 */
function transcriptSectionStatus(
  draft: VoiceMessageDraft,
): { label: string; tone: string; spinning: boolean } {
  if (draft.status === 'transcribing' || draft.transcript_status === 'pending' || draft.transcript_status === 'partial') {
    return { label: 'transcribing…', tone: 'text-text-tertiary', spinning: true }
  }
  if (draft.transcript_status === 'failed' || draft.status === 'failed') {
    return { label: 'failed', tone: 'text-danger', spinning: false }
  }
  if (draft.transcript_status === 'edited') {
    return { label: 'edited', tone: 'text-cyan', spinning: false }
  }
  if (draft.transcript_status === 'final') {
    return { label: 'ready', tone: 'text-cyan', spinning: false }
  }
  return { label: '', tone: 'text-text-tertiary', spinning: false }
}

/**
 * Collapsible transcript dropdown — P4S-31D1-E. Renders UNDER the audio card.
 * A header row ("Transcript" + status + a chevron toggle) sits over a
 * collapsible body that holds the transcript, the edit affordance, or the
 * precise failure reason. Long transcripts live inside the body so they never
 * flood the rail/thread. Expand/collapse is local component state only — no
 * store field is touched (the transcription-binding agent owns the store), and
 * the toggle never sends, never pastes into the chat input.
 *
 * Default open: short/ready transcripts start expanded; the operator may
 * collapse or re-expand at will.
 */
function TranscriptSection({
  draft,
  editing,
  editText,
  setEditText,
}: {
  draft: VoiceMessageDraft
  editing: boolean
  editText: string
  setEditText: (v: string) => void
}) {
  const isFailed = draft.status === 'failed' || draft.transcript_status === 'failed'
  const hasTranscript = draft.transcript.trim().length > 0
  // Default open when short & ready; a long transcript defaults collapsed so it
  // never floods the rail. Editing/failed always start open so the operator can
  // act. ~180 chars ≈ a few lines in this narrow rail.
  const longTranscript = draft.transcript.length > 180
  const [expanded, setExpanded] = useState<boolean>(
    isFailed || editing || (hasTranscript && !longTranscript),
  )
  const status = transcriptSectionStatus(draft)
  const Chevron = expanded ? ChevronDown : ChevronRight
  const toggle = () => setExpanded((e) => !e)

  return (
    <div className="mt-1" data-testid="transcript-section">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={expanded}
        aria-label="toggle transcript"
        data-testid="transcript-toggle"
        className="flex w-full items-center gap-1 font-mono text-[9px] uppercase text-text-tertiary hover:text-text-secondary transition-colors"
      >
        <Chevron size={10} className="shrink-0" />
        <span>Transcript</span>
        {status.label && (
          <span className={clsx('flex items-center gap-1', status.tone)}>
            {status.spinning && <Loader2 size={9} className="animate-spin" />}
            {status.label}
          </span>
        )}
      </button>

      {expanded && (
        <div className="mt-1" data-testid="transcript-body">
          {editing ? (
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={2}
              className="w-full text-[11px] font-mono px-1.5 py-1 rounded bg-surface border border-cyan text-text-primary outline-none resize-none"
              autoFocus
            />
          ) : isFailed ? (
            <p className="text-[9px] font-mono text-danger" data-testid="voice-failure-reason">
              {voiceFailureReason(draft.error)}
            </p>
          ) : hasTranscript ? (
            <p className="whitespace-pre-wrap text-[11px] text-text-primary">{draft.transcript}</p>
          ) : (
            <p className="text-[9px] font-mono text-text-tertiary italic">no transcript yet</p>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Lane C — the voice-MESSAGE bubble. A draft is a REVIEWABLE object, never a
 * chat message: it only becomes a chat message on the explicit Send
 * (sendDraft). Recording shows a pulsing indicator + live duration + the
 * provisional partial; once finalized it shows the audio player, the
 * transcript underneath, a status label, and the operator actions.
 */
function VoiceDraftCard({ draft }: { draft: VoiceMessageDraft }) {
  const sendDraft = useVoiceMessageStore((s) => s.sendDraft)
  const retryDraft = useVoiceMessageStore((s) => s.retryDraft)
  const editTranscript = useVoiceMessageStore((s) => s.editTranscript)
  const deleteDraft = useVoiceMessageStore((s) => s.deleteDraft)
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState(draft.transcript)
  const recordingSecs = useRecordingSeconds(draft.status === 'recording')

  useEffect(() => { if (!editing) setEditText(draft.transcript) }, [draft.transcript, editing])

  const isRecording = draft.status === 'recording'
  const isFailed = draft.status === 'failed'
  const canSend =
    draft.status === 'ready' &&
    (draft.transcript_status === 'final' || draft.transcript_status === 'edited') &&
    draft.transcript.trim().length > 0

  const statusColor = isFailed ? 'text-danger'
    : draft.status === 'ready' ? 'text-cyan'
    : draft.status === 'sent' ? 'text-ok'
    : 'text-text-tertiary'

  return (
    <div className="px-2 py-2 rounded text-[11px] bg-surface-raised text-text-primary ml-4 border border-border">
      <div className="flex items-center gap-1 font-mono text-[9px] text-text-tertiary mb-1">
        <span>YOU</span>
        <span className="text-[8px] px-1 rounded bg-surface text-text-tertiary flex items-center gap-1">
          <Mic size={8} className="inline" /> voice
        </span>
        {isRecording && (
          <span className="flex items-center gap-1 text-cyan">
            <span className="w-1.5 h-1.5 rounded-full bg-danger animate-pulse inline-block" />
            {recordingSecs.toFixed(1)}s
          </span>
        )}
        <span className={clsx('ml-auto text-[9px] font-mono uppercase', statusColor)}>
          {DRAFT_STATUS_LABEL[draft.status]}
        </span>
      </div>

      {isRecording && (
        <>
          <CaptureMeter />
          {/* P4S-31D1-F blob-only: no live partial while recording — the blob is
              transcribed on stop. Honest "Recording…" copy, meter shows liveness. */}
          <p className="whitespace-pre-wrap text-[10px] text-text-secondary italic min-h-[14px]">
            Recording… tap the mic again to stop
          </p>
        </>
      )}

      {!isRecording && draft.audioUrl && (
        <audio controls playsInline src={draft.audioUrl} className="w-full mt-1 mb-1" style={{ height: 32 }} />
      )}

      {!isRecording && (
        <TranscriptSection
          draft={draft}
          editing={editing}
          editText={editText}
          setEditText={setEditText}
        />
      )}

      {draft.confidence !== null && !isFailed && !isRecording && (
        <div className="text-[8px] font-mono text-text-tertiary mt-0.5">
          confidence {(draft.confidence * 100).toFixed(0)}%
        </div>
      )}

      {!isRecording && (
        <div className="flex flex-wrap gap-1 mt-1.5 pt-1.5 border-t border-border/50">
          {editing ? (
            <>
              <button
                onClick={() => { editTranscript(draft.draft_id, editText); setEditing(false) }}
                className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-cyan/30 text-cyan hover:bg-cyan-glow transition-colors"
              >
                Save
              </button>
              <button
                onClick={() => { setEditText(draft.transcript); setEditing(false) }}
                className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-border text-text-tertiary hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              {!isFailed && (
                <button
                  onClick={() => sendDraft(draft.draft_id)}
                  disabled={!canSend}
                  className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-cyan/30 text-cyan hover:bg-cyan-glow transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  <Send size={9} /> Send
                </button>
              )}
              <button
                onClick={() => retryDraft(draft.draft_id)}
                className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-border text-text-secondary hover:text-cyan hover:border-cyan/40 transition-colors"
              >
                Retry
              </button>
              {!isFailed && (
                <button
                  onClick={() => { setEditText(draft.transcript); setEditing(true) }}
                  className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-border text-text-secondary hover:text-cyan hover:border-cyan/40 transition-colors flex items-center gap-1"
                >
                  <Pencil size={9} /> Edit
                </button>
              )}
              <button
                onClick={() => deleteDraft(draft.draft_id)}
                className="text-[9px] font-mono px-1.5 py-0.5 rounded border border-border text-text-tertiary hover:text-danger hover:border-danger/40 transition-colors flex items-center gap-1"
              >
                <X size={9} /> Delete
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

function VoiceDraftCards() {
  const drafts = useVoiceMessageStore((s) => s.drafts)
  const visible = drafts.filter((d) => d.status !== 'sent' && d.status !== 'deleted')
  if (visible.length === 0) return null
  return (
    <>
      {visible.map((d) => (
        <VoiceDraftCard key={d.draft_id} draft={d} />
      ))}
    </>
  )
}

function ChatSection() {
  const aiName = useConfigStore((s) => s.aiName)
  const setConfigValue = useConfigStore((s) => s.setConfigValue)
  const messages = useChatStore((s) => s.messages)
  const input = useChatStore((s) => s.input)
  const sending = useChatStore((s) => s.sending)
  const error = useChatStore((s) => s.error)
  const setInput = useChatStore((s) => s.setInput)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const pendingMedia = useChatStore((s) => s.pendingMedia)
  const addPendingMedia = useChatStore((s) => s.addPendingMedia)
  const removePendingMedia = useChatStore((s) => s.removePendingMedia)
  const viewContext = useViewContextStore((s) => s.context)
  const setPanel = useCockpitStore((s) => s.setPanel)
  const micState = useVoiceStore((s) => s.micState)
  const ttsState = useVoiceStore((s) => s.ttsState)
  const voiceError = useVoiceStore((s) => s.error)
  const voiceLastOutcome = useVoiceStore((s) => s.lastOutcome)
  const consentState = useVoiceStore((s) => s.consentState)
  const voicePresentationStatus = useVoiceStore((s) => s.voicePresentationStatus)
  const draftMessage = useChatStore((s) => s.draftMessage)
  const placeholderMessage = useChatStore((s) => s.placeholderMessage)
  const hasVoiceDrafts = useVoiceMessageStore(
    (s) => s.drafts.some((d) => d.status !== 'sent' && d.status !== 'deleted'),
  )
  const scrollRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const displayName = aiName
  const [editingName, setEditingName] = useState(false)
  const [nameInput, setNameInput] = useState(aiName)
  const nameRef = useRef<HTMLInputElement>(null)
  const [voiceAvailable, setVoiceAvailable] = useState(true)

  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight) }, [messages])
  useEffect(() => { if (editingName) nameRef.current?.focus() }, [editingName])
  useEffect(() => { setNameInput(aiName) }, [aiName])

  useEffect(() => {
    if (typeof navigator.mediaDevices === 'undefined') {
      setVoiceAvailable(false)
    }
  }, [])

  const handleSend = () => {
    if (input.trim() || pendingMedia.length > 0) {
      const ctx: Record<string, unknown> = { ...viewContext }
      sendMessage(input, 'text', ctx)
    }
  }

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const files = Array.from(e.clipboardData.files).filter(
      (f) => f.type.startsWith('image/') || f.type.startsWith('video/'),
    )
    if (files.length > 0) {
      e.preventDefault()
      addPendingMedia(files)
    }
  }, [addPendingMedia])

  const handleFilePick = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length > 0) addPendingMedia(files)
    e.target.value = ''
  }, [addPendingMedia])

  const handleMicToggle = useCallback(async () => {
    if (micState === 'idle') {
      setVoiceAvailable(true)
      try {
        await desktopBrowserVoiceAdapter.startCapture()
      } catch (err) {
        // ROOT E: consent is auto-granted by the governed WS, so _consentAndStart no
        // longer throws ConsentRequiredError on the happy path. Keep the guard as a
        // defensive no-op (there is no "Enable Push-to-Talk" affordance to fall back
        // to anymore); any other failure surfaces via the terminal voiceError banner.
        if (err instanceof ConsentRequiredError) return
        setVoiceAvailable(false)
      }
    } else {
      desktopBrowserVoiceAdapter.stopCapture()
    }
  }, [micState])

  const handleRevokePushToTalk = useCallback(() => {
    desktopBrowserVoiceAdapter.revokeConsent('push_to_talk').catch(() => { /* fail-closed */ })
  }, [])

  const handleSuggestedAction = useCallback((action: SuggestedAction) => {
    switch (action.action) {
      case 'query':
        sendMessage(action.payload.content as string, 'text', { ...viewContext })
        break
      case 'navigate':
        if (action.payload.panel) setPanel(action.payload.panel as string)
        break
      case 'cc_send':
        fetchApi('/claude-session/send', {
          method: 'POST',
          body: JSON.stringify(action.payload),
        }).then((res) => {
          const r = res as Record<string, unknown>
          const msg = r.ok ? 'Sent to Claude Code session.' : `Claude Code: ${r.error || 'unavailable'}`
          sendMessage(msg, 'text')
        }).catch(() => sendMessage('Claude Code bridge unavailable.', 'text'))
        break
      case 'council':
        fetchApi('/council/review', {
          method: 'POST',
          body: JSON.stringify(action.payload),
        }).then(() => sendMessage('Council review submitted.', 'text'))
          .catch(() => sendMessage('Council review failed.', 'text'))
        break
      case 'decompose':
        fetchApi('/command-center/work-packets/decompose', {
          method: 'POST',
          body: JSON.stringify(action.payload),
        }).then(() => sendMessage('Intent decomposed into work packets.', 'text'))
          .catch(() => sendMessage('Decomposition failed.', 'text'))
        break
      case 'engineering_plan':
        import('../stores/engineeringStore').then(({ useEngineeringStore }) => {
          useEngineeringStore.getState().createPlan(action.payload.intent as string)
          setPanel('engineering')
          sendMessage('Engineering plan created.', 'text')
        }).catch(() => sendMessage('Failed to create engineering plan.', 'text'))
        break
      case 'approve_engineering_plan':
        fetchApi(`/engineering/plans/${action.payload.plan_id}/approve`, {
          method: 'POST',
        }).then(() => {
          sendMessage(`Plan ${action.payload.plan_id} approved. Work packets generated.`, 'text')
          return fetchApi(`/engineering/plans/${action.payload.plan_id}/dispatch`, {
            method: 'POST',
            body: JSON.stringify({ node_id: 'windows-desktop' }),
          })
        }).then((res) => {
          const r = res as Record<string, unknown>
          sendMessage(`Dispatched to Beast: ${r.dispatched || 0} tasks sent.`, 'text')
        }).catch(() => sendMessage('Plan approval or dispatch failed.', 'text'))
        break
      case 'reject_engineering_plan':
        fetchApi(`/engineering/plans/${action.payload.plan_id}/reject`, {
          method: 'POST',
        }).then(() => sendMessage(`Plan ${action.payload.plan_id} rejected.`, 'text'))
          .catch(() => sendMessage('Plan rejection failed.', 'text'))
        break
      default:
        break
    }
  }, [sendMessage, viewContext, setPanel])

  const commitName = () => {
    const trimmed = nameInput.trim()
    if (trimmed && trimmed !== aiName) {
      setConfigValue('ai_name', trimmed)
    }
    if (!trimmed) setNameInput(aiName)
    setEditingName(false)
  }

  // Consent is now handled INVISIBLY by the governed WS (auto-grant for the
  // authenticated principal). So the client no longer surfaces consent-flow noise
  // ("consent not granted", "server unreachable", "requesting mic", "enabling
  // push-to-talk") as user-facing text — those transients resolve on their own on
  // the happy path. We show only genuine live capture/playback states.
  const voiceLabel = micState === 'listening' ? 'Listening — tap to send'
    : micState === 'recording' ? 'Recording — tap to send'
    : micState === 'transcribing' ? 'Transcribing...'
    : micState === 'processing' ? 'Thinking...'
    : micState === 'interrupted' ? 'Listening — tap to send'
    : ttsState === 'generating_tts' ? 'Preparing voice...'
    : ttsState === 'speaking' ? 'Speaking...'
    : ttsState === 'tts_failed' ? 'Voice unavailable — showing text'
    : null

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-2">
        {editingName ? (
          <>
            <input
              ref={nameRef}
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') commitName(); if (e.key === 'Escape') { setNameInput(aiName); setEditingName(false) } }}
              onBlur={commitName}
              className="wv-label bg-transparent border-b border-cyan outline-none flex-1 uppercase"
              style={{ fontSize: 'inherit', lineHeight: 'inherit' }}
            />
            <button onClick={commitName} className="p-1 text-cyan hover:text-text-primary transition-colors">
              <Check size={10} />
            </button>
          </>
        ) : (
          <>
            <span className="wv-label">{displayName}</span>
            <button onClick={() => { setNameInput(aiName); setEditingName(true) }} className="p-1 text-text-tertiary hover:text-cyan transition-colors">
              <Pencil size={10} />
            </button>
          </>
        )}
      </div>
      {(viewContext.active_route || viewContext.selected_object_type) && (
        <div className="text-[9px] font-mono text-text-tertiary mb-1 px-1 py-0.5 bg-surface rounded border border-border truncate">
          Viewing: {viewContext.active_route}
          {viewContext.selected_object_type && ` > ${viewContext.selected_object_type}`}
          {viewContext.selected_object_summary && `: ${viewContext.selected_object_summary}`}
        </div>
      )}
      {error && (
        <div className="text-[9px] font-mono text-danger mb-1 px-1.5 py-1 bg-danger/10 rounded border border-danger/30">
          {error}
        </div>
      )}
      {/* ROOT E: voice failures were written to voiceStore.error but NEVER rendered
          (the banner above reads chatStore.error), so the mic silently returned to
          idle with no reason. Surface voiceError ONLY for genuine TERMINAL outcomes
          — this keeps the deliberate consent-flow silence (no requesting/granting
          transients) while making real dead-ends (mic denied, WS unreachable, STT
          failed, timeout) visible. */}
      {voiceError && VOICE_TERMINAL_OUTCOMES.has(voiceLastOutcome ?? '') && (
        <div className="text-[9px] font-mono text-danger mb-1 px-1.5 py-1 bg-danger/10 rounded border border-danger/40 flex items-center gap-1">
          <Mic size={9} className="shrink-0" />
          <span>{voiceError}</span>
        </div>
      )}
      <div ref={scrollRef} className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden space-y-2 mb-2">
        {messages.map((m) => (
          <MessageBubble key={m.id} msg={m} aiName={aiName} onAction={handleSuggestedAction} />
        ))}
        <VoiceDraftCards />
        {draftMessage && (
          <div className="px-2 py-2 rounded text-[11px] bg-surface-raised text-text-primary ml-4 opacity-70">
            <div className="flex items-center gap-1 font-mono text-[9px] text-text-tertiary mb-1">
              <span>YOU</span>
              <span className="text-[8px] px-1 rounded bg-surface text-text-tertiary">
                <Mic size={8} className="inline" /> speaking...
              </span>
            </div>
            <p className="whitespace-pre-wrap">{draftMessage.content || '...'}</p>
          </div>
        )}
        {(sending || voicePresentationStatus === 'thinking' || voicePresentationStatus === 'preparing_response') && (
          <div className="px-2 py-1.5 rounded text-[11px] bg-surface-raised text-text-tertiary mr-4 animate-pulse">
            {aiName} is thinking...
          </div>
        )}
        {(voicePresentationStatus === 'preparing_voice' || voicePresentationStatus === 'ready_to_commit') && (
          <div className="px-2 py-1.5 rounded text-[11px] bg-surface-raised text-text-tertiary mr-4 animate-pulse">
            {aiName} is preparing voice...
          </div>
        )}
        {placeholderMessage && voicePresentationStatus === 'idle' && (
          <div className="px-2 py-1.5 rounded text-[11px] bg-surface-raised text-text-tertiary mr-4 animate-pulse">
            {placeholderMessage.content}
          </div>
        )}
        {ttsState === 'tts_failed' && voiceError && voiceError.startsWith('Tap to play') && (
          <button
            onClick={() => {
              desktopBrowserVoiceAdapter.startCapture().catch(() => { /* ignore */ })
            }}
            className="px-2 py-1.5 rounded text-[10px] font-mono text-cyan border border-cyan/30 hover:bg-cyan-glow transition-colors cursor-pointer"
          >
            Tap to play audio
          </button>
        )}
        {messages.length === 0 && !sending && !draftMessage && !hasVoiceDrafts && (
          <p className="text-[11px] text-text-tertiary text-center py-4">Ask {aiName} anything</p>
        )}
      </div>
      <div className="flex flex-col gap-1 border-t border-border pt-2">
        {voiceLabel && (
          <div className={clsx(
            'text-[9px] font-mono px-1',
            (micState === 'recording') ? 'text-cyan font-bold' :
            'text-cyan animate-pulse',
          )}>{voiceLabel}</div>
        )}
        {/* Consent is auto-granted by the governed WS for the authenticated
            principal — no client "Enable Push-to-Talk" button, no "Enabling…"
            transient, no consent-error toast. The ONLY consent affordance we keep
            is the (rare) disable control once talk is active, for revocability. */}
        {consentState === 'active' && micState === 'idle' && (
          <div className="text-[8px] font-mono text-text-tertiary px-1">
            Push-to-talk enabled ·{' '}
            <button onClick={handleRevokePushToTalk} className="underline hover:text-danger cursor-pointer">disable</button>
          </div>
        )}
        {pendingMedia.length > 0 && (
          <div className="flex flex-wrap gap-1 px-1">
            {pendingMedia.map((pm, i) => (
              <div key={i} className="relative group">
                {pm.media_type === 'image' ? (
                  <img src={pm.previewUrl} alt="" className="rounded" style={{ height: 48, width: 48, objectFit: 'cover' }} />
                ) : pm.media_type === 'video' ? (
                  <div className="flex items-center justify-center rounded bg-surface-raised" style={{ height: 48, width: 48 }}>
                    <span className="text-[8px] font-mono text-text-tertiary">VID</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center rounded bg-surface-raised px-1" style={{ height: 48, minWidth: 48 }}>
                    <span className="text-[8px] font-mono text-text-tertiary truncate max-w-[60px]">{pm.file.name}</span>
                  </div>
                )}
                <button
                  onClick={() => removePendingMedia(i)}
                  className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-danger text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X size={8} />
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="flex items-center gap-1">
          <input
            ref={fileInputRef}
            type="file"
            accept="*/*"
            multiple
            className="hidden"
            onChange={handleFilePick}
          />
          <div className="flex-1 flex items-center rounded bg-surface-raised border border-border">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-1 ml-0.5 rounded text-text-tertiary hover:text-cyan transition-colors shrink-0"
              title="Attach file or take photo"
            >
              <Paperclip size={12} />
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
              onPaste={handlePaste}
              placeholder={`Message ${aiName}...`}
              className="flex-1 text-[11px] px-1.5 py-1.5 bg-transparent text-text-primary outline-none placeholder:text-text-tertiary min-w-0"
              disabled={sending}
            />
            <button
              onClick={handleMicToggle}
              disabled={!voiceAvailable || micState === 'requesting_permission' || micState === 'connecting_voice_ws' || micState === 'transcribing' || micState === 'processing'}
              className={clsx(
                'p-1 mr-0.5 rounded transition-colors shrink-0',
                !voiceAvailable ? 'text-text-tertiary opacity-30 cursor-not-allowed' :
                (micState === 'listening' || micState === 'recording') ? 'text-danger bg-danger/10' :
                (micState === 'requesting_permission' || micState === 'connecting_voice_ws' || micState === 'transcribing') ? 'text-amber opacity-60' :
                'text-text-tertiary hover:text-cyan',
              )}
              title={!voiceAvailable ? (voiceError || 'Voice requires desktop app or HTTPS') : (micState === 'listening' || micState === 'recording') ? 'Tap to send' : 'Voice input'}
            >
              {(micState === 'listening' || micState === 'recording') ? <MicOff size={12} /> : <Mic size={12} />}
            </button>
          </div>
          <button onClick={handleSend} disabled={sending || (!input.trim() && pendingMedia.length === 0)} className="p-1.5 rounded text-cyan hover:bg-cyan-glow transition-colors disabled:opacity-30 shrink-0">
            <Send size={12} />
          </button>
        </div>

      </div>
    </div>
  )
}

function ContextSection() {
  const [ctx, setCtx] = useState<Record<string, unknown> | null>(null)
  const [presence, setPresence] = useState<Record<string, unknown> | null>(null)

  usePolling(useCallback(() => {
    fetchApi('/meta-ide-context/context').then(setCtx).catch(() => {})
    fetchApi('/orchestrator-presence/snapshot').then(setPresence).catch(() => {})
  }, []), 5000, true, 750)

  const project = (presence?.active_project as string) || ''
  const repo = (presence?.active_repo as string) || ''
  const directory = (ctx?.active_directory as string) || ''
  const branch = (ctx?.active_branch as string) || ''
  const goals = (ctx?.related_goals as Array<Record<string, string>>) || []
  const decisions = (ctx?.related_decisions as Array<Record<string, string>>) || []
  const constraints = (ctx?.constraints as string[]) || []
  const activeFiles = (ctx?.active_files as string[]) || []

  return (
    <div className="space-y-3">
      <div className="wv-label mb-2">PROJECT CONTEXT</div>
      {project && <div className="text-[11px]"><span className="text-text-tertiary">Project</span> <span className="text-text-primary">{project}</span></div>}
      {repo && <div className="text-[11px]"><span className="text-text-tertiary">Repo</span> <span className="text-text-primary">{repo}</span></div>}
      {branch && <div className="text-[11px]"><span className="text-text-tertiary">Branch</span> <span className="text-cyan">{branch}</span></div>}
      {directory && <div className="text-[11px]"><span className="text-text-tertiary">Dir</span> <span className="text-text-secondary font-mono">{directory}</span></div>}

      {goals.length > 0 && (
        <div>
          <div className="wv-label mb-1">GOALS</div>
          {goals.slice(0, 5).map((g, i) => (
            <div key={i} className="text-[11px] text-text-secondary py-0.5">{g.title || g.description || JSON.stringify(g)}</div>
          ))}
        </div>
      )}

      {decisions.length > 0 && (
        <div>
          <div className="wv-label mb-1">DECISIONS</div>
          {decisions.slice(0, 5).map((d, i) => (
            <div key={i} className="text-[11px] text-text-secondary py-0.5">{d.title || d.description || JSON.stringify(d)}</div>
          ))}
        </div>
      )}

      {constraints.length > 0 && (
        <div>
          <div className="wv-label mb-1">CONSTRAINTS</div>
          {constraints.slice(0, 5).map((c, i) => (
            <div key={i} className="text-[11px] text-warn py-0.5">{c}</div>
          ))}
        </div>
      )}

      {activeFiles.length > 0 && (
        <div>
          <div className="wv-label mb-1">ACTIVE FILES</div>
          {activeFiles.slice(0, 8).map((f, i) => (
            <div key={i} className="text-[10px] font-mono text-text-tertiary py-0.5 truncate">{f}</div>
          ))}
        </div>
      )}

      {!project && !repo && (
        <p className="text-[11px] text-text-tertiary text-center py-4">No active context</p>
      )}
    </div>
  )
}

function ExecutionSection() {
  const s = useExecutionSummaryStore((st) => st.summary)

  const state = s.state
  const readyCount = s.ready_count
  const blockedCount = s.blocked_count
  const pendingApprovals = s.pending_approval_count
  const topBlockers = s.top_blockers
  const delegationCoverage = s.delegation_coverage

  const stateColor: Record<string, string> = {
    idle: 'text-text-tertiary', assessing: 'text-cyan', governed: 'text-ok',
    executing: 'text-ok', blocked: 'text-danger',
  }

  return (
    <div className="space-y-3">
      <div className="wv-label mb-2">EXECUTION STATE</div>
      <div className="flex items-center gap-2">
        <span className={clsx('text-[11px] font-mono uppercase', stateColor[state] || 'text-text-tertiary')}>{state}</span>
        <span className={clsx('text-[9px] font-mono uppercase', s.health === 'optimal' ? 'text-ok' : s.health === 'blocked' ? 'text-danger' : 'text-text-tertiary')}>{s.health}</span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div><div className="text-[14px] font-mono text-ok">{readyCount}</div><div className="text-[9px] text-text-tertiary">Ready</div></div>
        <div><div className="text-[14px] font-mono text-warn">{pendingApprovals}</div><div className="text-[9px] text-text-tertiary">Pending</div></div>
        <div><div className="text-[14px] font-mono text-danger">{blockedCount}</div><div className="text-[9px] text-text-tertiary">Blocked</div></div>
      </div>

      {delegationCoverage > 0 && (
        <div className="text-[11px]"><span className="text-text-tertiary">Delegation</span> <span className="text-text-primary">{Math.round(delegationCoverage * 100)}%</span></div>
      )}

      {topBlockers.length > 0 && (
        <div>
          <div className="wv-label mb-1">BLOCKERS</div>
          {topBlockers.slice(0, 5).map((b, i) => (
            <div key={i} className="text-[11px] text-danger py-0.5">{(b as Record<string, string>).description || JSON.stringify(b)}</div>
          ))}
        </div>
      )}

      {state === 'idle' && topBlockers.length === 0 && (
        <p className="text-[11px] text-text-tertiary text-center py-4">No active execution</p>
      )}
    </div>
  )
}
