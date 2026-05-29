import { useEffect, useRef, useCallback, useMemo } from 'react'
import { useVoiceStore } from '../stores/voiceStore'
import { useConfigStore } from '../stores/configStore'
import { startVoice, stopVoice } from '../api/voice-controller'

const CLAP_THRESHOLD = 0.6
const CLAP_COOLDOWN_MS = 1500

function makeWakeWords(name: string): string[] {
  const lower = name.toLowerCase()
  return [lower, `hey ${lower}`, `okay ${lower}`]
}

function VoiceOrb() {
  const aiName = useConfigStore((s) => s.aiName)
  const micState = useVoiceStore((s) => s.micState)
  const ttsState = useVoiceStore((s) => s.ttsState)
  const audioLevel = useVoiceStore((s) => s.audioLevel)

  const isActive = micState !== 'idle'
  const isSpeaking = ttsState === 'speaking'
  const scale = isActive ? 1 + audioLevel * 0.3 : 1

  let color = 'var(--text-tertiary)'
  let glow = 'none'
  let pulseClass = ''

  if (isSpeaking) {
    color = 'var(--accent-purple)'
    glow = '0 0 20px rgba(168, 85, 247, 0.4), 0 0 40px rgba(168, 85, 247, 0.2)'
  } else if (micState === 'processing') {
    color = 'var(--accent-amber)'
    glow = '0 0 16px rgba(245, 158, 11, 0.3)'
    pulseClass = 'animate-pulse'
  } else if (micState === 'listening') {
    color = 'var(--accent-cyan)'
    glow = `0 0 ${12 + audioLevel * 20}px rgba(0, 229, 255, ${0.2 + audioLevel * 0.3}), 0 0 ${24 + audioLevel * 40}px rgba(0, 229, 255, ${0.1 + audioLevel * 0.15})`
  }

  return (
    <button
      onClick={() => {
        if (micState === 'idle') startVoice()
        else stopVoice()
      }}
      className={`relative flex items-center justify-center rounded-full transition-all duration-150 ${pulseClass}`}
      style={{
        width: 48,
        height: 48,
        background: isActive ? `${color}20` : 'var(--surface-2)',
        border: `2px solid ${color}`,
        boxShadow: glow,
        transform: `scale(${scale})`,
        cursor: 'pointer',
      }}
      title={micState === 'idle' ? `Click to talk to ${aiName}` : 'Click to stop'}
    >
      {/* Inner rings for active state */}
      {isActive && (
        <>
          <span
            className="absolute rounded-full"
            style={{
              width: 56,
              height: 56,
              border: `1px solid ${color}`,
              opacity: 0.3,
              animation: 'voice-ring 2s ease-out infinite',
            }}
          />
          <span
            className="absolute rounded-full"
            style={{
              width: 64,
              height: 64,
              border: `1px solid ${color}`,
              opacity: 0.15,
              animation: 'voice-ring 2s ease-out infinite 0.5s',
            }}
          />
        </>
      )}

      {/* Icon */}
      {isSpeaking ? (
        <SpeakingBars color={color} />
      ) : micState === 'listening' ? (
        <ListeningBars level={audioLevel} color={color} />
      ) : micState === 'processing' ? (
        <span style={{ color, fontSize: 16 }}>⟳</span>
      ) : (
        <MicIcon color={color} />
      )}
    </button>
  )
}

function MicIcon({ color }: { color: string }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="18" x2="12" y2="22" />
    </svg>
  )
}

function ListeningBars({ level, color }: { level: number; color: string }) {
  const bars = 5
  return (
    <div className="flex items-center gap-[2px]" style={{ height: 18 }}>
      {Array.from({ length: bars }, (_, i) => {
        const offset = (i - 2) * 0.12
        const h = Math.max(3, (level + offset) * 16)
        return (
          <div
            key={i}
            className="rounded-full transition-all duration-75"
            style={{
              width: 3,
              height: h,
              background: color,
              opacity: 0.6 + level * 0.4,
            }}
          />
        )
      })}
    </div>
  )
}

function SpeakingBars({ color }: { color: string }) {
  return (
    <div className="flex items-center gap-[2px]" style={{ height: 18 }}>
      {[0, 0.2, 0.4, 0.2, 0].map((delay, i) => (
        <div
          key={i}
          className="rounded-full"
          style={{
            width: 3,
            background: color,
            animation: `speaking-bar 0.8s ease-in-out infinite ${delay}s`,
          }}
        />
      ))}
    </div>
  )
}

