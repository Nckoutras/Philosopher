// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import CallbackRejectLine from '../CallbackRejectLine'
import MessageList from '../MessageList'
import type { Message } from '@/lib/api'

const rejectCallback = vi.fn()
vi.mock('@/lib/api', () => ({
  api: {
    rejectCallback: (...a: unknown[]) => rejectCallback(...a),
    getPersonas: () => Promise.resolve([]),
  },
}))

beforeEach(() => {
  rejectCallback.mockReset()
})

describe('CallbackRejectLine', () => {
  it('rejects the callback and becomes one line (English)', async () => {
    rejectCallback.mockResolvedValue(undefined)
    render(<CallbackRejectLine callbackId="cb-1" replyText="A few weeks ago you said…" />)
    fireEvent.click(screen.getByRole('button', { name: "That's not right" }))
    expect(rejectCallback).toHaveBeenCalledWith('cb-1')
    expect(await screen.findByText("Noted. It won't come up again.")).toBeTruthy()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('speaks Greek under a Greek reply', async () => {
    rejectCallback.mockResolvedValue(undefined)
    render(<CallbackRejectLine callbackId="cb-2" replyText="Πριν από μερικές εβδομάδες έγραψες…" />)
    fireEvent.click(screen.getByRole('button', { name: 'Δεν ισχύει αυτό' }))
    expect(await screen.findByText('Εντάξει. Δεν θα ξαναναφερθεί.')).toBeTruthy()
  })

  it('offers the control again when the request fails', async () => {
    rejectCallback.mockRejectedValue(new Error('network'))
    render(<CallbackRejectLine callbackId="cb-3" replyText="reply" />)
    fireEvent.click(screen.getByRole('button', { name: "That's not right" }))
    await waitFor(() =>
      expect((screen.getByRole('button', { name: "That's not right" }) as HTMLButtonElement).disabled).toBe(false),
    )
    expect(screen.queryByText("Noted. It won't come up again.")).toBeNull()
  })
})

describe('MessageList', () => {
  const base = { safety_level: 'none', persona_override: false, created_at: '2026-10-05T00:00:00Z' }
  const messages: Message[] = [
    { ...base, id: 'u1', role: 'user', content: 'hi', callback_id: null },
    { ...base, id: 'a1', role: 'assistant', content: 'You said a few weeks ago…', callback_id: 'cb-1' },
    { ...base, id: 'a2', role: 'assistant', content: 'A plain reply.' },
  ]

  it('shows the control only under the reply that carries a callback id', () => {
    render(
      <MessageList
        messages={messages}
        onSaveLine={() => {}}
        onUpgradeConfirm={() => {}}
        onBringAnotherMind={() => {}}
      />,
    )
    expect(screen.getAllByRole('button', { name: "That's not right" })).toHaveLength(1)
  })
})
