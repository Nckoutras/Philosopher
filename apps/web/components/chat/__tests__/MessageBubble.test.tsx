// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MessageBubble from '../MessageBubble'

describe('MessageBubble', () => {
  it('user variant is right-aligned', () => {
    const { container } = render(<MessageBubble role="user" content="Hello" />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).toContain('justify-end')
  })

  it('user variant has paper background', () => {
    const { container } = render(<MessageBubble role="user" content="Hello" />)
    expect(container.querySelector('.bg-paper')).toBeTruthy()
  })

  it('assistant variant is left-aligned', () => {
    const { container } = render(<MessageBubble role="assistant" content="Hi there" />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).toContain('justify-start')
  })

  it('assistant variant has white background', () => {
    const { container } = render(<MessageBubble role="assistant" content="Hi there" />)
    expect(container.querySelector('.bg-white')).toBeTruthy()
  })

  it('renders content text', () => {
    render(<MessageBubble role="user" content="What is virtue?" />)
    expect(screen.getByText('What is virtue?')).toBeTruthy()
  })
})
