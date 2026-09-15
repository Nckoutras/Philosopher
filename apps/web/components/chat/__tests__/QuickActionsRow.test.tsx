// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import QuickActionsRow from '../QuickActionsRow'
import { useStore } from '@/lib/store'

vi.mock('react-hot-toast', () => ({ default: vi.fn() }))
vi.mock('@/components/chat/SaveLineInlineUpgrade', () => ({
  default: ({ onUpgrade, onDismiss }: { onUpgrade: () => void; onDismiss: () => void }) => (
    <div data-testid="inline-upgrade">
      <button onClick={onUpgrade}>upgrade</button>
      <button onClick={onDismiss}>dismiss</button>
    </div>
  ),
}))

import toast from 'react-hot-toast'

beforeEach(() => {
  useStore.setState({ freeSaveCount: 0, freeTierLimit: 3, subscription: null })
  vi.mocked(toast).mockClear()
})

describe('QuickActionsRow', () => {
  it('renders three action chips', () => {
    render(
      <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} />,
    )
    expect(screen.getByLabelText('Ask harder')).toBeTruthy()
    expect(screen.getByLabelText('Bring another mind')).toBeTruthy()
    expect(screen.getByLabelText('Save line')).toBeTruthy()
  })

  it('Ask harder shows Coming soon toast', () => {
    render(
      <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} />,
    )
    fireEvent.click(screen.getByLabelText('Ask harder'))
    expect(toast).toHaveBeenCalledWith('Coming soon', expect.any(Object))
  })

  it('Bring another mind calls onBringAnotherMind', () => {
    const onBringAnotherMind = vi.fn()
    render(
      <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={onBringAnotherMind} />,
    )
    fireEvent.click(screen.getByLabelText('Bring another mind'))
    expect(onBringAnotherMind).toHaveBeenCalledOnce()
  })

  it('calls onSave when Save line tapped and under limit', () => {
    const onSave = vi.fn()
    render(
      <QuickActionsRow messageId="m1" saved={false} onSave={onSave} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} />,
    )
    fireEvent.click(screen.getByLabelText('Save line'))
    expect(onSave).toHaveBeenCalledOnce()
  })

  it('shows inline upgrade card when at free tier limit', () => {
    useStore.setState({ freeSaveCount: 3, freeTierLimit: 3, subscription: null })
    render(
      <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} />,
    )
    fireEvent.click(screen.getByLabelText('Save line'))
    expect(screen.getByTestId('inline-upgrade')).toBeTruthy()
  })

  it('does not call onSave when at free tier limit', () => {
    useStore.setState({ freeSaveCount: 3, freeTierLimit: 3, subscription: null })
    const onSave = vi.fn()
    render(
      <QuickActionsRow messageId="m1" saved={false} onSave={onSave} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} />,
    )
    fireEvent.click(screen.getByLabelText('Save line'))
    expect(onSave).not.toHaveBeenCalled()
  })

  it('shows Saved chip when saved=true', () => {
    render(
      <QuickActionsRow messageId="m1" saved={true} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} />,
    )
    expect(screen.getByLabelText('Saved')).toBeTruthy()
  })

  it('upgrade card dismiss restores chips', () => {
    useStore.setState({ freeSaveCount: 3, freeTierLimit: 3, subscription: null })
    render(
      <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} />,
    )
    fireEvent.click(screen.getByLabelText('Save line'))
    expect(screen.getByTestId('inline-upgrade')).toBeTruthy()
    fireEvent.click(screen.getByText('dismiss'))
    expect(screen.getByLabelText('Save line')).toBeTruthy()
  })
})

// ── Γ-6: "Return to this" ────────────────────────────────────────────────────

describe('Return to this chip', () => {
  it('does not render when no handler is given', () => {
    // Optional by design: every existing call site and test renders unchanged.
    render(
      <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} />,
    )
    expect(screen.queryByLabelText('Return to this')).toBeNull()
  })

  it('renders beside Save line and calls the handler', () => {
    const onReturnToThis = vi.fn()
    render(
      <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} onReturnToThis={onReturnToThis} />,
    )
    expect(screen.getByLabelText('Save line')).toBeTruthy()
    fireEvent.click(screen.getByLabelText('Return to this'))
    expect(onReturnToThis).toHaveBeenCalledTimes(1)
  })

  it('does NOT consume the free save cap or show the inline upgrade', () => {
    // The two gates are different and the caller owns both. A free user at the
    // save cap tapping this must reach the SCHEDULING wall (Pro), not the save
    // wall — so this chip must notshort-circuit into SaveLineInlineUpgrade the way
    // Save line does.
    useStore.setState({ freeSaveCount: 3, freeTierLimit: 3, subscription: null })
    const onReturnToThis = vi.fn()
    render(
      <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} onReturnToThis={onReturnToThis} />,
    )
    fireEvent.click(screen.getByLabelText('Return to this'))
    expect(onReturnToThis).toHaveBeenCalledTimes(1)
    expect(screen.queryByTestId('inline-upgrade')).toBeNull()
  })

  it('the label is the founder-locked string', () => {
    // Copy lock, 2026-09-15. Pinned as a whole string: this is the name of the
    // gesture, and a reworded chip is a product decision rather than a refactor.
    const { container } = render(
      <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} onReturnToThis={vi.fn()} />,
    )
    expect(container.textContent).toContain('Return to this')
  })
})
