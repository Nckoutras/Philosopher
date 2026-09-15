// The You-vs-You read path (G-8): the copy, and the one structural decision it
// rests on.
//
// A source-level pin, in the shape ringTrueCopyParity.test.ts established on
// this same page and for the same reason: what needs asserting is that a FILE
// says a thing, and rendering a 400-line page behind a store and a router to
// read two strings back out would test the renderer instead.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'
import { api } from '../api'

const ROOT = resolve(__dirname, '../..')
const PAGE = 'app/app/you-vs-you/page.tsx'

// Founder-approved, 2026-09-15. Both strings ship together: the heading names
// the section and the second line is what stands in its place before the reader
// has any runs to list.
const HEADING = 'Earlier comparisons'
const EMPTY_STATE = 'Your past comparisons will gather here.'

function source(relative: string): string {
  return readFileSync(resolve(ROOT, relative), 'utf-8')
}

describe('the revisit list copy is the approved copy', () => {
  it('uses the approved heading', () => {
    expect(source(PAGE)).toContain(HEADING)
  })

  it('uses the approved empty state', () => {
    expect(source(PAGE)).toContain(EMPTY_STATE)
  })
})

describe('a past run replays through the live result view, not a second one', () => {
  // THE LOAD-BEARING DECISION. 'reading' and 'streaming' render the SAME tree,
  // so "shows what generation showed" holds by construction. Guard the result
  // view on `mode === 'streaming'` again and a reopened run silently renders
  // nothing -- the list would still be there, the rows would still be tappable,
  // and every other test in this repo would stay green.
  it('guards the result view on mode !== input', () => {
    expect(source(PAGE)).toContain("mode !== 'input'")
  })

  it('declares a reading mode alongside input and streaming', () => {
    expect(source(PAGE)).toContain("'input' | 'streaming' | 'reading'")
  })
})

describe('the read endpoints', () => {
  const calls: string[] = []

  beforeEach(() => {
    calls.length = 0
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        calls.push(String(url))
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => [],
          text: async () => '[]',
        } as unknown as Response
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lists past runs from the collection path', async () => {
    await api.listSelfComparisons()
    expect(calls[0]).toContain('/self-comparison')
    // Must NOT be the status path: /status is a sibling of /{id} on the server
    // and the two are distinguished only by declaration order.
    expect(calls[0]).not.toContain('/self-comparison/status')
  })

  it('reopens one run by id', async () => {
    await api.getSelfComparison('abc-123')
    expect(calls[0]).toContain('/self-comparison/abc-123')
  })
})
