/**
 * TTS Playback Controller — manages audio playback with iOS unlock support.
 *
 * iOS Safari blocks Audio.play() unless called from a user gesture context.
 * This controller unlocks audio on the first mic tap (a user gesture) and
 * reuses that unlocked Audio element for all subsequent TTS playback.
 *
 * Phase 14.13V — Voice UX Seal
 */

const log = (stage: string, ...args: unknown[]) =>
  console.log(`[TTSPlayback] ${stage}`, ...args)

export type PlaybackStatus = 'idle' | 'unlocking' | 'playing' | 'error'

export interface TtsPlaybackState {
  audioUnlocked: boolean
  unlockAttempted: boolean
  unlockError: string | null
  playbackStatus: PlaybackStatus
}

let _state: TtsPlaybackState = {
  audioUnlocked: false,
  unlockAttempted: false,
  unlockError: null,
  playbackStatus: 'idle',
}

type StateListener = (state: TtsPlaybackState) => void
const _listeners: StateListener[] = []

function _notify(): void {
  for (const fn of _listeners) fn({ ..._state })
}

export function onPlaybackStateChange(fn: StateListener): () => void {
  _listeners.push(fn)
  return () => {
    const idx = _listeners.indexOf(fn)
    if (idx >= 0) _listeners.splice(idx, 1)
  }
}

export function getPlaybackState(): TtsPlaybackState {
  return { ..._state }
}

/** Reusable Audio element — created once, reused for every TTS chunk. */
let _unlockedAudio: HTMLAudioElement | null = null
let _audioContext: AudioContext | null = null

/**
 * Unlock audio for iOS. Must be called from a user gesture handler (e.g. mic tap).
 * Creates a silent Audio element and calls play() to satisfy iOS autoplay policy.
 * Also resumes an AudioContext if suspended.
 */
export async function unlockAudioForIOS(): Promise<boolean> {
  if (_state.audioUnlocked) {
    log('already_unlocked')
    return true
  }

  _state.unlockAttempted = true
  _state.playbackStatus = 'unlocking'
  _state.unlockError = null
  _notify()
  log('unlock_attempt_start')

  try {
    // Create a silent WAV (44-byte header + no samples = valid empty WAV)
    const silentWav = _createSilentWav()
    const blob = new Blob([silentWav], { type: 'audio/wav' })
    const url = URL.createObjectURL(blob)

    const audio = new Audio(url)
    audio.volume = 0
    // P4S-VOICE-UNLOCK-HANG: on iOS 18.7 Safari, HTMLAudioElement.play() on a blob
    // URL can return a Promise that NEVER settles — it hung the whole voice-start
    // chain here (client diag: ios_audio_unlock_await never returned; the 8s watchdog
    // fired → false "Voice did not start in time"). Bound play() so a hung unlock
    // degrades to a fast failure instead of stalling recording. Unlock is a TTS-
    // playback nicety; it must NEVER block mic capture.
    await Promise.race([
      audio.play(),
      new Promise<void>((_, reject) =>
        setTimeout(() => reject(new Error('audio.play() timed out (iOS unlock hang)')), 1200),
      ),
    ])
    audio.pause()
    URL.revokeObjectURL(url)

    // Keep reference for reuse
    _unlockedAudio = new Audio()

    log('audio_element_unlocked')

    // Also resume AudioContext if one exists
    try {
      _audioContext = new AudioContext()
      if (_audioContext.state === 'suspended') {
        await _audioContext.resume()
        log('audio_context_resumed')
      }
    } catch (ctxErr) {
      log('audio_context_resume_skipped', ctxErr)
      // Non-critical — AudioContext is optional for TTS playback
    }

    _state.audioUnlocked = true
    _state.playbackStatus = 'idle'
    _state.unlockError = null
    _notify()
    log('unlock_success')
    return true
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Unknown audio unlock error'
    log('unlock_failed', msg)
    _state.audioUnlocked = false
    _state.playbackStatus = 'error'
    _state.unlockError = msg
    _notify()
    return false
  }
}

/** Audio playback queue — processes chunks sequentially. */
let _playQueue: ArrayBuffer[] = []
let _isPlaying = false
let _currentAudio: HTMLAudioElement | null = null

