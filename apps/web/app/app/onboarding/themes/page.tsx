'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

// Canonical lowercase slugs (match backend Pydantic enum)
const THEME_OPTIONS: { slug: string; label: string }[] = [
  { slug: 'separation', label: 'Separation' },
  { slug: 'anxiety', label: 'Anxiety' },
  { slug: 'fear', label: 'Fear' },
  { slug: 'grief', label: 'Grief' },
  { slug: 'acceptance', label: 'Acceptance' },
  { slug: 'work', label: 'Work' },
  { slug: 'relationships', label: 'Relationships' },
  { slug: 'purpose', label: 'Purpose' },
]

const MAX_OTHER_LENGTH = 500

export default function ThemesPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [selected, setSelected] = useState<string[]>([])
  const [otherText, setOtherText] = useState('')

  useEffect(() => {
    if (token === null) router.replace('/auth')
  }, [token, router])

  // Restore draft from sessionStorage if user navigated back
  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      const draft = sessionStorage.getItem('onboarding_themes')
      if (draft) setSelected(JSON.parse(draft))
      const draftOther = sessionStorage.getItem('onboarding_other_text')
      if (draftOther) setOtherText(draftOther)
    } catch {
      // ignore parse errors
    }
  }, [])

  const toggleTheme = (slug: string) => {
    setSelected((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]
    )
  }

  const trimmedOther = otherText.trim()
  const hasSignal = selected.length > 0 || trimmedOther.length > 0

  const handleContinue = () => {
    if (!hasSignal) return
    sessionStorage.setItem('onboarding_themes', JSON.stringify(selected))
    sessionStorage.setItem('onboarding_other_text', trimmedOther)
    router.push('/app/onboarding/need')
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <div className="flex-1 flex flex-col justify-center px-7 py-8">
        <div className="w-full max-w-[380px] mx-auto space-y-7">

          {/* Ornament */}
          <div className="flex justify-center">
            <BronzeDivider width={80} />
          </div>

          {/* Hero */}
          <header className="space-y-3 text-center">
            <h1 className="font-cormorant text-[26px] font-normal text-ink leading-tight">
              What brings you here?
            </h1>
            <p className="font-lora text-[13px] text-charcoal leading-[1.65]">
              Choose what speaks to you. You can pick more than one.
            </p>
          </header>

          {/* Chips */}
          <div className="flex flex-wrap gap-2 justify-center">
            {THEME_OPTIONS.map(({ slug, label }) => {
              const isSelected = selected.includes(slug)
              return (
                <button
                  key={slug}
                  type="button"
                  onClick={() => toggleTheme(slug)}
                  aria-pressed={isSelected}
                  className={`px-4 py-2 rounded-full font-lora text-[13px] border-[0.5px] transition-colors ${
                    isSelected
                      ? 'bg-linen-deep border-ink text-ink'
                      : 'bg-linen border-edge text-charcoal'
                  }`}
                >
                  {label}
                </button>
              )
            })}
          </div>

          {/* Other textarea */}
          <div className="space-y-2">
            <label className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
              Or describe in your own words
            </label>
            <textarea
              value={otherText}
              onChange={(e) => setOtherText(e.target.value.slice(0, MAX_OTHER_LENGTH))}
              placeholder="Something else…"
              rows={3}
              maxLength={MAX_OTHER_LENGTH}
              className="w-full bg-white border-[0.5px] border-edge rounded-md px-4 py-3 font-lora text-[14px] text-ink placeholder:text-sepia resize-none focus:outline-none focus:border-ink transition-colors"
            />
            <p className="font-lora text-[11px] text-sepia text-right">
              {otherText.length} / {MAX_OTHER_LENGTH}
            </p>
          </div>

          {/* Continue */}
          <button
            type="button"
            disabled={!hasSignal}
            onClick={handleContinue}
            className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum disabled:bg-linen disabled:text-charcoal transition-colors"
          >
            Continue
          </button>

        </div>
      </div>
    </main>
  )
}
