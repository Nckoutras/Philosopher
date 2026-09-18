import type { Quote } from '@/lib/api'

/**
 * The bounded rotation behind the quotes peek-carousel (BUG-024).
 *
 * The carousel appends a whole permutation of the corpus whenever the reader nears
 * the end, and before this module nothing was ever removed: the DOM went
 * 88 -> 176 -> 264 -> ... for as long as the tab stayed open. It is an infinite
 * peek-carousel, not a catalogue, so the fix is a bound rather than a search.
 *
 * The rule lives here rather than inline in the page for one reason: it is the only
 * part of the fix that can be tested without a browser. jsdom has no layout, so the
 * scroll compensation in the page can only be checked against stubbed geometry, but
 * this arithmetic is exact and can be checked properly.
 */

/** A quote at a position in the rotation. `seq` is identity; `quote` is content. */
export type FeedItem = { seq: number; quote: Quote }

/**
 * Cap on rendered cards.
 *
 * HOW IT CONVERGES, so the next person to raise it sees the trade:
 *
 *     88 -> 176 -> 264 -> trim 24 -> 240 -> append -> 328 -> trim 88 -> 240 -> ...
 *
 * It must clear one pool by a wide margin or every single append would trim. 240 is
 * ~2.7 passes at today's 88. Above it, 240 cards each carrying an image, a gradient
 * and text is where DOM cost starts to show on a mid-range phone.
 *
 * NOT expressed as a multiple of pool length, deliberately. That reads cleverer and
 * is worse: the pool is a server-controlled number, so a corpus of 400 would silently
 * set the cap to 1,200 — a bug that ships looking like cleverness.
 */
export const MAX_FEED = 240

/**
 * How many cards stay behind the centred one after a trim. The viewport shows ~1.5
 * cards, so 24 is far more back-swiping than anyone does, and it guarantees a trim
 * never reaches anything on screen or about to be.
 */
export const KEEP_BEHIND = 24

/**
 * How many cards to drop from the head, bounded twice: by the overshoot past the cap,
 * and by the reader's own position. The second bound is the safety — the trim can
 * never reach the card being viewed or the KEEP_BEHIND cards just behind it, whatever
 * the overshoot. A trim that loses the reader's place is a worse bug than the
 * unbounded feed it fixes.
 */
export function computeTrim(feedLength: number, currentIndex: number): number {
  return Math.min(
    Math.max(0, feedLength - MAX_FEED),
    Math.max(0, currentIndex - KEEP_BEHIND),
  )
}

/**
 * Append one permutation and trim the head. Pure: same inputs, same output, no refs
 * and no side effects, so React may re-invoke it (StrictMode, or a render retry)
 * without double-counting anything.
 *
 * `seq` is monotonic and assigned here. It never shifts and is never reused, which is
 * what makes a head-trim invisible to React's reconciliation — the page keys cards by
 * it. It cannot be the quote id: the same quote appears once per cycle, so ids repeat
 * down the feed by design.
 */
export function appendBounded(
  prev: FeedItem[],
  cycle: Quote[],
  currentIndex: number,
): FeedItem[] {
  // Avoid a seam repeat: the new cycle must not open with the quote the feed
  // currently ends on.
  let cyc = cycle
  const lastId = prev[prev.length - 1]?.quote.id
  if (cyc.length > 1 && cyc[0].id === lastId) {
    cyc = [cyc[1], cyc[0], ...cyc.slice(2)]
  }

  let nextSeq = (prev[prev.length - 1]?.seq ?? -1) + 1
  const grown = [...prev, ...cyc.map((quote) => ({ seq: nextSeq++, quote }))]

  const trim = computeTrim(grown.length, currentIndex)
  return trim === 0 ? grown : grown.slice(trim)
}

/**
 * Where the scroller must be after a head-trim.
 *
 * Removing N cards from the head shifts every remaining card left by N strides, so
 * scrollLeft must move by exactly the same amount or the carousel jumps under the
 * reader's finger. Exact rather than approximate because every card is
 * `w-[80vw] shrink-0` inside a uniform `gap-[8px]`, so the stride is constant.
 *
 * Extracted here for one reason: this is the arithmetic an off-by-one would live in,
 * and jsdom has no layout, so it cannot be asserted through a rendered carousel. The
 * WIRING — that the page reads a live stride and applies this before paint — is
 * covered by the smoke test, not by any test in this repository. That split is
 * stated rather than implied.
 */
export function compensatedScrollLeft(
  scrollLeft: number,
  trimmed: number,
  stride: number,
): number {
  if (trimmed <= 0 || stride <= 0) return scrollLeft
  return Math.max(0, scrollLeft - trimmed * stride)
}
