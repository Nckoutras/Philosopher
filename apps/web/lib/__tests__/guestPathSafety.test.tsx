// @vitest-environment jsdom
//
// TD-101 — the post-generation safety gate on the two guest paths.
//
// The server now runs check_output on another-mind and go-deeper, as it always
// has on send. On a positive it sends `safety_override`, then streams the
// app-voice response, and saves THAT in place of the reply. The client half of
// the fix is here: before it, neither sendAnotherMind nor sendGoDeeper had a
// case for the event, so the safety chunks would have been appended straight
// after the harmful text — one bubble holding both, and appended to the thread
// as the assistant's message.
//
// Asserted on real store state, the way fairUseToast.test.tsx does: the defect
// would be visible in what SafetyBubble and the message list read, so that is
// what is read here.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import { useStream } from '../useStream'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}))
vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))
vi.mock('react-hot-toast', () => {
  const fn = vi.fn()
  return { default: Object.assign(fn, { error: vi.fn(), success: vi.fn() }) }
})

const HARMFUL = 'Some would speak of a lethal dose.'
const SAFE = 'You matter. Please reach out to someone now.'

/** A Response whose body yields the given SSE events once, then ends. */
function sse(events: object[]): Response {
  const payload = new TextEncoder().encode(
    events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join(''),
  )
  let sent = false
  return {
    ok: true,
    status: 200,
    body: {
      getReader: () => ({
        read: async () => {
          if (sent) return { done: true, value: undefined }
          sent = true
          return { done: false, value: payload }
        },
      }),
    },
  } as unknown as Response
}

const OVERRIDDEN = [
  { type: 'start', persona_slug: 'socrates', persona_name: 'Socrates' },
  { type: 'chunk', data: HARMFUL },
  { type: 'safety_override', level: 'high' },
  { type: 'chunk', data: SAFE },
  { type: 'done', message_id: 'm-1' },
]

const CLEAN = [
  { type: 'start', persona_slug: 'socrates', persona_name: 'Socrates' },
  { type: 'chunk', data: 'Consider what is in your power.' },
  { type: 'done', message_id: 'm-2' },
]

const PATHS = [
  {
    name: 'sendAnotherMind',
    method: 'streamAnotherMind' as const,
    call: (s: ReturnType<typeof useStream>) => s.sendAnotherMind('socrates'),
  },
  {
    name: 'sendGoDeeper',
    method: 'streamGoDeeper' as const,
    call: (s: ReturnType<typeof useStream>) => s.sendGoDeeper(),
  },
]

beforeEach(() => {
  vi.clearAllMocks()
  vi.restoreAllMocks()
  useStore.setState({
    activeConversationId: 'conv-1',
    plan: 'pro',
    messages: [],
    safetyActive: false,
    safetyText: '',
    streamingContent: '',
  })
})

async function run(path: (typeof PATHS)[number], events: object[]) {
  vi.spyOn(api, path.method).mockResolvedValue(sse(events))
  const { result } = renderHook(() => useStream())
  await act(async () => {
    await path.call(result.current)
  })
}

describe.each(PATHS)('post-generation safety on $name', (path) => {
  it('hands the response to SafetyBubble and never shows the replaced reply', async () => {
    await run(path, OVERRIDDEN)
    const state = useStore.getState()

    expect(state.safetyActive).toBe(true)
    expect(state.safetyText).toBe(SAFE)
    // The streamed reply is gone from the screen…
    expect(state.streamingContent).not.toContain(HARMFUL)
    // …and never becomes a message in the thread.
    expect(JSON.stringify(state.messages)).not.toContain(HARMFUL)
    expect(JSON.stringify(state.messages)).not.toContain(SAFE)
    expect(state.messages).toHaveLength(0)
  })

  it('leaves a clean reply exactly as before', async () => {
    await run(path, CLEAN)
    const state = useStore.getState()

    expect(state.safetyActive).toBe(false)
    expect(state.messages).toHaveLength(1)
    expect(state.messages[0].content).toBe('Consider what is in your power.')
  })
})
