// @vitest-environment jsdom
//
// HOW THESE CAN FAIL. Before this PR the modal's CTA was `<button disabled>` labelled
// "Upgrade to Pro → Coming soon" with no route anywhere — the app could not take a
// payment from its highest-intent surface. Every routing case below fails on that base
// (a disabled button fires no onClick, so `mockPush` is never called), and the enabled
// assertion fails outright.
//
// The URL cases assert the EXACT destination per reason, so a version that hardcodes one
// reason fails four of the five, and one that drops `source` fails all five.
// `omits the persona key…` pins the two absences that would otherwise produce the string
// "undefined": the 429 variant carries no `reason` at all, and the quotes screen opens
// the paywall with no active persona in the store.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useStore } from '@/lib/store'
import { track } from '@/lib/analytics'
import PaywallModal from '../PaywallModal'
import type { PaywallDetails } from '@/lib/store'

const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))

const baseDetails: PaywallDetails = {
  upgradeTarget: 'pro',
  resetAt: new Date('2026-05-17T09:00:00'),
  limit: 10,
}

beforeEach(() => {
  vi.clearAllMocks()
  useStore.setState({ activePersonaName: 'Socrates', activePersonaSlug: 'socrates' })
})

function upgradeButton(): HTMLButtonElement {
  return screen.getByRole('button', { name: /Upgrade to Pro/i }) as HTMLButtonElement
}

