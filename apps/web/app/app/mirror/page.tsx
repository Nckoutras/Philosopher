'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { ChevronLeft } from 'lucide-react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { Mirror, Persona } from '@/lib/api'

export default function MirrorPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [loading, setLoading] = useState(true)
  const [mirror, setMirror] = useState<Mirror | null>(null)
  const [persona, setPersona] = useState<Persona | null>(null)
  const [ringTrue, setRingTrue] = useState<'yes' | 'partly' | 'no' | null>(null)
  const [ringTrueSubmitted, setRingTrueSubmitted] = useState(false)
  const [startingConv, setStartingConv] = useState(false)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }

    async function load() {
      try {
        const [mirrorRes, personasRes] = await Promise.allSettled([
          api.getLatestMirror(),
          api.getPersonas(),
        ])

        const m = mirrorRes.status === 'fulfilled' ? mirrorRes.value : null
        setMirror(m)

        if (m?.host_persona_slug && personasRes.status === 'fulfilled') {
          const found = personasRes.value.find((p) => p.slug === m.host_persona_slug)
          setPersona(found ?? null)
        }

        if (m?.ring_true) {
          setRingTrue(m.ring_true)
          setRingTrueSubmitted(true)
        }
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [token, router])

  async function handleRingTrue(value: 'yes' | 'partly' | 'no') {
    if (ringTrueSubmitted || !mirror) return
    setRingTrue(value)
    setRingTrueSubmitted(true)
    try {
      await api.setRingTrue(mirror.id, value)
    } catch {
      // optimistic -- silent
    }
  }

  async function handleContinueWithHost() {
    if (!mirror?.host_persona_slug || startingConv) return
    setStartingConv(true)
    try {
      const conv = await api.createConversation(mirror.host_persona_slug)
      router.push(`/app/chat/conv/${conv.id}`)
    } catch {
      setStartingConv(false)
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen [min-height:100svh] bg-vellum">
        <div className="px-[24px] pt-[22px] pb-[16px]">
          <div className="w-[32px] h-[32px] -ml-[4px] mb-[8px]" />
          <div className="h-[10px] w-[100px] bg-linen rounded animate-pulse mb-[8px]" />
          <div className="h-[28px] w-[210px] bg-linen rounded animate-pulse" />
        </div>
        <div className="px-[16px]">
          <div className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[24px] flex flex-col gap-[12px]">
            <div className="h-[18px] bg-linen rounded animate-pulse" />
            <div className="h-[18px] w-5/6 bg-linen rounded animate-pulse" />
            <div className="h-[18px] w-4/6 bg-linen rounded animate-pulse" />
            <div className="h-[18px] w-3/6 bg-linen rounded animate-pulse mt-[12px]" />
            <div className="h-[18px] bg-linen rounded animate-pulse" />
          </div>
        </div>
      </main>
    )
  }

  const eyebrow = mirror?.kind === 'preview' ? 'A FIRST REFLECTION' : 'WEEKLY MIRROR'

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[40px]">

      <div className="relative px-[24px] pt-[22px] pb-[16px] overflow-hidden">
        <svg
          aria-hidden="true"
          width="88"
          height="88"
          viewBox="0 0 88 88"
          fill="none"
          className="absolute top-0 right-0 opacity-[0.16] pointer-events-none"
        >
          <path d="M88 0 C88 48.6 48.6 88 0 88" stroke="#B89968" strokeWidth="1.2" />
          <path d="M88 18 C88 57 57 88 18 88" stroke="#B89968" strokeWidth="0.6" />
        </svg>

        <button
          type="button"
          onClick={() => router.push('/app/rituals')}
          aria-label="Back to rituals"
          className="flex items-center justify-center w-[32px] h-[32px] -ml-[4px] mb-[8px]"
        >
          <ChevronLeft size={20} strokeWidth={1.5} className="text-sepia" />
        </button>

        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-1">
          {eyebrow}
        </p>
        <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
          What the mirror reflects
        </h1>

        {mirror?.host_persona_name && (
          <div className="flex items-center gap-[10px] mt-[12px]">
            <div className="w-[34px] h-[34px] rounded-full overflow-hidden flex-shrink-0 bg-linen border border-[0.5px] border-edge flex items-center justify-center">
              {persona?.portrait_url ? (
                <Image
                  src={persona.portrait_url}
                  alt={mirror.host_persona_name}
                  width={34}
                  height={34}
                  className="object-cover w-full h-full"
                />
              ) : (
                <span className="font-cormorant text-[15px] font-medium text-charcoal">
                  {mirror.host_persona_name.charAt(0)}
                </span>
              )}
            </div>
            <span className="font-lora text-[12px] text-sepia border border-[0.5px] border-sepia/40 rounded-full px-[10px] py-[3px]">
              Through {mirror.host_persona_name}
            </span>
          </div>
        )}
      </div>

      {!mirror && (
        <div className="px-[16px]">
          <div className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[32px] text-center">
            <p className="font-cormorant text-[20px] font-normal text-ink leading-snug">
              Your first reflection is still forming.
            </p>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65] mt-[12px] px-[8px]">
              Keep talking with the minds &mdash; the mirror gathers what matters.
            </p>
            <button
              type="button"
              onClick={() => router.push('/app/rituals')}
              className="mt-[24px] font-lora text-[13px] text-sepia underline underline-offset-2"
            >
              Back to rituals
            </button>
          </div>
        </div>
      )}

      {mirror && (
        <div className="px-[16px] flex flex-col gap-[16px]">
          <div className="bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[16px] py-[24px] flex flex-col gap-[24px]">

            {mirror.payload && mirror.payload.thread && (
              <p className="font-cormorant text-[20px] font-normal text-ink leading-[1.55]">
                {mirror.payload.thread}
              </p>
            )}

            {mirror.payload && mirror.payload.moments && mirror.payload.moments.length > 0 && (
              <div>
                <p className="font-lora text-[10px] uppercase tracking-[0.18em] text-sepia mb-[14px]">
                  BENEATH THE WORDS
                </p>
                <div className="flex flex-col gap-[20px]">
                  {mirror.payload.moments.map((moment, i) => (
                    <div key={i}>
                      <p className="font-lora text-[15px] text-sepia leading-[1.6] italic">
                        &ldquo;{moment.said}&rdquo;
                      </p>
                      <p className="font-cormorant text-[17px] text-ink leading-[1.5] mt-[6px]">
                        {moment.meant}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {mirror.payload && mirror.payload.line_that_moved && (
              <div>
                <p className="font-lora text-[10px] uppercase tracking-[0.18em] text-sepia mb-[14px]">
                  THE LINE THAT MOVED
                </p>
                <div className="border-l-2 border-bronze pl-[14px] flex flex-col gap-[6px] mb-[12px]">
                  <p className="font-lora text-[13px] text-charcoal leading-[1.5]">
                    <span className="text-sepia">{mirror.payload.line_that_moved.earlier.label}</span>
                    {' — '}&lsquo;{mirror.payload.line_that_moved.earlier.quote}&rsquo;
                  </p>
                  <p className="font-lora text-[13px] text-charcoal leading-[1.5]">
                    <span className="text-sepia">{mirror.payload.line_that_moved.later.label}</span>
                    {' — '}&lsquo;{mirror.payload.line_that_moved.later.quote}&rsquo;
                  </p>
                </div>
                <p className="font-lora text-[15px] text-ink leading-[1.65]">
                  {mirror.payload.line_that_moved.read}
                </p>
              </div>
            )}

            <p className="font-lora text-[14px] text-sepia italic leading-[1.6]">
              This may be wrong. If it is, set it down.
            </p>

            {mirror.payload && mirror.payload.question && (
              <div>
                <p className="font-lora text-[10px] uppercase tracking-[0.18em] text-sepia mb-[10px]">
                  THE QUESTION
                </p>
                <p className="font-cormorant text-[20px] font-normal text-ink leading-[1.5]">
                  {mirror.payload.question}
                </p>
              </div>
            )}

            <div>
              <p className="font-lora text-[10px] uppercase tracking-[0.18em] text-sepia mb-[12px]">
                DOES THIS RING TRUE?
              </p>
              <div className="flex gap-[8px] flex-wrap">
                {(
                  [
                    { value: 'yes' as const, label: 'Rings true' },
                    { value: 'partly' as const, label: 'Partly' },
                    { value: 'no' as const, label: 'No' },
                  ] as const
                ).map(({ value, label }) => (
                  <button
                    key={value}
                    type="button"
                    disabled={ringTrueSubmitted}
                    onClick={() => handleRingTrue(value)}
                    className={[
                      'font-lora text-[13px] px-[16px] py-[8px] rounded-full border border-[0.5px] transition-colors',
                      ringTrue === value
                        ? 'border-bronze bg-bronze/10 text-bronze'
                        : 'border-edge text-charcoal',
                      ringTrueSubmitted && ringTrue !== value ? 'opacity-40' : '',
                    ].join(' ')}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {ringTrueSubmitted && (
                <p className="font-lora text-[12px] text-sepia italic mt-[8px]">Noted.</p>
              )}
            </div>

          </div>

          <div className="flex flex-col gap-[10px]">
            {mirror.host_persona_slug && mirror.host_persona_name && (
              <button
                type="button"
                onClick={handleContinueWithHost}
                disabled={startingConv}
                className="w-full py-[14px] rounded-md bg-ink text-vellum font-cormorant text-[17px] font-medium disabled:opacity-60"
              >
                {startingConv ? 'Opening…' : `Continue with ${mirror.host_persona_name}`}
              </button>
            )}

            <div className="relative">
              <button
                type="button"
                disabled
                className="w-full py-[14px] rounded-md border border-[0.5px] border-ink font-cormorant text-[17px] font-medium text-ink opacity-50 cursor-not-allowed"
              >
                Take it to the Council
              </button>
              <span className="absolute top-[-9px] right-[14px] font-lora text-[10px] text-sepia bg-vellum px-[6px] border border-[0.5px] border-edge rounded-full">
                Premium &middot; soon
              </span>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
