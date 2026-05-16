// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import SafetyReEntryCard from '../SafetyReEntryCard'

describe('SafetyReEntryCard', () => {
  it('renders the re-entry copy', () => {
    render(<SafetyReEntryCard />)
    expect(
      screen.getByText(/You can continue when you're ready\. Take your time\./),
    ).toBeTruthy()
  })

  it('renders the copy in italic', () => {
    const { container } = render(<SafetyReEntryCard />)
    const p = container.querySelector('p')
    expect(p?.className).toContain('italic')
  })

  it('has a Bronze left border', () => {
    const { container } = render(<SafetyReEntryCard />)
    const card = container.firstChild as HTMLElement
    expect(card.className).toContain('border-bronze')
  })
})
