/**
 * CutStudio core algorithms — pure functions over the EDL/transcript contract.
 *
 * The schemas here mirror the CutStudio API (`/api/cut`) exactly; they are the
 * canonical client-side view of `edl.py` + `transcribe.py` output. Nothing in
 * this module touches React, the store, or the network — every function is a
 * pure transform so the mapping math can be reasoned about (and tested) alone.
 *
 * A1 source<->output mapping, A3 word-strike -> EDL, plus the filler/silence
 * apply helpers (A5/A6 apply side; detection itself is server-computed).
 */

export interface Clip {
  start: number
  end: number
  label?: string
}

/**
 * The canonical EDL, matching `edl.py` EXACTLY. `version` and `source` are
 * required by the server's `validate()` — an EDL PUT without them is a 422, so
 * every transform here round-trips them untouched.
 *
 * The revision is deliberately NOT part of this shape: the server carries it in
 * the `X-EDL-Rev` response header and in `project.json`, never in the EDL body.
 * The store tracks it separately as the If-Match value.
 */
export interface Edl {
  version: number
  source: string
  clips: Clip[]
  captions?: boolean
  vertical?: boolean
  output?: string
}

export interface Word {
  word: string
  start: number
  end: number
}

export interface Segment {
  id: number
  start: number
  end: number
  text: string
  words: Word[]
}

export interface Transcript {
  language: string
  duration: number
  segments: Segment[]
}

export interface FillerHit {
  seg: number
  word: string
  start: number
  end: number
  text: string
}

export interface SilenceGap {
  after_word: string
  start: number
  end: number
  length: number
}

export interface Detections {
  filler_words: FillerHit[]
  silence_gaps: SilenceGap[]
}

export interface HighlightScore {
  hook: number
  flow: number
  value: number
  overall: number
}

export interface HighlightCandidate {
  start: number
  end: number
  hook_line: string
  reason: string
  score: HighlightScore
}

export type JobState = 'queued' | 'running' | 'done' | 'error'

export interface Job {
  id: string
  kind: string
  project_id: string
  state: JobState
  detail: string
  progress: number
  artifact: unknown | null
  created: number
  started: number | null
  finished: number | null
}

/**
 * A project as the API returns it. Two shapes reach the client and this type is
 * the union of both, so every consumer must treat the optional fields as
 * genuinely optional:
 *
 * - `GET /projects` (the list) omits `media` and returns `renders` as bare
 *   filenames.
 * - `GET /projects/{id}` returns the full `project.json` (so `media` IS
 *   present) but carries no `renders` key at all.
 *
 * `renders` is therefore render FILENAMES, not objects, and may be absent.
 */
export interface Project {
  id: string
  name: string
  created: number
  duration: number
  /** Present on the single-project fetch; absent from the list response. */
  media?: string
  size?: number
  width?: number
  height?: number
  fps?: number
  has_transcript: boolean
  /** Render filenames under the project's `renders/` dir; absent on the single fetch. */
  renders?: string[]
}

/** Adjacent clips closer than this merge back together on restore (A3). */
export const MERGE_GAP = 0.15
/** Minimum clip length a timeline drag may produce. */
export const MIN_CLIP = 0.2

/** Kept ranges = the EDL clips, sorted and defensively normalized. */
export function keptRanges(edl: Edl | null): Clip[] {
  if (!edl) return []
  return edl.clips
    .filter((c) => c.end > c.start)
    .map((c) => ({ start: c.start, end: c.end }))
    .sort((a, b) => a.start - b.start)
}

/** Total output duration = sum of kept clip durations. */
export function edlDuration(edl: Edl | null): number {
  return keptRanges(edl).reduce((acc, c) => acc + (c.end - c.start), 0)
}

/**
 * A1 — memoized source<->output mapping.
 *
 * Recomputing the prefix-sum table on every rAF frame (60Hz) would be wasteful,
 * and the EDL only changes on a mutation, so the table is cached per EDL
 * identity + rev. A single-entry cache is enough: exactly one EDL is open.
 */
