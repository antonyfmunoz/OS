/**
 * useVoice — browser-native voice input/output for the UMH cockpit.
 *
 * STT: Web Speech API (SpeechRecognition) — zero dependencies, Chrome/Edge.
 * TTS: Plays WAV binary frames received over the existing CockpitSocket.
 *
 * The hook manages the full voice lifecycle:
 *   idle → listening → processing → speaking → idle
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { socket } from '../lib/ws-client.ts'

export type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error'

interface UseVoiceReturn {
  state: VoiceState
  transcript: string
  lastResponse: string
  supported: boolean
  startListening: () => void
  stopListening: () => void
  toggle: () => void
}

// Web Speech API types (not in default TS lib)
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
  resultIndex: number
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string
}

type SpeechRecognitionInstance = {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  abort: () => void
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null
  onend: (() => void) | null
  onstart: (() => void) | null
}

function getSpeechRecognition(): (new () => SpeechRecognitionInstance) | null {
  const w = window as unknown as Record<string, unknown>
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as
    | (new () => SpeechRecognitionInstance)
    | null
}

export function useVoice(): UseVoiceReturn {
  const [state, setState] = useState<VoiceState>('idle')
  const [transcript, setTranscript] = useState('')
  const [lastResponse, setLastResponse] = useState('')

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const supported = getSpeechRecognition() !== null

  // Track pending audio to play when binary frame arrives
  const pendingAudioRef = useRef(false)

  // Listen for voice_response and binary audio frames on the WebSocket
  useEffect(() => {
    // Intercept binary messages for TTS audio playback.
    // CockpitSocket only handles text (JSON) — we attach a wrapper for binary.
    const checkWs = () => {
      const rawWs = socket.rawWs
      if (!rawWs) return

      const origHandler = rawWs.onmessage

      rawWs.onmessage = (event: MessageEvent) => {
        // Binary frame = TTS audio
        if (event.data instanceof Blob || event.data instanceof ArrayBuffer) {
          playAudioBlob(event.data)
          return
        }

        // Text frame — check for voice messages before passing through
        try {
          const msg = JSON.parse(event.data as string) as Record<string, unknown>
          if (msg.type === 'voice_ack') {
            setState('processing')
          } else if (msg.type === 'voice_response') {
            setLastResponse((msg.spoken_text as string) || (msg.text as string) || '')
            if (msg.has_audio) {
              pendingAudioRef.current = true
              setState('speaking')
            } else {
              setState('idle')
            }
          }
        } catch {
          // not JSON, ignore
        }

        // Pass through to original handler for non-voice messages
        if (origHandler) {
          origHandler.call(rawWs, event)
        }
      }
    }

    // Check immediately and on a short interval (socket may reconnect)
    checkWs()
    const interval = setInterval(checkWs, 2000)
    return () => clearInterval(interval)
  }, [])

  const playAudioBlob = useCallback(async (data: Blob | ArrayBuffer) => {
    try {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new AudioContext()
      }
      const ctx = audioCtxRef.current
      const buffer = data instanceof Blob ? await data.arrayBuffer() : data
      const audioBuffer = await ctx.decodeAudioData(buffer)
      const source = ctx.createBufferSource()
      source.buffer = audioBuffer
      source.connect(ctx.destination)
      source.onended = () => setState('idle')
      source.start()
    } catch (e) {
      console.error('[useVoice] audio playback failed:', e)
      setState('idle')
    }
  }, [])

  const startListening = useCallback(() => {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition) {
      setState('error')
      return
    }

    // Stop any existing session
    if (recognitionRef.current) {
      recognitionRef.current.abort()
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = 'en-US'
    recognitionRef.current = recognition

    recognition.onstart = () => {
      setState('listening')
      setTranscript('')
    }

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let final = ''
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result && result[0]) {
          if (result.isFinal) {
            final += result[0].transcript
          } else {
            interim += result[0].transcript
          }
        }
      }

      setTranscript(final || interim)

      // When we get a final result, send it to the backend
      if (final) {
        setState('processing')
        socket.send('voice_transcript', { transcript: final })
      }
    }

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error('[useVoice] recognition error:', event.error)
      if (event.error !== 'aborted') {
        setState('error')
        setTimeout(() => setState('idle'), 2000)
      }
    }

    recognition.onend = () => {
      // If we're still listening (no final result yet), restart
      if (state === 'listening') {
        setState('idle')
      }
    }

    recognition.start()
  }, [state])

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    if (state === 'listening') {
      setState('idle')
    }
  }, [state])

  const toggle = useCallback(() => {
    if (state === 'listening') {
      stopListening()
    } else if (state === 'idle' || state === 'error') {
      startListening()
    }
  }, [state, startListening, stopListening])

  return {
    state,
    transcript,
    lastResponse,
    supported,
    startListening,
    stopListening,
    toggle,
  }
}
