/**
 * Voice Turn Assembler — collects STT transcript segments into a single
 * coherent turn before dispatching to the advisor.
 *
 * Prevents duplicate messages from STT pauses. A "turn" starts when the
 * mic begins recording and ends either by:
 *   - Silence grace timeout (1600ms desktop / 2200ms mobile)
 *   - Tap-to-stop (immediate commit)
 *   - Barge-in (cancel current TTS, start new turn)
 *
 * Phase 14.13V — Voice UX Seal
 */

const log = (stage: string, ...args: unknown[]) =>
  console.log(`[VoiceTurn] ${stage}`, ...args)

export interface VoiceTranscriptSegment {
  text: string
  timestamp: number
  index: number
}

export type VoiceTurnStatus = 'active' | 'assembling' | 'committed' | 'cancelled'

export interface VoiceTurnState {
  voiceTurnId: string
  status: VoiceTurnStatus
  partialText: string
  finalSegments: VoiceTranscriptSegment[]
  assembledText: string
  createdAt: number
}

let _currentTurn: VoiceTurnState | null = null
let _silenceTimer: ReturnType<typeof setTimeout> | null = null
let _segmentIndex = 0

/** Detect mobile via user agent or viewport width. */
function _isMobile(): boolean {
  if (typeof window === 'undefined') return false
  const ua = navigator.userAgent || ''
  return /Mobi|Android|iPhone|iPad/i.test(ua) || window.innerWidth < 768
}

/** Silence grace window: 1600ms desktop, 2200ms mobile. */
export function getSilenceTimeoutMs(): number {
  return _isMobile() ? 2200 : 1600
}

/**
 * Create a new voice turn. Call this when mic recording starts.
 */
export function createTurn(): VoiceTurnState {
  // Cancel any pending silence timer from previous turn
  if (_silenceTimer) {
    clearTimeout(_silenceTimer)
    _silenceTimer = null
  }

  const turnId = _generateTurnId()
  _segmentIndex = 0

  _currentTurn = {
    voiceTurnId: turnId,
    status: 'active',
    partialText: '',
    finalSegments: [],
    assembledText: '',
    createdAt: Date.now(),
  }

  log('turn_created', turnId)
  return { ..._currentTurn }
}

/**
 * Append a final transcript segment to the current turn.
 * Called when STT sends final=true. Restarts the silence timer.
 */
export function appendSegment(text: string): VoiceTurnState | null {
  if (!_currentTurn || _currentTurn.status !== 'active') {
    log('append_ignored', 'no active turn')
    return null
  }

  const normalized = normalizeTranscript(text)
  if (!normalized) {
    log('append_ignored', 'empty after normalize')
    return _currentTurn ? { ..._currentTurn } : null
  }

  const segment: VoiceTranscriptSegment = {
    text: normalized,
    timestamp: Date.now(),
    index: _segmentIndex++,
  }

  _currentTurn.finalSegments.push(segment)
  _currentTurn.finalSegments = deduplicateSegments(_currentTurn.finalSegments)

  log('segment_appended', `idx=${segment.index}`, `segments=${_currentTurn.finalSegments.length}`, normalized.slice(0, 60))

  return { ..._currentTurn }
}

/**
 * Update the live partial text (non-final transcript).
 */
export function updatePartial(text: string): void {
  if (!_currentTurn || _currentTurn.status !== 'active') return
  _currentTurn.partialText = text
}

/**
 * Start or restart the silence timer. When it fires, the turn is committed.
 * Returns the timeout handle.
 */
export function startSilenceTimer(onTimeout: (turn: VoiceTurnState) => void): void {
  if (_silenceTimer) {
    clearTimeout(_silenceTimer)
  }

  const timeoutMs = getSilenceTimeoutMs()
  log('silence_timer_start', `${timeoutMs}ms`)

  _silenceTimer = setTimeout(() => {
    _silenceTimer = null
    if (_currentTurn && _currentTurn.status === 'active') {
      log('silence_timeout', `${timeoutMs}ms elapsed`)
      const committed = commitTurn()
      if (committed) {
        onTimeout(committed)
      }
    }
  }, timeoutMs)
}

/**
 * Commit the current turn: assemble all segments into final text.
 * Called by silence timer, tap-to-stop, or barge-in.
 */
