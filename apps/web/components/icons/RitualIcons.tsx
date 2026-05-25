interface IconProps {
  size?: number
  strokeWidth?: number
  className?: string
}

/**
 * Returning Path — a near-complete circle with a small gap and a dot
 * marking the endpoint. Symbolizes the cyclical return of ritual practice.
 *
 * Path: starts at 12 o'clock (top), traces counterclockwise down the left,
 * around the bottom, up the right side, terminating at ~1 o'clock where
 * a small filled dot sits.
 */
export function ReturningPathIcon({ size = 20, strokeWidth = 1.5, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M 12 3 A 9 9 0 1 0 16.5 4.2" />
      <circle cx="16.5" cy="4.2" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  )
}

/**
 * Mirror — vertical oval mirror with a small shine reflection inside,
 * mounted on a short stand with a horizontal base.
 */
export function MirrorIcon({ size = 56, strokeWidth = 1.2, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {/* Oval mirror body */}
      <ellipse cx="12" cy="9" rx="5" ry="7" />
      {/* Shine reflection inside oval */}
      <line x1="11.5" y1="5.5" x2="9.5" y2="8.5" />
      {/* Vertical stand */}
      <line x1="12" y1="16" x2="12" y2="20" />
      {/* Horizontal base */}
      <line x1="9" y1="20.5" x2="15" y2="20.5" />
    </svg>
  )
}
