// @vitest-environment jsdom
//
// A free user tapping a Pro mind in "Choose a mind" got a red error toast reading
// "Persona george_orwell requires plan upgrade" — the backend's PermissionError
// string surfaced verbatim (conversation_service.py → 403 detail →
// useTopicConversation). Two defects at once: a raw slug shown to a person, and an
// ERROR returned to the single most explicit purchase intent in the product. The
// user asked for a Pro mind; the answer should be the paywall.
//
// #576/#582 wired exactly this route from the persona detail page, AnotherMindSheet
// and the streaming refusal. The picker — six call sites: today, discuss,
// reflections, insights, letters, and the cross-persona flow — was missed.
//
// HOW THESE CAN FAIL. Case 1 asserts the destination AND that no toast fired, so the
// pre-fix version fails twice over. Case 3 pins the unlocked path, so a version that
// gated on `tier !== 'free'` — the badge, not the entitlement — would fail there by
// sending a paying Pro subscriber to the paywall instead of into the conversation.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { api, type Persona } from '@/lib/api'
import { track } from '@/lib/analytics'
import toast from 'react-hot-toast'
import PersonaPickerSheet from '../PersonaPickerSheet'

const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), back: vi.fn() }),
}))

vi.mock('next/image', () => ({
  default: ({ src, alt }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} />
  ),
}))

vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

// BottomSheet renders its children through a portal + transitions; the picker's
// behaviour under test is the tap handler, so keep the wrapper trivial.
vi.mock('@/components/ui/BottomSheet', () => ({
  default: ({ open, children }: { open: boolean; children: React.ReactNode }) =>
    open ? <div>{children}</div> : null,
}))

function makePersona(overrides: Partial<Persona> = {}): Persona {
  return {
    id: 'p1',
    slug: 'marcus-aurelius',
    name: 'Marcus Aurelius',
    era: 'Roman',
    tradition: 'Stoicism',
    tier: 'free',
    tagline: 'The emperor who wrote to himself.',
    avatar_emoji: null,
    opening_invocation: null,
    bio: 'A bio.',
    portrait_url: '/personas/marcus-aurelius.webp',
    is_accessible: true,
    ...overrides,
  }
}

const LOCKED = makePersona({
  id: 'p2',
  slug: 'george_orwell',
  name: 'George Orwell',
  tier: 'pro',
  is_accessible: false,
})

const FREE = makePersona()

beforeEach(() => {
  vi.clearAllMocks()
})

// ── (a) The locked tap routes to the paywall, and shows no error ─────────────

describe('tapping a locked mind', () => {
  it('routes to the paywall with source=persona_locked and the slug, and shows no toast', async () => {
    vi.spyOn(api, 'getPersonas').mockResolvedValue([FREE, LOCKED])
    const onSelect = vi.fn()

    render(<PersonaPickerSheet open onClose={vi.fn()} onSelect={onSelect} />)
    fireEvent.click(await screen.findByText('George Orwell'))

    await waitFor(() => expect(mockPush).toHaveBeenCalled())
    expect(mockPush).toHaveBeenCalledWith(
      '/app/upgrade?source=persona_locked&persona=george_orwell',
    )
    // THE DEFECT: an error where a conversion surface belongs.
    expect(toast.error).not.toHaveBeenCalled()
    // And the locked mind was never selected into the caller's flow.
    expect(onSelect).not.toHaveBeenCalled()
  })

  it('fires the existing upgrade_clicked event with the persona_locked source', async () => {
    vi.spyOn(api, 'getPersonas').mockResolvedValue([LOCKED])

    render(<PersonaPickerSheet open onClose={vi.fn()} onSelect={vi.fn()} />)
    fireEvent.click(await screen.findByText('George Orwell'))

    await waitFor(() => expect(track).toHaveBeenCalled())
    expect(track).toHaveBeenCalledWith('upgrade_clicked', {
      surface: 'persona_locked',
      reason: 'persona_locked',
    })
  })

  it('never calls the API that exists only to refuse it', async () => {
    vi.spyOn(api, 'getPersonas').mockResolvedValue([LOCKED])
    const create = vi.spyOn(api, 'createCrossPersonaConversation')

    render(<PersonaPickerSheet open savedLineId="sl1" onClose={vi.fn()} onCreated={vi.fn()} />)
    fireEvent.click(await screen.findByText('George Orwell'))

    await waitFor(() => expect(mockPush).toHaveBeenCalled())
    expect(create).not.toHaveBeenCalled()
  })

  it('closes the sheet on the way to the paywall', async () => {
    vi.spyOn(api, 'getPersonas').mockResolvedValue([LOCKED])
    const onClose = vi.fn()

    render(<PersonaPickerSheet open onClose={onClose} onSelect={vi.fn()} />)
    fireEvent.click(await screen.findByText('George Orwell'))

    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })
})