export function commitTurn(): VoiceTurnState | null {
  if (_silenceTimer) {
    clearTimeout(_silenceTimer)
    _silenceTimer = null
  }

  if (!_currentTurn) {
    log('commit_ignored', 'no current turn')
    return null
  }

  if (_currentTurn.status !== 'active') {
    log('commit_ignored', `status=${_currentTurn.status}`)
    return null
  }

  _currentTurn.status = 'assembling'

  // Assemble all segments into one text
  const assembled = _currentTurn.finalSegments
    .map(s => s.text)
    .join(' ')

  _currentTurn.assembledText = normalizeTranscript(assembled)
  _currentTurn.status = 'committed'

  log('turn_committed', _currentTurn.voiceTurnId, `segments=${_currentTurn.finalSegments.length}`, _currentTurn.assembledText.slice(0, 80))

  const result = { ..._currentTurn }
  _currentTurn = null
  return result
}

/**
 * Cancel the current turn without committing.
 */
export function cancelTurn(): void {
  if (_silenceTimer) {
    clearTimeout(_silenceTimer)
    _silenceTimer = null
  }
  if (_currentTurn) {
    _currentTurn.status = 'cancelled'
    log('turn_cancelled', _currentTurn.voiceTurnId)
    _currentTurn = null
  }
}

/**
 * Get the current turn state (immutable snapshot).
 */
export function getCurrentTurn(): VoiceTurnState | null {
  return _currentTurn ? { ..._currentTurn } : null
}

/**
 * Check if a turn is currently active.
 */
export function hasTurnActive(): boolean {
  return _currentTurn !== null && _currentTurn.status === 'active'
}

/**
 * Normalize transcript text: trim, collapse whitespace.
 */
export function normalizeTranscript(text: string): string {
  return text
    .trim()
    .replace(/\s+/g, ' ')
}

/**
 * Deduplicate segments by merging overlapping text.
 * If a later segment's text is a substring of the previous one
 * (or vice versa), keep the longer one.
 */
export function deduplicateSegments(segments: VoiceTranscriptSegment[]): VoiceTranscriptSegment[] {
  if (segments.length <= 1) return segments

  const result: VoiceTranscriptSegment[] = [segments[0]]

  for (let i = 1; i < segments.length; i++) {
    const prev = result[result.length - 1]
    const curr = segments[i]
    const prevLower = prev.text.toLowerCase()
    const currLower = curr.text.toLowerCase()

    // If current is a substring of previous, skip it
    if (prevLower.includes(currLower)) {
      log('dedup_skip_subset', `"${curr.text}" is subset of "${prev.text}"`)
      continue
    }

    // If previous is a substring of current, replace with current
    if (currLower.includes(prevLower)) {
      log('dedup_replace_superset', `"${curr.text}" supersedes "${prev.text}"`)
      result[result.length - 1] = curr
      continue
    }

    // Check for overlapping suffix/prefix
    const overlap = _findOverlap(prev.text, curr.text)
    if (overlap > 3) {
      // Merge: take previous text + non-overlapping part of current
      const merged = prev.text + ' ' + curr.text.slice(overlap)
      log('dedup_merge_overlap', `overlap=${overlap}`, `merged="${merged.slice(0, 60)}"`)
      result[result.length - 1] = {
        ...prev,
        text: normalizeTranscript(merged),
      }
      continue
    }

    result.push(curr)
  }

  return result
}

/**
 * Find the length of the longest suffix of `a` that matches a prefix of `b`.
 */
function _findOverlap(a: string, b: string): number {
  const aLower = a.toLowerCase()
  const bLower = b.toLowerCase()
  const maxLen = Math.min(a.length, b.length)

  for (let len = maxLen; len > 0; len--) {
    if (aLower.endsWith(bLower.substring(0, len))) {
      return len
    }
  }
  return 0
}

/**
 * Generate a voice turn ID using crypto.randomUUID if available,
 * falling back to Math.random.
 */
function _generateTurnId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `vt-${crypto.randomUUID()}`
  }
  // Fallback
  const rand = Math.random().toString(36).slice(2, 14)
  return `vt-${Date.now()}-${rand}`
}
