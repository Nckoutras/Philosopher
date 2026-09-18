// BUG-024 — the quotes feed grew without bound.
//
// appendCycle appended a whole permutation of the corpus each time the reader neared
// the end, and nothing was ever removed: 88 -> 176 -> 264 -> ... for as long as the
// tab stayed open.
//
// The arithmetic is here rather than in the page because it is the half that CAN be
// checked. jsdom has no layout — offsetLeft is 0 on every element — so the trim and
// its scroll compensation cannot be asserted through a rendered carousel at all. This
// module is pure, so convergence, the safety bound and the compensation can be proven
// rather than sampled.
//
// WHAT IS NOT COVERED HERE, said plainly rather than left to be assumed: the WIRING.
// That the page reads a live stride from two adjacent cards, and applies the
// compensation in a layout effect before paint, is verified by the smoke test and by
// nothing in this repository. A component-level attempt was written and abandoned —
// the carousel keeps its own interval and jsdom reports no geometry, so the test hung
// rather than failing, which is worse than not having it.
import { describe, it, expect } from 'vitest'
import {
  appendBounded,
  compensatedScrollLeft,
  computeTrim,
  MAX_FEED,
  KEEP_BEHIND,
  type FeedItem,
} from '../quotesFeed'
import type { Quote } from '@/lib/api'

const pool = (n: number, tag = 'q'): Quote[] =>
  Array.from({ length: n }, (_, i) => ({ id: `${tag}${i}` }) as Quote)

describe('computeTrim — bounded twice', () => {
  it('trims nothing under the cap, however far along the reader is', () => {
    expect(computeTrim(MAX_FEED, 10_000)).toBe(0)
    expect(computeTrim(MAX_FEED - 1, 10_000)).toBe(0)
  })

  it('trims the overshoot once past the cap', () => {
    // Reader far enough along that the position bound is not the binding one.
    expect(computeTrim(MAX_FEED + 24, 10_000)).toBe(24)
    expect(computeTrim(MAX_FEED + 88, 10_000)).toBe(88)
  })

  it('NEVER trims past the reader, whatever the overshoot', () => {
    // The safety bound, and the reason this fix cannot become the bug it replaces.
    // A reader still at the head has nothing behind them to remove.
    expect(computeTrim(MAX_FEED + 1000, 0)).toBe(0)
    expect(computeTrim(MAX_FEED + 1000, KEEP_BEHIND)).toBe(0)
    expect(computeTrim(MAX_FEED + 1000, KEEP_BEHIND - 1)).toBe(0)
  })

  it('leaves exactly KEEP_BEHIND cards behind the reader when position binds', () => {
    const index = KEEP_BEHIND + 5
    expect(computeTrim(MAX_FEED + 1000, index)).toBe(5)
  })

  it('never returns a negative trim', () => {
    for (const len of [0, 1, 50, MAX_FEED, MAX_FEED + 1]) {
      for (const idx of [0, 1, 24, 100, 10_000]) {
        expect(computeTrim(len, idx)).toBeGreaterThanOrEqual(0)
      }
    }
  })
})

describe('appendBounded — identity', () => {
  it('assigns monotonic seq that never repeats across appends', () => {
    let feed: FeedItem[] = []
    for (let i = 0; i < 5; i++) feed = appendBounded(feed, pool(10, `c${i}-`), 0)

    const seqs = feed.map((f) => f.seq)
    expect(new Set(seqs).size).toBe(seqs.length)
    expect([...seqs].sort((a, b) => a - b)).toEqual(seqs)
  })

  it('keeps seq STABLE across a trim — the whole reason a trim is possible', () => {
    // Before this, the page keyed cards by array index, so removing one item from the
    // head changed every remaining key and React remounted the entire list. The
    // reader lost their place: the exact failure the trim exists to avoid.
    let feed: FeedItem[] = []
    for (let i = 0; i < 30; i++) feed = appendBounded(feed, pool(20, `c${i}-`), 10_000)
    expect(feed.length).toBeLessThanOrEqual(MAX_FEED)

    const survivor = feed[feed.length - 50]
    const after = appendBounded(feed, pool(20, 'next-'), 10_000)
    const stillThere = after.find((f) => f.seq === survivor.seq)

    expect(stillThere).toBeDefined()
    expect(stillThere!.quote.id).toBe(survivor.quote.id)
  })

  it('avoids a seam repeat: the new cycle never opens on the quote the feed ends on', () => {
    const first = appendBounded([], pool(5), 0)
    const lastId = first[first.length - 1].quote.id
    // A cycle deliberately starting with that same quote.
    const colliding = [{ id: lastId } as Quote, ...pool(4, 'other')]
    const next = appendBounded(first, colliding, 0)

    expect(next[first.length].quote.id).not.toBe(lastId)
  })
})

