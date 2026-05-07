/**
 * Spinner per DESIGN_SYSTEM_v4 A1 spec.
 * Edge ring (0.8px stroke) + Ink rotating arc (1.2px stroke), 1.4s rotation.
 * Used in: A1 splash, C1 chat sending state, H2 checkout loading bridge.
 */
type SpinnerProps = {
  /** Diameter in pixels. Default 32. */
  size?: number
  /** Optional className for positioning. */
  className?: string
}

export function Spinner({ size = 32, className = '' }: SpinnerProps) {
  const center = size / 2
  const radius = (size - 4) / 2
  const circumference = 2 * Math.PI * radius
  const arcLength = circumference * 0.25

  return (
    <svg
      role="status"
      aria-label="Loading"
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={`animate-spin-slow ${className}`}
    >
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="#D4C8B0"
        strokeWidth="0.8"
      />
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="#1F1B14"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeDasharray={`${arcLength} ${circumference}`}
        transform={`rotate(-90 ${center} ${center})`}
      />
    </svg>
  )
}

export default Spinner
