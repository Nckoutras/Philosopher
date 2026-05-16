// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import SafetyBubble from '../SafetyBubble'

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
      screen.getByText(/Great Minds can offer reflection/),
    ).toBeTruthy()
  })

  it('renders the Great Minds eyebrow', () => {
    render(<SafetyBubble />)
    expect(screen.getByText('Great Minds')).toBeTruthy()
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
