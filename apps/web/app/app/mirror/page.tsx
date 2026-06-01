'use client'

import { Fragment, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Check, ChevronLeft, ChevronRight } from 'lucide-react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { Mirror, MirrorHost, Persona } from '@/lib/api'
import styles from '../council/council.module.css'

// ──────────────────────────────────────────────
// Constants (same values as Council)
// ──────────────────────────────────────────────
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
const INTRO_HOLD = 1100
const WORD_STAGGER = 105
const SENTENCE_PAUSE = 480
const VEIL_OPACITY = 0.75

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

// ──────────────────────────────────────────────
// Word-reveal helpers
// ──────────────────────────────────────────────
type RevealSeg = { key: string; words: string[]; startIdx: number }

function tokenize(text: string): string[] {
  return text.split(/\s+/).filter(Boolean)
}

function sentenceEnds(word: string): boolean {
  return /[.!?]["')\]]*$/.test(word)
}

function buildSegs(mirror: Mirror): { segs: RevealSeg[]; flatWords: string[] } {
  const segs: RevealSeg[] = []
  const flatWords: string[] = []
  if (mirror.payload?.moments) {
    for (let i = 0; i < mirror.payload.moments.length; i++) {
      const m = mirror.payload.moments[i]
      const sw = tokenize(m.said)
      segs.push({ key: `said_${i}`, words: sw, startIdx: flatWords.length })
      flatWords.push(...sw)
      const mw = tokenize(m.meant)
      segs.push({ key: `meant_${i}`, words: mw, startIdx: flatWords.length })
      flatWords.push(...mw)
    }
  }
  if (mirror.payload?.thread) {
    const tw = tokenize(mirror.payload.thread)
    segs.push({ key: 'thread', words: tw, startIdx: flatWords.length })
    flatWords.push(...tw)
  }
  return { segs, flatWords }
}

function segWords(segs: RevealSeg[], key: string, totalRevealed: number): string[] {
  const seg = segs.find(s => s.key === key)
  if (!seg) return []
  return seg.words.slice(0, Math.max(0, Math.min(totalRevealed - seg.startIdx, seg.words.length)))
}

// ──────────────────────────────────────────────
// Component
// ──────────────────────────────────────────────
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

  // ── Animation state ──
  const [animPhase, setAnimPhase] = useState<'idle' | 'intro' | 'revealing' | 'done'>('idle')
  const [totalRevealed, setTotalRevealed] = useState(0)

  // ── Animation refs ──
  const segsRef = useRef<RevealSeg[]>([])
  const flatWordsRef = useRef<string[]>([])
  const totalRevealedRef = useRef(0)
  const animRef = useRef<{
    phase: 'idle' | 'intro' | 'revealing' | 'done'
    phaseStart: number
    lastWordTime: number
    nextWordDelay: number
  }>({ phase: 'idle', phaseStart: 0, lastWordTime: 0, nextWordDelay: WORD_STAGGER })
  const rafRef = useRef<number | null>(null)

  // ── Scroll refs ──
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)
  const scrollPendingRef = useRef(false)
  const autoScrollPaused = useRef(false)

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

        if (m) {
          const { segs, flatWords } = buildSegs(m)
          segsRef.current = segs
          flatWordsRef.current = flatWords
          animRef.current = {
            phase: 'intro',
            phaseStart: performance.now(),
            lastWordTime: 0,
            nextWordDelay: WORD_STAGGER,
          }
          setAnimPhase('intro')
          rafRef.current = requestAnimationFrame(tick)
        }
      } finally {
        setLoading(false)
      }
    }

    load()

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [token, router])

  // ──────────────────────────────────────────────
  // Animation tick (rAF loop) — same pattern as Council
  // ──────────────────────────────────────────────
  function tick(now: number) {
    if (scrollPendingRef.current && !autoScrollPaused.current) {
      sentinelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
      scrollPendingRef.current = false
    }

    const a = animRef.current

    if (a.phase === 'intro') {
      if (now - a.phaseStart >= INTRO_HOLD) {
        a.phase = 'revealing'
        a.lastWordTime = now
        a.nextWordDelay = WORD_STAGGER
        scrollPendingRef.current = true
        setAnimPhase('revealing')
      }
    } else if (a.phase === 'revealing') {
      const flatWords = flatWordsRef.current
      const revealed = totalRevealedRef.current

      if (now - a.lastWordTime >= a.nextWordDelay && revealed < flatWords.length) {
        const next = revealed + 1
        totalRevealedRef.current = next
        a.lastWordTime = now
        const justRevealed = flatWords[revealed]
        const jitter = Math.random() * 20 - 10
        a.nextWordDelay = WORD_STAGGER + jitter + (sentenceEnds(justRevealed) ? SENTENCE_PAUSE : 0)
        if (next % 4 === 0) scrollPendingRef.current = true
        setTotalRevealed(next)
      } else if (revealed >= flatWords.length) {
        a.phase = 'done'
        scrollPendingRef.current = true
        setAnimPhase('done')
        return
      }
    }

    if (a.phase !== 'done') {
      rafRef.current = requestAnimationFrame(tick)
    }
  }

  function handleScrollContainer(e: React.UIEvent<HTMLDivElement>) {
    const el = e.currentTarget
    const fromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    autoScrollPaused.current = fromBottom > 80
  }

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

  // ── Loading skeleton ──
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
  const showContent = animPhase === 'revealing' || animPhase === 'done'
  const threadW = mirror ? segWords(segsRef.current, 'thread', totalRevealed) : []

  return (
    <main className="relative min-h-screen [min-height:100svh] overflow-hidden">
      {/* Full-bleed background + vellum veil */}
      <div className="fixed inset-0 z-0">
        <Image
          src="/personas/mirror.png"
          alt=""
          fill
          className="object-cover object-center"
          priority
        />
        <div className="absolute inset-0" style={{ backgroundColor: '#EFE3CC', opacity: VEIL_OPACITY }} />
      </div>

      {/* Scrollable content with faint readability scrim */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScrollContainer}
        className="relative z-10 min-h-screen [min-height:100svh] overflow-y-auto px-[24px] pt-[22px] pb-[56px] flex flex-col gap-[32px]"
        style={{ background: 'linear-gradient(to bottom, rgba(239,227,204,0.10) 0%, rgba(239,227,204,0.22) 100%)' }}
      >
        {/* Header — always shown after loading */}
        <div>
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

        {/* No mirror yet */}
        {!mirror && (
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
        )}

        {/* Mirror payload — hidden during intro hold, reveals word-by-word after */}
        {mirror && showContent && (
          <div className="flex flex-col gap-[16px]">
            <div className="bg-paper border-[0.5px] border-edge rounded-[18px] shadow-card px-[20px] py-[28px] flex flex-col gap-[28px]">

              <p className="font-lora text-[11px] font-semibold uppercase tracking-[0.2em] text-bronze-dark">
                Beneath the words
              </p>

              {mirror.payload?.moments && mirror.payload.moments.length > 0 && (
                <div className="flex flex-col gap-[24px]">
                  {mirror.payload.moments.map((moment, i) => {
                    const saidW = segWords(segsRef.current, `said_${i}`, totalRevealed)
                    const meantW = segWords(segsRef.current, `meant_${i}`, totalRevealed)
                    return (
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
                            <p className="font-lora italic text-[14px] text-sepia leading-[1.55]">
                              {saidW.map((word, wi) => (
                                <Fragment key={wi}>
                                  {wi > 0 && ' '}
                                  <span className={styles.word}>{word}</span>
                                </Fragment>
                              ))}
                            </p>
                          </div>
                          <div className="border-l-[3px] border-bronze pl-[16px] mt-[12px]">
                            <p className="font-lora text-[10.5px] font-semibold uppercase tracking-[0.16em] text-bronze-dark mb-[6px]">
                              What it may mean
                            </p>
                            <p className="font-cormorant text-[22px] text-ink leading-snug">
                              {meantW.map((word, wi) => (
                                <Fragment key={wi}>
                                  {wi > 0 && ' '}
                                  <span className={styles.word}>{word}</span>
                                </Fragment>
                              ))}
                            </p>
                          </div>
                        </div>
                      </Fragment>
                    )
                  })}
                </div>
              )}

              {/* Thread — appears when first thread word is ready */}
              {threadW.length > 0 && (
                <>
                  <div className="h-px bg-edge my-[30px]" />
                  <div className="text-center">
                    <p className="font-lora text-[11px] font-semibold uppercase tracking-[0.2em] text-bronze-dark mb-[14px]">
                      {mirror.host_persona_name ? `What ${mirror.host_persona_name} sees` : 'The reflection'}
                    </p>
                    <p className="font-cormorant text-[25px] text-ink leading-snug">
                      {threadW.map((word, wi) => (
                        <Fragment key={wi}>
                          {wi > 0 && ' '}
                          <span className={styles.word}>{word}</span>
                        </Fragment>
                      ))}
                    </p>
                  </div>
                </>
              )}

              {/* Humility + ring-true — appear when all words are revealed */}
              {animPhase === 'done' && (
                <>
                  <p className="font-cormorant italic text-[17px] text-sepia text-center my-[28px]">
                    This may be wrong. If it is, set it down.
                  </p>
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
                </>
              )}
            </div>

            {/* CTAs — appear when all words are revealed */}
            {animPhase === 'done' && (
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
                    router.push('/app/council')
                  }}
                  className="w-full py-[14px] rounded-[14px] border-[1.5px] border-bronze font-cormorant text-[17px] font-medium text-ink"
                >
                  Take it to the Council
                </button>
              </div>
            )}
          </div>
        )}

        {/* Bottom sentinel — auto-scroll target */}
        <div ref={sentinelRef} aria-hidden="true" />
      </div>

      {/* Picker sheet — unchanged */}
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