describe('PaywallModal', () => {
  it('renders when open is true', () => {
    render(<PaywallModal open details={baseDetails} onClose={vi.fn()} />)
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(screen.getByText('Daily limit reached.')).toBeTruthy()
  })

  it('renders nothing when open is false', () => {
    const { container } = render(
      <PaywallModal open={false} details={baseDetails} onClose={vi.fn()} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders correct upgrade target label for Pro', () => {
    render(<PaywallModal open details={baseDetails} onClose={vi.fn()} />)
    expect(upgradeButton()).toBeTruthy()
  })

  it('never offers Premium — a pro user still sees the Pro label', () => {
    // Single Pro tier. Before this, a paying Pro user who hit a rate limit was
    // shown "Upgrade to Premium → Coming soon" for a tier that will never exist.
    // upgradeTarget can no longer even be typed as 'premium'; this pins the
    // rendering so a reintroduced ternary would fail here.
    render(<PaywallModal open details={baseDetails} onClose={vi.fn()} />)
    expect(upgradeButton()).toBeTruthy()
    expect(screen.queryByText(/Premium/i)).toBeNull()
  })

  it('calls onClose when the × button is clicked', () => {
    const onClose = vi.fn()
    render(<PaywallModal open details={baseDetails} onClose={onClose} />)
    fireEvent.click(screen.getByLabelText('Close'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when the Close text link is clicked', () => {
    const onClose = vi.fn()
    render(<PaywallModal open details={baseDetails} onClose={onClose} />)
    fireEvent.click(screen.getByText('Close'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose when backdrop is clicked', () => {
    const onClose = vi.fn()
    const { container } = render(<PaywallModal open details={baseDetails} onClose={onClose} />)
    const backdrop = container.querySelector('[aria-hidden="true"]') as HTMLElement
    fireEvent.click(backdrop)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('Upgrade CTA button is enabled and offers no "Coming soon"', () => {
    // Inverted from its previous form, which asserted `disabled === true`. The
    // button was hard-disabled behind a "Coming soon" tooltip while Stripe
    // checkout was already live on /app/upgrade — so no user could ever reach
    // checkout from a paywall.
    render(<PaywallModal open details={baseDetails} onClose={vi.fn()} />)
    expect(upgradeButton().disabled).toBe(false)
    expect(screen.queryByText(/Coming soon/i)).toBeNull()
    expect(screen.queryByRole('tooltip')).toBeNull()
  })

  it('renders persona name from store in body copy', () => {
    render(<PaywallModal open details={baseDetails} onClose={vi.fn()} />)
    expect(screen.getByText(/You've used today's reflections with Socrates\./)).toBeTruthy()
  })

  it('falls back to "this mind" when activePersonaName is null', () => {
    useStore.setState({ activePersonaName: null })
    render(<PaywallModal open details={baseDetails} onClose={vi.fn()} />)
    expect(screen.getByText(/You've used today's reflections with this mind\./)).toBeTruthy()
  })

  it('renders the save-limit copy and no daily-limit copy when reason is save_limit', () => {
    // The four saved-line call sites used to open the paywall with no reason, so a
    // user who hit the 3-line save cap was shown the DAILY MESSAGE limit copy plus a
    // placeholder "resets today at <now>". The save cap has no reset at all.
    const saveLimitDetails: PaywallDetails = {
      upgradeTarget: 'pro',
      reason: 'save_limit',
    }
    render(<PaywallModal open details={saveLimitDetails} onClose={vi.fn()} />)

    expect(screen.getByText("You're keeping all three.")).toBeTruthy()
    expect(
      screen.getByText(
        /Free saving stops at three lines\. Pro has no limit — everything you mark stays in your reflections\./,
      ),
    ).toBeTruthy()

    expect(screen.queryByText('Daily limit reached.')).toBeNull()
    expect(screen.queryByText(/Your free conversations reset/)).toBeNull()
  })

  describe('upgrade routing', () => {
    // One row per trigger reason the store can carry. `undefined` is the 429 path,
    // which sets no reason at all — it must serialize as 'daily', never as absent
    // and never as the string "undefined".
    const cases: Array<[string, PaywallDetails['reason'], string]> = [
      ['daily (no reason set — the 429 path)', undefined, 'daily'],
      ['go_deeper_depth', 'go_deeper_depth', 'go_deeper_depth'],
      ['deep_mode', 'deep_mode', 'deep_mode'],
      ['save_limit', 'save_limit', 'save_limit'],
      ['persona_locked', 'persona_locked', 'persona_locked'],
    ]

    it.each(cases)(
      '%s routes to the upgrade page with source + reason',
      (_label, reason, expected) => {
        render(
          <PaywallModal open details={{ upgradeTarget: 'pro', reason }} onClose={vi.fn()} />,
        )
        fireEvent.click(upgradeButton())

        expect(mockPush).toHaveBeenCalledTimes(1)
        expect(mockPush).toHaveBeenCalledWith(
          `/app/upgrade?source=paywall_modal&reason=${expected}&persona=socrates`,
        )
      },
    )

    it.each(cases)(
      '%s fires paywall_viewed on open and upgrade_clicked on click',
      (_label, reason, expected) => {
        render(
          <PaywallModal open details={{ upgradeTarget: 'pro', reason }} onClose={vi.fn()} />,
        )
        expect(track).toHaveBeenCalledWith('paywall_viewed', {
          surface: 'paywall_modal',
          reason: expected,
        })
        expect(track).not.toHaveBeenCalledWith('upgrade_clicked', expect.anything())

        fireEvent.click(upgradeButton())
        expect(track).toHaveBeenCalledWith('upgrade_clicked', {
          surface: 'paywall_modal',
          reason: expected,
        })
      },
    )

    it('fires no paywall_viewed while closed', () => {
      render(<PaywallModal open={false} details={baseDetails} onClose={vi.fn()} />)
      expect(track).not.toHaveBeenCalled()
    })

    it('omits the persona key rather than serializing "undefined" when no context exists', () => {
      // The quotes screen opens persona_locked with no active conversation, so
      // activePersonaSlug is null there. Combined with the 429 path's absent reason,
      // this is the case that would produce "?reason=undefined&persona=undefined"
      // under naive template-string interpolation.
      useStore.setState({ activePersonaName: null, activePersonaSlug: null })
      render(<PaywallModal open details={{ upgradeTarget: 'pro' }} onClose={vi.fn()} />)
      fireEvent.click(upgradeButton())

      const url = mockPush.mock.calls[0][0] as string
      expect(url).toBe('/app/upgrade?source=paywall_modal&reason=daily')
      expect(url).not.toContain('undefined')
      expect(url).not.toContain('persona=')
    })

    it('puts the persona SLUG in the URL and never the display name', () => {
      // personaVoice / activePersonaName are user-facing copy. Only internal ids
      // travel in the query string.
      useStore.setState({
        activePersonaName: 'Marcus Aurelius',
        activePersonaSlug: 'marcus-aurelius',
      })
      render(
        <PaywallModal
          open
          details={{
            upgradeTarget: 'pro',
            reason: 'persona_locked',
            personaVoice: 'Marcus Aurelius',
          }}
          onClose={vi.fn()}
        />,
      )
      fireEvent.click(upgradeButton())

      const url = mockPush.mock.calls[0][0] as string
      expect(url).toContain('persona=marcus-aurelius')
      expect(url).not.toContain('Marcus')
      expect(url).not.toContain('personaVoice')
    })
  })
})
