'use client'

import { Fragment, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Check, ChevronLeft, ChevronRight } from 'lucide-react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { Mirror, MirrorHost, Persona } from '@/lib/api'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function formatWeekSpan(start: string, end: string): string {
  const s = new Date(start)
  const e = new Date(end)
  const sm = MONTHS[s.getUTCMonth()]
  const sd = s.getUTCDate()
  const em = MONTHS[e.getUTCMonth()]
  const ed = e.getUTCDate()
  const yr = e.getUTCFullYear()
  if (sm === em) return `${sm} ${sd}–${ed}, ${yr}`
  return `${sm} ${sd} – ${em} ${ed}, ${yr}`
}

export default function MirrorPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [loading, setLoading] = useState(true)
  const [mirror, setMirror] = useState<Mirror | null>(null)
  const [persona, setPersona] = useState<Persona | null>(null)
  const [ringTrue, setRingTrue] = useState<'yes' | 'partly' | 'no' | null>(null)
  const [ringTrueSubmitted, setRingTrueSubmitted] = useState(false)
  const [startingConv, setStartingConv] = useState(false)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [hosts, setHosts] = useState<MirrorHost[]>([])
  const [selectedHost, setSelectedHost] = useState<string | null>(null)
  const [savedHostName, setSavedHostName] = useState<string | null>(null)

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

  async function openPicker() {
    setPickerOpen(true)
    try {
      const res = await api.getMirrorHosts()
      setHosts(res.hosts)
      setSelectedHost(res.selected ?? res.default)
    } catch { /* leave empty; sheet shows nothing gracefully */ }
  }

  async function chooseHost(slug: string, name: string) {
    setSelectedHost(slug)
    try {
      await api.setMirrorHost(slug)
      setSavedHostName(name)
    } catch { /* optimistic; ignore */ }
  }

  if (loading) {
    return (
      <main className="min-h-screen [min-height:100svh] bg-vellum">
        <div className="px-[24px] pt-[22px] pb-[16px]">
          <div className="w-[32px] h-[32px] -ml-[4px] mb-[8px]" />
          <div className="h-[10px] w-[100px] bg-linen rounded animate-pulse mb-[8px]" />
          <div className="h-[44px] w-[280px] bg-linen rounded animate-pulse mb-[20px]" />
          <div className="flex items-center gap-[16px]">
            <div className="w-[72px] h-[72px] rounded-full bg-linen animate-pulse flex-shrink-0" />
            <div className="flex flex-col gap-[6px]">
              <div className="h-[10px] w-[50px] bg-linen rounded animate-pulse" />
              <div className="h-[28px] w-[120px] bg-linen rounded animate-pulse" />
              <div className="h-[10px] w-[80px] bg-linen rounded animate-pulse" />
            </div>
          </div>
        </div>
        <div className="px-[16px]">
          <div className="bg-paper border-[0.5px] border-edge rounded-[18px] shadow-card px-[20px] py-[28px] flex flex-col gap-[12px]">
            <div className="h-[20px] bg-linen rounded animate-pulse" />
            <div className="h-[20px] w-5/6 bg-linen rounded animate-pulse" />
            <div className="h-[20px] w-4/6 bg-linen rounded animate-pulse" />
            <div className="h-[20px] w-3/6 bg-linen rounded animate-pulse mt-[12px]" />
            <div className="h-[20px] bg-linen rounded animate-pulse" />
          </div>
        </div>
      </main>
    )
  }

  const eyebrow = mirror?.kind === 'preview' ? 'A FIRST REFLECTION' : 'WEEKLY MIRROR'

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[40px] relative overflow-hidden">

      <svg aria-hidden="true" viewBox="0 0 250 540" fill="none"
           className="absolute top-[14px] right-[-58px] w-[250px] h-[540px] z-0 pointer-events-none">
        <path d="M20 540 L20 150 C20 60 76 8 125 8 C174 8 230 60 230 150 L230 540" stroke="#B89968" strokeWidth="1.6" opacity="0.5" />
        <path d="M40 540 L40 156 C40 78 86 30 125 30 C164 30 210 78 210 156 L210 540" stroke="#B89968" strokeWidth="0.7" opacity="0.28" />
        <path d="M150 70 C120 110 110 180 120 280" stroke="#B89968" strokeWidth="0.6" opacity="0.16" />
      </svg>

      {/* Header */}
      <div className="relative px-[24px] pt-[22px] pb-[24px] overflow-hidden">
        <div className="relative z-10">
          <button
            type="button"
            onClick={() => router.push('/app/rituals')}
            aria-label="Back to rituals"
            className="flex items-center justify-center w-[32px] h-[32px] -ml-[4px] mb-[10px]"
          >
            <ChevronLeft size={20} strokeWidth={1.5} className="text-sepia" />
          </button>

          <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark mb-[6px]">
            {eyebrow}
          </p>
          <h1 className="font-cormorant text-[44px] font-medium text-ink leading-tight">
            What the mirror reflects
          </h1>
          <p className="font-lora italic text-[14.5px] leading-relaxed text-charcoal mt-[14px] max-w-[300px]">
            Once a week, the mind you chose reads your own words back to you &mdash; not what you said, but what it meant.
          </p>

          {mirror?.host_persona_name && (
            <div className="flex items-center gap-[16px] mt-[24px]">
              <div className="w-[72px] h-[72px] rounded-full overflow-hidden flex-shrink-0 bg-linen border border-bronze flex items-center justify-center">
                {persona?.portrait_url ? (
                  <Image
                    src={persona.portrait_url}
                    alt={mirror.host_persona_name}
                    width={72}
                    height={72}
                    className="object-cover w-full h-full"
                  />
                ) : (
                  <span className="font-cormorant text-[28px] font-medium text-charcoal">
                    {mirror.host_persona_name.charAt(0)}
                  </span>
                )}
              </div>
              <button type="button" onClick={openPicker} className="flex flex-col gap-[2px] text-left">
                <p className="font-lora text-[11px] uppercase tracking-wide text-sepia">Through</p>
                <p className="font-cormorant text-[30px] font-medium text-ink leading-none flex items-center gap-[4px]">
                  {mirror.host_persona_name}
                  <ChevronRight size={16} strokeWidth={1.5} className="text-bronze" />
                </p>
                <p className="font-lora text-[12px] text-sepia">
                  {formatWeekSpan(mirror.period_start, mirror.period_end)}
                </p>
              </button>
            </div>
          )}
        </div>
      </div>

      {!mirror && (
        <div className="relative z-10 px-[16px]">
          <div className="bg-paper border-[0.5px] border-edge rounded-[18px] shadow-card px-[16px] py-[32px] text-center">
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
        <div className="relative z-10 px-[16px] flex flex-col gap-[16px]">
          <div className="bg-paper border-[0.5px] border-edge rounded-[18px] shadow-card px-[20px] py-[28px] flex flex-col gap-[28px]">

            {/* 1. Section label */}
            <p className="font-lora text-[11px] font-semibold uppercase tracking-[0.2em] text-bronze-dark">
              Beneath the words
            </p>

            {/* 2. Moments */}
            {mirror.payload?.moments && mirror.payload.moments.length > 0 && (
              <div className="flex flex-col gap-[24px]">
                {mirror.payload.moments.map((moment, i) => (
                  <Fragment key={i}>
                    {i > 0 && (
                      <div className="flex justify-center" aria-hidden="true">
                        <span className="text-bronze text-[12px] tracking-[0.3em] opacity-70">◆</span>
                      </div>
                    )}
                    <div>
                      <div className="bg-linen-deep/30 rounded-[10px] p-[12px_14px]">
                        <p className="font-lora text-[10.5px] font-semibold uppercase tracking-[0.16em] text-charcoal mb-[6px]">
                          What you said
                        </p>
                        <p className="font-lora italic text-[14px] text-sepia leading-[1.55] line-clamp-3">
                          &ldquo;{moment.said}&rdquo;
                        </p>
                      </div>
                      <div className="border-l-[3px] border-bronze pl-[16px] mt-[12px]">
                        <p className="font-lora text-[10.5px] font-semibold uppercase tracking-[0.16em] text-bronze-dark mb-[6px]">
                          What it may mean
                        </p>
                        <p className="font-cormorant text-[22px] text-ink leading-snug">
                          {moment.meant}
                        </p>
                      </div>
                    </div>
                  </Fragment>
                ))}
              </div>
            )}

            {/* 3. Divider */}
            <div className="h-px bg-edge my-[30px]" />

            {/* 4. Synthesis (thread moved here, centered, host-attributed) */}
            {mirror.payload?.thread && (
              <div className="text-center">
                <p className="font-lora text-[11px] font-semibold uppercase tracking-[0.2em] text-bronze-dark mb-[14px]">
                  {mirror.host_persona_name ? `What ${mirror.host_persona_name} sees` : 'The reflection'}
                </p>
                <p className="font-cormorant text-[25px] text-ink leading-snug">{mirror.payload.thread}</p>
              </div>
            )}

            {/* 5. Humility */}
            <p className="font-cormorant italic text-[17px] text-sepia text-center my-[28px]">
              This may be wrong. If it is, set it down.
            </p>

            {/* 6. Ring-true */}
            <div className="flex flex-col items-center gap-[12px]">
              <p className="font-lora text-[11px] font-semibold uppercase tracking-[0.18em] text-charcoal text-center">
                Does this ring true?
              </p>
              <div className="flex gap-[8px] flex-wrap justify-center">
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
                      'font-lora text-[13px] px-[16px] py-[8px] rounded-full transition-colors',
                      ringTrue === value
                        ? 'border-[1.5px] border-bronze bg-bronze/10 text-bronze'
                        : 'border-[1.5px] border-bronze text-charcoal',
                      ringTrueSubmitted && ringTrue !== value ? 'opacity-40' : '',
                    ].join(' ')}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {ringTrueSubmitted && (
                <p className="font-lora text-[12px] text-sepia italic">Noted.</p>
              )}
            </div>

          </div>

          <div className="flex flex-col gap-[10px]">
            {mirror.host_persona_slug && mirror.host_persona_name && (
              <button
                type="button"
                onClick={handleContinueWithHost}
                disabled={startingConv}
                className="w-full py-[14px] rounded-[14px] bg-ink text-vellum font-cormorant text-[17px] font-medium disabled:opacity-60"
              >
                {startingConv ? 'Opening…' : `Continue with ${mirror.host_persona_name}`}
              </button>
            )}

            <button
              type="button"
              onClick={() => {
                sessionStorage.setItem('council_prefill', mirror.payload?.thread ?? '')
                sessionStorage.setItem('council_source', 'mirror')
                sessionStorage.setItem('council_mirror_id', mirror.id)
                router.push('/council')
              }}
              className="w-full py-[14px] rounded-[14px] border-[0.5px] border-bronze font-cormorant text-[17px] font-medium text-ink"
            >
              Take it to the Council
            </button>
          </div>
        </div>
      )}
      {pickerOpen && (
        <>
          <div
            className="fixed inset-0 bg-ink/40 z-40"
            onClick={() => setPickerOpen(false)}
          />
          <div
            className="fixed bottom-0 left-0 right-0 z-50 bg-paper rounded-t-[20px] px-[20px] pt-[20px] pb-[32px] shadow-card"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="font-cormorant text-[24px] font-medium text-ink">Whose eyes?</p>
            <p className="font-lora text-[13px] text-sepia mt-[4px]">
              Choose the mind that holds your weekly mirror. Your next mirror will come through them.
            </p>
            <div className="flex flex-col mt-[12px]">
              {hosts.map((host) => (
                <button
                  key={host.slug}
                  type="button"
                  onClick={() => chooseHost(host.slug, host.name)}
                  className="flex items-center gap-[14px] py-[12px] w-full"
                >
                  <div className="w-[48px] h-[48px] rounded-full overflow-hidden flex-shrink-0 bg-linen flex items-center justify-center">
                    {host.portrait_url ? (
                      <Image
                        src={host.portrait_url}
                        alt={host.name}
                        width={48}
                        height={48}
                        className="object-cover w-full h-full"
                      />
                    ) : (
                      <span className="font-cormorant text-[20px] font-medium text-charcoal">
                        {host.name.charAt(0)}
                      </span>
                    )}
                  </div>
                  <span className="font-cormorant text-[22px] text-ink flex-1 text-left">{host.name}</span>
                  {host.slug === selectedHost && (
                    <Check size={18} className="text-bronze" />
                  )}
                </button>
              ))}
            </div>
            {savedHostName && (
              <p className="font-lora text-[13px] text-bronze-dark italic">
                Your next mirror will come through {savedHostName}.
              </p>
            )}
            <button
              type="button"
              onClick={() => setPickerOpen(false)}
              className="w-full mt-[20px] bg-ink text-vellum rounded-[14px] py-[14px] font-cormorant text-[17px]"
            >
              Done
            </button>
          </div>
        </>
      )}
    </main>
  )
}
