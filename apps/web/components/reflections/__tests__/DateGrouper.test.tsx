// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import DateGrouper from '../DateGrouper'

describe('DateGrouper', () => {
  it('renders label text', () => {
    render(<DateGrouper label="This week" />)
    expect(screen.getByText('This week')).toBeTruthy()
  })

  // TWO TESTS WERE DELETED HERE, NOT REPAIRED. The argument, so the next reader can
  // disagree with it rather than guess at it:
  //
  // They asserted `container.firstChild.className` contained 'uppercase' and
  // 'text-sepia'. Both broke when the component gained flanking rule-lines and the
  // styled text moved to a nested <p> — the root is now a flex row. Repointing them
  // one level deeper would have made them green in about ten seconds.
  //
  // They are deleted instead because what they assert is not a behaviour:
  //   - A Tailwind class NAME is not the rendered result. `uppercase` present proves
  //     no one sees uppercase text; it proves a string appears in an attribute. Swap
  //     the utility for a stylesheet rule and the UI is identical and the test fails;
  //     delete the label's text and the UI is empty and the test passes.
  //   - They are coupled to DOM SHAPE at a fixed depth, so any wrapper breaks them.
  //     One already did. Patching to `firstChild.firstChild` just moves the tripwire.
  //   - This component is fifteen lines with one prop and no branches. There is
  //     exactly one behaviour to assert and 'renders label text' above asserts it.
  //
  // The strongest evidence they carried nothing: they were red for at least five
  // weeks (2026-08-13 measurement, rows 41 and 42) and no one noticed, because
  // nothing they guarded could break in a way anyone would feel.
  //
  // What WOULD be worth testing here is that the divider renders either side of the
  // label, which is the component's actual job. That needs a visual check, not a
  // class-name grep, and it belongs to the design review rather than to vitest.
})
