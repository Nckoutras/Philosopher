'use client'

import { useState } from 'react'
import { Zap, Users, Bookmark, Sparkle, ArrowRight, Landmark } from 'lucide-react'
import { useStore } from '@/lib/store'
import SaveLineInlineUpgrade from './SaveLineInlineUpgrade'

interface Props {
  messageId: string
  saved: boolean
  onSave: () => void
  onUpgradeConfirm: () => void
  onBringAnotherMind: () => void
  onGoDeeper: () => void
  showInsightChip?: boolean
  onInsightTap?: () => void
  showCouncilChip?: boolean
  onTakeToCouncil?: () => void
  // Sticky guest: shown only on a brought-in message whose guest is not already
  // the active mind. Tapping makes that guest the active mind for next turns.
  continueWithName?: string | null
  onContinueWith?: () => void
}

export default function QuickActionsRow({ messageId: _messageId, saved, onSave, onUpgradeConfirm, onBringAnotherMind, onGoDeeper, showInsightChip = false, onInsightTap, showCouncilChip = false, onTakeToCouncil, continueWithName = null, onContinueWith }: Props) {
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

  return (
    <div className="flex gap-[6px] flex-wrap ml-[32px] mt-[4px]">
      <button
        type="button"
        onClick={onGoDeeper}
        className={chipBase}
        aria-label="Go deeper"
      >
        <Zap size={11} strokeWidth={1.5} />
        <span className="hidden min-[360px]:inline">Go deeper</span>
      </button>
      <button
        type="button"
        onClick={onBringAnotherMind}
        className={chipBase}
        aria-label="Bring another mind"
      >
        <Users size={11} strokeWidth={1.5} />
        <span className="hidden min-[360px]:inline">Bring another mind</span>
      </button>
      {showCouncilChip && onTakeToCouncil && (
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
      {showInsightChip && (
        <button
          type="button"
          onClick={onInsightTap}
          className="bg-paper text-ink border-[0.5px] border-bronze px-[10px] py-[6px] font-lora text-[13px] rounded-sm inline-flex items-center gap-[5px] shadow-[0_0_8px_rgba(184,153,104,0.45)]"
          aria-label="View insight"
        >
          <Sparkle size={11} strokeWidth={1.5} className="text-bronze" />
          <span>Insight</span>
        </button>
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
