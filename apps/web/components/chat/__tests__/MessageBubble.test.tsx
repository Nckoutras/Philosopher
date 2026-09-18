// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MessageBubble from '../MessageBubble'

// Props gained `id` and `saved` after this file was written; the fixtures did not
// follow, which is the 7-error half of the TD-86 typecheck set. Both are now set
// explicitly on every render (C-06) rather than cast away — `saved` is false because
// that is the state these five cases are about, not because false is the default.
describe('MessageBubble', () => {
  it('user variant is right-aligned', () => {
    const { container } = render(<MessageBubble id="m1" saved={false} role="user" content="Hello" />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).toContain('justify-end')
  })

  it('user variant has paper background', () => {
    const { container } = render(<MessageBubble id="m1" saved={false} role="user" content="Hello" />)
    expect(container.querySelector('.bg-paper')).toBeTruthy()
  })

  it('assistant variant is left-aligned', () => {
    const { container } = render(<MessageBubble id="m1" saved={false} role="assistant" content="Hi there" />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).toContain('justify-start')
  })

  it('assistant variant has white background', () => {
    const { container } = render(<MessageBubble id="m1" saved={false} role="assistant" content="Hi there" />)
    expect(container.querySelector('.bg-white')).toBeTruthy()
  })

  it('renders content text', () => {
    render(<MessageBubble id="m1" saved={false} role="user" content="What is virtue?" />)
    expect(screen.getByText('What is virtue?')).toBeTruthy()
  })
})
