// @vitest-environment jsdom
import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import SafetyBubble from '../SafetyBubble'
import { useStore } from '@/lib/store'

// SAFETY-003 (founder ruling 2026-09-28): ONE crisis text, written by the server,
// rendered here for every language. The English cases used to assert four
// hardcoded paragraphs as a "fallback" — that copy is gone from the web by ruling,
// so those assertions are replaced, not loosened.

// The rendered server texts, verbatim (apps/api/prompts/safety_response*.jinja2).
const ENGLISH_COPY =
  "Some of what you've shared sounds heavy, and your safety matters more than this conversation.\n\n" +
  'If you are in immediate danger, call your local emergency number now.\n\n' +
  'In the US, call or text 988. In the UK and Ireland, call Samaritans on 116 123. ' +
  'Anywhere else, find a free, confidential helpline at findahelpline.com. You can also ' +
  'reach out to a trusted person near you, or a qualified mental health professional.\n\n' +
  'The Wise Room can offer reflection, but it cannot provide crisis support, diagnosis or ' +
  'medical treatment. This conversation will pause here so that comes first.'

const GREEK_COPY =
  'Αυτή η συζήτηση αγγίζει κάτι σοβαρό που χρειάζεται ανθρώπινη υποστήριξη τώρα.\n\n' +
  'Αν κινδυνεύεις άμεσα, κάλεσε το 112. Στην Ελλάδα: 1018 — Γραμμή Παρέμβασης για την ' +
  'Αυτοκτονία (24 ώρες) · 10306 — Γραμμή Ψυχοκοινωνικής Υποστήριξης (24 ώρες, δωρεάν).'

beforeEach(() => {
  useStore.setState({ safetyText: '' })
})

function hrefOf(label: string): string | null {
  return screen.getByRole('link', { name: label }).getAttribute('href')
}

describe('SafetyBubble — English (SAFETY-003)', () => {
  it('renders the server English text, not a hardcoded copy', () => {
    useStore.setState({ safetyText: ENGLISH_COPY })
    const { container } = render(<SafetyBubble />)
    // The whole text, as the server sent it: nothing added, nothing dropped.
    expect(container.querySelector('[role="alert"]')?.textContent).toBe(ENGLISH_COPY)
  })

  it('makes 988, 116 123 and findahelpline.com tappable', () => {
    useStore.setState({ safetyText: ENGLISH_COPY })
    render(<SafetyBubble />)
    expect(hrefOf('988')).toBe('tel:988')
    expect(hrefOf('116 123')).toBe('tel:116123')
    expect(hrefOf('findahelpline.com')).toBe('https://findahelpline.com')
  })

  it('opens the directory in a new tab, without an opener', () => {
    useStore.setState({ safetyText: ENGLISH_COPY })
    render(<SafetyBubble />)
    const link = screen.getByRole('link', { name: 'findahelpline.com' })
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toBe('noopener noreferrer')
  })

  it('marks the bubble lang=en', () => {
    useStore.setState({ safetyText: ENGLISH_COPY })
    render(<SafetyBubble />)
    expect(screen.getByRole('alert').getAttribute('lang')).toBe('en')
  })

  it('renders the The Wise Room eyebrow and role=alert', () => {
    useStore.setState({ safetyText: ENGLISH_COPY })
    render(<SafetyBubble />)
    expect(screen.getByText('The Wise Room')).toBeTruthy()
    expect(screen.getByRole('alert')).toBeTruthy()
  })
})

describe('SafetyBubble — Greek', () => {
  it('renders the Greek text', () => {
    useStore.setState({ safetyText: GREEK_COPY })
    const { container } = render(<SafetyBubble />)
    expect(container.querySelector('[role="alert"]')?.textContent).toBe(GREEK_COPY)
  })

  it('makes 112, 1018 and 10306 tappable', () => {
    useStore.setState({ safetyText: GREEK_COPY })
    render(<SafetyBubble />)
    expect(hrefOf('112')).toBe('tel:112')
    expect(hrefOf('1018')).toBe('tel:1018')
    expect(hrefOf('10306')).toBe('tel:10306')
  })

  it('does not turn "24" (hours) into a link', () => {
    useStore.setState({ safetyText: GREEK_COPY })
    render(<SafetyBubble />)
    expect(screen.getAllByRole('link').map((a) => a.textContent)).toEqual(['112', '1018', '10306'])
  })

  it('marks the bubble lang=el so a screen reader does not read Greek as English', () => {
    useStore.setState({ safetyText: GREEK_COPY })
    render(<SafetyBubble />)
    expect(screen.getByRole('alert').getAttribute('lang')).toBe('el')
  })
})

describe('SafetyBubble — before the text arrives', () => {
  it('renders nothing rather than an empty bubble', () => {
    useStore.setState({ safetyText: '   ' })
    const { container } = render(<SafetyBubble />)
    expect(container.innerHTML).toBe('')
  })

  it('carries no hardcoded English crisis copy any more', () => {
    useStore.setState({ safetyText: '' })
    const { container } = render(<SafetyBubble />)
    expect(container.textContent).not.toMatch(/sounds heavy|immediate danger|crisis/i)
  })
})
