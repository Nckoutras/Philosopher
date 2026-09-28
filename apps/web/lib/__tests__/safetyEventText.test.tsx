// @vitest-environment jsdom
//
// SAFETY-003 — the safety event carries the whole crisis text.
//
// Removing the hardcoded English fallback from SafetyBubble made one failure
// possible that was not before: a connection dropped between the `safety` event
// and its first chunk would leave the crisis bubble EMPTY. The server now puts the
// full text inside the event itself, and useStream renders it the moment the event
// lands. The chunks still follow, for older clients, and must not double the text.
//
// All three chat streams are covered: send (pre-generation `safety`), and the two
// guest paths (post-generation `safety_override`).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, renderHook, act, screen } from '@testing-library/react'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import { useStream } from '../useStream'
import SafetyBubble from '@/components/chat/SafetyBubble'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}))
vi.mock('@/lib/analytics', () => ({ track: vi.fn() }))
vi.mock('react-hot-toast', () => {
  const fn = vi.fn()
  return { default: Object.assign(fn, { error: vi.fn(), success: vi.fn() }) }
})

const CRISIS =
  "Some of what you've shared sounds heavy, and your safety matters more than this conversation.\n\n" +
  'In the US, call or text 988. In the UK and Ireland, call Samaritans on 116 123.'

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

const PATHS = [
  {
    name: 'send',
    method: 'streamMessage' as const,
    event: 'safety',
    call: (s: ReturnType<typeof useStream>) => s.send('I want to die'),
  },
  {
    name: 'sendAnotherMind',
    method: 'streamAnotherMind' as const,
    event: 'safety_override',
    call: (s: ReturnType<typeof useStream>) => s.sendAnotherMind('socrates'),
  },
  {
    name: 'sendGoDeeper',
    method: 'streamGoDeeper' as const,
    event: 'safety_override',
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

describe.each(PATHS)('the crisis text rides on the safety event — $name', (path) => {
  it('shows the text when NO chunk ever arrives (the dropped connection)', async () => {
    // The stream ends right after the event: no chunks, no `done`.
    await run(path, [{ type: path.event, level: 'high', text: CRISIS }])

    expect(useStore.getState().safetyActive).toBe(true)
    expect(useStore.getState().safetyText).toBe(CRISIS)
    const { container } = render(<SafetyBubble />)
    expect(container.querySelector('[role="alert"]')?.textContent).toBe(CRISIS)
    expect(screen.getByRole('link', { name: '988' }).getAttribute('href')).toBe('tel:988')
  })

  it('does not double the text when the chunks follow as usual', async () => {
    await run(path, [
      { type: path.event, level: 'high', text: CRISIS },
      { type: 'chunk', data: CRISIS.slice(0, 40) },
      { type: 'chunk', data: CRISIS.slice(40) },
      { type: 'done' },
    ])
    expect(useStore.getState().safetyText).toBe(CRISIS)
  })

  it('still fills from the chunks when the event has no text (an older server)', async () => {
    await run(path, [
      { type: path.event, level: 'high' },
      { type: 'chunk', data: CRISIS.slice(0, 40) },
      { type: 'chunk', data: CRISIS.slice(40) },
      { type: 'done' },
    ])
    expect(useStore.getState().safetyText).toBe(CRISIS)
  })
})