/** Callback invoked when playback completes (queue drained) or play() is rejected. */
let _onPlaybackDone: (() => void) | null = null
let _onPlaybackRejected: ((reason: string) => void) | null = null

export function setPlaybackCallbacks(
  onDone: (() => void) | null,
  onRejected: ((reason: string) => void) | null,
): void {
  _onPlaybackDone = onDone
  _onPlaybackRejected = onRejected
}

/**
 * Queue a TTS audio buffer for playback. Plays sequentially.
 * If audio is not unlocked on iOS, play() may reject — the rejection
 * is surfaced via onPlaybackRejected callback.
 */
export function playTtsAudio(buffer: ArrayBuffer): void {
  log('audio_queued', `bytes=${buffer.byteLength}`, `queue_depth=${_playQueue.length}`)
  _playQueue.push(buffer)
  if (!_isPlaying) _drainQueue()
}

/**
 * Cancel all queued and current playback.
 */
export function cancelPlayback(): void {
  _playQueue = []
  if (_currentAudio) {
    _currentAudio.pause()
    _currentAudio.onended = null
    _currentAudio.onerror = null
    _currentAudio = null
  }
  _isPlaying = false
  _state.playbackStatus = 'idle'
  _notify()
  log('playback_cancelled')
}

/**
 * Check if currently playing or has queued audio.
 */
export function isPlaybackActive(): boolean {
  return _isPlaying || _playQueue.length > 0
}

function _drainQueue(): void {
  const buf = _playQueue.shift()
  if (!buf) {
    _isPlaying = false
    _currentAudio = null
    _state.playbackStatus = 'idle'
    _notify()
    log('queue_drained')
    _onPlaybackDone?.()
    return
  }

  _isPlaying = true
  _state.playbackStatus = 'playing'
  _notify()

  try {
    const blob = new Blob([buf], { type: 'audio/wav' })
    const url = URL.createObjectURL(blob)

    // Reuse unlocked audio element if available (iOS), otherwise create new
    const audio = _unlockedAudio ? _unlockedAudio : new Audio()
    audio.src = url
    _currentAudio = audio

    audio.onended = () => {
      URL.revokeObjectURL(url)
      log('chunk_played')
      _drainQueue()
    }

    audio.onerror = () => {
      URL.revokeObjectURL(url)
      log('chunk_play_error')
      _drainQueue()
    }

    audio.play().catch((err) => {
      URL.revokeObjectURL(url)
      const reason = err instanceof Error ? err.message : 'play() rejected'
      log('play_rejected', reason)
      _state.playbackStatus = 'error'
      _state.unlockError = reason
      _notify()
      // Drain remaining queue on failure
      _playQueue = []
      _isPlaying = false
      _currentAudio = null
      _onPlaybackRejected?.(reason)
    })
  } catch (err) {
    log('playback_exception', err)
    _drainQueue()
  }
}

/**
 * Reset all playback state. Called on voice session teardown.
 */
export function resetPlayback(): void {
  cancelPlayback()
  _unlockedAudio = null
  if (_audioContext && _audioContext.state !== 'closed') {
    _audioContext.close().catch(() => { /* ignore */ })
  }
  _audioContext = null
  _state = {
    audioUnlocked: false,
    unlockAttempted: false,
    unlockError: null,
    playbackStatus: 'idle',
  }
  _notify()
  log('playback_reset')
}

/**
 * Create a minimal valid WAV file with silence (44 bytes header, 0 data bytes).
 * Used to unlock audio on iOS via a user gesture.
 */
function _createSilentWav(): ArrayBuffer {
  const numSamples = 1
  const buffer = new ArrayBuffer(44 + numSamples * 2)
  const view = new DataView(buffer)
  const sampleRate = 16000

  // RIFF header
  _writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + numSamples * 2, true)
  _writeString(view, 8, 'WAVE')

  // fmt chunk
  _writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // byte rate
  view.setUint16(32, 2, true) // block align
  view.setUint16(34, 16, true) // bits per sample

  // data chunk
  _writeString(view, 36, 'data')
  view.setUint32(40, numSamples * 2, true)
  view.setInt16(44, 0, true) // one silent sample

  return buffer
}

function _writeString(view: DataView, offset: number, str: string): void {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i))
  }
}
