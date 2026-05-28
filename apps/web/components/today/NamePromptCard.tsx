'use client'

import { useState } from 'react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'

interface Props {
  onDismiss: () => void
}

export default function NamePromptCard({ onDismiss }: Props) {
  const setUser = useStore((s) => s.setUser)
  const [value, setValue] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [leaving, setLeaving] = useState(false)

  const trimmed = value.trim()
  const canSave = trimmed.length > 0 && !saving

  async function handleSave() {
    if (!canSave) return
    setSaving(true)
    setError(null)
    try {
      const updated = await api.updateMe(trimmed)
      setUser(updated)
      setLeaving(true)
    } catch {
      setError('Something went wrong. Try again.')
      setSaving(false)
    }
  }

  function handleNotNow() {
    setLeaving(true)
  }

  return (
    <div
      style={{
        maxHeight: leaving ? 0 : 999,
        opacity: leaving ? 0 : 1,
        overflow: 'hidden',
        transition: 'max-height 350ms ease, opacity 250ms ease',
      }}
      onTransitionEnd={(e) => {
        if (e.propertyName === 'max-height') onDismiss()
      }}
    >
      <div className="bg-paper border border-[0.5px] border-edge rounded-sm shadow-card px-[16px] py-[16px]">
        <p className="font-cormorant text-[19px] font-normal text-ink leading-snug mb-[12px]">
          What should we call you?
        </p>
        <input
          type="text"
          placeholder="First name"
          value={value}
          onChange={(e) => setValue(e.target.value.slice(0, 100))}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSave() }}
          disabled={saving}
          maxLength={100}
          className="w-full bg-white border border-ink rounded-sm px-[12px] py-[10px] font-lora text-[15px] text-ink placeholder:text-sepia/60 focus:outline-none disabled:opacity-50 mb-[10px]"
        />
        {error && (
          <p className="font-lora text-[12px] text-sepia mb-[8px]">{error}</p>
        )}
        <div className="flex items-center gap-[16px]">
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave}
            className="px-[20px] py-[10px] rounded-sm bg-ink text-vellum font-cormorant text-[16px] font-medium disabled:opacity-40 transition-opacity"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
          <button
            type="button"
            onClick={handleNotNow}
            disabled={saving}
            className="font-lora text-[13px] text-sepia"
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  )
}
