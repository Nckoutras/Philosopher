// One speech act, one wording, three surfaces.
//
// WHY THIS FILE EXISTS AT ALL. The ruling asked me to "amend its test pin" when
// You-vs-You's third label changed from 'Not really' to 'No'. There was no pin:
// nothing in the repository asserted any of this copy, and there is no
// you-vs-you test file. That absence is how the two surfaces drifted in the
// first place — Mirror shipped 'No', You-vs-You shipped 'Not really', both
// looked right in isolation, and nothing compared them.
//
// So this is the pin that should have existed. It reads the three sources and
// asserts they ask the same question with the same three answers. A source-level
// assertion rather than a rendered one, deliberately: the point is that three
// FILES agree, and rendering three pages to compare their strings would test the
// renderer instead.

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const ROOT = resolve(__dirname, '../..')

const SURFACES: [string, string][] = [
  ['Mirror', 'app/app/mirror/page.tsx'],
  ['You-vs-You', 'app/app/you-vs-you/page.tsx'],
  ['Insight card', 'components/chat/InsightCard.tsx'],
]

// Founder-locked, 2026-09-14.
const QUESTION = 'Does this ring true?'
const LABELS = ['Rings true', 'Partly', 'No']
const CONFIRMATION = 'Noted.'

function source(relative: string): string {
  return readFileSync(resolve(ROOT, relative), 'utf-8')
}

describe('the ring-true row asks the same question everywhere', () => {
  it.each(SURFACES)('%s asks it', (_name, path) => {
    expect(source(path)).toContain(QUESTION)
  })

  it.each(SURFACES)('%s offers exactly the three locked labels', (_name, path) => {
    const src = source(path)
    for (const label of LABELS) {
      expect(src).toContain(`'${label}'`)
    }
  })

  // All three confirm now. You-vs-You was the holdout — it showed only a
  // selected button and said nothing — and gained the line on founder copy
  // (2026-09-14). No surface is exempt from this list any more, which is the
  // state the list is here to keep.
  it.each(SURFACES)('%s confirms with the same word', (_name, path) => {
    expect(source(path)).toContain(CONFIRMATION)
  })
})

describe('the retired wording is gone', () => {
  it.each(SURFACES)('%s no longer says "Not really"', (_name, path) => {
    // The label You-vs-You shipped with. Pinned as an ABSENCE so a revert, or a
    // fourth surface copied from the old one, fails here rather than shipping a
    // third phrasing of one question.
    expect(source(path)).not.toContain('Not really')
  })
})

// ── The failure path, on all three (Γ-2b) ───────────────────────────────────
//
// Founder ruling: "Noted." must mean STORED. Before this, Mirror and You-vs-You
// were optimistic-and-silent — a failed write left the confirmation on screen
// for an answer that never landed, and on Mirror the once-only guard then
// refused the retry that would have fixed it.
//
// WHAT THESE CAN AND CANNOT PROVE. The insight card's failure path is asserted
// BEHAVIOURALLY in components/chat/__tests__/InsightCardRingTrue.test.tsx —
// rendered, clicked, with a rejecting and a deferred promise. Mirror and
// You-vs-You are whole pages with reveal animations, persona fetches and
// several stores; standing them up would test the harness more than the rule.
// So they are pinned STRUCTURALLY here: the three shapes that make "Noted."
// mean stored. A structural pin is weaker than a behavioural one and is called
// out as such — it catches the revert being deleted, not every way it could be
// wrong.

const HANDLERS: [string, string, string][] = [
  // surface, file, the handler's name
  ['Mirror', 'app/app/mirror/page.tsx', 'handleRingTrue'],
  ['You-vs-You', 'app/app/you-vs-you/page.tsx', 'submitRingTrue'],
  ['Insight card', 'components/chat/InsightCard.tsx', 'handleRingTrue'],
]

/** The body of the named function, from its signature to the next top-level `}`. */
function handlerBody(path: string, name: string): string {
  const src = source(path)
  const start = src.indexOf(`function ${name}(`)
  expect(start, `${name} not found in ${path}`).toBeGreaterThan(-1)
  const end = src.indexOf('\n  }', start)
  expect(end, `could not find the end of ${name} in ${path}`).toBeGreaterThan(start)
  return src.slice(start, end)
}

describe('a failed write never leaves "Noted." on screen', () => {
  it.each(HANDLERS)('%s awaits the write before confirming', (_name, path, fn) => {
    const body = handlerBody(path, fn)
    expect(body).toContain('await ')
    // The confirmation setter must appear AFTER the await, not beside the
    // optimistic selection — that ordering is what makes "Noted." mean stored.
    const awaitAt = body.indexOf('await ')
    const confirmAt = Math.max(
      body.indexOf('setRingTrueSubmitted(true)'),
      body.indexOf('setRingTrueConfirmed(true)'),
      body.indexOf('setConfirmed(true)'),
    )
    expect(confirmAt, `${_name}: no confirmation setter found`).toBeGreaterThan(-1)
    expect(confirmAt).toBeGreaterThan(awaitAt)
  })

  it.each(HANDLERS)('%s reverts the selection in its catch', (_name, path, fn) => {
    const body = handlerBody(path, fn)
    expect(body).toContain('catch')
    // The catch must restore a captured previous value rather than swallow.
    expect(body).toMatch(/const previous\w* = /)
    expect(body).toMatch(/set\w*[Vv]erdict\(previous|setRingTrue\(previous/)
  })

  it.each(HANDLERS)('%s no longer swallows the failure silently', (_name, path, fn) => {
    const body = handlerBody(path, fn)
    // The exact comments the three carried while they were optimistic-and-silent.
    expect(body).not.toContain('optimistic -- silent')
    expect(body).not.toContain('best-effort signal')
  })
})
