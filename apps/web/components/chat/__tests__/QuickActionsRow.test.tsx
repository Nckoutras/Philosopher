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

// THE 'Ask harder' CASES ARE GONE, AND WERE NOT DELETED (TD-86 step 2, cause 1).
//
// Two tests here asserted a chip labelled 'Ask harder' that showed a "Coming soon"
// toast. That chip no longer exists: it was productised into TWO real features —
// the deep-mode toggle and the Council door — and NEITHER had a single test. Deleting
// the stale cases would have removed a red mark and left that gap invisible, so the
// cases below are what replaces them. The coverage is new; it was never written when
// the features shipped.
//
// VERIFIED, NOT ASSUMED (TD-45). Every assertion below was read against the current
// component and then checked by breaking it: each `aria-label` string is quoted from
// QuickActionsRow.tsx:104-160, and the suppression rule at :143 was confirmed by
// rendering with insightType='dilemma' and watching the Council chip disappear.
describe('QuickActionsRow', () => {
  it('renders only the two always-on chips when no optional chip is enabled', () => {
    render(
      <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()} />,
    )
    expect(screen.getByLabelText('Bring another mind')).toBeTruthy()
    expect(screen.getByLabelText('Save line')).toBeTruthy()
    // showDeepChip and showCouncilChip both default to false (:60), so the row is two
    // chips wide on every message except the last assistant one. The previous version
    // of this test asserted THREE, counting a chip that has not existed for months.
    expect(screen.queryByLabelText(/Deep mode/)).toBeNull()
    expect(screen.queryByLabelText('Ask the Council')).toBeNull()
  })

  describe('the deep-mode chip', () => {
    it('renders OFF and says how to turn it on', () => {
      render(
        <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()}
          showDeepChip onToggleDeepMode={vi.fn()} />,
      )
      const chip = screen.getByLabelText('Deep mode off — tap to turn on')
      expect(chip.getAttribute('aria-pressed')).toBe('false')
    })

    it('renders ON, and aria-pressed carries the state a sighted user reads from colour', () => {
      render(
        <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()}
          showDeepChip deepMode onToggleDeepMode={vi.fn()} />,
      )
      const chip = screen.getByLabelText('Deep mode on — tap to turn off')
      expect(chip.getAttribute('aria-pressed')).toBe('true')
    })

    it('calls onToggleDeepMode when tapped', () => {
      const onToggleDeepMode = vi.fn()
      render(
        <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()}
          showDeepChip onToggleDeepMode={onToggleDeepMode} />,
      )
      fireEvent.click(screen.getByLabelText('Deep mode off — tap to turn on'))
      expect(onToggleDeepMode).toHaveBeenCalledTimes(1)
    })

    it('LOCKED takes precedence over ON: an out-of-quota free user sees the Pro lock, not the on-state', () => {
      const onToggleDeepMode = vi.fn()
      const onDeepPaywall = vi.fn()
      render(
        <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()}
          showDeepChip deepMode deepLocked onToggleDeepMode={onToggleDeepMode} onDeepPaywall={onDeepPaywall} />,
      )
      // The precedence is stated at :100-102 and is the whole reason the locked branch
      // is checked first. deepMode is TRUE here on purpose: a version that tested the
      // flag before the lock would render the on-state and send a lapsed user into a
      // feature they cannot use.
      fireEvent.click(screen.getByLabelText('Deep mode — Pro'))
      expect(onDeepPaywall).toHaveBeenCalledTimes(1)
      expect(onToggleDeepMode).not.toHaveBeenCalled()
      expect(screen.queryByLabelText(/tap to turn off/)).toBeNull()
    })
  })

  describe('the Council chip', () => {
    it('renders and calls onTakeToCouncil when enabled', () => {
      const onTakeToCouncil = vi.fn()
      render(
        <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()}
          showCouncilChip onTakeToCouncil={onTakeToCouncil} />,
      )
      fireEvent.click(screen.getByLabelText('Ask the Council'))
      expect(onTakeToCouncil).toHaveBeenCalledTimes(1)
    })

    it('is SUPPRESSED on a dilemma insight, because the insight door is already a Council door', () => {
      render(
        <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()}
          showCouncilChip onTakeToCouncil={vi.fn()} insightType="dilemma" onInsightDoor={vi.fn()} />,
      )
      // :142-143. Without the suppression the message shows two Council entries, one
      // labelled 'Ask the Council' and one 'Bring it to the Council' (:13).
      expect(screen.queryByLabelText('Ask the Council')).toBeNull()
      expect(screen.getByLabelText('Bring it to the Council')).toBeTruthy()
    })

    it('still renders for a non-dilemma insight, so the suppression is narrow', () => {
      render(
        <QuickActionsRow messageId="m1" saved={false} onSave={vi.fn()} onUpgradeConfirm={vi.fn()} onBringAnotherMind={vi.fn()}
          showCouncilChip onTakeToCouncil={vi.fn()} insightType="belief" onInsightDoor={vi.fn()} />,
      )
      expect(screen.getByLabelText('Ask the Council')).toBeTruthy()
      expect(screen.getByLabelText('Put it to the test')).toBeTruthy()
    })
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
