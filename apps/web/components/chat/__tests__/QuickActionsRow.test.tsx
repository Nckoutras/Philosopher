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
