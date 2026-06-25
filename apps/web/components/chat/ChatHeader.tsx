interface Props {
  personaName: string
  portraitUrl: string
  // Sticky guest: when an active guest overrides the origin, show a quiet
  // "Return to [origin]" affordance. originName is the immutable home persona.
  originName?: string | null
  isGuestActive?: boolean
  onReturnToOrigin?: () => void
  // Pro sticky deep mode: a quiet toggle, rendered only for Pro users. When on,
  // every reply is deep until turned off.
  showDeepMode?: boolean
  deepMode?: boolean
  onToggleDeepMode?: () => void
}

export default function ChatHeader({
  personaName,
  portraitUrl,
  originName = null,
  isGuestActive = false,
  onReturnToOrigin,
  showDeepMode = false,
  deepMode = false,
  onToggleDeepMode,
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
      </div>
      {showDeepMode && onToggleDeepMode && (
        <button
          type="button"
          onClick={onToggleDeepMode}
          aria-pressed={deepMode}
          aria-label={deepMode ? 'Deep mode on — tap to turn off' : 'Deep mode off — tap to turn on'}
          className={`ml-auto flex-shrink-0 inline-flex items-center gap-[6px] rounded-full border-[0.5px] px-[10px] py-[5px] font-lora text-[12px] transition-colors ${
            deepMode
              ? 'border-bronze bg-bronze/10 text-bronze-dark'
              : 'border-edge text-sepia'
          }`}
        >
          <span
            aria-hidden="true"
            className={`w-[7px] h-[7px] rounded-full ${deepMode ? 'bg-bronze' : 'bg-edge'}`}
          />
          Deep mode
        </button>
      )}
    </header>
  )
}
