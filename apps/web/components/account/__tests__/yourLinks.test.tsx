// @vitest-environment jsdom
/**
 * "Your links" — the surface that makes revocation reachable.
 *
 * WHAT IS PINNED, and why each one is here rather than assumed:
 *
 *   1. A REVOKED ROW STAYS, MUTED, WITH NO ACTION. Seeing that you turned a
 *      link off IS the confirmation that you did. A list that dropped the row
 *      would leave a person wondering whether the tap registered — the exact
 *      uncertainty this screen exists to remove.
 *   2. THE CONFIRM BODY TELLS THE TRUTH. It is the one piece of copy in this
 *      feature that says revocation cannot recall the card. Shortening it into
 *      "this will delete the image" is the failure mode the whole design was
 *      built to avoid, so the words are asserted, not just the dialog's
 *      presence.
 *   3. NO VIEW COUNTS ANYWHERE. A ruling, not an omission, and the kind of
 *      thing a later "small addition" reverses without noticing.
 *   4. THE EMPTY STATE IS NOT THE ERROR STATE. A person with no links and a
 *      person whose request failed must not read the same sentence.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

import YourLinks from '../YourLinks'

const LIVE = {
  public_id: 'AbCdEfGhIjKlMnOpQrStUv',
  url: 'https://thewiseroom.app/s/AbCdEfGhIjKlMnOpQrStUv',
  artifact_type: 'line' as const,
  created_at: '2026-09-20T08:09:39Z',
  revoked: false,
}

const REVOKED = { ...LIVE, public_id: 'ZzZzZzZzZzZzZzZzZzZzZz', revoked: true }

const listMyShares = vi.fn()
const revokeShare = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    listMyShares: (...a: unknown[]) => listMyShares(...a),
    revokeShare: (...a: unknown[]) => revokeShare(...a),
  },
}))

vi.mock('react-hot-toast', () => ({ default: Object.assign(vi.fn(), { dismiss: vi.fn() }) }))

beforeEach(() => {
  listMyShares.mockReset()
  revokeShare.mockReset()
})
afterEach(() => vi.clearAllMocks())

describe('the list', () => {
  it('shows the type, the short url and the date', async () => {
    listMyShares.mockResolvedValue([LIVE])
    render(<YourLinks />)

    expect(await screen.findByText('Reflection')).toBeTruthy()
    // The card's printed form — no scheme, so it matches what is on the image.
    expect(screen.getByText('thewiseroom.app/s/AbCdEfGhIjKlMnOpQrStUv')).toBeTruthy()
    expect(screen.getByText(/20 September 2026/)).toBeTruthy()
  })

  it('offers the action on a live row', async () => {
    listMyShares.mockResolvedValue([LIVE])
    render(<YourLinks />)
    expect(await screen.findByText('Turn off this link')).toBeTruthy()
  })

  it('keeps a revoked row listed and gives it no action', async () => {
    listMyShares.mockResolvedValue([REVOKED])
    const { container } = render(<YourLinks />)

    await screen.findByText('Reflection')
    expect(container.textContent).toContain('Turned off')
    expect(screen.queryByText('Turn off this link')).toBeNull()
  })

  it('never shows a view count', async () => {
    listMyShares.mockResolvedValue([LIVE, REVOKED])
    const { container } = render(<YourLinks />)

    await screen.findAllByText('Reflection')
    const text = (container.textContent ?? '').toLowerCase()
    for (const forbidden of ['view', 'opened', 'visit', 'seen by']) {
      expect(text).not.toContain(forbidden)
    }
  })
})

describe('the empty and error states', () => {
  it('says there are no links yet', async () => {
    listMyShares.mockResolvedValue([])
    const { container } = render(<YourLinks />)

    expect(await screen.findByText('No links yet.')).toBeTruthy()
    expect(container.textContent).toContain(
      'When you share a reflection, the link will appear here.',
    )
  })

  it('does not call a failed request an empty list', async () => {
    listMyShares.mockRejectedValue(new Error('network'))
    const { container } = render(<YourLinks />)

    await waitFor(() => expect(container.textContent).toContain('Something on our side'))
    expect(container.textContent).not.toContain('No links yet.')
  })
})

describe('turning a link off', () => {
  it('asks first, and the question tells the whole truth', async () => {
    listMyShares.mockResolvedValue([LIVE])
    const { container } = render(<YourLinks />)

    fireEvent.click(await screen.findByText('Turn off this link'))

    expect(screen.getByText('Turn off this link?')).toBeTruthy()
    const text = container.textContent ?? ''
    expect(text).toContain('Anyone who opens it will see that it was withdrawn.')
    // THE SENTENCE THAT MUST SURVIVE EVERY FUTURE EDIT.
    expect(text).toContain('turning off the link does not recall it')
    expect(screen.getByText('Turn it off')).toBeTruthy()
    // "Keep it on" says what happens; "Cancel" does not.
    expect(screen.getByText('Keep it on')).toBeTruthy()
  })

  it('never claims the card is deleted', async () => {
    listMyShares.mockResolvedValue([LIVE])
    const { container } = render(<YourLinks />)
    fireEvent.click(await screen.findByText('Turn off this link'))

    const text = (container.textContent ?? '').toLowerCase()
    for (const forbidden of ['delete', 'recall the', 'erase', 'remove the image']) {
      expect(text).not.toContain(forbidden)
    }
  })

  it('does nothing until confirmed', async () => {
    listMyShares.mockResolvedValue([LIVE])
    render(<YourLinks />)
    fireEvent.click(await screen.findByText('Turn off this link'))
    fireEvent.click(screen.getByText('Keep it on'))

    expect(revokeShare).not.toHaveBeenCalled()
  })

  it('mutes the row in place once confirmed, rather than dropping it', async () => {
    listMyShares.mockResolvedValue([LIVE])
    revokeShare.mockResolvedValue(undefined)
    const { container } = render(<YourLinks />)

    fireEvent.click(await screen.findByText('Turn off this link'))
    fireEvent.click(screen.getByText('Turn it off'))

    await waitFor(() => expect(revokeShare).toHaveBeenCalledWith(LIVE.public_id))
    // Still there — that IS the confirmation.
    await waitFor(() => expect(container.textContent).toContain('Turned off'))
    expect(screen.getByText('Reflection')).toBeTruthy()
    expect(screen.queryByText('Turn off this link')).toBeNull()
    // And it did not refetch: the row is updated in place.
    expect(listMyShares).toHaveBeenCalledTimes(1)
  })

  it('keeps the row actionable when the revoke fails', async () => {
    listMyShares.mockResolvedValue([LIVE])
    revokeShare.mockRejectedValue(new Error('500'))
    const { container } = render(<YourLinks />)

    fireEvent.click(await screen.findByText('Turn off this link'))
    fireEvent.click(screen.getByText('Turn it off'))

    await waitFor(() =>
      expect(container.textContent).toContain('Could not turn the link off.'),
    )
    // NOT muted. A row that looks withdrawn after a failed request is a lie the
    // person will only discover from someone else opening the link.
    expect(container.textContent).not.toContain('Turned off')
  })
})