describe('appendBounded — convergence', () => {
  it('converges and stays bounded over a long session', () => {
    // The trace in the module docstring, executed: 88 -> 176 -> 264 -> trim -> 240 ...
    const CORPUS = 88
    let feed: FeedItem[] = appendBounded([], pool(CORPUS), 0)
    let peak = feed.length

    for (let i = 0; i < 200; i++) {
      // The reader is always near the end when an append fires — that is what
      // triggers it (idx >= total - 3).
      feed = appendBounded(feed, pool(CORPUS, `c${i}-`), feed.length - 3)
      peak = Math.max(peak, feed.length)
    }

    // Bounded: a single append may overshoot the cap by one corpus before the next
    // trim, and nothing may ever exceed that.
    expect(peak).toBeLessThanOrEqual(MAX_FEED + CORPUS)
    // Settled, not merely capped.
    expect(feed.length).toBe(MAX_FEED)
  })

  it('does not thrash: a steady reader sees one trim per append at steady state', () => {
    const CORPUS = 88
    let feed: FeedItem[] = appendBounded([], pool(CORPUS), 0)
    for (let i = 0; i < 10; i++) {
      feed = appendBounded(feed, pool(CORPUS, `w${i}-`), feed.length - 3)
    }

    const before = feed.length
    feed = appendBounded(feed, pool(CORPUS, 'final-'), feed.length - 3)
    // Grew by a corpus, trimmed by a corpus, same length out.
    expect(feed.length).toBe(before)
  })

  it('a corpus LARGER than the cap still bounds, rather than looping or emptying', () => {
    // The pool is server-controlled. A 400-quote corpus must not break the rule.
    let feed: FeedItem[] = appendBounded([], pool(400), 0)
    expect(feed.length).toBe(400) // reader at the head: nothing behind them to trim

    feed = appendBounded(feed, pool(400, 'b'), feed.length - 3)
    expect(feed.length).toBeGreaterThan(0)
    expect(feed.length).toBeLessThanOrEqual(MAX_FEED + 400)
  })
})

describe('compensatedScrollLeft — the reader does not move', () => {
  const STRIDE = 300

  it('subtracts exactly one stride per removed card', () => {
    expect(compensatedScrollLeft(100 * STRIDE, 24, STRIDE)).toBe(76 * STRIDE)
    expect(compensatedScrollLeft(100 * STRIDE, 88, STRIDE)).toBe(12 * STRIDE)
  })

  it('is a no-op when nothing was trimmed', () => {
    expect(compensatedScrollLeft(5_000, 0, STRIDE)).toBe(5_000)
  })

  it('is a no-op when the stride is unmeasurable', () => {
    // Before first layout, or with a single card, offsetLeft deltas are 0. Scaling by
    // a zero or negative stride would slam the carousel to the head.
    expect(compensatedScrollLeft(5_000, 24, 0)).toBe(5_000)
    expect(compensatedScrollLeft(5_000, 24, -10)).toBe(5_000)
  })

  it('never goes negative', () => {
    expect(compensatedScrollLeft(2 * STRIDE, 24, STRIDE)).toBe(0)
  })

  it('round-trips: trim then compensate leaves the same card centred', () => {
    // The property the smoke test checks by eye, stated as arithmetic. A reader
    // centred on index i, after t cards are removed from the head, is centred on
    // index i - t — and the scroll offset for that index is what we produce.
    const i = 150
    const t = computeTrim(MAX_FEED + 24, i)
    expect(compensatedScrollLeft(i * STRIDE, t, STRIDE)).toBe((i - t) * STRIDE)
  })
})
