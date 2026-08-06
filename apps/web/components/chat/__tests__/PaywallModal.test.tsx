// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useStore } from '@/lib/store'
import PaywallModal from '../PaywallModal'
import type { PaywallDetails } from '@/lib/store'

const baseDetails: PaywallDetails = {
  upgradeTarget: 'pro',
  resetAt: new Date('2026-05-17T09:00:00'),
  limit: 10,
}

beforeEach(() => {
  useStore.setState({ activePersonaName: 'Socrates' })
})

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
    expect(screen.getByRole('button', { name: /Upgrade to Pro/i })).toBeTruthy()
  })

  it('never offers Premium — a pro user still sees the Pro label', () => {
    // Single Pro tier. Before this, a paying Pro user who hit a rate limit was
    // shown "Upgrade to Premium → Coming soon" for a tier that will never exist.
    // upgradeTarget can no longer even be typed as 'premium'; this pins the
    // rendering so a reintroduced ternary would fail here.
    render(<PaywallModal open details={baseDetails} onClose={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Upgrade to Pro/i })).toBeTruthy()
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

  it('Upgrade CTA button is disabled', () => {
    render(<PaywallModal open details={baseDetails} onClose={vi.fn()} />)
    const upgradeBtn = screen.getByRole('button', { name: /Upgrade to Pro/i }) as HTMLButtonElement
    expect(upgradeBtn.disabled).toBe(true)
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
})
