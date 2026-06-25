'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { ProfileValue, DisagreementStyle } from '@/lib/api'
import { BronzeDivider } from '@/components/ui/BronzeDivider'
import { VALUE_OPTIONS, MAX_VALUES, DISAGREEMENT_OPTIONS } from '@/lib/profile'

export default function ProfilePage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [values, setValues] = useState<ProfileValue[]>([])
  const [disagreement, setDisagreement] = useState<DisagreementStyle | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // After save we briefly show the instant reflection, then route to matches.
  const [reflection, setReflection] = useState<string[] | null>(null)

  useEffect(() => {
    if (token === null) router.replace('/auth')
  }, [token, router])

  const hasSignal = values.length > 0 || disagreement !== null

  const toggleValue = (slug: ProfileValue) => {
    setValues((prev) => {
      if (prev.includes(slug)) return prev.filter((s) => s !== slug)
      if (prev.length >= MAX_VALUES) return prev // cap at MAX_VALUES
      return [...prev, slug]
    })
  }

  const goToMatches = () => router.push('/app/onboarding/matches')

  const handleContinue = async () => {
    if (!hasSignal || !token || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      await api.saveProfile({ values, disagreement_style: disagreement })
      // Instant reflection — best-effort. Empty/failed → skip the beat silently.
      let bullets: string[] = []
      try {
        const res = await api.getProfileReflection()
        bullets = res.bullets
      } catch {
        bullets = []
      }
      if (bullets.length > 0) {
        setReflection(bullets)
        setSubmitting(false)
      } else {
        goToMatches()
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong'
      setError(message)
      setSubmitting(false)
    }
  }

  // ── Reflection beat ──────────────────────────────────────────────────────
  if (reflection) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
        <div className="flex-1 flex flex-col justify-center px-7 py-8">
          <div className="w-full max-w-[380px] mx-auto space-y-7">
            <div className="flex justify-center">
              <BronzeDivider width={80} />
            </div>
            <header className="space-y-3 text-center">
              <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
                What&rsquo;s beginning to take shape
              </h1>
            </header>
            <ul className="space-y-3">
              {reflection.map((b, i) => (
                <li
                  key={i}
                  className="font-lora italic text-[15px] text-charcoal leading-[1.7] pl-[14px] border-l-2 border-bronze/60"
                >
                  {b}
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={goToMatches}
              className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
            >
              Continue
            </button>
          </div>
        </div>
      </main>
    )
  }

  // ── Questions ────────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <div className="flex-1 flex flex-col justify-center px-7 py-8">
        <div className="w-full max-w-[380px] mx-auto space-y-7">

          <div className="flex justify-center">
            <BronzeDivider width={80} />
          </div>

          {/* Q1 — values (multi-select, cap 3) */}
          <header className="space-y-3 text-center">
            <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
              What do you value most?
            </h1>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Pick up to three.
            </p>
          </header>

          <div className="flex flex-wrap gap-2 justify-center">
            {VALUE_OPTIONS.map(({ slug, label }) => {
              const isSelected = values.includes(slug as ProfileValue)
              const atCap = !isSelected && values.length >= MAX_VALUES
              return (
                <button
                  key={slug}
                  type="button"
                  onClick={() => toggleValue(slug as ProfileValue)}
                  aria-pressed={isSelected}
                  disabled={submitting || atCap}
                  className={`px-4 py-2 rounded-full font-lora text-[13px] border-[0.5px] transition-colors ${
                    isSelected
                      ? 'bg-bronze border-bronze-dark text-ink'
                      : 'bg-white border-bronze/60 text-charcoal shadow-card'
                  } ${atCap ? 'opacity-40' : ''}`}
                >
                  {label}
                </button>
              )
            })}
          </div>

          {/* Q2 — disagreement style (single-select) */}
          <header className="space-y-3 text-center pt-2">
            <h2 className="font-cormorant text-[22px] font-medium text-ink leading-tight">
              When you disagree, you tend to…
            </h2>
          </header>

          <div className="flex flex-wrap gap-2 justify-center">
            {DISAGREEMENT_OPTIONS.map(({ slug, label }) => {
              const isSelected = disagreement === slug
              return (
                <button
                  key={slug}
                  type="button"
                  onClick={() =>
                    setDisagreement((prev) => (prev === slug ? null : (slug as DisagreementStyle)))
                  }
                  aria-pressed={isSelected}
                  disabled={submitting}
                  className={`px-4 py-2 rounded-full font-lora text-[13px] border-[0.5px] transition-colors ${
                    isSelected
                      ? 'bg-bronze border-bronze-dark text-ink'
                      : 'bg-white border-bronze/60 text-charcoal shadow-card'
                  }`}
                >
                  {label}
                </button>
              )
            })}
          </div>

          {error && (
            <p className="font-lora text-[12px] text-safety text-center">{error}</p>
          )}

          <button
            type="button"
            disabled={!hasSignal || submitting}
            onClick={handleContinue}
            className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum disabled:bg-linen disabled:text-charcoal transition-colors"
          >
            {submitting ? 'Saving…' : 'Continue'}
          </button>

          {/* Quiet skip — the profile enhances, it does not gate. No save. */}
          <button
            type="button"
            onClick={goToMatches}
            disabled={submitting}
            className="w-full font-lora text-[13px] text-sepia underline underline-offset-2 disabled:opacity-50"
          >
            Skip for now
          </button>

        </div>
      </div>
    </main>
  )
}
