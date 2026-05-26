import { useEffect, useRef, useCallback } from 'react'
import { useVoiceStore } from '../stores/voiceStore'
import { startVoice } from '../api/voice-controller'

const CLAP_THRESHOLD = 0.6
const CLAP_COOLDOWN_MS = 1500
const WAKE_WORDS = ['dex', 'hey dex', 'okay dex']

export function useVoiceDetection(): void {
  const clapEnabled = useVoiceStore((s) => s.clapEnabled)
  const wakeWordEnabled = useVoiceStore((s) => s.wakeWordEnabled)
  const alwaysOnEnabled = useVoiceStore((s) => s.alwaysOnEnabled)
  const micState = useVoiceStore((s) => s.micState)
  const lastTranscript = useVoiceStore((s) => s.lastTranscript)

  const lastClapRef = useRef(0)
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

  useEffect(() => {
    if (!clapEnabled) {
      if (clapRafRef.current) cancelAnimationFrame(clapRafRef.current)
      clapStreamRef.current?.getTracks().forEach(t => t.stop())
      if (clapContextRef.current?.state !== 'closed') clapContextRef.current?.close()
      clapStreamRef.current = null
      clapContextRef.current = null
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

          if (normalized > CLAP_THRESHOLD && prevPeak < CLAP_THRESHOLD * 0.5) {
            const mic = useVoiceStore.getState().micState
            if (mic === 'idle') handleClap()
          }
          prevPeak = normalized
          clapRafRef.current = requestAnimationFrame(checkClap)
        }
        checkClap()
      } catch (err) {
        console.error('[VoiceDetection] Clap detection mic access failed:', err)
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

  useEffect(() => {
    if (!wakeWordEnabled) return
    if (micState !== 'idle') return

    const lower = lastTranscript.toLowerCase().trim()
    if (WAKE_WORDS.some(w => lower.includes(w))) {
      useVoiceStore.getState().setActivationMode('wake_word')
      startVoice()
    }
  }, [lastTranscript, wakeWordEnabled, micState])

  useEffect(() => {
    if (alwaysOnEnabled && micState === 'idle') {
      useVoiceStore.getState().setActivationMode('always_on')
      startVoice()
    }
  }, [alwaysOnEnabled, micState])
}
