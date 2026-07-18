'use client'

import { useState } from 'react'
import { Users, Bookmark, Sparkle, ArrowRight, Landmark, Swords, GitCompareArrows, Send, X, Lock, type LucideIcon } from 'lucide-react'
import { useStore } from '@/lib/store'
import SaveLineInlineUpgrade from './SaveLineInlineUpgrade'

// Named one-tap ritual door chip (D1a). Each known insight type maps to the ritual
// its existing door routes to (see useInsightDoors.primary); the chip label + icon
// name that ritual so a single tap goes straight in. Null/unknown types get NO
// chip — the old generic "Insight" fallback is gone.
const INSIGHT_DOOR: Record<string, { label: string; Icon: LucideIcon }> = {
  dilemma: { label: 'Bring it to the Council', Icon: Landmark },
  belief: { label: 'Put it to the test', Icon: Swords },
  aspiration: { label: 'Write to your future self', Icon: Send },
  shift: { label: 'Then and now', Icon: GitCompareArrows },
  pattern: { label: 'Reflect in the Mirror', Icon: Sparkle },
}

// Strong bronze glow so the door chip stands clearly apart from the utility chips.
// Single tunable knob — premium, not neon; will be tuned on a real device.
const DOOR_GLOW = 'shadow-[0_0_16px_rgba(184,153,104,0.8)]'

interface Props {
  messageId: string
  saved: boolean
  onSave: () => void
  onUpgradeConfirm: () => void
  onBringAnotherMind: () => void
  // Deep-mode chip: a conversation-level toggle rendered ONLY on the last
  // assistant message (showDeepChip), mirroring the insight/council last-message
  // gate. Three states: locked (free + exhausted) → paywall; on (filled bronze)
  // → turn off; off (normal chip) → turn on.
  showDeepChip?: boolean
  deepMode?: boolean
  deepLocked?: boolean
  onToggleDeepMode?: () => void
  onDeepPaywall?: () => void
  // Named door chip: the insight type drives label/icon/route. Only the four known
  // types render a chip. onInsightDoor routes via the existing door; onInsightDismiss
  // is the 5s-undo dismiss.
  insightType?: string | null
  onInsightDoor?: () => void
  onInsightDismiss?: () => void
  showCouncilChip?: boolean
  onTakeToCouncil?: () => void
  // Sticky guest: shown only on a brought-in message whose guest is not already
  // the active mind. Tapping makes that guest the active mind for next turns.
  continueWithName?: string | null
  onContinueWith?: () => void
}