interface MapTable {
  ranges: Clip[]
  /** prefix[i] = output time at which ranges[i] begins. */
  prefix: number[]
  total: number
}

let _cacheEdl: Edl | null = null
let _cacheTable: MapTable | null = null

/**
 * Cached on EDL object identity. Every mutation here returns a NEW Edl object,
 * so identity is a sound cache key — and it stays correct without a rev, which
 * the EDL body does not carry.
 */
function tableFor(edl: Edl | null): MapTable {
  if (!edl) return { ranges: [], prefix: [], total: 0 }
  if (_cacheEdl === edl && _cacheTable) return _cacheTable

  const ranges = keptRanges(edl)
  const prefix: number[] = []
  let acc = 0
  for (const r of ranges) {
    prefix.push(acc)
    acc += r.end - r.start
  }
  const table: MapTable = { ranges, prefix, total: acc }
  _cacheEdl = edl
  _cacheTable = table
  return table
}

/**
 * Source time -> output (cut) time. A source time that falls inside a REMOVED
 * gap has no exact output position; it resolves to the nearest kept edge, which
 * is what a playhead landing in a gap should visually snap to.
 */
export function sourceToOutput(edl: Edl | null, t: number): number {
  const { ranges, prefix, total } = tableFor(edl)
  if (ranges.length === 0) return 0
  for (let i = 0; i < ranges.length; i++) {
    const r = ranges[i]
    if (t < r.start) return prefix[i]
    if (t <= r.end) return prefix[i] + (t - r.start)
  }
  return total
}

/** Output (cut) time -> source time, walking kept ranges. */
export function outputToSource(edl: Edl | null, t: number): number {
  const { ranges, prefix } = tableFor(edl)
  if (ranges.length === 0) return 0
  const clamped = Math.max(0, t)
  for (let i = 0; i < ranges.length; i++) {
    const r = ranges[i]
    const len = r.end - r.start
    if (clamped < prefix[i] + len) return r.start + (clamped - prefix[i])
  }
  const last = ranges[ranges.length - 1]
  return last.end
}

/** The kept range containing `t`, or null when `t` sits in a removed gap. */
export function rangeAt(edl: Edl | null, t: number): Clip | null {
  const { ranges } = tableFor(edl)
  for (const r of ranges) {
    if (t >= r.start && t < r.end) return r
  }
  return null
}

/** The first kept range starting at or after `t` (A2 skip target). */
export function nextRangeAfter(edl: Edl | null, t: number): Clip | null {
  const { ranges } = tableFor(edl)
  for (const r of ranges) {
    if (r.start > t - 1e-6) return r
  }
  return null
}

/** True when the source time is inside a kept clip. */
export function isKept(edl: Edl | null, t: number): boolean {
  return rangeAt(edl, t) !== null
}

function normalize(clips: Clip[], mergeGap = MERGE_GAP): Clip[] {
  const sorted = clips
    .filter((c) => c.end - c.start > 1e-4)
    .sort((a, b) => a.start - b.start)
  const out: Clip[] = []
  for (const c of sorted) {
    const prev = out[out.length - 1]
    if (prev && c.start - prev.end < mergeGap) {
      prev.end = Math.max(prev.end, c.end)
    } else {
      out.push({ ...c })
    }
  }
  // Labels are positional (`clip00`, `clip01`) on the server; renumber so a
  // split or merge doesn't leave two clips claiming the same label.
  return out.map((c, i) => ({ ...c, label: `clip${String(i).padStart(2, '0')}` }))
}

/**
 * Rebuild an EDL around a new clip list, carrying every other schema field
 * through untouched. `version` and `source` are required by the server's
 * validate(), so dropping them would turn any save into a 422.
 */
function withClips(edl: Edl, clips: Clip[]): Edl {
  return { ...edl, clips }
}

/**
 * A3 — remove [start, end] from the EDL.
 *
 * Per overlapped clip: fully inside the strike -> dropped; strike fully inside
 * the clip -> split in two; edge overlap -> trimmed. Word boundary times are
 * used exactly, so a strike always cuts on the word edges the operator saw.
 */