function TranscriptDisplay() {
  const aiName = useConfigStore((s) => s.aiName)
  const micState = useVoiceStore((s) => s.micState)
  const ttsState = useVoiceStore((s) => s.ttsState)
  const lastTranscript = useVoiceStore((s) => s.lastTranscript)

  if (micState === 'idle' && ttsState === 'idle') return null

  let text = ''
  let color = 'var(--text-secondary)'

  if (ttsState === 'speaking') {
    text = `${aiName} is speaking...`
    color = 'var(--accent-purple)'
  } else if (micState === 'processing') {
    text = 'thinking...'
    color = 'var(--accent-amber)'
  } else if (micState === 'listening') {
    text = lastTranscript || 'listening...'
    color = lastTranscript ? 'var(--text-primary)' : 'var(--text-tertiary)'
  }

  return (
    <span
      className="font-mono text-xs truncate max-w-[300px] transition-colors duration-150"
      style={{ color }}
    >
      {text}
    </span>
  )
}

function ActivationIndicators() {
  const aiName = useConfigStore((s) => s.aiName)
  const wakeWordEnabled = useVoiceStore((s) => s.wakeWordEnabled)
  const clapEnabled = useVoiceStore((s) => s.clapEnabled)
  const alwaysOnEnabled = useVoiceStore((s) => s.alwaysOnEnabled)
  const setWakeWordEnabled = useVoiceStore((s) => s.setWakeWordEnabled)
  const setClapEnabled = useVoiceStore((s) => s.setClapEnabled)
  const setAlwaysOnEnabled = useVoiceStore((s) => s.setAlwaysOnEnabled)

  return (
    <div className="flex items-center gap-2">
      <TogglePill
        label="wake word"
        active={wakeWordEnabled}
        onClick={() => setWakeWordEnabled(!wakeWordEnabled)}
        title={`"Hey ${aiName}" to activate`}
      />
      <TogglePill
        label="clap"
        active={clapEnabled}
        onClick={() => setClapEnabled(!clapEnabled)}
        title="Double-clap to activate"
      />
      <TogglePill
        label="always on"
        active={alwaysOnEnabled}
        onClick={() => setAlwaysOnEnabled(!alwaysOnEnabled)}
        title="Always listening, silence-based turns"
      />
    </div>
  )
}

function TogglePill({ label, active, onClick, title }: {
  label: string
  active: boolean
  onClick: () => void
  title: string
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full transition-all duration-150 cursor-pointer"
      style={{
        color: active ? 'var(--accent-cyan)' : 'var(--text-tertiary)',
        background: active ? 'var(--glow-cyan)' : 'transparent',
        border: `1px solid ${active ? 'var(--accent-cyan)' : 'var(--border)'}`,
      }}
    >
      {label}
    </button>
  )
}

