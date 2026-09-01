'use client'

interface Props {
  checked: boolean
  onChange: (next: boolean) => void
  /** Names what the switch controls, for screen readers. */
  label: string
}

/**
 * Minimal on/off switch. The first one in the app — there was no toggle,
 * checkbox or switch anywhere in components/ui before this.
 *
 * role="switch" + aria-checked rather than a styled <input type="checkbox">:
 * the control is a single tap target with two states and no form to submit,
 * and this keeps the whole thing inside the design tokens.
 */
export default function Switch({ checked, onChange, label }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative w-[44px] h-[26px] rounded-full transition-colors ${
        checked ? 'bg-ink' : 'bg-linen-deep'
      }`}
    >
      <span
        aria-hidden="true"
        className={`absolute top-[3px] w-[20px] h-[20px] rounded-full bg-paper shadow-card transition-[left] ${
          checked ? 'left-[21px]' : 'left-[3px]'
        }`}
      />
    </button>
  )
}
