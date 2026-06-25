import { Scale } from 'lucide-react'

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
  // Take to the Council: visible to EVERYONE (upsell surface). Disabled until
  // there is something to send (a user message). Tap routing is the caller's
  // job: Pro → seeded Council; free → upgrade wall.
  onTakeToCouncil?: () => void
  councilEnabled?: boolean
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
  onTakeToCouncil,
  councilEnabled = false,
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
      <div className="ml-auto flex items-center gap-[8px] flex-shrink-0">
        {onTakeToCouncil && (
          <button
            type="button"
            onClick={onTakeToCouncil}
            disabled={!councilEnabled}
            aria-label="Take this to the Council"
            className="min-h-[36px] min-w-[36px] flex items-center justify-center rounded-full text-sepia active:opacity-50 disabled:opacity-30"
          >
            <Scale size={18} strokeWidth={1.5} />
          </button>
        )}
        {showDeepMode && onToggleDeepMode && (
          <button
            type="button"
            onClick={onToggleDeepMode}
            aria-pressed={deepMode}
            aria-label={deepMode ? 'Deep mode on — tap to turn off' : 'Deep mode off — tap to turn on'}
            className={`inline-flex items-center gap-[6px] rounded-full border-[0.5px] px-[10px] py-[5px] font-lora text-[12px] transition-colors ${
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
      </div>
    </header>
  )
}
