'use client'

import { Fragment, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Bookmark, Share2 } from 'lucide-react'
import { useStore } from '@/lib/store'
import { api, RateLimitError } from '@/lib/api'
import type { SSEEvent, SSEEventMember } from '@/lib/api'
import styles from './council.module.css'

// ──────────────────────────────────────────────
// Constants (all tunable)
// ──────────────────────────────────────────────
const MATTER_MAX = 600
const INTRO_HOLD = 1100
const WORD_STAGGER = 105
const SENTENCE_PAUSE = 480
const SEAT_LIGHT = 950
const MEMBER_GAP = 1500

// ──────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────
type BenchState = 'pending' | 'lighting' | 'speaking' | 'done'

type BenchItem = {
  slug: string
  name: string
  position: number
  portraitUrl: string
  benchState: BenchState
}

type VerdictCard = {
  slug: string
  name: string
  portraitUrl: string
  revealedWords: string[]
}

type SessionPhase = {
  kind: 'session'
  bench: BenchItem[]
  verdicts: VerdictCard[]
  synthesisWords: string[]
  synthesisActive: boolean
  allDone: boolean
}

type VisualPhase =
  | { kind: 'idle' }
  | { kind: 'intro' }
  | { kind: 'convening' }
  | SessionPhase
  | { kind: 'safety' }
  | { kind: 'error'; message: string }

type AnimPhase = 'idle' | 'intro' | 'convening' | 'seat' | 'speak' | 'gap' | 'synthesis' | 'done'

// ──────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────
function tokenize(text: string): string[] {
  return text.split(/\s+/).filter(Boolean)
}

