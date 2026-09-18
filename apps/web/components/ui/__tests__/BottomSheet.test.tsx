// @vitest-environment jsdom
//
// BUG-017. The register called this a "mobile dead end"; it is not. Escape already
// closed the sheet and the scrim already dismissed on tap, both before this change.
// The three real defects were DISCOVERABILITY (no visible control at all in three of
// the five consumers), no FOCUS TRAP, and no FOCUS RETURN.
//
// WHAT THIS FILE CAN AND CANNOT CHECK. jsdom does not move focus on a Tab keypress —
// no browser layout, no tab order — and @testing-library/user-event, which simulates
// it, is not a dependency of this app. So the native traversal BETWEEN the boundaries
// is not asserted here; it is the browser's, and it is checked on the preview deploy.
//
// What IS ours and is asserted here: the sheet puts focus inside itself on open, our
// keydown handler wraps Tab at both boundaries and pulls stray focus back in, Escape
// closes, and focus returns to the opener on close. Every one of those is code in
// BottomSheet.tsx that runs in jsdom, so every one of them can fail here.
//
// Note there was no test for the two older traps (DeleteConfirmModal,
// SharePreviewModal) to copy — see TD-84. This is the first.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import BottomSheet from '../BottomSheet'

// A sheet plus the button that opened it, which is what focus return needs: the
// opener has to be a real focused element OUTSIDE the panel before `open` flips.
function Harness({ open, onClose = () => {} }: { open: boolean; onClose?: () => void }) {
  return (
    <>
      <button type="button" data-testid="opener">
        Open the sheet
      </button>
      <BottomSheet open={open} onClose={onClose}>
        <button type="button">Alpha</button>
        <button type="button">Omega</button>
      </BottomSheet>
    </>
  )
}

const closeControl = () => screen.getByRole('button', { name: 'Close' })
const opener = () => screen.getByTestId('opener')

beforeEach(() => {
  vi.clearAllMocks()
})

describe('BottomSheet — the visible close control', () => {
  it('renders one, and only one, for a consumer that provides none of its own', () => {
    render(<Harness open />)
    // Exactly one: the point of moving it into the sheet was that two consumers had
    // hand-rolled their own, and a sheet that renders its own on top of those would
    // have shipped two × buttons side by side.
    expect(screen.getAllByLabelText('Close')).toHaveLength(1)
  })

  it('calls onClose when it is clicked', () => {
    const onClose = vi.fn()
    render(<Harness open onClose={onClose} />)

    fireEvent.click(closeControl())
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('sits before the consumer content, so it cannot overlay a header-less panel', () => {
    render(<Harness open />)
    const panel = screen.getByRole('dialog')
    const focusables = Array.from(panel.querySelectorAll('button'))
    // quotes/page.tsx opens straight into 26px Cormorant text with no header of its
    // own. The control clears that content by being a ROW ahead of it in the flow
    // rather than a corner overlay, and "ahead of it" is what this asserts.
    expect(focusables[0]).toBe(closeControl())
  })
})

describe('BottomSheet — Escape', () => {
  it('closes on Escape', () => {
    const onClose = vi.fn()
    render(<Harness open onClose={onClose} />)

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does nothing on Escape once closed', () => {
    const onClose = vi.fn()
    render(<Harness open={false} onClose={onClose} />)

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
  })
})

describe('BottomSheet — the focus trap', () => {
  it('moves focus into the sheet when it opens', () => {
    const { rerender } = render(<Harness open={false} />)
    opener().focus()
    expect(document.activeElement).toBe(opener())

    rerender(<Harness open />)
    expect(document.activeElement).toBe(closeControl())
  })

  it('wraps forward: Tab on the last focusable returns to the first', () => {
    render(<Harness open />)
    const omega = screen.getByRole('button', { name: 'Omega' })
    omega.focus()

    fireEvent.keyDown(window, { key: 'Tab' })
    expect(document.activeElement).toBe(closeControl())
  })

  it('wraps backward: Shift+Tab on the first focusable returns to the last', () => {
    render(<Harness open />)
    closeControl().focus()

    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Omega' }))
  })

  it('pulls focus back in when it has escaped the panel', () => {
    render(<Harness open />)
    // The realistic route out: a tap on the page behind the scrim. The two older
    // traps in this codebase only wrap at the boundaries, so focus that is already
    // outside keeps tabbing through the document under an aria-modal dialog.
    opener().focus()
    expect(document.activeElement).toBe(opener())

    fireEvent.keyDown(window, { key: 'Tab' })
    expect(document.activeElement).toBe(closeControl())
  })

  it('leaves keys other than Tab and Escape alone', () => {
    const onClose = vi.fn()
    render(<Harness open onClose={onClose} />)
    const omega = screen.getByRole('button', { name: 'Omega' })
    omega.focus()

    fireEvent.keyDown(window, { key: 'a' })
    expect(document.activeElement).toBe(omega)
    expect(onClose).not.toHaveBeenCalled()
  })
})

describe('BottomSheet — focus return', () => {
  it('hands focus back to the element that opened it', () => {
    const { rerender } = render(<Harness open={false} />)
    opener().focus()

    rerender(<Harness open />)
    expect(document.activeElement).toBe(closeControl())

    rerender(<Harness open={false} />)
    expect(document.activeElement).toBe(opener())
  })

  it('does not throw when the opener is gone by the time the sheet closes', () => {
    // A sheet opened from a row that the sheet's own action then deleted. Focusing a
    // detached node does not raise — it silently drops focus to <body> — so the guard
    // is on isConnected, and this asserts the unmount path does not explode.
    function Vanishing({ open, keepOpener }: { open: boolean; keepOpener: boolean }) {
      return (
        <>
          {keepOpener && (
            <button type="button" data-testid="opener">
              Open the sheet
            </button>
          )}
          <BottomSheet open={open} onClose={() => {}}>
            <button type="button">Alpha</button>
          </BottomSheet>
        </>
      )
    }

    const { rerender } = render(<Vanishing open={false} keepOpener />)
    opener().focus()
    rerender(<Vanishing open keepOpener />)

    expect(() => rerender(<Vanishing open={false} keepOpener={false} />)).not.toThrow()
  })
})
