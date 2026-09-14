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
