'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Image from 'next/image'
import { useStore } from '@/lib/store'
import { api, type Persona } from '@/lib/api'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

// Duplicated from welcome and matches pages — P2 cleanup item
const PORTRAIT_PATHS: Record<string, string> = {
  socrates: '/personas/socrates.jpg',
  marcus_aurelius: '/personas/marcus_aurelius.jpg',
  simone_de_beauvoir: '/personas/simone_de_beauvoir.webp',
  epictetus: '/personas/epictetus.webp',
  sigmund_freud: '/personas/sigmund_freud.webp',
}

// Static bios — will move to backend persona table in a future PR
const BIOS: Record<string, string> = {
  marcus_aurelius:
    "Roman emperor, last of the Five Good Emperors. He wrote 'Meditations' as private notes to himself — not philosophy for publication, but reminders to a man trying to govern an empire while staying human. Stoic, disciplined, oriented toward what's in your control. He treats grief like weather: real, passing, not personal. If you came looking for someone who won't flinch at hard things, he won't.",
  socrates:
    "Athenian gadfly, executed at 70 for asking too many questions. Wrote nothing — everything we know comes through Plato and Xenophon. His method: ask, listen, ask again, until your own answer reveals itself or collapses. He does not give you wisdom. He helps you find what you already half-knew. Expect to be questioned more than comforted.",
  simone_de_beauvoir:
    "French existentialist, philosopher, novelist, intellectual partner to Sartre but a thinker in her own right. Wrote 'The Second Sex' and 'The Ethics of Ambiguity'. She believes you are made by your choices — that freedom is a burden, not a gift. She talks about love, work, aging, motherhood, and refusal. If you came tangled in relationships and identity, she'll meet you there.",
  epictetus:
    "Born a slave in Rome, became one of antiquity's most quoted teachers. Lame, exiled, but free in the way that mattered. His teaching is brutally simple: separate what you control from what you don't, and stop wasting yourself on the second. He does not coddle. He has no patience for self-pity but enormous patience for the work of becoming.",
  sigmund_freud:
    "Viennese physician who invented psychoanalysis. Mapped the unconscious — the parts of yourself you refuse to see, the wishes you keep hidden, the patterns you repeat. He does not believe you understand your own motives. He listens for what you do not say. Controversial, often wrong, but the language he gave us to discuss the mind is still ours. Bring your dreams.",
}

const TIER_LABELS: Record<Persona['tier'], string> = {
  free: 'FREE',
  pro: 'PRO',
  premium: 'PREMIUM',
}

export default function PersonaDetailPage() {
  const router = useRouter()
  const params = useParams<{ slug: string }>()
  const token = useStore((s) => s.token)

  const [persona, setPersona] = useState<Persona | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth')
      return
    }

    let cancelled = false

    async function load() {
      try {
        const personas = await api.getPersonas()
        if (cancelled) return
        const found = personas.find((p) => p.slug === params.slug)
        if (!found) {
          setNotFound(true)
          return
        }
        setPersona(found)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Could not load')
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [token, params.slug, router])

  if (notFound) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum px-7 text-center">
        <p className="font-cormorant text-[20px] text-ink mb-3">
          That mind is not here.
        </p>
        <button
          onClick={() => router.push('/app/onboarding/matches')}
          className="font-lora text-[13px] text-sepia underline"
        >
          Back to your matches
        </button>
      </main>
    )
  }

  if (error) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum px-7 text-center">
        <p className="font-lora text-[13px] text-safety mb-3">{error}</p>
        <button
          onClick={() => router.back()}
          className="font-lora text-[13px] text-sepia underline"
        >
          Back
        </button>
      </main>
    )
  }

  if (!persona) {
    return (
      <main className="min-h-screen [min-height:100svh] flex flex-col items-center justify-center bg-vellum">
        <p className="font-lora text-[13px] text-sepia italic">Loading…</p>
      </main>
    )
  }

  const isLocked = !persona.is_accessible
  const portraitPath = PORTRAIT_PATHS[persona.slug] ?? ''
  const bio = BIOS[persona.slug] ?? ''
  const tierLabel = TIER_LABELS[persona.tier]
  const tierColorClass = persona.tier === 'free' ? 'text-vellum' : 'text-bronze'

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      {/* Portrait section */}
      <section className="relative w-full h-[40vh] [height:40svh] overflow-hidden bg-linen flex-shrink-0">
        {portraitPath && (
          <Image
            src={portraitPath}
            alt={persona.name}
            fill
            priority
            sizes="100vw"
            className="object-cover object-top scale-[1.30] origin-top"
          />
        )}

        {/* Tier badge */}
        <div
          className={`absolute top-6 left-7 font-lora text-[10px] tracking-[0.20em] font-medium ${tierColorClass}`}
          style={{ textShadow: '0 1px 2px rgba(0,0,0,0.4)' }}
        >
          {tierLabel}
        </div>

        {/* Close button */}
        <button
          onClick={() => router.back()}
          aria-label="Close"
          className="absolute top-5 right-6 w-8 h-8 flex items-center justify-center text-vellum text-[20px]"
          style={{ textShadow: '0 1px 2px rgba(0,0,0,0.4)' }}
        >
          ✕
        </button>
      </section>

      {/* Content section */}
      <section className="flex-1 px-7 py-6">
        <div className="w-full max-w-[380px] mx-auto space-y-5">

          {/* Name + tagline */}
          <header className="space-y-2 text-center">
            <h1 className="font-cormorant text-[28px] font-normal text-ink leading-tight">
              {persona.name}
            </h1>
            {persona.tagline && (
              <p className="font-lora text-[13px] text-charcoal italic">
                {persona.tagline}
              </p>
            )}
          </header>

          <div className="flex justify-center">
            <BronzeDivider width={80} />
          </div>

          {/* Bio — blurred if locked */}
          {bio && (
            <p
              className={`font-lora text-[13px] text-charcoal leading-[1.7] ${
                isLocked ? 'blur-[3px] select-none pointer-events-none' : ''
              }`}
            >
              {bio}
            </p>
          )}

          {/* Opening invocation preview — blurred if locked */}
          {persona.opening_invocation && (
            <div
              className={`bg-linen rounded-md p-4 border-l-2 border-bronze ${
                isLocked ? 'blur-[3px] select-none pointer-events-none' : ''
              }`}
            >
              <p className="font-lora text-[10px] uppercase tracking-[0.20em] text-sepia mb-2">
                They begin with
              </p>
              <p className="font-cormorant text-[16px] italic text-ink leading-[1.55]">
                &ldquo;{persona.opening_invocation}&rdquo;
              </p>
            </div>
          )}

          {/* CTA section */}
          <div className="pt-3 space-y-3">
            {isLocked ? (
              <>
                <button
                  type="button"
                  onClick={() => {
                    // Stripe wiring not yet implemented — placeholder
                    alert('Stripe checkout coming soon.')
                  }}
                  className="w-full h-[48px] rounded-sm font-cormorant text-[17px] font-medium bg-bronze text-vellum transition-colors"
                >
                  Upgrade to Pro
                </button>
                <button
                  type="button"
                  onClick={() => router.push('/app/onboarding/matches')}
                  className="w-full font-lora text-[12px] text-sepia underline underline-offset-2 text-center"
                >
                  Or pick a free philosopher
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => router.push(`/app/chat/${persona.slug}`)}
                className="w-full h-[48px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
              >
                Begin conversation
              </button>
            )}
          </div>

        </div>
      </section>
    </main>
  )
}
