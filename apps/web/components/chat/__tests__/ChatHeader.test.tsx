// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChatHeader from '../ChatHeader'

describe('ChatHeader', () => {
  it('renders persona name', () => {
    render(<ChatHeader personaName="Socrates" portraitUrl="/socrates.jpg" />)
    expect(screen.getByText('Socrates')).toBeTruthy()
  })

  it('renders portrait img with correct src and alt', () => {
    render(<ChatHeader personaName="Socrates" portraitUrl="/socrates.jpg" />)
    const img = screen.getByAltText('Socrates') as HTMLImageElement
    expect(img.src).toContain('socrates.jpg')
  })
})

// ── Γ-3: the escape hatch ────────────────────────────────────────────────────
//
// Without this action a person who wanted a clean start could not get one —
// worse than the old always-new behaviour it replaces. So the interesting
// assertions are the two absences: it must NOT appear on a thread that was not
// resumed, and it must not displace the sticky-guest affordance that shares
// the same slot.

import { vi } from 'vitest'

describe('ChatHeader — Start fresh', () => {
  it('offers it when the thread was resumed', () => {
    render(
      <ChatHeader personaName="Socrates" portraitUrl="/s.jpg" onStartFresh={vi.fn()} />,
    )
    expect(screen.getByRole('button', { name: 'Start fresh' })).toBeTruthy()
  })

  it('does NOT offer it on a thread that was not resumed', () => {
    // The default. A brand-new conversation already IS fresh; offering to start
    // one would be an action with no effect a user could perceive.
    render(<ChatHeader personaName="Socrates" portraitUrl="/s.jpg" />)
    expect(screen.queryByRole('button', { name: 'Start fresh' })).toBeNull()
  })

  it('calls back exactly once per tap', () => {
    const onStartFresh = vi.fn()
    render(
      <ChatHeader personaName="Socrates" portraitUrl="/s.jpg" onStartFresh={onStartFresh} />,
    )
    screen.getByRole('button', { name: 'Start fresh' }).click()
    expect(onStartFresh).toHaveBeenCalledTimes(1)
  })

  it('coexists with the sticky-guest Return affordance', () => {
    // Both live under the persona name. A resumed thread can carry a sticky
    // guest, so the two are not mutually exclusive and neither may hide the other.
    render(
      <ChatHeader
        personaName="Marcus Aurelius"
        portraitUrl="/m.jpg"
        originName="Socrates"
        isGuestActive
        onReturnToOrigin={vi.fn()}
        onStartFresh={vi.fn()}
      />,
    )
    expect(screen.getByRole('button', { name: 'Return to Socrates' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Start fresh' })).toBeTruthy()
  })

  it('uses the founder-locked wording', () => {
    render(<ChatHeader personaName="Socrates" portraitUrl="/s.jpg" onStartFresh={vi.fn()} />)
    expect(screen.getByText('Start fresh')).toBeTruthy()
    expect(screen.queryByText('New conversation')).toBeNull()
    expect(screen.queryByText('Begin again')).toBeNull()
  })
})
