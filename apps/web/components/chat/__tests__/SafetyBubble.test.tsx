// @vitest-environment jsdom
import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import SafetyBubble from '../SafetyBubble'
import { useStore } from '@/lib/store'

// The English cases below deliberately do NOT set safetyText. That is the
// fallback path, and it must stay byte-identical to what shipped before the
// Greek work — so these assertions are left exactly as they were.
beforeEach(() => {
  useStore.setState({ safetyText: '' })
})

describe('SafetyBubble', () => {
  it('renders the full 4-paragraph safety copy', () => {
    render(<SafetyBubble />)
    expect(
      screen.getByText(/Some of what you've shared sounds heavy/),
    ).toBeTruthy()
    expect(
      screen.getByText(/If you may be in immediate danger/),
    ).toBeTruthy()
    expect(
      screen.getByText(/reach out to a trusted person/),
    ).toBeTruthy()
    expect(
      screen.getByText(/The Wise Room can offer reflection/),
    ).toBeTruthy()
  })

  it('renders the The Wise Room eyebrow', () => {
    render(<SafetyBubble />)
    expect(screen.getByText('The Wise Room')).toBeTruthy()
  })

  it('second paragraph (danger warning) is rendered with bold font weight', () => {
    const { container } = render(<SafetyBubble />)
    const paragraphs = container.querySelectorAll('p')
    // paragraph index 1 (0-indexed) is the "immediate danger" paragraph
    const dangerParagraph = paragraphs[1]
    expect(dangerParagraph.className).toContain('font-medium')
  })

  it('renders a role=alert on the bubble for accessibility', () => {
    render(<SafetyBubble />)
    expect(screen.getByRole('alert')).toBeTruthy()
  })
})

// ── The Greek path ────────────────────────────────────────────────────────────
//
// The server builds the crisis response in the language the user wrote in and
// streams it; useStream collects it into safetyText. Before this, the component
// ignored it and rendered English at a Greek speaker in crisis.

describe('SafetyBubble — the server-sent crisis text', () => {
  const GREEK_COPY =
    'Αυτή η συζήτηση αγγίζει κάτι σοβαρό που χρειάζεται ανθρώπινη υποστήριξη τώρα.\n\n' +
    'Αν κινδυνεύεις άμεσα, κάλεσε το 112. Στην Ελλάδα: 1018 — Γραμμή Παρέμβασης για την ' +
    'Αυτοκτονία (24 ώρες) · 10306 — Γραμμή Ψυχοκοινωνικής Υποστήριξης (24 ώρες, δωρεάν).'

  it('renders the Greek text instead of the English copy', () => {
    useStore.setState({ safetyText: GREEK_COPY })
    render(<SafetyBubble />)

    expect(screen.getByText(/Αυτή η συζήτηση αγγίζει κάτι σοβαρό/)).toBeTruthy()
    // The whole point: the English paragraphs must be GONE, not merely appended to.
    expect(screen.queryByText(/Some of what you've shared sounds heavy/)).toBeNull()
  })

  it('shows the approved helpline numbers to a Greek speaker', () => {
    useStore.setState({ safetyText: GREEK_COPY })
    const { container } = render(<SafetyBubble />)
    const text = container.textContent ?? ''

    for (const number of ['1018', '10306', '112']) {
      expect(text).toContain(number)
    }
  })

  it('marks the bubble lang=el so a screen reader does not read Greek as English', () => {
    useStore.setState({ safetyText: GREEK_COPY })
    render(<SafetyBubble />)
    expect(screen.getByRole('alert').getAttribute('lang')).toBe('el')
  })

  it('keeps role=alert and the eyebrow on the Greek path', () => {
    useStore.setState({ safetyText: GREEK_COPY })
    render(<SafetyBubble />)
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByText('The Wise Room')).toBeTruthy()
  })

  it('falls back to the English copy when the server text is English', () => {
    // English streams through the same field. It must NOT displace the fuller
    // founder-locked English bubble, which says more than the English template.
    useStore.setState({ safetyText: 'This conversation involves something serious.' })
    render(<SafetyBubble />)

    expect(screen.getByText(/Some of what you've shared sounds heavy/)).toBeTruthy()
    expect(screen.queryByText(/This conversation involves something serious/)).toBeNull()
  })

  it('falls back to the English copy when no text arrived at all', () => {
    useStore.setState({ safetyText: '   ' })
    render(<SafetyBubble />)
    expect(screen.getByText(/The Wise Room can offer reflection/)).toBeTruthy()
  })
})