export default function QuickActionsRow({ messageId: _messageId, saved, onSave, onUpgradeConfirm, onBringAnotherMind, showDeepChip = false, deepMode = false, deepLocked = false, onToggleDeepMode, onDeepPaywall, insightType = null, onInsightDoor, onInsightDismiss, showCouncilChip = false, onTakeToCouncil, continueWithName = null, onContinueWith }: Props) {
  const [showUpgrade, setShowUpgrade] = useState(false)
  const freeSaveCount = useStore((s) => s.freeSaveCount)
  const freeTierLimit = useStore((s) => s.freeTierLimit)
  const plan = useStore((s) => s.plan)

  if (showUpgrade) {
    return (
      <SaveLineInlineUpgrade
        onUpgrade={() => {
          onUpgradeConfirm()
          setShowUpgrade(false)
        }}
        onDismiss={() => setShowUpgrade(false)}
      />
    )
  }

  function handleSaveTap() {
    if (!saved) {
      const isAtLimit = plan === 'free' && freeTierLimit !== null && freeSaveCount >= freeTierLimit
      if (isAtLimit) {
        setShowUpgrade(true)
        return
      }
    }
    onSave()
  }

  const chipBase =
    'bg-paper text-ink border border-[0.5px] border-edge px-[10px] py-[6px] font-lora text-[13px] rounded-sm inline-flex items-center gap-[5px] transition-colors'
  const chipSaved =
    'bg-linen-deep text-ink border border-ink font-medium px-[10px] py-[6px] font-lora text-[13px] rounded-sm inline-flex items-center gap-[5px]'

  // Resolve the door for this message's insight type (undefined for null/unknown).
  const door = insightType ? INSIGHT_DOOR[insightType] : undefined
  const DoorIcon = door?.Icon

  return (
    <div className="flex gap-[6px] flex-wrap ml-[32px] mt-[4px]">
      {/* Deep-mode toggle — last assistant message only. Locked state (free tier
          exhausted) takes precedence over the on-state: even if the flag is on,
          an out-of-quota free user sees the Pro lock. */}
      {showDeepChip && (
        deepLocked ? (
          <button
            type="button"
            onClick={onDeepPaywall}
            className={chipBase}
            aria-label="Deep mode — Pro"
          >
            <Lock size={11} strokeWidth={1.5} />
            <span className="hidden min-[360px]:inline">Deep mode — Pro</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={onToggleDeepMode}
            aria-pressed={deepMode}
            aria-label={deepMode ? 'Deep mode on — tap to turn off' : 'Deep mode off — tap to turn on'}
            className={
              deepMode
                ? 'bg-bronze text-vellum border-[0.5px] border-bronze px-[10px] py-[6px] font-lora text-[13px] rounded-sm inline-flex items-center gap-[5px] transition-colors'
                : chipBase
            }
          >
            <span
              aria-hidden="true"
              className={`w-[7px] h-[7px] rounded-full ${deepMode ? 'bg-vellum' : 'bg-edge'}`}
            />
            <span className="hidden min-[360px]:inline">Deep mode</span>
          </button>
        )
      )}
      <button
        type="button"
        onClick={onBringAnotherMind}
        className={chipBase}
        aria-label="Bring another mind"
      >
        <Users size={11} strokeWidth={1.5} />
        <span className="hidden min-[360px]:inline">Bring another mind</span>
      </button>
      {/* A dilemma door IS a Council door — suppress the always-on Council chip so
          the message shows only one Council entry. Other types leave it unchanged. */}
      {showCouncilChip && onTakeToCouncil && insightType !== 'dilemma' && (
        <button
          type="button"
          onClick={onTakeToCouncil}
          className={chipBase}
          aria-label="Ask the Council"
        >
          <Landmark size={11} strokeWidth={1.5} />
          <span className="hidden min-[360px]:inline">Ask the Council</span>
        </button>
      )}
      <button
        type="button"
        onClick={handleSaveTap}
        className={saved ? chipSaved : chipBase}
        aria-label={saved ? 'Saved' : 'Save line'}
        aria-pressed={saved}
      >
        <Bookmark
          size={11}
          strokeWidth={1.5}
          fill={saved ? 'var(--ink)' : 'none'}
        />
        <span className="hidden min-[360px]:inline">{saved ? 'Saved' : 'Save line'}</span>
      </button>
      {/* Named one-tap ritual door. Body → straight into the ritual (existing door);
          the trailing × is the 5s-undo dismiss. One chip, two tap targets. */}
      {door && DoorIcon && (
        <div className={`bg-paper text-ink border-[0.5px] border-bronze rounded-sm inline-flex items-center ${DOOR_GLOW}`}>
          <button
            type="button"
            onClick={onInsightDoor}
            className="pl-[10px] pr-[6px] py-[6px] font-lora text-[13px] inline-flex items-center gap-[5px]"
            aria-label={door.label}
          >
            <DoorIcon size={11} strokeWidth={1.5} className="text-bronze" />
            <span>{door.label}</span>
          </button>
          <button
            type="button"
            onClick={onInsightDismiss}
            className="pr-[8px] pl-[4px] py-[6px] min-w-[24px] min-h-[24px] inline-flex items-center justify-center text-sepia"
            aria-label="Dismiss insight"
          >
            <X size={12} strokeWidth={1.5} />
          </button>
        </div>
      )}
      {continueWithName && onContinueWith && (
        <button
          type="button"
          onClick={onContinueWith}
          className={chipBase}
          aria-label={`Continue with ${continueWithName}`}
        >
          <ArrowRight size={11} strokeWidth={1.5} />
          <span>Continue with {continueWithName}</span>
        </button>
      )}
    </div>
  )
}
