'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { ProfileValue, DisagreementStyle } from '@/lib/api'
import { BronzeDivider } from '@/components/ui/BronzeDivider'
import { VALUE_OPTIONS, MAX_VALUES, DISAGREEMENT_OPTIONS } from '@/lib/profile'

// Standalone editable profile. Reached by direct URL only in v1 — no nav entry
// (the Explore-tab hook is a future addition). Reuses the onboarding pill UI.
export default function EditProfilePage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [loading, setLoading] = useState(true)
  const [values, setValues] = useState<ProfileValue[]>([])
  const [disagreement, setDisagreement] = useState<DisagreementStyle | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    async function load() {
      try {
        const prefs = await api.getPreferences()
        if (prefs.profile) {
          setValues(prefs.profile.values ?? [])
          setDisagreement(prefs.profile.disagreement_style ?? null)
        }
      } catch {
        // 404 (no preferences yet) or transient — start from an empty profile.
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token, router])

  const toggleValue = (slug: ProfileValue) => {
    setSaved(false)
    setValues((prev) => {
      if (prev.includes(slug)) return prev.filter((s) => s !== slug)
      if (prev.length >= MAX_VALUES) return prev
      return [...prev, slug]
    })
  }

  const handleSave = async () => {
    if (saving) return
    setSaving(true)
    setError(null)
    try {
      await api.saveProfile({ values, disagreement_style: disagreement })
      setSaved(true)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong'
      setError(message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen [min-height:100svh] bg-vellum px-7 pt-10">
        <div className="w-full max-w-[380px] mx-auto space-y-4">
          <div className="h-[28px] w-[200px] bg-linen rounded animate-pulse" />
          <div className="h-[18px] w-[260px] bg-linen rounded animate-pulse" />
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <div className="flex-1 flex flex-col justify-center px-7 py-8">
        <div className="w-full max-w-[380px] mx-auto space-y-7">

          <div className="flex justify-center">
            <BronzeDivider width={80} />
          </div>

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
                  disabled={saving || atCap}
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
                  onClick={() => {
                    setSaved(false)
                    setDisagreement((prev) => (prev === slug ? null : (slug as DisagreementStyle)))
                  }}
                  aria-pressed={isSelected}
                  disabled={saving}
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
            disabled={saving}
            onClick={handleSave}
            className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum disabled:bg-linen disabled:text-charcoal transition-colors"
          >
            {saving ? 'Saving…' : saved ? 'Saved' : 'Save'}
          </button>

          {saved && (
            <p className="font-lora text-[12px] text-sepia text-center">
              The minds will carry this forward.
            </p>
          )}

        </div>
      </div>
    </main>
  )
}
