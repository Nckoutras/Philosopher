// @vitest-environment jsdom
//
// THE REPORTED PRODUCTION DEFECT LIVES HERE. handlePersonaSelected's catch block
// rendered `err.message` verbatim, and the API hands the client the backend's
// FastAPI `detail` string — so a free user who tapped George Orwell in "Choose a
// mind" (Home / /app/discuss) read a red toast saying:
//
//     Persona george_orwell requires plan upgrade
//
// A raw slug, an internal sentence, and an error in place of the paywall the user
// had just asked for.
//
// The picker now gates on is_accessible before this hook is reached, so in practice
// this is the race path. It is tested directly because it is where the observed
// string came from, and because the picker's own "no raw slug" assertion cannot see
// it — the slug was never in the sheet, it was in the toast.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { api } from '@/lib/api'
import { track } from '@/lib/analytics'
import toast from 'react-hot-toast'
import { useTopicConversation } from '../useTopicConversation'

const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('handlePersonaSelected when the persona gate refuses', () => {
  it('routes to the paywall and never toasts the API message', async () => {
    vi.spyOn(api, 'createConversation').mockRejectedValue(
      new Error('Persona george_orwell requires plan upgrade'),
    )

    const { result } = renderHook(() => useTopicConversation())
    await act(async () => {
      await result.current.handlePersonaSelected('george_orwell')
    })

    expect(mockPush).toHaveBeenCalledWith(
      '/app/upgrade?source=persona_locked&persona=george_orwell',
    )
    // The exact regression: no toast at all, so certainly not one naming a slug.
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('never puts the raw refusal text or the slug in front of the user', async () => {
    vi.spyOn(api, 'createConversation').mockRejectedValue(
      new Error('Persona george_orwell requires plan upgrade'),
    )

    const { result } = renderHook(() => useTopicConversation())
    await act(async () => {
      await result.current.handlePersonaSelected('george_orwell')
    })

    const shown = (toast.error as unknown as { mock: { calls: unknown[][] } }).mock.calls
      .map((c) => String(c[0]))
      .join(' ')
    expect(shown).not.toContain('george_orwell')
    expect(shown).not.toContain('requires plan upgrade')
  })

  it('fires the existing upgrade_clicked event', async () => {
    vi.spyOn(api, 'createConversation').mockRejectedValue(
      new Error('Persona george_orwell requires plan upgrade'),
    )

    const { result } = renderHook(() => useTopicConversation())
    await act(async () => {
      await result.current.handlePersonaSelected('george_orwell')
    })

    expect(track).toHaveBeenCalledWith('upgrade_clicked', {
      surface: 'persona_locked',
      reason: 'persona_locked',
    })
  })
})

describe('handlePersonaSelected on other outcomes', () => {
  it('opens the conversation when the mind is accessible', async () => {
    vi.spyOn(api, 'createConversation').mockResolvedValue({ id: 'c1' } as never)

    const { result } = renderHook(() => useTopicConversation())
    await act(async () => {
      await result.current.handlePersonaSelected('marcus-aurelius')
    })

    expect(mockPush).toHaveBeenCalledWith('/app/chat/conv/c1')
    expect(toast.error).not.toHaveBeenCalled()
  })

  it('shows a calm fixed sentence for a genuine failure, not the API text', async () => {
    // A developer-facing detail string must never reach a person, whatever it says.
    vi.spyOn(api, 'createConversation').mockRejectedValue(
      new Error('psycopg2.OperationalError: connection refused'),
    )

    const { result } = renderHook(() => useTopicConversation())
    await act(async () => {
      await result.current.handlePersonaSelected('marcus-aurelius')
    })

    expect(toast.error).toHaveBeenCalledWith('Could not start conversation. Try again.')
    expect(mockPush).not.toHaveBeenCalled()
  })

  it('reopens the picker after a genuine failure so the user can retry', async () => {
    vi.spyOn(api, 'createConversation').mockRejectedValue(new Error('Network down'))

    const { result } = renderHook(() => useTopicConversation())
    await act(async () => {
      await result.current.handlePersonaSelected('marcus-aurelius')
    })

    expect(result.current.topicPickerOpen).toBe(true)
  })
})
