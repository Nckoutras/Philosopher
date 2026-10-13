// @vitest-environment jsdom
//
// INS-001 (ruling 2026-10-13): the insight card never wraps its statement in
// quotation marks. The dilemma, belief and aspiration cards used to, which
// presented the room's sentence as a quote of the person. That was literally
// true on UAT Day 2, when a dilemma card was the person's own sentence copied
// whole. The backend now rephrases; this pins the frontend half: no type renders
// the statement in quotes.

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import InsightCard from '../InsightCard'

const STATEMENT = "I'm deciding whether to say what's bothering me or keep the peace."
const TYPES = ['dilemma', 'belief', 'aspiration', 'pattern', 'shift', null]

describe('the statement is never quoted', () => {
  it.each(TYPES)('insight_type=%s renders the statement as-is', (insightType) => {
    render(
      <InsightCard
        insightId="cccccccc-0000-0000-0000-000000000004"
        content={STATEMENT}
        insightType={insightType}
        onPrimary={vi.fn()}
        onDoubt={vi.fn()}
        onDiscard={vi.fn()}
      />,
    )
    // Exact text match: a quoted rendering (“…”) would not match.
    const el = screen.getByText(STATEMENT)
    expect(el.textContent).toBe(STATEMENT)
    expect(el.textContent).not.toMatch(/[“”]/)
  })

  it('keeps the observation line on the dilemma card', () => {
    render(
      <InsightCard
        insightId="cccccccc-0000-0000-0000-000000000005"
        content={STATEMENT}
        insightType="dilemma"
        onPrimary={vi.fn()}
        onDoubt={vi.fn()}
        onDiscard={vi.fn()}
      />,
    )
    expect(screen.getByText('This sounds like a decision with two sides.')).toBeTruthy()
  })
})
