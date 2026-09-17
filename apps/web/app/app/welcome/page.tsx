'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { api, type Persona } from '@/lib/api'
import { useStore } from '@/lib/store'
import { useAuthGate } from '@/lib/useAuthGate'
import { signOut } from '@/lib/auth'

// How long the "have you talked to anyone yet" read may hang before the page
// calls it dead.
//
// A NAMED PROPOSAL, NOT A DERIVATION — said plainly because the 90s go-deeper
// timeout in the counterview reader IS a derivation and the two must not be
// confused. apps/web has no timeout precedent of any kind: there is no other
// constant of this sort in the whole frontend. The 90s figure belongs to
// `WorkerSettings.job_timeout` and governs an LLM generation; it does not
// transfer to one indexed read behind one HTTP call.
//
// 10s is a judgement about that read, Render cold start included. It is far
// outside normal latency and short enough that a stuck CTA becomes a handled
// state while the person is still looking at it. The honest way to replace this
// number is to measure p99 on the endpoint; until someone does, it is a guess
// with its reasoning attached rather than a borrowed number that does not fit.
const LAST_CONVERSATION_TIMEOUT_MS = 10_000

// Deterministic daily index — same for all users, rotates at UTC midnight.
function mindOfTheDayIndex(rotationSize: number): number {
  const dayMs = 86_400_000
  const dayNumber = Math.floor(Date.now() / dayMs)
  return dayNumber % rotationSize
}

export default function WelcomePage() {
  const router = useRouter()
  useAuthGate()

  const [mind, setMind] = useState<Persona | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [hasConversations, setHasConversations] = useState<boolean | null>(null)
  const [convLoading, setConvLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const all = await api.getPersonas()
        const rotation = all.filter((p) => p.portrait_url)
        if (rotation.length === 0) {
          if (!cancelled) setLoadError(true)
          return
        }
        const idx = mindOfTheDayIndex(rotation.length)
        if (!cancelled) setMind(rotation[idx])
      } catch {
        if (!cancelled) setLoadError(true)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    // BUG-001 residue. This call had no deadline, and the two CTA slots render as
    // inert grey placeholders while `hasConversations === null`. The .catch below
    // covers a REJECTION; a HANG left those placeholders forever — which is the
    // literal "Begin does nothing" the 2026-09-14 UAT saw. A hang now becomes the
    // same handled error state a rejection produces.
    let settled = false
    const timer = setTimeout(() => {
      if (!settled) setLoadError(true)
    }, LAST_CONVERSATION_TIMEOUT_MS)
    api.getLastConversation()
      .then((result) => { settled = true; setHasConversations(result !== null) })
      .catch(() => { settled = true; setHasConversations(false) })
      .finally(() => clearTimeout(timer))
  }, [])

  async function handleConverse() {
    if (!mind) return
    setConvLoading(true)
    try {
      const conv = await api.createConversation(mind.slug)
      router.push(`/app/chat/conv/${conv.id}`)
    } catch {
      toast.error('Could not start conversation.')
      router.push('/app/library')
    } finally {
      setConvLoading(false)
    }
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      {/* Top: full-bleed portrait area (~70% height) */}
      <section className="relative flex-1 min-h-[70vh] [min-height:70svh] overflow-hidden bg-linen">
        {mind && (
          <Image
            src={mind.portrait_url}
            alt={mind.name}
            fill
            priority
            sizes="100vw"
            className="object-cover object-top scale-[1.30] origin-top"
          />
        )}

        {/* Dark gradient overlay — top-anchored so hero text is always readable */}
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-0 h-[40%] bg-gradient-to-b from-black/65 via-black/35 to-transparent pointer-events-none"
        />

        {/* Hero text — V2: white serif + drop shadow */}
        <div className="absolute inset-x-0 top-0 z-10 px-3 flex flex-col items-center text-center" style={{ paddingTop: 'max(0.75rem, env(safe-area-inset-top))' }}>
          <h1
            className="font-cormorant font-medium text-white text-[44px] leading-[1.05] tracking-wide"
            style={{ textShadow: '0 2px 8px rgba(0,0,0,0.6), 0 1px 3px rgba(0,0,0,0.8)' }}
          >
            The Wise Room
          </h1>
          <p
            className="font-cormorant font-normal text-white text-[19px] mt-2 leading-snug tracking-wide"
            style={{ textShadow: '0 1px 4px rgba(0,0,0,0.5)' }}
          >
            Reflect with the greatest thinkers
          </p>
        </div>
      </section>

      {/* Bottom: Vellum tray */}
      <section className="bg-vellum px-7 pt-4 pb-safe">
        <div className="w-full max-w-[380px] mx-auto">
          {loadError ? (
            <div className="text-center space-y-3">
              <p className="font-lora text-[13px] text-charcoal">
                Could not load today&apos;s mind.
              </p>
              {/* TWO ROUTES OUT, and the second is the point (BUG-001 residue).
                  Reload is right for a transient failure and can NEVER fix a
                  stale-but-present token: it repeats the same failing call, so a
                  user in that state was looped here with no way out. Sign out is
                  the escape that does not depend on the call that failed.
                  Reached by a hang as well as an error — the two are the same
                  thing to the reader, and the escape is identical. */}
              <div className="flex items-center justify-center gap-4">
                <button
                  type="button"
                  onClick={() => { setLoadError(false); window.location.reload() }}
                  className="font-lora text-[13px] text-sepia underline underline-offset-2"
                >
                  Try again
                </button>
                <button
                  type="button"
                  onClick={() => signOut()}
                  className="font-lora text-[13px] text-sepia underline underline-offset-2"
                >
                  Sign in again
                </button>
              </div>
            </div>
          ) : (
            <>
              <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia text-center">
                Mind of the day
              </p>
              <h2 className="mt-2 font-cormorant text-[24px] font-medium text-ink text-center leading-tight min-h-[32px]">
                {mind?.name ?? ' '}
              </h2>
              <p className="mt-1 font-lora text-[14px] text-charcoal text-center leading-snug min-h-[42px]">
                {mind?.tagline ?? ' '}
              </p>
            </>
          )}

          {/* CTAs — state-aware */}
          <div className="mt-5 space-y-2">
            {hasConversations === null ? (
              // Loading state — placeholder buttons to prevent layout shift
              <>
                <div className="w-full h-[46px] rounded-sm bg-linen" />
                <div className="w-full h-[46px] rounded-sm bg-linen" />
              </>
            ) : !hasConversations ? (
              // First-time user — onboarding CTAs
              <>
                <button
                  type="button"
                  onClick={() => router.push('/app/onboarding/themes')}
                  className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
                >
                  Begin
                </button>
                <button
                  type="button"
                  onClick={() => router.push('/app/library?mode=browse')}
                  className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium border-[0.5px] border-edge bg-white text-ink transition-colors"
                >
                  Explore Minds
                </button>
              </>
            ) : (
              // Returning user — converse with today's mind
              <>
                <button
                  type="button"
                  onClick={handleConverse}
                  disabled={convLoading || !mind}
                  className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors disabled:opacity-50"
                >
                  {convLoading ? 'Opening…' : `Converse with ${mind?.name ?? "today's mind"}`}
                </button>
                <button
                  type="button"
                  onClick={() => router.push('/app/library')}
                  className="w-full h-[46px] rounded-sm font-cormorant text-[17px] font-medium border-[0.5px] border-edge bg-white text-ink transition-colors"
                >
                  Past Conversations
                </button>
              </>
            )}
          </div>
        </div>
      </section>
    </main>
  )
}
