// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChatHeader from '../ChatHeader'

describe('ChatHeader', () => {
  it('renders persona name', () => {
    render(<ChatHeader personaName="Socrates" portraitUrl="/socrates.jpg" />)
    expect(screen.getByText('Socrates')).toBeTruthy()
  })

  it('renders portrait img with correct src and alt', () => {
    render(<ChatHeader personaName="Socrates" portraitUrl="/socrates.jpg" />)
    const img = screen.getByAltText('Socrates') as HTMLImageElement
    expect(img.src).toContain('socrates.jpg')
  })
})
