import type { VoiceCommandState, VoiceTranscript } from './voiceTypes'

type SpeechRecognitionLike = {
  continuous: boolean
  interimResults: boolean
  lang: string
  start(): void
  stop(): void
  abort(): void
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onerror: ((event: SpeechRecognitionErrorLike) => void) | null
  onend: (() => void) | null
  onstart: (() => void) | null
}

type SpeechRecognitionEventLike = {
  resultIndex: number
  results: {
    length: number
    [index: number]: {
      isFinal: boolean
      [index: number]: { transcript: string; confidence: number }
      length: number
    }
  }
}

type SpeechRecognitionErrorLike = {
  error: string
  message?: string
}

export type SpeechStateListener = (state: VoiceCommandState) => void
export type TranscriptListener = (transcript: VoiceTranscript) => void
export type ErrorListener = (error: string) => void

let _idCounter = 0
function nextTranscriptId(): string {
  return `vt-${Date.now()}-${++_idCounter}`
}

function getSpeechRecognitionConstructor(): (new () => SpeechRecognitionLike) | null {
  const w = globalThis as Record<string, unknown>
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as
    | (new () => SpeechRecognitionLike)
    | null
}

export class SpeechInputAdapter {
  private recognition: SpeechRecognitionLike | null = null
  private state: VoiceCommandState = 'idle'
  private sessionId: string = ''
  private currentTranscriptId: string = ''
  private startedAt: string = ''

  private stateListeners: SpeechStateListener[] = []
  private interimListeners: TranscriptListener[] = []
  private finalListeners: TranscriptListener[] = []
  private errorListeners: ErrorListener[] = []

  isSupported(): boolean {
    return getSpeechRecognitionConstructor() !== null
  }

  startListening(sessionId: string): boolean {
    if (!this.isSupported()) {
      this.setState('unsupported')
      this.emitError('Speech recognition not supported in this browser')
      return false
    }

    const Ctor = getSpeechRecognitionConstructor()!
    this.recognition = new Ctor()
    this.recognition.continuous = false
    this.recognition.interimResults = true
    this.recognition.lang = 'en-US'
    this.sessionId = sessionId
    this.currentTranscriptId = nextTranscriptId()
    this.startedAt = new Date().toISOString()

    this.recognition.onstart = () => {
      this.setState('listening')
    }

    this.recognition.onresult = (event: SpeechRecognitionEventLike) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        const alt = result[0]
        const transcript: VoiceTranscript = {
          transcript_id: this.currentTranscriptId,
          session_id: this.sessionId,
          text: alt.transcript,
          confidence: alt.confidence,
          source: 'browser_speech',
          interim: !result.isFinal,
          final: result.isFinal,
          started_at: this.startedAt,
          completed_at: result.isFinal ? new Date().toISOString() : null,
          error: null,
        }

        if (result.isFinal) {
          this.setState('transcribed')
          this.emitFinalTranscript(transcript)
        } else {
          this.setState('processing')
          this.emitInterimTranscript(transcript)
        }
      }
    }

    this.recognition.onerror = (event: SpeechRecognitionErrorLike) => {
      const msg = event.message || event.error
      this.setState('error')
      this.emitError(msg)
    }

    this.recognition.onend = () => {
      if (this.state === 'listening' || this.state === 'processing') {
        this.setState('idle')
      }
    }

    try {
      this.recognition.start()
      return true
    } catch {
      this.setState('error')
      this.emitError('Failed to start speech recognition')
      return false
    }
  }

  stopListening(): void {
    if (this.recognition) {
      this.recognition.stop()
    }
  }

  abort(): void {
    if (this.recognition) {
      this.recognition.abort()
      this.setState('idle')
    }
  }

  getState(): VoiceCommandState {
    return this.state
  }

  onStateChange(listener: SpeechStateListener): () => void {
    this.stateListeners.push(listener)
    return () => {
      this.stateListeners = this.stateListeners.filter((l) => l !== listener)
    }
  }

  onInterimTranscript(listener: TranscriptListener): () => void {
    this.interimListeners.push(listener)
    return () => {
      this.interimListeners = this.interimListeners.filter((l) => l !== listener)
    }
  }

  onFinalTranscript(listener: TranscriptListener): () => void {
    this.finalListeners.push(listener)
    return () => {
      this.finalListeners = this.finalListeners.filter((l) => l !== listener)
    }
  }

  onError(listener: ErrorListener): () => void {
    this.errorListeners.push(listener)
    return () => {
      this.errorListeners = this.errorListeners.filter((l) => l !== listener)
    }
  }

  private setState(state: VoiceCommandState): void {
    this.state = state
    for (const l of this.stateListeners) l(state)
  }

  private emitInterimTranscript(t: VoiceTranscript): void {
    for (const l of this.interimListeners) l(t)
  }

  private emitFinalTranscript(t: VoiceTranscript): void {
    for (const l of this.finalListeners) l(t)
  }

  private emitError(error: string): void {
    for (const l of this.errorListeners) l(error)
  }
}

export const speechAdapter = new SpeechInputAdapter()
