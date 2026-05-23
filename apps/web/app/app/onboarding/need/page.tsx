'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

const NEED_OPTIONS: {
  slug: 'comfort' | 'challenge' | 'interpretation' | 'practical_steadiness'
  label: string
  subtitle: string
}[] = [
  {
    slug: 'comfort',
    label: 'Comfort',
    subtitle: 'Soothing words. A philosopher who holds space.',
  },
  {
    slug: 'challenge',
    label: 'Challenge',
    subtitle: 'Confront me. Push my thinking.',
  },
  {
    slug: 'interpretation',
    label: 'Interpretation',
    subtitle: "Help me decode what I'm feeling.",
  },
  {
    slug: 'practical_steadiness',
    label: 'Practical steadiness',
    subtitle: 'Concrete actions. Stoic discipline.',
  },
]

export default function NeedPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const _hasHydrated = useStore((s) => s._hasHydrated)

  const [selected, setSelected] = useState<typeof NEED_OPTIONS[number]['slug'] | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!_hasHydrated) return
    if (token === null) router.replace('/auth')
  }, [_hasHydrated, token, router])

  const handleContinue = async () => {
    if (!selected || !token || submitting) return

    setSubmitting(true)
    setError(null)

    try {
      const themesJson = sessionStorage.getItem('onboarding_themes')
      const otherText = sessionStorage.getItem('onboarding_other_text') || ''
      const themes: string[] = themesJson ? JSON.parse(themesJson) : []

      await api.upsertPreferences({
        themes,
        other_text: otherText.trim() === '' ? null : otherText.trim(),
        need_most: selected,
      })

      sessionStorage.removeItem('onboarding_themes')
      sessionStorage.removeItem('onboarding_other_text')

      router.push('/app/onboarding/matches')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong'
      setError(message)
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <div className="flex-1 flex flex-col justify-center px-7 py-8">
        <div className="w-full max-w-[380px] mx-auto space-y-7">

          <div className="flex justify-center">
            <BronzeDivider width={80} />
          </div>

          <header className="space-y-3 text-center">
            <h1 className="font-cormorant text-[26px] font-normal text-ink leading-tight">
              What do you need most?
            </h1>
            <p className="font-lora text-[13px] text-charcoal leading-[1.65]">
              Pick the one that fits today.
            </p>
          </header>

          <div className="space-y-2">
            {NEED_OPTIONS.map(({ slug, label, subtitle }) => {
              const isSelected = selected === slug
              return (
                <button
                  key={slug}
                  type="button"
                  onClick={() => setSelected(slug)}
                  aria-pressed={isSelected}
                  disabled={submitting}
                  className={`w-full text-left p-4 rounded-md border-[0.5px] transition-colors ${
                    isSelected
                      ? 'bg-linen-deep border-ink'
                      : 'bg-linen border-edge'
                  } ${submitting ? 'opacity-50' : ''}`}
                >
                  <div className="font-cormorant text-[18px] font-medium text-ink leading-none mb-1">
                    {label}
                  </div>
                  <div className="font-lora text-[12px] text-charcoal leading-[1.5]">
                    {subtitle}
                  </div>
                </button>
              )
            })}
          </div>

          {error && (
            <p className="font-lora text-[12px] text-safety text-center">
              {error}
            </p>
          )}

          <button
            type="button"
            disabled={!selected || submitting}
            onClick={handleContinue}
            className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum disabled:bg-linen disabled:text-charcoal transition-colors"
          >
            {submitting ? 'Saving…' : 'Continue'}
          </button>

        </div>
      </div>
    </main>
  )
}
