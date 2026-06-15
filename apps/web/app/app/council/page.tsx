'use client'

import { Fragment, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Bookmark, Share2 } from 'lucide-react'
import { useStore } from '@/lib/store'
import { api, RateLimitError } from '@/lib/api'
import type { SSEEvent, SSEEventMember } from '@/lib/api'
import styles from './council.module.css'
import SharePreviewModal from '@/components/share/SharePreviewModal'
import WiseMark from '@/components/ui/WiseMark'
import SubPageNav from '@/components/layout/SubPageNav'

// ──────────────────────────────────────────────
// Constants (all tunable)
// ──────────────────────────────────────────────
const MATTER_MAX = 600
const INTRO_HOLD = 2100
const WORD_STAGGER = 105
const SENTENCE_PAUSE = 480
const SEAT_LIGHT = 950
const MEMBER_GAP = 1500
const VEIL_OPACITY = 0.75

// Backend sends members in this order; bench is always shown in this order.
const ROSTER = [
  'niccolo_machiavelli',
  'epictetus',
  'sigmund_freud',
  'simone_de_beauvoir',
] as const

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
  | { kind: 'convening'; bench: BenchItem[] }
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

function slugToDisplay(slug: string): string {
  return slug.replace(/_/g, ' ')
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
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [shareModalOpen, setShareModalOpen] = useState(false)

  // ── Network-side refs ──
  // slug → { name, portraitUrl } — loaded once from API, stable across sessions
  const rosterMeta = useRef(new Map<string, { name: string; portraitUrl: string }>())
  // slug → { text, netDone } — per-session text buffers
  const memberBufs = useRef(new Map<string, { text: string; netDone: boolean }>())
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

  // ── Scroll refs ──
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)
  const autoScrollPaused = useRef(false)
  // Set true before a setPhase that adds new content; consumed at the START of the next tick
  // (after React commits), so scrollIntoView sees the new DOM.
  const scrollPendingRef = useRef(false)

  // ──────────────────────────────────────────────
  // Mount
  // ──────────────────────────────────────────────
  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }

    api.getPersonas().then((ps) => {
      for (const p of ps) {
        rosterMeta.current.set(p.slug, { name: p.name, portraitUrl: p.portrait_url })
      }
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
  // Bench builder — always reads from ROSTER, safe in stale closures
  // activeIdx = -1 means all pending; index into ROSTER/memberOrder
  // ──────────────────────────────────────────────
  function buildBench(activeIdx: number, activeState: BenchState): BenchItem[] {
    return ROSTER.map((slug, idx) => {
      const meta = rosterMeta.current.get(slug)
      let benchState: BenchState
      if (idx < activeIdx) benchState = 'done'
      else if (idx === activeIdx) benchState = activeState
      else benchState = 'pending'
      return {
        slug,
        name: meta?.name ?? slugToDisplay(slug),
        position: idx,
        portraitUrl: meta?.portraitUrl ?? '',
        benchState,
      }
    })
  }

  // ──────────────────────────────────────────────
  // Animation tick (rAF loop)
  // ──────────────────────────────────────────────
  function tick(now: number) {
    // Execute scroll deferred from the previous frame's setPhase calls.
    // By the time this fires, React has committed those renders to the DOM.
    if (scrollPendingRef.current && !autoScrollPaused.current) {
      sentinelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
      scrollPendingRef.current = false
    }

    const a = anim.current

    // Network errors take priority
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
          // Show all-pending bench immediately on entering convening
          setPhase({ kind: 'convening', bench: buildBench(-1, 'pending') })
        }
        break
      }

      case 'convening': {
        if (memberOrder.current.length > 0) {
          a.phase = 'seat'
          a.memberIdx = 0
          a.phaseStart = now
          scrollPendingRef.current = true
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
          const meta = rosterMeta.current.get(slug)
          const name = meta?.name ?? slugToDisplay(slug)
          const portraitUrl = meta?.portraitUrl ?? ''
          // New verdict card is about to appear — scroll after render
          scrollPendingRef.current = true
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
          const justRevealed = words[revealed]
          const jitter = Math.random() * 20 - 10
          a.nextWordDelay = WORD_STAGGER + jitter + (sentenceEnds(justRevealed) ? SENTENCE_PAUSE : 0)

          // Scroll roughly every 1-2 lines (every 24th word)
          if (next % 24 === 0) scrollPendingRef.current = true

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
            scrollPendingRef.current = true
            setPhase((prev) => {
              if (prev.kind !== 'session') return prev
              return { ...prev, synthesisActive: true }
            })
          }
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

          if (next % 24 === 0) scrollPendingRef.current = true

          const slice = words.slice(0, next)
          setPhase((prev) => {
            if (prev.kind !== 'session') return prev
            return { ...prev, synthesisWords: slice }
          })
        } else if (revealed >= words.length && synBuf.current.netDone) {
          a.phase = 'done'
          scrollPendingRef.current = true
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
    autoScrollPaused.current = false
    scrollPendingRef.current = false
    anim.current = { phase: 'idle', phaseStart: 0, memberIdx: -1, nextWordDelay: WORD_STAGGER, lastWordTime: 0 }
  }

  function handleReset() {
    resetSession()
    setPhase({ kind: 'idle' })
    setMatter('')
    setSessionId(null)
    setSaved(false)
  }

  // ──────────────────────────────────────────────
  // Scroll guard — pauses auto-scroll when user scrolls away from bottom
  // ──────────────────────────────────────────────
  function handleScrollContainer(e: React.UIEvent<HTMLDivElement>) {
    const el = e.currentTarget
    const fromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    autoScrollPaused.current = fromBottom > 80
  }

  // ──────────────────────────────────────────────
  // Save / unsave reading
  // ──────────────────────────────────────────────
  async function handleSave() {
    if (!sessionId) return
    const next = !saved
    setSaved(next)
    try {
      if (next) {
        await api.saveCouncil(sessionId)
      } else {
        await api.unsaveCouncil(sessionId)
      }
    } catch {
      setSaved(!next) // revert on error
    }
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
              memberBufs.current.set(ev.slug, { text: '', netDone: false })
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
            case 'synthesis_error': {
              synBuf.current.netDone = true
              break
            }
            case 'done': {
              synBuf.current.netDone = true
              if (event.session_id) setSessionId(event.session_id)
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
  const fromMirror = source === 'mirror' && matter.length > 0

  if (phase.kind === 'idle') {
    return (
      <main className="min-h-screen [min-height:100svh] bg-vellum px-[24px] pt-[32px] pb-[40px] flex flex-col gap-[24px]">
        <div className="text-center">
          <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark mb-[6px]">
            THE COUNCIL
          </p>
          <h1 className="font-cormorant text-[44px] font-medium text-ink leading-tight">
            Bring your matter before them
          </h1>
        </div>

        <div className="flex flex-col gap-[12px]">
          {fromMirror && (
            <p className="font-lora text-[10px] uppercase tracking-[0.22em] text-bronze-dark">
              Carried from your mirror — make it your own
            </p>
          )}
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
        <div className="absolute inset-0" style={{ backgroundColor: '#EFE3CC', opacity: VEIL_OPACITY }} />
      </div>

      {/* Scrollable content with faint readability scrim */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScrollContainer}
        className="relative z-10 min-h-screen [min-height:100svh] overflow-y-auto px-[24px] pt-[44px] pb-[56px] flex flex-col gap-[32px]"
        style={{ background: 'linear-gradient(to bottom, rgba(239,227,204,0.10) 0%, rgba(239,227,204,0.22) 100%)' }}
      >
        <SubPageNav fallbackHref="/app/rituals" />

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

        {/* ── Convening: bench (all pending) + indicator ── */}
        {phase.kind === 'convening' && (
          <>
            <div className="flex justify-center gap-[10px] flex-nowrap">
              {phase.bench.map((m) => (
                <BenchPortrait key={m.slug} member={m} />
              ))}
            </div>
            <p className="font-lora italic text-[15px] text-sepia text-center">
              The council convenes…
            </p>
          </>
        )}

        {/* ── Session ── */}
        {phase.kind === 'session' && (
          <>
            {/* Bench — all 4 always shown */}
            <div className="flex justify-center gap-[10px] flex-nowrap">
              {phase.bench.map((m) => (
                <BenchPortrait key={m.slug} member={m} />
              ))}
            </div>

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
                <div className="flex items-center justify-center gap-[8px]">
                  <WiseMark size={24} />
                  <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark">
                    THE COUNCIL&apos;S READING
                  </p>
                </div>
                <p className="font-cormorant font-medium text-[21px] text-ink leading-snug">
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
                      onClick={handleSave}
                      disabled={!sessionId}
                      className="flex items-center gap-[6px] font-lora text-[15px] text-vellum bg-ink rounded-full px-[20px] py-[11px] disabled:opacity-40"
                    >
                      <Bookmark size={16} strokeWidth={1.5} fill={saved ? 'currentColor' : 'none'} />
                      {saved ? 'Saved' : 'Save reading'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShareModalOpen(true)}
                      disabled={!sessionId}
                      className="flex items-center gap-[6px] font-lora text-[13px] text-sepia border-[0.5px] border-edge rounded-full px-[16px] py-[8px] disabled:opacity-40"
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

        {/* Bottom sentinel — auto-scroll target */}
        <div ref={sentinelRef} aria-hidden="true" />
      </div>

      {/* Share modal */}
      <SharePreviewModal
        isOpen={shareModalOpen}
        onClose={() => setShareModalOpen(false)}
        kind="council"
        councilSessionId={sessionId ?? ''}
        quote={phase.kind === 'session' ? phase.synthesisWords.join(' ') : ''}
      />
    </main>
  )
}

// ──────────────────────────────────────────────
// Sub-components
// ──────────────────────────────────────────────

function BenchPortrait({ member }: { member: BenchItem }) {
  const isLit = member.benchState === 'lighting' || member.benchState === 'speaking'
  const isPending = member.benchState === 'pending'
  const isDone = member.benchState === 'done'

  return (
    <div className="flex flex-col items-center gap-[5px]">
      <div
        className={[
          'w-[66px] h-[66px] rounded-full overflow-hidden transition-all duration-500',
          isLit
            ? 'ring-[2.5px] ring-[#B89968] shadow-[0_4px_18px_rgba(184,153,104,0.4)] -translate-y-[3px]'
            : '',
        ].join(' ')}
        style={{
          opacity: isLit ? 1 : isPending ? 0.35 : isDone ? 0.5 : 1,
        }}
      >
        {member.portraitUrl ? (
          <Image
            src={member.portraitUrl}
            alt={member.name}
            width={66}
            height={66}
            className="object-cover w-full h-full"
          />
        ) : (
          <div className="w-full h-full bg-linen flex items-center justify-center">
            <span className="font-cormorant text-[28px] font-medium text-charcoal">
              {member.name.charAt(0)}
            </span>
          </div>
        )}
      </div>
      <p
        className={`font-lora text-[11px] font-medium text-center leading-tight ${isLit ? 'text-ink' : 'text-sepia'}`}
        style={{ opacity: isLit ? 1 : isPending ? 0.4 : 0.6 }}
      >
        {member.name.split(' ')[0]}
      </p>
    </div>
  )
}

function VerdictBlock({ verdict }: { verdict: VerdictCard }) {
  return (
    <div className="flex flex-col gap-[12px] bg-paper/90 border-[0.5px] border-edge rounded-[14px] px-[16px] py-[14px]">
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
      <p className="font-cormorant font-medium text-[21px] text-ink leading-snug">
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