export function VoiceCommandBar() {
  const aiName = useConfigStore((s) => s.aiName)
  const wakeWords = useMemo(() => makeWakeWords(aiName), [aiName])
  const micState = useVoiceStore((s) => s.micState)
  const clapEnabled = useVoiceStore((s) => s.clapEnabled)
  const wakeWordEnabled = useVoiceStore((s) => s.wakeWordEnabled)
  const alwaysOnEnabled = useVoiceStore((s) => s.alwaysOnEnabled)
  const lastTranscript = useVoiceStore((s) => s.lastTranscript)
  const lastClapRef = useRef(0)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const clapStreamRef = useRef<MediaStream | null>(null)
  const clapContextRef = useRef<AudioContext | null>(null)
  const clapRafRef = useRef<number>(0)

  const handleClap = useCallback(() => {
    const now = Date.now()
    if (now - lastClapRef.current < CLAP_COOLDOWN_MS) return
    lastClapRef.current = now

    const mic = useVoiceStore.getState().micState
    if (mic === 'idle') {
      useVoiceStore.getState().setActivationMode('clap')
      startVoice()
    }
  }, [])

  // Clap detection via ambient mic monitoring
  useEffect(() => {
    if (!clapEnabled) {
      if (clapRafRef.current) cancelAnimationFrame(clapRafRef.current)
      clapStreamRef.current?.getTracks().forEach(t => t.stop())
      if (clapContextRef.current?.state !== 'closed') clapContextRef.current?.close()
      clapStreamRef.current = null
      clapContextRef.current = null
      analyserRef.current = null
      return
    }

    let active = true

    async function startClapDetection() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        if (!active) { stream.getTracks().forEach(t => t.stop()); return }
        clapStreamRef.current = stream

        const ctx = new AudioContext()
        clapContextRef.current = ctx
        const source = ctx.createMediaStreamSource(stream)
        const analyser = ctx.createAnalyser()
        analyser.fftSize = 512
        source.connect(analyser)
        analyserRef.current = analyser

        const dataArray = new Uint8Array(analyser.frequencyBinCount)
        let prevPeak = 0

        function checkClap() {
          if (!active) return
          analyser.getByteFrequencyData(dataArray)
          let peak = 0
          for (let i = 0; i < dataArray.length; i++) {
            if (dataArray[i] > peak) peak = dataArray[i]
          }
          const normalized = peak / 255

          // Clap = sudden spike after relative quiet
          if (normalized > CLAP_THRESHOLD && prevPeak < CLAP_THRESHOLD * 0.5) {
            const mic = useVoiceStore.getState().micState
            if (mic === 'idle') handleClap()
          }
          prevPeak = normalized
          clapRafRef.current = requestAnimationFrame(checkClap)
        }
        checkClap()
      } catch (err) {
        console.error('[VoiceCommandBar] Clap detection mic access failed:', err)
      }
    }

    startClapDetection()
    return () => {
      active = false
      if (clapRafRef.current) cancelAnimationFrame(clapRafRef.current)
      clapStreamRef.current?.getTracks().forEach(t => t.stop())
      if (clapContextRef.current?.state !== 'closed') clapContextRef.current?.close()
    }
  }, [clapEnabled, handleClap])

  // Wake word detection: check transcript for wake words
  useEffect(() => {
    if (!wakeWordEnabled) return
    if (micState !== 'idle') return

    const lower = lastTranscript.toLowerCase().trim()
    if (wakeWords.some(w => lower.includes(w))) {
      useVoiceStore.getState().setActivationMode('wake_word')
      startVoice()
    }
  }, [lastTranscript, wakeWordEnabled, micState, wakeWords])

  // Always-on: auto-start voice when enabled
  useEffect(() => {
    if (alwaysOnEnabled && micState === 'idle') {
      useVoiceStore.getState().setActivationMode('always_on')
      startVoice()
    }
  }, [alwaysOnEnabled, micState])

  const isActive = micState !== 'idle'

  return (
    <>
      {/* CSS animations */}
      <style>{`
        @keyframes voice-ring {
          0% { transform: scale(1); opacity: 0.3; }
          100% { transform: scale(1.5); opacity: 0; }
        }
        @keyframes speaking-bar {
          0%, 100% { height: 4px; }
          50% { height: 14px; }
        }
      `}</style>

      <div
        className="flex items-center justify-center gap-4 transition-all duration-200"
        style={{
          position: 'absolute',
          bottom: 'calc(var(--hud-height) + 16px)',
          left: '50%',
          transform: 'translateX(-50%)',
          padding: isActive ? '8px 20px 8px 16px' : '6px 16px',
          background: isActive ? 'var(--surface-2)' : 'var(--surface-1)',
          border: `1px solid ${isActive ? 'var(--border-focus)' : 'var(--border)'}`,
          borderRadius: 28,
          backdropFilter: 'blur(12px)',
          boxShadow: isActive
            ? '0 4px 24px rgba(0, 0, 0, 0.4), 0 0 1px rgba(0, 229, 255, 0.1)'
            : '0 2px 12px rgba(0, 0, 0, 0.3)',
          zIndex: 50,
        }}
      >
        <VoiceOrb />

        {isActive ? (
          <TranscriptDisplay />
        ) : (
          <div className="flex items-center gap-3">
            <span
              className="font-mono text-xs uppercase tracking-wider"
              style={{ color: 'var(--text-tertiary)' }}
            >
              talk to {aiName.toLowerCase()}
            </span>
            <ActivationIndicators />
          </div>
        )}

        {isActive && (
          <button
            onClick={stopVoice}
            className="flex items-center justify-center w-6 h-6 rounded-full transition-colors duration-150"
            style={{
              background: 'var(--surface-3)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
            }}
            title="Stop voice"
          >
            <span className="text-[10px]">✕</span>
          </button>
        )}
      </div>
    </>
  )
}