export function strikeRange(edl: Edl, start: number, end: number): Edl {
  if (end <= start) return edl
  const clips: Clip[] = []
  for (const c of edl.clips) {
    if (c.end <= start || c.start >= end) {
      clips.push({ start: c.start, end: c.end })
      continue
    }
    if (c.start < start) clips.push({ start: c.start, end: start })
    if (c.end > end) clips.push({ start: end, end: c.end })
  }
  return withClips(edl, normalize(clips, 0))
}

/** Strike a contiguous run of words (inclusive of both ends). */
export function strikeWords(edl: Edl, words: Word[]): Edl {
  if (words.length === 0) return edl
  const start = Math.min(...words.map((w) => w.start))
  const end = Math.max(...words.map((w) => w.end))
  return strikeRange(edl, start, end)
}

/**
 * Restore [start, end] to the EDL. Newly adjacent clips merge when the gap
 * between them is under MERGE_GAP, so restoring a word doesn't leave a
 * sub-frame sliver that renders as a stutter.
 */
export function restoreRange(edl: Edl, start: number, end: number): Edl {
  if (end <= start) return edl
  // Restore ranges come from word boundaries or existing clip edges, so they
  // are already inside the media; only the lower bound needs guarding.
  const restored: Clip = { start: Math.max(0, start), end }
  return withClips(edl, normalize([...edl.clips.map((c) => ({ ...c })), restored]))
}

/** Restore a contiguous run of words. */
export function restoreWords(edl: Edl, words: Word[]): Edl {
  if (words.length === 0) return edl
  const start = Math.min(...words.map((w) => w.start))
  const end = Math.max(...words.map((w) => w.end))
  return restoreRange(edl, start, end)
}

/** Replace one clip wholesale (timeline edge drag), keeping the EDL normalized. */
export function replaceClip(edl: Edl, index: number, next: Clip): Edl {
  const clips = edl.clips.map((c, i) => (i === index ? { ...next } : { ...c }))
  return withClips(edl, normalize(clips, 0))
}

/** A5 apply — strike every selected filler hit. */
export function applyFillerStrikes(edl: Edl, hits: FillerHit[]): Edl {
  return hits.reduce((acc, h) => strikeRange(acc, h.start, h.end), edl)
}

/**
 * A6 apply — strike detected silence gaps, keeping `pad` seconds of room on
 * each side so the cut breathes instead of clipping the neighbouring words.
 */
export function applySilenceStrikes(edl: Edl, gaps: SilenceGap[], pad = 0.15): Edl {
  return gaps.reduce((acc, g) => {
    const start = g.start + pad
    const end = g.end - pad
    if (end <= start) return acc
    return strikeRange(acc, start, end)
  }, edl)
}

/** All words in the transcript, flattened in time order. */
export function allWords(transcript: Transcript | null): Word[] {
  if (!transcript) return []
  return transcript.segments.flatMap((s) => s.words)
}

/** Snap a time to the nearest word boundary within `tolerance` seconds. */
export function snapToWord(words: Word[], t: number, tolerance = 0.12): number {
  let best = t
  let bestDelta = tolerance
  for (const w of words) {
    for (const edge of [w.start, w.end]) {
      const delta = Math.abs(edge - t)
      if (delta < bestDelta) {
        bestDelta = delta
        best = edge
      }
    }
  }
  return best
}

/** mm:ss for transport/timeline readouts. */
export function fmtTime(s: number): string {
  if (!isFinite(s) || s < 0) s = 0
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

/** Human summary of an EDL proposal against the current EDL (chat diff card). */
export function edlDiffSummary(current: Edl | null, proposed: Edl | null): string {
  if (!proposed) return ''
  const before = edlDuration(current)
  const after = edlDuration(proposed)
  const delta = before - after
  const sign = delta >= 0 ? '−' : '+'
  return `keeps ${proposed.clips.length} of ${current?.clips.length ?? proposed.clips.length} clips, ${sign}${Math.abs(delta).toFixed(1)}s`
}