function sentenceEnds(word: string): boolean {
  return /[.!?]["')\]]*$/.test(word)
}

// ──────────────────────────────────────────────
// Component
// ──────────────────────────────────────────────
export default function CouncilPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [matter, setMatter] = useState('')
  const [source, setSource] = useState('direct')
  const [mirrorId, setMirrorId] = useState<string | null>(null)
  const [phase, setPhase] = useState<VisualPhase>({ kind: 'idle' })

  // ── Network-side refs (mutated by SSE, read by animation tick) ──
  const portraits = useRef(new Map<string, string>())
  const memberBufs = useRef(
    new Map<string, { text: string; netDone: boolean; name: string; position: number }>()
  )
  const memberOrder = useRef<string[]>([])
  const synBuf = useRef({ text: '', netDone: false })
  const synStartedRef = useRef(false)
  const netErrRef = useRef<{ kind: 'safety' | 'error'; message: string } | null>(null)

  // ── Animation-side refs ──
  const revealedBySlug = useRef(new Map<string, number>())
  const synRevealedRef = useRef(0)

  const anim = useRef<{
    phase: AnimPhase
    phaseStart: number
    memberIdx: number
    nextWordDelay: number
    lastWordTime: number
  }>({ phase: 'idle', phaseStart: 0, memberIdx: -1, nextWordDelay: WORD_STAGGER, lastWordTime: 0 })

  const rafRef = useRef<number | null>(null)

  // ──────────────────────────────────────────────
  // Mount
  // ──────────────────────────────────────────────
  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }

    api.getPersonas().then((ps) => {
      for (const p of ps) portraits.current.set(p.slug, p.portrait_url ?? '')
    }).catch(() => {})

    const prefill = sessionStorage.getItem('council_prefill') ?? ''
    const src = sessionStorage.getItem('council_source') ?? 'direct'
    const mid = sessionStorage.getItem('council_mirror_id') ?? null
    sessionStorage.removeItem('council_prefill')
    sessionStorage.removeItem('council_source')
    sessionStorage.removeItem('council_mirror_id')
    if (prefill) setMatter(prefill)
    setSource(src)
    setMirrorId(mid)

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [token, router])

  // ──────────────────────────────────────────────
  // Bench builder (reads only refs, safe in stale closures)
  // ──────────────────────────────────────────────
  function buildBench(activeIdx: number, activeState: BenchState): BenchItem[] {
    const slugs = [...memberOrder.current].sort((a, b) => {
      const pa = memberBufs.current.get(a)?.position ?? 0
      const pb = memberBufs.current.get(b)?.position ?? 0
      return pa - pb
    })
    return slugs.map((slug) => {
      const buf = memberBufs.current.get(slug)!
      const idx = memberOrder.current.indexOf(slug)
      let benchState: BenchState
      if (idx < activeIdx) benchState = 'done'
      else if (idx === activeIdx) benchState = activeState
      else benchState = 'pending'
      return {
        slug,
        name: buf.name,
        position: buf.position,
        portraitUrl: portraits.current.get(slug) ?? '',
        benchState,
      }
    })
  }

  // ──────────────────────────────────────────────
  // Animation tick (rAF loop)
  // ──────────────────────────────────────────────
  function tick(now: number) {
    const a = anim.current

    // Network errors take priority — checked every frame
    if (netErrRef.current) {
      const err = netErrRef.current
      netErrRef.current = null
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current)
        rafRef.current = null
      }
      setPhase(err.kind === 'safety' ? { kind: 'safety' } : { kind: 'error', message: err.message })
      return
    }

    switch (a.phase) {
      case 'intro': {
        if (now - a.phaseStart >= INTRO_HOLD) {
          a.phase = 'convening'
          setPhase({ kind: 'convening' })
        }
        break
      }

      case 'convening': {
        if (memberOrder.current.length > 0) {
          a.phase = 'seat'
          a.memberIdx = 0
          a.phaseStart = now
          setPhase({
            kind: 'session',
            bench: buildBench(0, 'lighting'),
            verdicts: [],
            synthesisWords: [],
            synthesisActive: false,
            allDone: false,
          })
        }
        break
      }

      case 'seat': {
        if (now - a.phaseStart >= SEAT_LIGHT) {
          const slug = memberOrder.current[a.memberIdx]
          a.phase = 'speak'
          a.lastWordTime = now
          a.nextWordDelay = WORD_STAGGER
          const name = memberBufs.current.get(slug)?.name ?? ''
          const portraitUrl = portraits.current.get(slug) ?? ''
          setPhase((prev) => {
            if (prev.kind !== 'session') return prev
            return {
              ...prev,
              bench: buildBench(a.memberIdx, 'speaking'),
              verdicts: [...prev.verdicts, { slug, name, portraitUrl, revealedWords: [] }],
            }
          })
        }
        break
      }

      case 'speak': {
        const slug = memberOrder.current[a.memberIdx]
        const buf = memberBufs.current.get(slug)
        if (!buf) break

        const words = tokenize(buf.text)
        const revealed = revealedBySlug.current.get(slug) ?? 0

        if (now - a.lastWordTime >= a.nextWordDelay && revealed < words.length) {
          const next = revealed + 1
          revealedBySlug.current.set(slug, next)
          a.lastWordTime = now
          // Delay for the NEXT word is based on the word we just revealed
          const justRevealed = words[revealed]
          const jitter = Math.random() * 20 - 10
          a.nextWordDelay = WORD_STAGGER + jitter + (sentenceEnds(justRevealed) ? SENTENCE_PAUSE : 0)

          const slice = words.slice(0, next)
          setPhase((prev) => {
            if (prev.kind !== 'session') return prev
            return {
              ...prev,
              verdicts: prev.verdicts.map((v) =>
                v.slug === slug ? { ...v, revealedWords: slice } : v
              ),
            }
          })
        } else if (revealed >= words.length && buf.netDone) {
          a.phase = 'gap'
          a.phaseStart = now
          setPhase((prev) => {
            if (prev.kind !== 'session') return prev
            return { ...prev, bench: buildBench(a.memberIdx, 'done') }
          })
        }
        break
      }

      case 'gap': {
        if (now - a.phaseStart >= MEMBER_GAP) {
          const nextIdx = a.memberIdx + 1
          if (nextIdx < memberOrder.current.length) {
            a.phase = 'seat'
            a.memberIdx = nextIdx
            a.phaseStart = now
            setPhase((prev) => {
              if (prev.kind !== 'session') return prev
              return { ...prev, bench: buildBench(nextIdx, 'lighting') }
            })
          } else if (synStartedRef.current) {
            a.phase = 'synthesis'
            a.lastWordTime = now
            a.nextWordDelay = WORD_STAGGER
            setPhase((prev) => {
              if (prev.kind !== 'session') return prev
              return { ...prev, synthesisActive: true }
            })
          }
          // else: wait for next member event or synthesis_start
        }
        break
      }

      case 'synthesis': {
        const words = tokenize(synBuf.current.text)
        const revealed = synRevealedRef.current

        if (now - a.lastWordTime >= a.nextWordDelay && revealed < words.length) {
          const next = revealed + 1
          synRevealedRef.current = next
          a.lastWordTime = now
          const justRevealed = words[revealed]
          const jitter = Math.random() * 20 - 10
          a.nextWordDelay = WORD_STAGGER + jitter + (sentenceEnds(justRevealed) ? SENTENCE_PAUSE : 0)

          const slice = words.slice(0, next)
          setPhase((prev) => {
            if (prev.kind !== 'session') return prev
            return { ...prev, synthesisWords: slice }
          })
        } else if (revealed >= words.length && synBuf.current.netDone) {
          a.phase = 'done'
          setPhase((prev) => {
            if (prev.kind !== 'session') return prev
            return { ...prev, allDone: true, synthesisActive: false }
          })
        }
        break
      }
    }

    if (a.phase !== 'idle' && a.phase !== 'done') {
      rafRef.current = requestAnimationFrame(tick)
    }
  }

  // ──────────────────────────────────────────────
  // Reset helpers
  // ──────────────────────────────────────────────
  function resetSession() {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    memberBufs.current.clear()
    memberOrder.current = []
    synBuf.current = { text: '', netDone: false }
    synStartedRef.current = false
    netErrRef.current = null
    revealedBySlug.current.clear()
    synRevealedRef.current = 0
    anim.current = { phase: 'idle', phaseStart: 0, memberIdx: -1, nextWordDelay: WORD_STAGGER, lastWordTime: 0 }
  }

  function handleReset() {
    resetSession()
    setPhase({ kind: 'idle' })
    setMatter('')
  }

  // ──────────────────────────────────────────────
  // Convene
  // ──────────────────────────────────────────────
  async function handleConvene() {
    if (!matter.trim() || phase.kind !== 'idle') return

    resetSession()
    anim.current.phase = 'intro'
    anim.current.phaseStart = performance.now()
    setPhase({ kind: 'intro' })
    rafRef.current = requestAnimationFrame(tick)

    try {
      const res = await api.streamCouncil({
        matter: matter.trim(),
        source,
        mirror_id: mirrorId,
      })

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let sseBuf = ''
      let activeSlug: string | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        sseBuf += decoder.decode(value, { stream: true })
        const lines = sseBuf.split('\n')
        sseBuf = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          let event: SSEEvent
          try { event = JSON.parse(raw) as SSEEvent }
          catch { continue }

          switch (event.type) {
            case 'member': {
              const ev = event as SSEEventMember
              if (activeSlug) {
                const prev = memberBufs.current.get(activeSlug)
                if (prev) prev.netDone = true
              }
              memberOrder.current = [...memberOrder.current, ev.slug]
              memberBufs.current.set(ev.slug, { text: '', netDone: false, name: ev.name, position: ev.position })
              activeSlug = ev.slug
              break
            }
            case 'chunk': {
              if (synStartedRef.current) {
                synBuf.current.text += event.data
              } else if (activeSlug) {
                const buf = memberBufs.current.get(activeSlug)
                if (buf) buf.text += event.data
              }
              break
            }
            case 'synthesis_start': {
              if (activeSlug) {
                const buf = memberBufs.current.get(activeSlug)
                if (buf) buf.netDone = true
              }
              activeSlug = null
              synStartedRef.current = true
              break
            }
            case 'done':
            case 'synthesis_error': {
              synBuf.current.netDone = true
              break
            }
            case 'safety':
            case 'safety_override': {
              netErrRef.current = { kind: 'safety', message: '' }
              break
            }
            case 'error': {
              netErrRef.current = { kind: 'error', message: event.error_code ?? 'Something went wrong.' }
              break
            }
          }
        }
      }
    } catch (err) {
      netErrRef.current = {
        kind: 'error',
        message: err instanceof RateLimitError
          ? 'You have reached your weekly Council limit.'
          : 'Something went wrong. Please try again.',
      }
    }
  }

  // ──────────────────────────────────────────────
  // Render — Idle
  // ──────────────────────────────────────────────
  const canSubmit = matter.trim().length > 0 && matter.length <= MATTER_MAX && phase.kind === 'idle'

  if (phase.kind === 'idle') {
    return (
      <main className="min-h-screen [min-height:100svh] bg-vellum px-[24px] pt-[32px] pb-[40px] flex flex-col gap-[24px]">
        <div>
          <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark mb-[6px]">
            THE COUNCIL
          </p>
          <h1 className="font-cormorant text-[44px] font-medium text-ink leading-tight">
            The council is in session
          </h1>
        </div>

        <div className="flex flex-col gap-[12px]">
          <textarea
            value={matter}
            onChange={(e) => setMatter(e.target.value)}
            maxLength={MATTER_MAX}
            rows={6}
            placeholder="What do you want the council to consider?"
            className="w-full bg-paper border-[0.5px] border-edge rounded-[14px] px-[16px] py-[14px] font-lora text-[15px] text-ink placeholder:text-sepia/50 resize-none focus:outline-none focus:ring-1 focus:ring-bronze"
          />
          <div className="flex items-center justify-between">
            <span className={`font-lora text-[11px] ${matter.length > MATTER_MAX ? 'text-safety' : 'text-sepia'}`}>
              {matter.length} / {MATTER_MAX}
            </span>
            <button
              type="button"
              disabled={!canSubmit}
              onClick={handleConvene}
              className="font-cormorant text-[17px] font-medium px-[24px] py-[12px] rounded-[12px] bg-ink text-vellum disabled:opacity-40"
            >
              Convene the council
            </button>
          </div>
        </div>
      </main>
    )
  }

  // ──────────────────────────────────────────────
  // Render — Session (intro / convening / session / safety / error)
  // ──────────────────────────────────────────────
  return (
    <main className="relative min-h-screen [min-height:100svh] overflow-hidden">
      {/* Full-bleed background + vellum veil */}
      <div className="fixed inset-0 z-0">
        <Image
          src="/personas/boardroom.webp"
          alt=""
          fill
          className="object-cover object-center"
          priority
        />
        <div className="absolute inset-0" style={{ backgroundColor: '#EFE3CC', opacity: 0.85 }} />
      </div>

      {/* Scrollable content */}
      <div className="relative z-10 min-h-screen [min-height:100svh] overflow-y-auto px-[24px] pt-[44px] pb-[56px] flex flex-col gap-[32px]">

        {/* ── Header (convening + session) ── */}
        {(phase.kind === 'convening' || phase.kind === 'session') && (
          <div className="text-center">
            <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark mb-[6px]">
              THE COUNCIL
            </p>
            <h1 className="font-cormorant text-[44px] font-medium text-ink leading-tight">
              The council is in session
            </h1>
            {matter && (
              <p className="font-lora italic text-[14.5px] leading-relaxed text-charcoal mt-[12px] max-w-[300px] mx-auto">
                {matter}
              </p>
            )}
          </div>
        )}

        {/* ── Convening indicator ── */}
        {phase.kind === 'convening' && (
          <p className="font-lora italic text-[15px] text-sepia text-center">
            The council convenes…
          </p>
        )}

        {/* ── Session ── */}
        {phase.kind === 'session' && (
          <>
            {/* Bench */}
            {phase.bench.length > 0 && (
              <div className="flex justify-center gap-[18px] flex-wrap">
                {phase.bench.map((m) => (
                  <BenchPortrait key={m.slug} member={m} />
                ))}
              </div>
            )}

            {/* Verdicts */}
            {phase.verdicts.length > 0 && (
              <div className="flex flex-col gap-[36px]">
                {phase.verdicts.map((v) => (
                  <VerdictBlock key={v.slug} verdict={v} />
                ))}
              </div>
            )}

            {/* Synthesis card */}
            {(phase.synthesisActive || phase.synthesisWords.length > 0) && (
              <div className="bg-paper border border-edge rounded-[16px] px-[24px] py-[28px] flex flex-col gap-[20px]">
                <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark text-center">
                  THE COUNCIL&apos;S READING
                </p>
                <p className="font-cormorant text-[21px] text-ink leading-snug">
                  {phase.synthesisWords.map((word, i) => (
                    <Fragment key={i}>
                      {i > 0 && ' '}
                      <span className={styles.word}>{word}</span>
                    </Fragment>
                  ))}
                </p>
                {phase.allDone && (
                  <div className="flex gap-[10px] justify-center flex-wrap">
                    <button
                      type="button"
                      onClick={() => {}}
                      className="flex items-center gap-[6px] font-lora text-[13px] text-sepia border-[0.5px] border-edge rounded-full px-[16px] py-[8px]"
                    >
                      <Bookmark size={14} strokeWidth={1.5} />
                      Save reading
                    </button>
                    <button
                      type="button"
                      onClick={() => {}}
                      className="flex items-center gap-[6px] font-lora text-[13px] text-sepia border-[0.5px] border-edge rounded-full px-[16px] py-[8px]"
                    >
                      <Share2 size={14} strokeWidth={1.5} />
                      Share reading
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Footer */}
            {phase.allDone && (
              <div className="text-center">
                <button
                  type="button"
                  onClick={handleReset}
                  className="font-lora text-[13px] text-sepia underline underline-offset-2"
                >
                  Bring another matter
                </button>
              </div>
            )}
          </>
        )}

        {/* ── Safety ── */}
        {phase.kind === 'safety' && (
          <div className="bg-paper/90 border-[0.5px] border-edge rounded-[14px] px-[20px] py-[24px] text-center mt-[40px]">
            <p className="font-lora text-[14px] text-charcoal leading-relaxed">
              The council cannot meet on this matter.
            </p>
            <button
              type="button"
              onClick={handleReset}
              className="mt-[16px] font-lora text-[13px] text-sepia underline underline-offset-2"
            >
              Try a different matter
            </button>
          </div>
        )}

        {/* ── Error ── */}
        {phase.kind === 'error' && (
          <div className="bg-paper/90 border-[0.5px] border-edge rounded-[14px] px-[20px] py-[24px] text-center mt-[40px]">
            <p className="font-lora text-[14px] text-charcoal leading-relaxed">{phase.message}</p>
            <button
              type="button"
              onClick={handleReset}
              className="mt-[16px] font-lora text-[13px] text-sepia underline underline-offset-2"
            >
              Try again
            </button>
          </div>
        )}
      </div>
    </main>
  )
}

// ──────────────────────────────────────────────
// Sub-components
// ──────────────────────────────────────────────

function BenchPortrait({ member }: { member: BenchItem }) {
  const isLit = member.benchState === 'lighting' || member.benchState === 'speaking'
  const isDimmed = member.benchState === 'pending' || member.benchState === 'done'

  return (
    <div className="flex flex-col items-center gap-[6px]">
      <div
        className={[
          'w-[84px] h-[84px] rounded-full overflow-hidden transition-all duration-500',
          isLit
            ? 'ring-[2.5px] ring-[#B89968] shadow-[0_4px_18px_rgba(184,153,104,0.38)] -translate-y-[3px] opacity-100'
            : isDimmed
            ? 'opacity-40'
            : 'opacity-100',
        ].join(' ')}
      >
        {member.portraitUrl ? (
          <Image
            src={member.portraitUrl}
            alt={member.name}
            width={84}
            height={84}
            className="object-cover w-full h-full"
          />
        ) : (
          <div className="w-full h-full bg-linen flex items-center justify-center">
            <span className="font-cormorant text-[32px] font-medium text-charcoal">
              {member.name.charAt(0)}
            </span>
          </div>
        )}
      </div>
      <p
        className={`font-lora text-[11px] text-center leading-tight ${
          isDimmed ? 'text-sepia/50' : 'text-sepia'
        }`}
      >
        {member.name.split(' ')[0]}
      </p>
    </div>
  )
}

function VerdictBlock({ verdict }: { verdict: VerdictCard }) {
  return (
    <div className="flex flex-col gap-[12px]">
      <div className="flex items-center gap-[12px]">
        <div className="w-[60px] h-[60px] rounded-full overflow-hidden flex-shrink-0 bg-linen">
          {verdict.portraitUrl ? (
            <Image
              src={verdict.portraitUrl}
              alt={verdict.name}
              width={60}
              height={60}
              className="object-cover w-full h-full"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <span className="font-cormorant text-[24px] font-medium text-charcoal">
                {verdict.name.charAt(0)}
              </span>
            </div>
          )}
        </div>
        <p className="font-lora text-[11px] font-semibold uppercase tracking-[0.18em] text-bronze-dark">
          {verdict.name}
        </p>
      </div>
      <p className="font-cormorant text-[21px] text-ink leading-snug">
        {verdict.revealedWords.map((word, i) => (
          <Fragment key={i}>
            {i > 0 && ' '}
            <span className={styles.word}>{word}</span>
          </Fragment>
        ))}
      </p>
    </div>
  )
}
