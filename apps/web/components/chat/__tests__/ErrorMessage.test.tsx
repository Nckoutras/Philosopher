// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useStore } from '@/lib/store'
import ErrorMessage from '../ErrorMessage'

beforeEach(() => {
  useStore.setState({ streamError: null, messages: [] })
})

describe('ErrorMessage', () => {
  it('renders streamError persona_voice when present', () => {
    useStore.setState({
      streamError: { error_code: 'llm_unavailable', persona_voice: 'I cannot speak now.' },
    })
    render(<ErrorMessage send={vi.fn()} />)
    expect(screen.getByText('I cannot speak now.')).toBeTruthy()
  })

  it('renders nothing when streamError is null', () => {
    useStore.setState({ streamError: null })
    const { container } = render(<ErrorMessage send={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('retry button calls send with last user message content', () => {
    const mockSend = vi.fn()
    useStore.setState({
      streamError: { error_code: 'llm_unavailable', persona_voice: 'Retry please.' },
      messages: [
        {
          id: '1',
          role: 'user',
          content: 'What is virtue?',
          safety_level: 'none',
          persona_override: false,
          created_at: new Date().toISOString(),
        },
      ],
    })

    render(<ErrorMessage send={mockSend} />)
    fireEvent.click(screen.getByText('Try again'))

    expect(mockSend).toHaveBeenCalledWith('What is virtue?')
  })

  it('retry button clears streamError', () => {
    useStore.setState({
      streamError: { error_code: 'llm_unavailable', persona_voice: 'Retry please.' },
      messages: [
        {
          id: '1',
          role: 'user',
          content: 'Hello',
          safety_level: 'none',
          persona_override: false,
          created_at: new Date().toISOString(),
        },
      ],
    })

    render(<ErrorMessage send={vi.fn()} />)
    fireEvent.click(screen.getByText('Try again'))

    expect(useStore.getState().streamError).toBeNull()
  })
})
