export default function WiseMark({
  size = 28,
  className = '',
}: {
  size?: number
  className?: string
}) {
  return (
    <span
      className={`inline-flex items-center justify-center flex-shrink-0 rounded-full bg-bronze ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <span
        className="font-cormorant font-medium text-vellum leading-none"
        style={{ fontSize: Math.round(size * 0.5) }}
      >
        W
      </span>
    </span>
  )
}
