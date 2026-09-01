// @vitest-environment jsdom
//
// The locked persona-detail CTA was the app's other dead paywall: a bronze
// "Upgrade to Pro" button whose handler called `alert('Stripe checkout coming
// soon.')` while Stripe checkout was already live on /app/upgrade. It is the
// most explicit purchase intent a user can express — they opened a locked mind
// and pressed Upgrade — and it went nowhere.
//
// HOW THESE CAN FAIL. Case 1 asserts the exact destination, so a version that
// routes without `source`/`reason`/`persona` fails it, and the pre-PR version
// fails it twice over (no push at all, and `alert` called). Case 3 pins the
// unlocked path: a version that shows the upgrade CTA to a user who already has
// access would fail there rather than silently offering a redundant upsell.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useStore } from '@/lib/store'
import { api, type Persona } from '@/lib/api'
import { track } from '@/lib/analytics'
import PersonaDetailPage from '../page'

const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), back: vi.fn() }),
  useParams: () => ({ slug: 'marcus-aurelius' }),
}))

vi.mock('next/image', () => ({
  default: ({ src, alt }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} />
  ),
}))

vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))

function makePersona(overrides: Partial<Persona> = {}): Persona {
  return {
    id: 'p1',
    slug: 'marcus-aurelius',
    name: 'Marcus Aurelius',
    era: 'Roman',
    tradition: 'Stoicism',
    tier: 'pro',
    tagline: 'The emperor who wrote to himself.',
    avatar_emoji: null,
    opening_invocation: null,
    bio: 'Meditations was a private notebook.',
    portrait_url: '/personas/marcus-aurelius.webp',
    is_accessible: false,
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  useStore.setState({ token: 'tok' })
})

describe('persona detail — locked upgrade CTA', () => {
  it('routes to the live upgrade page with source, reason and persona slug', async () => {
    vi.spyOn(api, 'getPersonas').mockResolvedValue([makePersona()])
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})

    render(<PersonaDetailPage />)
    const cta = await screen.findByRole('button', { name: 'Upgrade to Pro' })
    fireEvent.click(cta)

    expect(mockPush).toHaveBeenCalledWith(
      '/app/upgrade?source=persona_detail&reason=persona_locked&persona=marcus-aurelius',
    )
    // The placeholder this PR removes. Nothing on this surface may block on a
    // native dialog again.
    expect(alertSpy).not.toHaveBeenCalled()
  })

  it('fires paywall_viewed on the locked render and upgrade_clicked on the press', async () => {
    vi.spyOn(api, 'getPersonas').mockResolvedValue([makePersona()])

    render(<PersonaDetailPage />)
    const cta = await screen.findByRole('button', { name: 'Upgrade to Pro' })

    expect(track).toHaveBeenCalledWith('paywall_viewed', {
      surface: 'persona_detail',
      reason: 'persona_locked',
    })
    expect(track).not.toHaveBeenCalledWith('upgrade_clicked', expect.anything())

    fireEvent.click(cta)
    expect(track).toHaveBeenCalledWith('upgrade_clicked', {
      surface: 'persona_detail',
      reason: 'persona_locked',
    })
  })

  it('shows no upgrade CTA and fires no paywall event when the mind is accessible', async () => {
    vi.spyOn(api, 'getPersonas').mockResolvedValue([makePersona({ is_accessible: true })])

    render(<PersonaDetailPage />)
    await screen.findByRole('button', { name: 'Begin conversation' })

    expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).toBeNull()
    await waitFor(() => {
      expect(track).not.toHaveBeenCalled()
    })
  })
})
