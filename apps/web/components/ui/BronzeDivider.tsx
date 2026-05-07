/**
 * Bronze divider per DESIGN_SYSTEM_v4 §7.3 ornament inventory.
 * Structure: 1px Bronze line + 9×9 lozenge (rotated 45°) + 1px Bronze line.
 * Used in: A1 splash, B1 welcome, A6+A7 disclaimer, F4 weekly letter.
 */
type BronzeDividerProps = {
  /** Total width in pixels. Default 80. */
  width?: number
  /** Optional className for layout positioning (margin, alignment). */
  className?: string
}

export function BronzeDivider({ width = 80, className = '' }: BronzeDividerProps) {
  return (
    <div
      role="presentation"
      aria-hidden="true"
      className={`inline-flex items-center justify-center gap-1 ${className}`}
      style={{ width: `${width}px` }}
    >
      <span className="flex-1 bg-bronze" style={{ height: '1px' }} />
      <span
        className="block bg-bronze"
        style={{
          width: '9px',
          height: '9px',
          transform: 'rotate(45deg)',
        }}
      />
      <span className="flex-1 bg-bronze" style={{ height: '1px' }} />
    </div>
  )
}

export default BronzeDivider
