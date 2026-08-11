import { describe, expect, it } from 'vitest'
import {
  edlDuration,
  keptRanges,
  nextRangeAfter,
  outputToSource,
  rangeAt,
  restoreRange,
  snapToWord,
  sourceToOutput,
  strikeRange,
  strikeWords,
} from '../utils/cutAlgorithms'
import type { Edl, Word } from '../utils/cutAlgorithms'

/** A full-schema EDL — `version`/`source` are required by the server's validate(). */
function edlOf(clips: Array<[number, number]>): Edl {
  return {
    version: 1,
    source: '/media/vod.mp4',
    clips: clips.map(([start, end]) => ({ start, end })),
    captions: false,
    vertical: false,
    output: 'cut_output.mp4',
  }
}

describe('strikeRange (A3)', () => {
  it('splits a clip when the strike falls inside it', () => {
    const next = strikeRange(edlOf([[0, 10]]), 4, 6)
    expect(next.clips.map((c) => [c.start, c.end])).toEqual([
      [0, 4],
      [6, 10],
    ])
  })

  it('drops a clip that sits entirely inside the strike', () => {
    const next = strikeRange(edlOf([[0, 2], [4, 6], [8, 10]]), 3, 7)
    expect(next.clips.map((c) => [c.start, c.end])).toEqual([
      [0, 2],
      [8, 10],
    ])
  })

  it('trims a clip overlapped at its edge', () => {
    const next = strikeRange(edlOf([[0, 10]]), 8, 20)
    expect(next.clips.map((c) => [c.start, c.end])).toEqual([[0, 8]])
  })

  it('preserves the schema fields the server requires', () => {
    const next = strikeRange(edlOf([[0, 10]]), 4, 6)
    expect(next.version).toBe(1)
    expect(next.source).toBe('/media/vod.mp4')
    expect(next.output).toBe('cut_output.mp4')
  })

  it('uses word boundary times exactly', () => {
    const words: Word[] = [
      { word: 'um', start: 3.25, end: 3.5 },
      { word: 'so', start: 3.5, end: 3.9 },
    ]
    const next = strikeWords(edlOf([[0, 10]]), words)
    expect(next.clips.map((c) => [c.start, c.end])).toEqual([
      [0, 3.25],
      [3.9, 10],
    ])
  })

  it('returns the EDL untouched for an empty range', () => {
    const before = edlOf([[0, 10]])
    expect(strikeRange(before, 5, 5)).toBe(before)
  })
})

describe('restoreRange (A3)', () => {
  it('merges clips left adjacent by the restore', () => {
    const struck = strikeRange(edlOf([[0, 10]]), 4, 6)
    const restored = restoreRange(struck, 4, 6)
    expect(restored.clips.map((c) => [c.start, c.end])).toEqual([[0, 10]])
  })

  it('merges across a sub-threshold gap but not a wide one', () => {
    const narrow = restoreRange(edlOf([[0, 4], [4.1, 10]]), 4, 4.05)
    expect(narrow.clips).toHaveLength(1)

    const wide = restoreRange(edlOf([[0, 4], [9, 10]]), 4, 4.05)
    expect(wide.clips).toHaveLength(2)
  })
})

describe('source<->output mapping (A1)', () => {
  const edl = edlOf([[0, 10], [20, 30]])

  it('sums only kept material', () => {
    expect(edlDuration(edl)).toBe(20)
    expect(keptRanges(edl)).toHaveLength(2)
  })

  it('maps source time past a gap to compacted output time', () => {
    expect(sourceToOutput(edl, 5)).toBe(5)
    expect(sourceToOutput(edl, 25)).toBe(15)
  })

  it('snaps a source time inside a removed gap to the kept edge', () => {
    expect(sourceToOutput(edl, 15)).toBe(10)
  })

  it('round-trips output->source->output', () => {
    for (const t of [0, 3, 10, 15, 19.9]) {
      expect(sourceToOutput(edl, outputToSource(edl, t))).toBeCloseTo(t, 6)
    }
  })

  it('maps output time back across the gap', () => {
    expect(outputToSource(edl, 15)).toBe(25)
  })

  it('recomputes after a mutation rather than serving a stale cache', () => {
    expect(edlDuration(edl)).toBe(20)
    const cut = strikeRange(edl, 0, 5)
    expect(edlDuration(cut)).toBe(15)
    expect(edlDuration(edl)).toBe(20)
  })
})

describe('playback helpers (A2)', () => {
  const edl = edlOf([[0, 10], [20, 30]])

  it('reports the range containing a time, and null inside a gap', () => {
    expect(rangeAt(edl, 5)?.start).toBe(0)
    expect(rangeAt(edl, 15)).toBeNull()
  })

  it('finds the next kept range to jump to, and null past the end', () => {
    expect(nextRangeAfter(edl, 10)?.start).toBe(20)
    expect(nextRangeAfter(edl, 30)).toBeNull()
  })
})

describe('snapToWord', () => {
  const words: Word[] = [
    { word: 'hello', start: 1.0, end: 1.4 },
    { word: 'world', start: 1.45, end: 2.0 },
  ]

  it('snaps to a boundary inside the tolerance', () => {
    expect(snapToWord(words, 1.42)).toBe(1.4)
  })

  it('leaves a time outside the tolerance alone', () => {
    expect(snapToWord(words, 5.0)).toBe(5.0)
  })
})
