// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import FilterPills from '../FilterPills'

vi.mock('react-hot-toast', () => ({ default: vi.fn() }))

import toast from 'react-hot-toast'

const personas = [
  { slug: 'epictetus', display_name: 'Epictetus' },
  { slug: 'marcus-aurelius', display_name: 'Marcus Aurelius' },
]

beforeEach(() => {
  vi.mocked(toast).mockClear()
})

describe('FilterPills', () => {
  it('renders All, By mind, By theme pills', () => {
    render(
      <FilterPills active="all" personas={[]} selectedPersonaSlug={null} onChange={vi.fn()} />,
    )
    expect(screen.getByText('All')).toBeTruthy()
    expect(screen.getByText('By mind')).toBeTruthy()
    expect(screen.getByText('By theme')).toBeTruthy()
  })

  it('calls onChange("all") when All tapped', () => {
    const onChange = vi.fn()
    render(
      <FilterPills active="by-mind" personas={[]} selectedPersonaSlug={null} onChange={onChange} />,
    )
    fireEvent.click(screen.getByText('All'))
    expect(onChange).toHaveBeenCalledWith('all')
  })

  it('calls onChange("by-mind") when By mind tapped', () => {
    const onChange = vi.fn()
    render(
      <FilterPills active="all" personas={[]} selectedPersonaSlug={null} onChange={onChange} />,
    )
    fireEvent.click(screen.getByText('By mind'))
    expect(onChange).toHaveBeenCalledWith('by-mind')
  })

  it('shows persona sub-row when active=by-mind and personas provided', () => {
    render(
      <FilterPills
        active="by-mind"
        personas={personas}
        selectedPersonaSlug={null}
        onChange={vi.fn()}
      />,
    )
    expect(screen.getByText('Epictetus')).toBeTruthy()
    expect(screen.getByText('Marcus Aurelius')).toBeTruthy()
  })

  it('By theme shows Coming soon toast', () => {
    render(
      <FilterPills active="all" personas={[]} selectedPersonaSlug={null} onChange={vi.fn()} />,
    )
    fireEvent.click(screen.getByLabelText('By theme (coming soon)'))
    expect(toast).toHaveBeenCalledWith('Coming soon', expect.any(Object))
  })

  it('does not show persona sub-row when active=all', () => {
    render(
      <FilterPills
        active="all"
        personas={personas}
        selectedPersonaSlug={null}
        onChange={vi.fn()}
      />,
    )
    expect(screen.queryByText('Epictetus')).toBeNull()
  })
})
