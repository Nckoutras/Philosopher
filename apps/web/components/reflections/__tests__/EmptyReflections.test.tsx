// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import EmptyReflections from '../EmptyReflections'

describe('EmptyReflections', () => {
  it('renders headline from §4.3', () => {
    render(<EmptyReflections onStartConversation={vi.fn()} />)
    expect(screen.getByText('A space for the lines that stay with you.')).toBeTruthy()
  })

  it('renders body copy from §4.3', () => {
    render(<EmptyReflections onStartConversation={vi.fn()} />)
    expect(screen.getByText(/When a sentence settles, save it/)).toBeTruthy()
  })

  it('renders 3-item instruction list', () => {
    render(<EmptyReflections onStartConversation={vi.fn()} />)
    expect(screen.getByText('Save what resonates')).toBeTruthy()
    expect(screen.getByText('Group by mind or theme')).toBeTruthy()
    expect(screen.getByText('Return when you need them')).toBeTruthy()
  })

  it('renders Start a conversation CTA', () => {
    render(<EmptyReflections onStartConversation={vi.fn()} />)
    expect(screen.getByText('Start a conversation')).toBeTruthy()
  })

  it('calls onStartConversation when CTA tapped', () => {
    const fn = vi.fn()
    render(<EmptyReflections onStartConversation={fn} />)
    fireEvent.click(screen.getByText('Start a conversation'))
    expect(fn).toHaveBeenCalledOnce()
  })
})
