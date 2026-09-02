// @vitest-environment jsdom
//
// The typed-confirmation gate, and the guarantee that adding it changed nothing
// for the callers that do not use it.
//
// WHY THIS MATTERS. This modal is shared: conversation delete, letter delete and
// now account deletion. Account deletion is the only irreversible one, so it is
// the only one that asks the user to type a word. If the gate leaked into the
// other callers it would train people to type through the prompt, and the
// friction would stop meaning anything on the one screen where it must.
//
// The comparison is case-sensitive on purpose. Every softening — trim(),
// toLowerCase() — moves the gate back toward something a stray paste or an
// autocapitalising keyboard satisfies by accident.
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import DeleteConfirmModal from '../DeleteConfirmModal'

function setup(props: Partial<React.ComponentProps<typeof DeleteConfirmModal>> = {}) {
  const onConfirm = vi.fn()
  const onClose = vi.fn()
  const utils = render(
    <DeleteConfirmModal
      open
      title="Title"
      body="Body"
      loading={false}
      error={null}
      onConfirm={onConfirm}
      onClose={onClose}
      {...props}
    />,
  )
  return { onConfirm, onClose, ...utils }
}

// Plain DOM assertions: this project does not install @testing-library/jest-dom,
// so .disabled / .value are read directly rather than through custom matchers.
const confirmButton = () =>
  screen.getByRole('button', { name: /delete/i }) as HTMLButtonElement
const textbox = () => screen.getByRole('textbox') as HTMLInputElement

describe('DeleteConfirmModal — without typed confirmation', () => {
  it('confirms immediately, exactly as before this prop existed', () => {
    const { onConfirm } = setup()
    expect(confirmButton().disabled).toBe(false)
    fireEvent.click(confirmButton())
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('renders no input at all', () => {
    setup()
    expect(screen.queryByRole('textbox')).toBeNull()
  })
})

describe('DeleteConfirmModal — with typed confirmation', () => {
  const typed = { requireTypedConfirmation: 'DELETE', typedConfirmationLabel: 'Type DELETE' }

  it('starts disabled and does not fire on click', () => {
    const { onConfirm } = setup(typed)
    expect(confirmButton().disabled).toBe(true)
    fireEvent.click(confirmButton())
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('stays disabled for a partial match', () => {
    setup(typed)
    fireEvent.change(textbox(), { target: { value: 'DELET' } })
    expect(confirmButton().disabled).toBe(true)
  })

  it('stays disabled for the wrong case', () => {
    setup(typed)
    fireEvent.change(textbox(), { target: { value: 'delete' } })
    expect(confirmButton().disabled).toBe(true)
  })

  it('stays disabled for surrounding whitespace', () => {
    setup(typed)
    fireEvent.change(textbox(), { target: { value: ' DELETE ' } })
    expect(confirmButton().disabled).toBe(true)
  })

  it('enables on an exact match and then confirms', () => {
    const { onConfirm } = setup(typed)
    fireEvent.change(textbox(), { target: { value: 'DELETE' } })
    expect(confirmButton().disabled).toBe(false)
    fireEvent.click(confirmButton())
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('re-disables if the user edits the text back to something wrong', () => {
    setup(typed)
    const input = textbox()
    fireEvent.change(input, { target: { value: 'DELETE' } })
    expect(confirmButton().disabled).toBe(false)
    fireEvent.change(input, { target: { value: 'DELETX' } })
    expect(confirmButton().disabled).toBe(true)
  })

  it('clears the typed text when the modal closes', () => {
    // A cancelled deletion that is reopened must not present an
    // already-satisfied confirmation.
    const { rerender } = setup(typed)
    fireEvent.change(textbox(), { target: { value: 'DELETE' } })

    rerender(
      <DeleteConfirmModal
        open={false}
        title="Title"
        body="Body"
        loading={false}
        error={null}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
        {...typed}
      />,
    )
    rerender(
      <DeleteConfirmModal
        open
        title="Title"
        body="Body"
        loading={false}
        error={null}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
        {...typed}
      />,
    )

    expect(textbox().value).toBe('')
    expect(confirmButton().disabled).toBe(true)
  })

  it('renders the label', () => {
    setup(typed)
    expect(screen.getByLabelText('Type DELETE')).toBeTruthy()
  })
})