// ── (b) A free mind still selects normally ──────────────────────────────────

describe('tapping an accessible mind', () => {
  it('selects it and does not route to the paywall', async () => {
    vi.spyOn(api, 'getPersonas').mockResolvedValue([FREE, LOCKED])
    const onSelect = vi.fn()

    render(<PersonaPickerSheet open onClose={vi.fn()} onSelect={onSelect} />)
    fireEvent.click(await screen.findByText('Marcus Aurelius'))

    await waitFor(() => expect(onSelect).toHaveBeenCalledWith('marcus-aurelius'))
    expect(mockPush).not.toHaveBeenCalled()
    expect(track).not.toHaveBeenCalled()
  })

  it('opens a PRO mind normally for a subscriber who has access', async () => {
    // tier is 'pro' but is_accessible is true — a paying subscriber. Gating on the
    // badge instead of the entitlement would send this user to the paywall.
    const proButOwned = makePersona({
      slug: 'george_orwell',
      name: 'George Orwell',
      tier: 'pro',
      is_accessible: true,
    })
    vi.spyOn(api, 'getPersonas').mockResolvedValue([proButOwned])
    const onSelect = vi.fn()

    render(<PersonaPickerSheet open onClose={vi.fn()} onSelect={onSelect} />)
    fireEvent.click(await screen.findByText('George Orwell'))

    await waitFor(() => expect(onSelect).toHaveBeenCalledWith('george_orwell'))
    expect(mockPush).not.toHaveBeenCalled()
  })

  it('creates the conversation on the onCreated path', async () => {
    vi.spyOn(api, 'getPersonas').mockResolvedValue([FREE])
    vi.spyOn(api, 'createCrossPersonaConversation').mockResolvedValue({ id: 'c1' } as never)
    const onCreated = vi.fn()

    render(<PersonaPickerSheet open savedLineId="sl1" onClose={vi.fn()} onCreated={onCreated} />)
    fireEvent.click(await screen.findByText('Marcus Aurelius'))

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith('c1'))
    expect(mockPush).not.toHaveBeenCalled()
  })
})

// ── (c) The server-refusal fallback, and no raw slug anywhere ───────────────

describe('a server refusal that slips past the client gate', () => {
  it('routes to the paywall instead of toasting the API message', async () => {
    // The race: the loaded list said accessible, the server disagrees.
    vi.spyOn(api, 'getPersonas').mockResolvedValue([
      makePersona({ slug: 'george_orwell', name: 'George Orwell', tier: 'pro', is_accessible: true }),
    ])
    vi.spyOn(api, 'createCrossPersonaConversation').mockRejectedValue(
      new Error('Persona george_orwell requires plan upgrade'),
    )

    render(<PersonaPickerSheet open savedLineId="sl1" onClose={vi.fn()} onCreated={vi.fn()} />)
    fireEvent.click(await screen.findByText('George Orwell'))

    await waitFor(() => expect(mockPush).toHaveBeenCalled())
    expect(mockPush).toHaveBeenCalledWith(
      '/app/upgrade?source=persona_locked&persona=george_orwell',
    )
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('still shows the calm generic toast for a genuine failure', async () => {
    vi.spyOn(api, 'getPersonas').mockResolvedValue([FREE])
    vi.spyOn(api, 'createCrossPersonaConversation').mockRejectedValue(new Error('Network down'))
    vi.spyOn(console, 'error').mockImplementation(() => {})

    render(<PersonaPickerSheet open savedLineId="sl1" onClose={vi.fn()} onCreated={vi.fn()} />)
    fireEvent.click(await screen.findByText('Marcus Aurelius'))

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    expect(toast.error).toHaveBeenCalledWith('Could not open conversation. Try again.')
    expect(mockPush).not.toHaveBeenCalled()
  })

  it('renders no raw slug anywhere in the sheet', async () => {
    vi.spyOn(api, 'getPersonas').mockResolvedValue([FREE, LOCKED])

    const { container } = render(<PersonaPickerSheet open onClose={vi.fn()} onSelect={vi.fn()} />)
    await screen.findByText('George Orwell')

    // Display names only. The slug travels in the query string, never on screen.
    expect(container.textContent).not.toContain('george_orwell')
    expect(container.textContent).not.toContain('requires plan upgrade')
  })
})
