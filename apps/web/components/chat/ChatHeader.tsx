interface Props {
  personaName: string
  portraitUrl: string
  // Sticky guest: when an active guest overrides the origin, show a quiet
  // "Return to [origin]" affordance. originName is the immutable home persona.
  originName?: string | null
  isGuestActive?: boolean
  onReturnToOrigin?: () => void
  // Γ-3 escape hatch. Rendered only when this thread was RESUMED — a person who
  // wanted a clean start would otherwise have no way to get one, which is worse
  // than the old always-new behaviour. Founder-locked copy: "Start fresh".
  onStartFresh?: () => void
}

export default function ChatHeader({
  personaName,
  portraitUrl,
  originName = null,
  isGuestActive = false,
  onReturnToOrigin,
  onStartFresh,
}: Props) {
  return (
    <header className="sticky top-0 z-10 flex items-center gap-3 px-4 py-3 bg-vellum border-b border-edge">
      <div className="w-11 h-11 rounded-full overflow-hidden flex-shrink-0 bg-linen">
        {portraitUrl && (
          <img
            src={portraitUrl}
            alt={personaName}
            className="w-full h-full object-cover object-top"
          />
        )}
      </div>
      <div className="flex flex-col min-w-0">
        <h1 className="font-cormorant text-[20px] text-ink font-medium leading-tight">
          {personaName}
        </h1>
        {isGuestActive && originName && onReturnToOrigin && (
          <button
            type="button"
            onClick={onReturnToOrigin}
            className="font-lora text-[12px] text-sepia text-left leading-tight mt-[1px]"
            aria-label={`Return to ${originName}`}
          >
            ← Return to {originName}
          </button>
        )}
        {onStartFresh && (
          <button
            type="button"
            onClick={onStartFresh}
            className="font-lora text-[12px] text-sepia text-left leading-tight mt-[1px]"
          >
            Start fresh
          </button>
        )}
      </div>
    </header>
  )
}
