'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

type DisclaimerCopy = {
  version_string: string
  age_copy: string
  positioning_copy: string
}

export default function DisclaimerPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [copy, setCopy] = useState<DisclaimerCopy | null>(null)
  const [confirmedAge, setConfirmedAge] = useState(false)
  const [confirmedPositioning, setConfirmedPositioning] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [fetchError, setFetchError] = useState(false)

  useEffect(() => {
    if (token === null) router.replace('/auth')
  }, [token, router])

  async function fetchCopy() {
    setFetchError(false)
    try {
      const data = await api.getDisclaimerCurrent()
      setCopy(data)
    } catch {
      setFetchError(true)
      toast.error('Could not load disclaimer. Tap retry to try again.')
    }
  }

  useEffect(() => {
    fetchCopy()
  }, [])

  async function handleSubmit() {
    setIsSubmitting(true)
    try {
      await api.acceptDisclaimer({
        confirmed_age_18: true,
        confirmed_non_therapy: true,
        locale: 'en',
      })
      router.replace('/app/today')
    } catch {
      toast.error('Could not save your acceptance. Please try again.')
      setIsSubmitting(false)
    }
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
              Before we begin.
            </h1>
            <p className="font-lora text-[13px] text-charcoal leading-[1.65]">
              Two things to confirm.
            </p>
          </header>

          {/* Cards */}
          <div className="space-y-3">

            {/* Card 1: Age */}
            <button
              type="button"
              onClick={() => setConfirmedAge((v) => !v)}
              aria-pressed={confirmedAge}
              disabled={!copy}
              className="w-full bg-white border-[0.5px] border-edge rounded-md px-5 py-4 flex items-start gap-3 text-left transition-colors disabled:opacity-50"
            >
              <span
                aria-hidden="true"
                className={`mt-0.5 w-5 h-5 flex-shrink-0 border-[1.5px] rounded-sm flex items-center justify-center transition-colors ${
                  confirmedAge ? 'bg-ink border-ink' : 'bg-white border-edge'
                }`}
              >
                {confirmedAge && (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path
                      d="M2 6L5 9L10 3"
                      stroke="var(--vellum)"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </span>
              <span className="font-lora text-[14px] font-medium text-ink leading-[1.5]">
                {copy?.age_copy ?? ' '}
              </span>
            </button>

            {/* Card 2: Positioning */}
            <button
              type="button"
              onClick={() => setConfirmedPositioning((v) => !v)}
              aria-pressed={confirmedPositioning}
              disabled={!copy}
              className="w-full bg-white border-[0.5px] border-edge rounded-md px-5 py-4 flex items-start gap-3 text-left transition-colors disabled:opacity-50"
            >
              <span
                aria-hidden="true"
                className={`mt-0.5 w-5 h-5 flex-shrink-0 border-[1.5px] rounded-sm flex items-center justify-center transition-colors ${
                  confirmedPositioning ? 'bg-ink border-ink' : 'bg-white border-edge'
                }`}
              >
                {confirmedPositioning && (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path
                      d="M2 6L5 9L10 3"
                      stroke="var(--vellum)"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </span>
              <span className="font-lora text-[14px] font-normal text-ink leading-[1.5]">
                {copy?.positioning_copy ?? ' '}
              </span>
            </button>
          </div>

          {/* Retry link — only visible on fetch error */}
          {fetchError && (
            <button
              type="button"
              onClick={fetchCopy}
              className="w-full font-lora text-[13px] text-charcoal underline underline-offset-2 decoration-[0.5px] text-center"
            >
              Retry
            </button>
          )}

          {/* CTA */}
          <button
            type="button"
            disabled={!confirmedAge || !confirmedPositioning || !copy || isSubmitting}
            onClick={handleSubmit}
            className="w-full h-[50px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum disabled:bg-linen disabled:text-charcoal transition-colors"
          >
            {isSubmitting ? 'Saving…' : 'Continue'}
          </button>

        </div>
      </div>
    </main>
  )
}
