// @vitest-environment jsdom
//
// TD-77 half 2 — the in-app path to a kept appointment.
//
// /app/scheduled-letters existed as BOTH a list and a detail route, and nothing
// in the application linked to either. The only inbound link in the repository
// was the arrival URL inside the future-self email — so an appointment somebody
// made was reachable only if that mail arrived AND its link worked, which is the
// failure the guard in this same PR closes. These two things were one bug.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import RitualsPage from '../page'
import { useStore } from '@/lib/store'

const push = vi.fn()
const replace = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ push, replace }) }))
vi.mock('next/image', () => ({ default: () => null }))
vi.mock('@/components/layout/AppHeader', () => ({ default: () => null }))
vi.mock('@/components/rituals/RitualScheduleSheet', () => ({ default: () => null }))

const LABEL = 'Messages waiting to return'

beforeEach(() => {
  push.mockClear()
  replace.mockClear()
  useStore.setState({
    token: 'tok',
    user: { id: 'u1', email: 'a@b.c' } as never,
    subscription: { status: 'active', plan: 'pro' } as never,
  })
})

describe('the link to scheduled returns', () => {
  it('renders with the founder-locked string', () => {
    // Copy lock, 2026-09-15. A whole string: this names the destination, and the
    // destination's own H1 ("Messages to future self.") is what it has to agree
    // with for the journey not to feel like two different places.
    render(<RitualsPage />)
    expect(screen.getByText(LABEL)).toBeTruthy()
  })

  it('routes to the orphaned list', () => {
    render(<RitualsPage />)
    fireEvent.click(screen.getByText(LABEL))
    expect(push).toHaveBeenCalledWith('/app/scheduled-letters')
  })

  it('shows for a FREE user too — the endpoint is all-tiers on purpose', () => {
    // Scheduling is Pro, so a free user has nothing here. A LAPSED subscriber
    // still has pending appointments and is exactly the person who most needs to
    // reach them — which is why GET /scheduled-emails is "All tiers" by its own
    // docstring. Gating this link would contradict the endpoint.
    useStore.setState({ subscription: { status: 'canceled', plan: 'free' } as never })
    render(<RitualsPage />)
    expect(screen.getByText(LABEL)).toBeTruthy()
    fireEvent.click(screen.getByText(LABEL))
    expect(push).toHaveBeenCalledWith('/app/scheduled-letters')
    // And it must NOT be diverted to the paywall the Future Self card uses.
    expect(push).not.toHaveBeenCalledWith(expect.stringContaining('/app/upgrade'))
  })

  it('does not become a sixth ritual card', () => {
    // The five cards are practices; this is a record of things already
    // scheduled. If it ever grows the card chrome, it is claiming to be a
    // practice — which is the misread this placement was chosen to avoid.
    render(<RitualsPage />)
    const link = screen.getByText(LABEL)
    expect(link.className).not.toContain('shadow-card')
    expect(link.className).not.toContain('border-edge')
  })
})
