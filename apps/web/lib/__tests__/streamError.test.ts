// RF-01: verify the streamError Zustand store state that useStream writes to
import { describe, it, expect, beforeEach } from 'vitest'
import { useStore } from '../store'

beforeEach(() => {
  useStore.setState({ streamError: null })
})

describe('RF-01 streamError store state', () => {
  it('surfaces persona_voice via setStreamError', () => {
    useStore.getState().setStreamError({
      error_code: 'llm_unavailable',
      persona_voice: 'I cannot form thought right now.',
    })

    const { streamError } = useStore.getState()
    expect(streamError).not.toBeNull()
    expect(streamError?.error_code).toBe('llm_unavailable')
    expect(streamError?.persona_voice).toBe('I cannot form thought right now.')
  })

  it('clears streamError when set to null (start of next send)', () => {
    useStore.getState().setStreamError({ error_code: 'llm_unavailable', persona_voice: 'test' })
    useStore.getState().setStreamError(null)

    expect(useStore.getState().streamError).toBeNull()
  })
})
