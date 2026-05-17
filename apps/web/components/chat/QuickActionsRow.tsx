'use client'

import { useState } from 'react'
import { Zap, Users, Bookmark } from 'lucide-react'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import SaveLineInlineUpgrade from './SaveLineInlineUpgrade'

interface Props {
  messageId: string
  saved: boolean
  onSave: () => void
  onUpgradeConfirm: () => void
}

export default function QuickActionsRow({ messageId: _messageId, saved, onSave, onUpgradeConfirm }: Props) {
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
    if (saved) return
    const isAtLimit = plan === 'free' && freeTierLimit !== null && freeSaveCount >= freeTierLimit
    if (isAtLimit) {
      setShowUpgrade(true)
      return
    }
    onSave()
  }

  const chipBase =
    'bg-paper text-ink border border-[0.5px] border-edge px-[10px] py-[6px] font-lora text-[11px] rounded-sm inline-flex items-center gap-[5px] transition-colors'
  const chipSaved =
    'bg-linen-deep text-ink border border-ink font-medium px-[10px] py-[6px] font-lora text-[11px] rounded-sm inline-flex items-center gap-[5px]'

  return (
    <div className="flex gap-[6px] flex-wrap ml-[32px] mt-[4px]">
      <button
        type="button"
        onClick={() => toast('Coming soon', { duration: 2000 })}
        className={chipBase}
        aria-label="Ask harder"
      >
        <Zap size={11} strokeWidth={1.5} />
        <span className="hidden min-[360px]:inline">Ask harder</span>
      </button>
      <button
        type="button"
        onClick={() => toast('Coming soon', { duration: 2000 })}
        className={chipBase}
        aria-label="Bring another mind"
      >
        <Users size={11} strokeWidth={1.5} />
        <span className="hidden min-[360px]:inline">Bring another mind</span>
      </button>
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
    </div>
  )
}
