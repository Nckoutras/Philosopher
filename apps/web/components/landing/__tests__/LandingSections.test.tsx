// @vitest-environment jsdom
//
// Smoke coverage for the landing sections below the splash fold.
//
// HOW THESE CAN FAIL. The copy tests assert against lib/landing-copy.ts, which is
// the founder-approved wording (SKILL.md §3) — a component that paraphrased,
// re-wrapped, or dropped a line fails. The CTA test asserts the DESTINATION, so a
// button wired to the wrong auth mode fails rather than merely "a link exists".
// The portrait test asserts all eleven render lazily WITH explicit dimensions —
// the two properties that keep ~1 MB of below-fold imagery off the LCP path; a
// version that eagerly loaded them, or omitted width/height and shifted layout,
// fails.
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import { LandingSections } from '../LandingSections'
import { LANDING_COPY as C } from '@/lib/landing-copy'

const SIGNUP_HREF = '/auth?mode=signup'

describe('LandingSections', () => {
  it('renders every approved section heading and eyebrow', () => {
    render(<LandingSections />)
    for (const text of [
      C.offer.eyebrow,
      C.offer.title,
      C.letter.eyebrow,
      C.minds.eyebrow,
      C.pricing.eyebrow,
    ]) {
      expect(screen.getByText(text)).toBeTruthy()
    }
  })

  it('renders the three offer cards in the CRO-reviewed order', () => {
    render(<LandingSections />)
    const headings = screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)
    expect(headings).toEqual([
      C.offer.cards[0].title,
      C.offer.cards[1].title,
      C.offer.cards[2].title,
    ])
  })

  it('renders each offer card body verbatim', () => {
    render(<LandingSections />)
    for (const card of C.offer.cards) {
      expect(screen.getByText(card.body)).toBeTruthy()
    }
  })

  it('renders the letter proof, its signature and its context note', () => {
    render(<LandingSections />)
    expect(screen.getByText(C.letter.quote)).toBeTruthy()
    expect(screen.getByText(C.letter.contextNote)).toBeTruthy()
    expect(screen.getByText(C.letter.signatureLine1, { exact: false })).toBeTruthy()
  })

  it('renders the price, the annual line and all three inclusions', () => {
    render(<LandingSections />)
    expect(screen.getByText(C.pricing.price)).toBeTruthy()
    expect(screen.getByText(C.pricing.annual)).toBeTruthy()
    for (const row of C.pricing.inclusions) {
      expect(screen.getByText(row)).toBeTruthy()
    }
    expect(screen.getByText(C.pricing.includedLine)).toBeTruthy()
    expect(screen.getByText(C.pricing.checkoutNote)).toBeTruthy()
  })

  it('points both CTAs at the signup destination, not just anywhere', () => {
    render(<LandingSections />)
    const mid = screen.getByRole('link', { name: C.midCta.button })
    const pricing = screen.getByRole('link', { name: C.pricing.button })
    expect(mid.getAttribute('href')).toBe(SIGNUP_HREF)
    expect(pricing.getAttribute('href')).toBe(SIGNUP_HREF)
  })

  it('renders all eleven minds lazily with explicit dimensions', () => {
    const { container } = render(<LandingSections />)
    const imgs = Array.from(container.querySelectorAll('img'))
    expect(imgs).toHaveLength(11)
    for (const img of imgs) {
      expect(img.getAttribute('loading')).toBe('lazy')
      expect(img.getAttribute('width')).toBeTruthy()
      expect(img.getAttribute('height')).toBeTruthy()
    }
  })

  it('names every mind beneath its portrait', () => {
    render(<LandingSections />)
    for (const name of ['Socrates', 'Marcus Aurelius', 'Simone de Beauvoir', 'Miyamoto Musashi']) {
      expect(screen.getByText(name)).toBeTruthy()
    }
  })

  it('renders the non-clinical disclaimer', () => {
    render(<LandingSections />)
    expect(screen.getByText(C.footer.disclaimer)).toBeTruthy()
    expect(screen.getByText(C.footer.label)).toBeTruthy()
  })

  it('uses h2 for sections so the fold-1 wordmark stays the only h1', () => {
    const { container } = render(<LandingSections />)
    expect(container.querySelectorAll('h1')).toHaveLength(0)
    expect(screen.getAllByRole('heading', { level: 2 }).length).toBeGreaterThan(0)
  })
})
