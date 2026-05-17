// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import DateGrouper from '../DateGrouper'

describe('DateGrouper', () => {
  it('renders label text', () => {
    render(<DateGrouper label="This week" />)
    expect(screen.getByText('This week')).toBeTruthy()
  })

  it('renders uppercase styling', () => {
    const { container } = render(<DateGrouper label="Earlier" />)
    expect((container.firstChild as HTMLElement).className).toContain('uppercase')
  })

  it('renders sepia color class', () => {
    const { container } = render(<DateGrouper label="Last month" />)
    expect((container.firstChild as HTMLElement).className).toContain('text-sepia')
  })
})
