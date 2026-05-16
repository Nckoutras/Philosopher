// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import OpeningInvocation from '../OpeningInvocation'

describe('OpeningInvocation', () => {
  it('renders the given text', () => {
    render(<OpeningInvocation text="Know thyself." />)
    expect(screen.getByText('Know thyself.')).toBeTruthy()
  })

  it('renders text in italic style', () => {
    const { container } = render(<OpeningInvocation text="Know thyself." />)
    const italic = container.querySelector('.italic')
    expect(italic).toBeTruthy()
  })
})
