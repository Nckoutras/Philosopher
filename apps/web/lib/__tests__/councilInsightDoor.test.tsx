// @vitest-environment jsdom
//
// Γ-7-lite — the insight → Council door carries the insight's ID.
//
// THE DEFECT THIS CLOSES. Three rituals can be opened from an insight card. The
// Mirror and the Counterview both record which insight sent the person there
// (mirrors.insight_id, counterviews.insight_id — both nullable FKs with partial
// unique indexes). The Council did not: this door has always written the
// insight's CONTENT into sessionStorage as a prefill and council_source='nudge',
// so a case recorded that it came from AN insight and never which one.
//
// The belief branch three lines down has passed `?insightId=` to Counterview all
// along. Same fact, same door pattern, one surface missing it.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useInsightDoors } from '@/lib/useInsightDoors'
import { useStore } from '@/lib/store'

const push = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/lib/api', () => ({ api: { dismissInsight: vi.fn() } }))
vi.mock('@/components/chat/discardToast', () => ({ renderDiscardUndoToast: vi.fn() }))

const DILEMMA = {
  id: 'insight-abc',
  content: 'Whether to take the job.',
  insight_type: 'dilemma',
  conversation_id: 'conv-1',
  is_dismissed: false,
  created_at: '2026-09-15T00:00:00Z',
}
// The `as never` used to sit HERE, on the constant, which made the object itself
// unspreadable — `{ ...DILEMMA }` at the belief case below is a TS2698. The cast
// belongs at the call sites, where it is narrowing an argument, not erasing the
// shape of a fixture other cases need to read.

beforeEach(() => {
  push.mockClear()
  sessionStorage.clear()
  useStore.setState({ plan: 'pro' })
})

describe('the dilemma → Council door', () => {
  it('writes the insight id alongside the prefill it always wrote', () => {
    const { result } = renderHook(() => useInsightDoors())
    act(() => result.current.primary(DILEMMA as never))

    expect(sessionStorage.getItem('council_insight_id')).toBe('insight-abc')
    // The pre-existing handoff is untouched — this adds a key, it does not
    // replace one, and the members still receive the same prefilled matter.
    expect(sessionStorage.getItem('council_prefill')).toBe('Whether to take the job.')
    expect(sessionStorage.getItem('council_source')).toBe('nudge')
    expect(push).toHaveBeenCalledWith('/app/council')
  })

  it('writes nothing for a free user, who never reaches the council', () => {
    // The Pro gate returns before any sessionStorage write. A stale insight id
    // left behind here would attach itself to whatever council that person
    // eventually convened after upgrading.
    useStore.setState({ plan: 'free' })
    const { result } = renderHook(() => useInsightDoors())
    act(() => result.current.primary(DILEMMA as never))

    expect(sessionStorage.getItem('council_insight_id')).toBeNull()
    expect(push).toHaveBeenCalledWith('/app/upgrade?source=insight_door')
  })

  it('leaves the council keys alone for a non-dilemma insight', () => {
    // A belief goes to Counterview with ?insightId= in the URL. If it also wrote
    // council_insight_id, the NEXT council the person opened — by any route —
    // would claim an insight that was never brought before it.
    const { result } = renderHook(() => useInsightDoors())
    act(() => result.current.primary({ ...DILEMMA, insight_type: 'belief' } as never))

    expect(sessionStorage.getItem('council_insight_id')).toBeNull()
    expect(push).toHaveBeenCalledWith('/app/counterview?insightId=insight-abc')
  })
})
