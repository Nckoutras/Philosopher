// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import BookmarkIndicator from '../BookmarkIndicator'

describe('BookmarkIndicator', () => {
  it('renders nothing when visible=false', () => {
    const { container } = render(<BookmarkIndicator visible={false} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders bookmark icon when visible=true', () => {
    const { container } = render(<BookmarkIndicator visible={true} />)
    expect(container.firstChild).not.toBeNull()
  })

  it('has pointer-events-none so it does not block bubble taps', () => {
    const { container } = render(<BookmarkIndicator visible={true} />)
    const span = container.firstChild as HTMLElement
    expect(span.className).toContain('pointer-events-none')
  })
})
