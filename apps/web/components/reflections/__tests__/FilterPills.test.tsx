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

  // VERIFIED against FilterPills.tsx:40-47, not assumed (TD-45). The pill is now
  // `disabled` with no onClick, and the component does not import toast at all
  // (repo grep: zero hits in that file). The product moved from an apology to an
  // affordance that cannot be tapped, which is the better answer — so the assertion
  // follows it rather than pinning the apology.
  //
  // This case was miscategorised in the 2026-08-13 measurement as cleanup fallout
  // ("multiple labels By theme (coming soon)"). Fixing the cleanup let it reach its
  // assertion, where it failed for an entirely different reason. TD-45's corollary:
  // an assertion reached for the first time in months is unverified text.
  it('By theme is disabled and fires nothing', () => {
    render(
      <FilterPills active="all" personas={[]} selectedPersonaSlug={null} onChange={vi.fn()} />,
    )
    const pill = screen.getByLabelText('By theme (coming soon)')
    expect((pill as HTMLButtonElement).disabled).toBe(true)

    fireEvent.click(pill)
    expect(toast).not.toHaveBeenCalled()
  })

  it('By theme does not change the filter', () => {
    const onChange = vi.fn()
    render(
      <FilterPills active="all" personas={[]} selectedPersonaSlug={null} onChange={onChange} />,
    )
    fireEvent.click(screen.getByLabelText('By theme (coming soon)'))
    // The point of the disabled state: tapping it must not select a filter that has
    // no implementation behind it.
    expect(onChange).not.toHaveBeenCalled()
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
