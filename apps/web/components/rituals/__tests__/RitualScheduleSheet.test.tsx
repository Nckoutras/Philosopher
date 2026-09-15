// @vitest-environment jsdom
//
// Γ-6 — the schedule sheet's two doors.
//
// ONE FORM, TWO ENTRANCES, and these tests exist to keep it that way. The
// Rituals tab opens the sheet to choose a line; the chat chip opens it already
// bound to one. A second copy of this form for the second door would drift —
// same endpoint, same fields, two sets of validation — so the difference is two
// optional props, and what follows pins what each one changes and what it does
// not.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import RitualScheduleSheet from '../RitualScheduleSheet'

const createScheduledEmail = vi.fn()
const listSavedLines = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    createScheduledEmail: (...a: unknown[]) => createScheduledEmail(...a),
    listSavedLines: () => listSavedLines(),
    getPersonas: () => Promise.resolve([]),
  },
}))

const toastSuccess = vi.fn()
vi.mock('react-hot-toast', () => ({
  default: { success: (...a: unknown[]) => toastSuccess(...a), error: vi.fn() },
}))

const LINE = {
  id: 'line-1', message_id: 'm1', persona_id: 'p1', persona_slug: 'oscar_wilde',
  persona_display_name: 'Oscar Wilde', message_content: 'The line you kept.',
  conversation_id: 'c1', saved_at: '2026-09-01T00:00:00Z', source_type: 'manual_save',
}
const OTHER = { ...LINE, id: 'line-2', message_id: 'm2', message_content: 'A different line.' }

beforeEach(() => {
  createScheduledEmail.mockReset().mockResolvedValue({})
  listSavedLines.mockReset().mockResolvedValue({ items: [OTHER, LINE] })
  toastSuccess.mockReset()
})

describe('preset horizons', () => {
  it('renders the three founder-locked labels', () => {
    // Copy lock, 2026-09-15. Whole strings: these name the offer.
    render(<RitualScheduleSheet open onClose={vi.fn()} userEmail="a@b.c" />)
    expect(screen.getByText('In a week')).toBeTruthy()
    expect(screen.getByText('In a month')).toBeTruthy()
    expect(screen.getByText('In three months')).toBeTruthy()
  })

  it('a preset WRITES the date field rather than bypassing it', () => {
    // One source of truth for scheduled_for. If a preset submitted its own date
    // without filling the input, the person could not see or adjust what they
    // just chose — and the field and the payload could disagree.
    const { container } = render(<RitualScheduleSheet open onClose={vi.fn()} userEmail="a@b.c" />)
    const input = container.querySelector('input[type="datetime-local"]') as HTMLInputElement
    expect(input.value).toBe('')
    fireEvent.click(screen.getByText('In a week'))
    expect(input.value).not.toBe('')
    expect(screen.getByText('In a week').getAttribute('aria-pressed')).toBe('true')
  })

  it('the date picker survives — presets are a shortcut, not a replacement', () => {
    const { container } = render(<RitualScheduleSheet open onClose={vi.fn()} userEmail="a@b.c" />)
    expect(container.querySelector('input[type="datetime-local"]')).toBeTruthy()
  })

  it('a week is nearer than a month is nearer than three months', () => {
    // Ordering asserted from the rendered values, not from the constant, so a
    // relabelled preset that kept the old day count fails here.
    const { container } = render(<RitualScheduleSheet open onClose={vi.fn()} userEmail="a@b.c" />)
    const input = container.querySelector('input[type="datetime-local"]') as HTMLInputElement
    const at = (label: string) => {
      fireEvent.click(screen.getByText(label))
      return new Date(input.value).getTime()
    }
    expect(at('In a week')).toBeLessThan(at('In a month'))
    fireEvent.click(screen.getByText('In a month'))
    const month = new Date(input.value).getTime()
    expect(month).toBeLessThan(at('In three months'))
  })
})

describe('pre-bound door (Return to this)', () => {
  it('shows the bound line and no chooser', async () => {
    render(
      <RitualScheduleSheet open onClose={vi.fn()} userEmail="a@b.c" presetLineId="line-1" />,
    )
    await waitFor(() => expect(screen.getByText('The line you kept.')).toBeTruthy())
    // The other line must not be offered — the person already chose, in the chat.
    expect(screen.queryByText('A different line.')).toBeNull()
  })

  it('submits the BOUND line, not the newest one', async () => {
    // The regression this guards: the lazy load defaults the selection to
    // items[0], which is a DIFFERENT line and arrives a tick after open. Without
    // the guard, the appointment would silently be made against the wrong line.
    render(
      <RitualScheduleSheet open onClose={vi.fn()} userEmail="a@b.c" presetLineId="line-1" />,
    )
    await waitFor(() => expect(screen.getByText('The line you kept.')).toBeTruthy())
    fireEvent.click(screen.getByText('In a week'))
    fireEvent.click(screen.getByText('Schedule message'))
    await waitFor(() => expect(createScheduledEmail).toHaveBeenCalled())
    expect(createScheduledEmail.mock.calls[0][0].saved_line_id).toBe('line-1')
  })

  it('shows the founder-locked confirmation', async () => {
    render(
      <RitualScheduleSheet
        open onClose={vi.fn()} userEmail="a@b.c"
        presetLineId="line-1" confirmationText="Noted. It will return to you."
      />,
    )
    await waitFor(() => expect(screen.getByText('The line you kept.')).toBeTruthy())
    fireEvent.click(screen.getByText('In a month'))
    fireEvent.click(screen.getByText('Schedule message'))
    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith('Noted. It will return to you.'))
  })
})

describe('the Rituals door is unchanged', () => {
  it('still offers the picker and still states the date on success', async () => {
    // The whole point of two optional props: absent, this component behaves
    // exactly as it did before Γ-6. There the person set a date on a form and
    // the date IS the confirmation; the new copy would read as a non-sequitur.
    const { container } = render(<RitualScheduleSheet open onClose={vi.fn()} userEmail="a@b.c" />)
    await waitFor(() => expect(screen.getByText('A different line.')).toBeTruthy())
    fireEvent.click(screen.getByText('In a week'))
    fireEvent.click(screen.getByText('Schedule message'))
    await waitFor(() => expect(toastSuccess).toHaveBeenCalled())
    expect(toastSuccess.mock.calls[0][0]).toMatch(/^Message scheduled for /)
    expect(container).toBeTruthy()
  })
})
