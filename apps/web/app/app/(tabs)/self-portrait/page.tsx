'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { SelfPortraitQuestion, SelfPortraitPortrait } from '@/lib/api'
import { BronzeDivider } from '@/components/ui/BronzeDivider'
import { observationFor } from '@/lib/selfPortraitObservations'
import {
  ThemeGlyph,
  CardArtwork,
  PatternArtwork,
  EyeGlyph,
} from '@/components/self-portrait/Artwork'
import { PortraitRadar } from '@/components/self-portrait/PortraitRadar'
import { PortraitMap } from '@/components/self-portrait/PortraitMap'
import { renderPortraitCardBlob, sharePortraitCardBlob } from '@/lib/portraitShareCard'
import { User, Shield, Feather, Flame, HelpCircle, Anchor, Users, Compass } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { topObservationCards, type CardIcon } from '@/lib/selfPortraitObservationCards'

// Card icon NAME → lucide component (the frozen card map stores names to stay plain data).
const CARD_ICONS: Record<CardIcon, LucideIcon> = {
  User,
  Shield,
  Feather,
  Flame,
  HelpCircle,
  Anchor,
  Users,
  Compass,
}

// Human-readable category labels. Title-case fallback for any value not listed
// (so a future bank category can never render blank or as a raw machine value).
const CATEGORY_LABELS: Record<string, string> = {
  conflict: 'Conflict',
  desire: 'Desire',
  family: 'Family',
  fear: 'Fear',
  friendship: 'Friendship',
  identity: 'Identity',
  meaning: 'Meaning',
  money: 'Money',
  mortality: 'Mortality',
  relationships: 'Relationships',
  solitude: 'Solitude',
  work_and_ambition: 'Work & Ambition',
}

function categoryLabel(value: string): string {
  return (
    CATEGORY_LABELS[value] ??
    value
      .split('_')
      .map((w) => (w ? w.charAt(0).toUpperCase() + w.slice(1) : w))
      .join(' ')
  )
}

// Shared category filter — a horizontal row of pills ("All" + each category),
// reused by both the question flow (#6.2) and the revisit list (#7).
function CategoryFilter({
  categories,
  value,
  onChange,
}: {
  categories: string[]
  value: string
  onChange: (next: string) => void
}) {
  const options = ['all', ...categories]
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      {options.map((opt) => {
        const isActive = opt === value
        return (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            aria-pressed={isActive}
            className={`flex-shrink-0 px-3 py-1.5 rounded-full font-lora text-[12px] border-[0.5px] transition-colors ${
              isActive
                ? 'bg-bronze border-bronze-dark text-ink'
                : 'bg-white border-bronze/40 text-charcoal'
            }`}
          >
            {opt === 'all' ? 'All' : categoryLabel(opt)}
          </button>
        )
      })}
    </div>
  )
}

// Quiet segmented switch between the question flow and the portrait payoff. Lets
// the user move between the two faces of the tab without a reload (#5c — fixes the
// PR4 one-way latch where, once started, there was no route back to the portrait).
function ViewSwitch({
  view,
  onChange,
}: {
  view: 'questions' | 'portrait'
  onChange: (next: 'questions' | 'portrait') => void
}) {
  const tabs: { key: 'questions' | 'portrait'; label: string }[] = [
    { key: 'questions', label: 'Questions' },
    { key: 'portrait', label: 'Your portrait' },
  ]
  return (
    <div className="flex justify-center">
      <div className="inline-flex rounded-full border-[0.5px] border-bronze/40 bg-white p-[3px]">
        {tabs.map((t) => {
          const isActive = t.key === view
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => onChange(t.key)}
              aria-pressed={isActive}
              className={`px-4 py-1.5 rounded-full font-lora text-[12px] transition-colors ${
                isActive ? 'bg-bronze text-vellum' : 'text-sepia'
              }`}
            >
              {t.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// B2: quiet pill toggle between the two visualizations of the SAME theme scores —
// the radar ("Shape") and the spatial map ("Map"). Same visual family as ViewSwitch;
// instant, local, no refetch.
function VizToggle({
  viz,
  onChange,
}: {
  viz: 'radar' | 'map'
  onChange: (next: 'radar' | 'map') => void
}) {
  const tabs: { key: 'radar' | 'map'; label: string }[] = [
    { key: 'radar', label: 'Shape' },
    { key: 'map', label: 'Map' },
  ]
  return (
    <div className="flex justify-center">
      <div className="inline-flex rounded-full border-[0.5px] border-bronze/40 bg-white p-[3px]">
        {tabs.map((t) => {
          const isActive = t.key === viz
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => onChange(t.key)}
              aria-pressed={isActive}
              className={`px-6 py-1.5 rounded-full font-lora text-[13px] transition-colors ${
                isActive ? 'bg-bronze text-vellum' : 'text-sepia'
              }`}
            >
              {t.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// Round persona avatar — reuses the PR2 saved-readings markup: portrait when
// present, else the persona's initial, else a neutral circle.
function PersonaAvatar({ portraitUrl, name }: { portraitUrl: string | null; name: string }) {
  return (
    <div className="w-[48px] h-[48px] rounded-full overflow-hidden flex-shrink-0 bg-linen border border-edge flex items-center justify-center">
      {portraitUrl ? (
        <Image
          src={portraitUrl}
          alt={name}
          width={48}
          height={48}
          className="object-cover w-full h-full"
        />
      ) : name ? (
        <span className="font-cormorant text-[20px] font-medium text-charcoal">
          {name.charAt(0)}
        </span>
      ) : null}
    </div>
  )
}

// Perpetual self-knowledge quiz. A long, calm set of small questions; the user
// answers as many or as few as they like, one at a time, returning whenever.
// Mirrors profile/page.tsx in structure and DS-v5 pill styling. NO progress bar,
// streak, points, %, fraction, or completion meter anywhere — by design.
export default function SelfPortraitPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)

  const [loading, setLoading] = useState(true)
  const [questions, setQuestions] = useState<SelfPortraitQuestion[]>([])
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [isPro, setIsPro] = useState(false)
  const [lockedCount, setLockedCount] = useState(0)
  // While a PATCH is in flight, every pill is disabled — this SERIALIZES the
  // read-modify-write on profile.answers so concurrent taps can't lose an answer.
  const [inFlight, setInFlight] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // #8/#5c: which face of the tab is showing. 'entry' = the two calm doors on a
  // fresh open (NOT persisted); 'questions' = the quiz flow; 'portrait' = payoff.
  const [view, setView] = useState<'entry' | 'questions' | 'portrait'>('entry')
  // Portrait payoff — lazily fetched only when the portrait view is opened.
  const [portrait, setPortrait] = useState<SelfPortraitPortrait | null>(null)
  const [portraitLoading, setPortraitLoading] = useState(false)
  // B2: which visualization of the same theme_scores is showing. Local UI only —
  // no URL, no refetch; defaults to the radar (B1's view).
  const [portraitViz, setPortraitViz] = useState<'radar' | 'map'>('radar')
  // B3: shareable card. The ref reads the ACTIVE radar/map <svg> at share time; the
  // preview overlay shows the rendered card (blob) before it leaves the device.
  const portraitCardRef = useRef<HTMLDivElement>(null)
  const shareBlobRef = useRef<Blob | null>(null)
  const [shareOpen, setShareOpen] = useState(false)
  const [shareBusy, setShareBusy] = useState(false)
  const [sharePreviewUrl, setSharePreviewUrl] = useState<string | null>(null)
  // B: "Save" renders + downloads the PNG directly (no share sheet). Its own busy flag
  // so it never entangles with the share-preview modal's spinner.
  const [saveBusy, setSaveBusy] = useState(false)

  // #6.2 / #7: independent category filters for the question flow and the
  // revisit list (same component, separate state so they don't cross-filter).
  const [questionCategory, setQuestionCategory] = useState('all')
  const [revisitOpen, setRevisitOpen] = useState(false)
  const [revisitCategory, setRevisitCategory] = useState('all')
  // Phase A: after answering a question in the MAIN flow, the card pauses here
  // instead of auto-advancing — it shows "The Room notices" and waits for an
  // explicit "Next question →". Holds the just-answered {qid, pillIndex}; null means
  // "show the next unanswered question". Revisit-edits never set this (no pause).
  const [justAnswered, setJustAnswered] = useState<{ qid: string; pillIndex: number } | null>(null)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    async function load() {
      try {
        const data = await api.getSelfPortrait()
        setQuestions(data.questions)
        setAnswers(data.answers)
        setIsPro(data.is_pro)
        setLockedCount(data.locked_count)
      } catch {
        // Transient — leave the empty state; the user can pull back later.
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token, router])

  // Refetch the portrait on each entry to that view. Only surface the loading state
  // when there's nothing on screen yet — a cached GET resolves ~instantly, so a
  // prior portrait stays visible silently while a refetch runs (no flicker, no
  // spinner over a 200ms response). Failure leaves any prior portrait in place; a
  // first-time failure falls through to the calm "still forming" message below.
  useEffect(() => {
    if (view !== 'portrait') return
    let active = true
    if (portrait === null) setPortraitLoading(true)
    api
      .getSelfPortraitPortrait()
      .then((data) => {
        if (active) setPortrait(data)
      })
      .catch(() => {
        // Keep any prior portrait; the render handles "no content" gracefully.
      })
      .finally(() => {
        if (active) setPortraitLoading(false)
      })
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refetch on each portrait entry
  }, [view])

  // Categories present in the questions this tier can see (drives both filters).
  const categories = useMemo(
    () => Array.from(new Set(questions.map((q) => q.category))).sort(),
    [questions],
  )

  // Unfiltered next/answered/all-answered — these drive the Pro nudge and the
  // all-answered note, whose logic is intentionally left unchanged.
  const nextQuestion = useMemo(
    () => questions.find((q) => answers[q.id] === undefined) ?? null,
    [questions, answers],
  )
  const answered = useMemo(
    () => questions.filter((q) => answers[q.id] !== undefined),
    [questions, answers],
  )
  const allAnswered = questions.length > 0 && nextQuestion === null

  // #6.2: the question actually shown respects the selected category. When "all"
  // is selected this is exactly the unfiltered nextQuestion (original behaviour).
  // Phase A: while paused on a just-answered question (the observation beat), keep
  // showing THAT question until "Next question →" clears the pause — only then does
  // the next unanswered question surface.
  const activeQuestion = useMemo(() => {
    if (justAnswered) {
      return questions.find((q) => q.id === justAnswered.qid) ?? null
    }
    const pool =
      questionCategory === 'all'
        ? questions
        : questions.filter((q) => q.category === questionCategory)
    return pool.find((q) => answers[q.id] === undefined) ?? null
  }, [questions, answers, questionCategory, justAnswered])

  // #7: the revisit list respects its own category filter.
  const revisitAnswered = useMemo(
    () =>
      revisitCategory === 'all'
        ? answered
        : answered.filter((q) => q.category === revisitCategory),
    [answered, revisitCategory],
  )

  // The per-answer "The Room notices" line for the question currently paused on its
  // observation beat — null when not paused, or when no pool covers this answer. The
  // combined truthy check narrows both values for the lookup; deterministic by qid so
  // the line is stable while the card is held.
  const observationLine =
    justAnswered && activeQuestion && justAnswered.qid === activeQuestion.id
      ? observationFor(activeQuestion.category, justAnswered.pillIndex, activeQuestion.id)
      : null

  // Faint persona watermark URL for the radar/map — ready-state only, else null. Hoisted
  // so the radar and map branches share one source of truth (the components further gate
  // on a non-empty string, so null/"" render nothing).
  const portraitWatermarkUrl =
    portrait && portrait.state === 'ready' && portrait.best_fit.length > 0
      ? portrait.best_fit[0].portrait_url
      : null

  // B3: only allow sharing when there's real signal — never a "keep answering" card.
  const portraitHasSignal = (portrait?.theme_scores ?? []).some((s) => s.score > 0)

  // Ready vs forming drives the section-header + progress-line wording.
  const isReady = portrait?.state === 'ready'

  // B (mock): deterministic top-3 observation cards (frozen slug→copy map, no LLM/counts).
  // Empty when there's no signal, so cards render only alongside a real viz.
  const observationCards = portraitHasSignal ? topObservationCards(portrait?.theme_scores) : []

  // Open the share preview: render the card from the ACTIVE svg up-front (the heavy
  // async work — fonts.ready, decode, toBlob), so the later "Share" tap fires
  // navigator.share on an already-ready blob (clean gesture, no iOS activation strip).
  const openShare = async () => {
    const svg = portraitCardRef.current?.querySelector('svg')
    if (!svg) return
    setShareOpen(true)
    setShareBusy(true)
    setSharePreviewUrl(null)
    shareBlobRef.current = null
    try {
      const blob = await renderPortraitCardBlob(svg)
      shareBlobRef.current = blob
      setSharePreviewUrl(URL.createObjectURL(blob))
    } catch {
      toast('Could not build the card — try again.')
      setShareOpen(false)
    } finally {
      setShareBusy(false)
    }
  }

  // B: "Save" — render the card from the ACTIVE svg and download the PNG directly,
  // skipping the share sheet entirely. Reuses the shipped B3 render path; never opens
  // the preview modal.
  const savePortrait = async () => {
    const svg = portraitCardRef.current?.querySelector('svg')
    if (!svg || saveBusy) return
    setSaveBusy(true)
    try {
      const blob = await renderPortraitCardBlob(svg)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'my-self-portrait.png'
      a.click()
      URL.revokeObjectURL(url)
      toast('Saved to your downloads')
    } catch {
      toast('Could not build the card — try again.')
    } finally {
      setSaveBusy(false)
    }
  }

  const closeShare = () => {
    setShareOpen(false)
    setShareBusy(false)
    if (sharePreviewUrl) URL.revokeObjectURL(sharePreviewUrl)
    setSharePreviewUrl(null)
    shareBlobRef.current = null
  }

  const confirmShare = async () => {
    const blob = shareBlobRef.current
    if (!blob) return
    setShareBusy(true)
    try {
      const result = await sharePortraitCardBlob(blob)
      if (result === 'downloaded') toast('Image saved — share it from your downloads')
      closeShare()
    } catch (err) {
      // AbortError = user dismissed the native sheet; keep the preview open to retry.
      if (!(err instanceof DOMException && err.name === 'AbortError')) {
        toast('Could not share — try again.')
      }
    } finally {
      setShareBusy(false)
    }
  }

  // Revoke the preview object URL when it changes / on unmount (no leak).
  useEffect(() => {
    return () => {
      if (sharePreviewUrl) URL.revokeObjectURL(sharePreviewUrl)
    }
  }, [sharePreviewUrl])

  // `fromMainFlow` distinguishes a fresh answer in the one-at-a-time question flow
  // (which pauses on the observation beat) from a revisit-list edit (which does not).
  const choose = async (
    qid: string,
    pillIndex: number,
    opts?: { fromMainFlow?: boolean },
  ) => {
    if (inFlight) return
    setInFlight(true)
    setError(null)
    const prev = answers
    // Optimistic: record the choice immediately. The SAVE fires on tap exactly as
    // before; only the VISUAL advance changes — in the main flow the card now pauses
    // on the observation and waits for "Next question →" (justAnswered), rather than
    // auto-advancing to the next question.
    setAnswers({ ...answers, [qid]: pillIndex })
    setEditingId(null)
    if (opts?.fromMainFlow) {
      setJustAnswered({ qid, pillIndex })
    }
    try {
      await api.updateSelfPortrait(qid, pillIndex)
    } catch (err) {
      setAnswers(prev) // revert on failure
      if (opts?.fromMainFlow) setJustAnswered(null) // drop the pause; no false observation
      setError(err instanceof Error ? err.message : 'Could not save that — try again.')
    } finally {
      setInFlight(false)
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen [min-height:100svh] bg-vellum px-7 pt-10">
        <div className="w-full max-w-[380px] mx-auto space-y-4">
          <div className="h-[28px] w-[200px] bg-linen rounded animate-pulse" />
          <div className="h-[18px] w-[260px] bg-linen rounded animate-pulse" />
          <div className="h-[120px] w-full bg-linen rounded animate-pulse" />
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <div className="flex-1 flex flex-col px-7 py-8">
        <div className="w-full max-w-[380px] mx-auto space-y-7">

          {view === 'entry' ? (
            <>
              {/* HERO — first paint of this tab. Fixed svh height so the page never jumps
                  when the image decodes; soft bottom fade into the vellum page. */}
              <div className="relative w-full h-[46vh] [height:46svh] rounded-lg overflow-hidden">
                <Image
                  src="/self-portrait/hero.webp"
                  alt=""
                  fill
                  priority
                  sizes="(max-width: 420px) 100vw, 380px"
                  className="object-cover scale-[1.45]"
                />
                <div className="absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-b from-transparent to-vellum pointer-events-none" />
              </div>

              {/* INTRO — existing copy, verbatim. */}
              <p className="font-lora text-[15px] text-charcoal leading-[1.65] text-center">
                A long set of small questions about how you actually move through life. Answer
                as many or as few as you like — even a handful sharpens how the room understands
                you. Come back whenever; it keeps your place.
              </p>

              {/* ENTRY BUTTONS — pill language. Primary bronze; secondary bordered-white so
                  the primary reads as primary. Handlers + labels unchanged (local setView). */}
              <section className="flex flex-col gap-3">
                <button
                  type="button"
                  onClick={() => setView('questions')}
                  className="w-full h-12 rounded-full font-lora text-[16px] font-medium bg-bronze text-vellum transition-colors"
                >
                  {answered.length > 0 ? 'Continue the questions' : 'Start the journey'}
                </button>
                <button
                  type="button"
                  onClick={() => setView('portrait')}
                  className="w-full h-12 rounded-full font-lora text-[16px] font-medium border-[0.5px] border-bronze-dark bg-white text-ink transition-colors"
                >
                  Your portrait
                </button>
              </section>
            </>
          ) : (
            <>
              {/* Divider + title — EXACTLY as before, now rendered in the non-entry views
                  only (questions + portrait). Zero change to those two views. */}
              <div className="flex justify-center">
                <BronzeDivider width={80} />
              </div>

              <header className="space-y-3 text-center">
                <h1 className="font-cormorant text-[28px] font-medium text-ink leading-tight">
                  Self-Portrait
                </h1>
              </header>
            </>
          )}

          {/* Quiet switch between the two faces once past the entry screen. */}
          {view !== 'entry' && <ViewSwitch view={view} onChange={setView} />}

          {/* ── The question flow, picker, feedback and revisit (relocated from the
              PR4 `started` gate, unchanged) ── */}
          {view === 'questions' && (
            <>
              {error && (
                <p className="font-lora text-[12px] text-safety text-center">{error}</p>
              )}

              {/* #6.2 category picker for the question flow. */}
              {categories.length > 0 && (
                <CategoryFilter
                  categories={categories}
                  value={questionCategory}
                  onChange={setQuestionCategory}
                />
              )}

              {/* One question at a time, as an artwork card. After answering, the
                  card pauses on "The Room notices" + an explicit "Next question →"
                  (justAnswered) rather than auto-advancing. */}
              {activeQuestion && (
                <section className="space-y-4">
                  {/* Eyebrow — the life-area this question sits in. No count/meter. */}
                  <p className="font-lora text-[11px] uppercase tracking-[0.14em] text-sepia text-center">
                    Current theme — {categoryLabel(activeQuestion.category)}
                  </p>

                  <div className="rounded-lg border-[0.5px] border-bronze/30 bg-white shadow-card overflow-hidden">
                    {/* Top artwork band (placeholder now; real watercolor drops in). */}
                    <CardArtwork category={activeQuestion.category} />
                    <div className="px-5 py-5 space-y-4">
                      <h2 className="font-cormorant text-[21px] font-medium text-ink leading-snug text-center">
                        {activeQuestion.question}
                      </h2>
                      <div className="flex flex-wrap gap-2 justify-center">
                        {activeQuestion.pills.map((pill, idx) => {
                          const paused = justAnswered?.qid === activeQuestion.id
                          const isChosen = answers[activeQuestion.id] === idx
                          return (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => choose(activeQuestion.id, idx, { fromMainFlow: true })}
                              disabled={inFlight || paused}
                              aria-pressed={isChosen}
                              className={`px-5 py-2.5 rounded-full font-lora text-[15px] border-[0.5px] transition-colors disabled:opacity-40 ${
                                paused && isChosen
                                  ? 'bg-ink border-ink text-vellum'
                                  : paused
                                    ? 'bg-white border-bronze/30 text-sepia'
                                    : 'bg-bronze border-bronze-dark text-vellum shadow-card'
                              }`}
                            >
                              {pill}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  </div>

                  {/* "The Room notices" — the per-answer observation, then Next. */}
                  {justAnswered?.qid === activeQuestion.id && (
                    <div className="space-y-4">
                      {observationLine && (
                        <div className="rounded-lg border-[0.5px] border-bronze/30 bg-linen/40 px-4 py-4 flex items-start gap-3">
                          <span className="mt-[2px]">
                            <EyeGlyph />
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="font-lora text-[11px] uppercase tracking-[0.12em] text-sepia">
                              The Room notices
                            </p>
                            <p className="font-cormorant italic text-[16px] text-ink mt-1 leading-snug">
                              {observationLine}
                            </p>
                          </div>
                        </div>
                      )}
                      <button
                        type="button"
                        onClick={() => setJustAnswered(null)}
                        className="w-full py-3 rounded-full font-cormorant text-[16px] font-medium bg-ink text-vellum transition-colors"
                      >
                        Next question →
                      </button>
                    </div>
                  )}
                </section>
              )}

              {/* Category exhausted but more remain elsewhere — calm, not the Pro nudge. */}
              {!activeQuestion && questionCategory !== 'all' && !allAnswered && (
                <section className="text-center">
                  <p className="font-lora text-[14px] text-charcoal leading-[1.65]">
                    You&rsquo;ve answered everything in {categoryLabel(questionCategory)} for now.
                    Choose another area above, or revisit what you&rsquo;ve said.
                  </p>
                </section>
              )}

              {/* Pro nudge: free user has answered everything visible and more waits in Pro. */}
              {allAnswered && !isPro && lockedCount > 0 && (
                <section className="rounded-lg border-[0.5px] border-bronze/40 bg-white shadow-card px-5 py-5 space-y-3 text-center">
                  <p className="font-lora text-[14px] text-charcoal leading-[1.65]">
                    There&rsquo;s more of the Self-Portrait in Pro — the full set, across every part
                    of life.
                  </p>
                  <Link
                    href="/app/upgrade"
                    className="inline-block font-cormorant text-[16px] font-medium text-ink underline decoration-bronze/60 underline-offset-4"
                  >
                    See Pro
                  </Link>
                </section>
              )}

              {/* Pro user has answered everything currently in the bank. */}
              {allAnswered && isPro && (
                <section className="text-center">
                  <p className="font-lora text-[14px] text-charcoal leading-[1.65]">
                    You&rsquo;ve answered everything here for now. Edit any answer anytime — what
                    changes is its own kind of signal.
                  </p>
                </section>
              )}

              {/* #7 Revisit answers — reveals the category filter over the answered list. */}
              {answered.length > 0 && (
                <section className="space-y-3 pt-2">
                  <div className="flex justify-center">
                    <BronzeDivider width={56} />
                  </div>
                  {!revisitOpen ? (
                    <div className="text-center">
                      <button
                        type="button"
                        onClick={() => setRevisitOpen(true)}
                        className="font-cormorant text-[18px] font-medium text-ink underline decoration-bronze/60 underline-offset-4"
                      >
                        Revisit answers
                      </button>
                    </div>
                  ) : (
                    <>
                      <h2 className="font-cormorant text-[18px] font-medium text-ink text-center">
                        Your answers
                      </h2>
                      <CategoryFilter
                        categories={categories}
                        value={revisitCategory}
                        onChange={setRevisitCategory}
                      />
                      <ul className="space-y-2">
                        {revisitAnswered.map((q) => {
                          const chosen = answers[q.id]
                          const isEditing = editingId === q.id
                          return (
                            <li
                              key={q.id}
                              className="rounded-lg border-[0.5px] border-bronze/30 bg-white shadow-card px-4 py-3"
                            >
                              <button
                                type="button"
                                onClick={() => setEditingId(isEditing ? null : q.id)}
                                className="w-full text-left flex items-start gap-3"
                                aria-expanded={isEditing}
                              >
                                {/* Small per-theme artwork tile (placeholder now). */}
                                <ThemeGlyph category={q.category} size={56} />
                                <div className="flex-1 min-w-0">
                                  <p className="font-lora text-[13px] text-charcoal leading-[1.55]">
                                    {q.question}
                                  </p>
                                  <p className="font-lora text-[13px] text-ink mt-1 font-medium">
                                    {q.pills[chosen]}
                                  </p>
                                </div>
                              </button>
                              {isEditing && (
                                <div className="flex flex-wrap gap-2 mt-3">
                                  {q.pills.map((pill, idx) => {
                                    const isSelected = idx === chosen
                                    return (
                                      <button
                                        key={idx}
                                        type="button"
                                        onClick={() => choose(q.id, idx)}
                                        disabled={inFlight}
                                        aria-pressed={isSelected}
                                        className={`px-5 py-2.5 rounded-full font-lora text-[15px] border-[0.5px] transition-colors disabled:opacity-40 ${
                                          isSelected
                                            ? 'bg-ink border-ink text-vellum'
                                            : 'bg-bronze border-bronze-dark text-vellum shadow-card'
                                        }`}
                                      >
                                        {pill}
                                      </button>
                                    )
                                  })}
                                </div>
                              )}
                            </li>
                          )
                        })}
                      </ul>
                    </>
                  )}
                </section>
              )}
            </>
          )}

          {/* ── Your portrait (#5c payoff) ── */}
          {view === 'portrait' && (
            <section className="space-y-5">
              {/* B1: the radar — the portrait's data-visualization. Real theme scores;
                  faint persona watermark only in the ready state. Shown once the
                  portrait has loaded; the supporting summary/forming text sits below. */}
              {portrait && (
                // Perimeter frame — a thin bronze plate/plaque wrapping the progress line,
                // section header, toggle, radar, and observation cards. Vellum (transparent)
                // bg, no shadow. The radar's own px-4 + this px-4 hold the overflow labels.
                <div className="rounded-xl border-[1px] border-bronze/50 px-4 py-6 space-y-5">
                  {/* Progress line — the plate's header (real answered count). */}
                  <p className="font-lora text-[11px] tracking-[0.18em] uppercase text-sepia text-center">
                    Portrait {isReady ? 'ready' : 'forming'} · {answered.length} answers
                  </p>

                  {/* Section header — two centered lines; wording flips with ready state. */}
                  <div className="text-center space-y-1">
                    <p className="font-lora text-[11px] tracking-[0.2em] uppercase text-sepia">
                      {isReady ? 'The shape of' : 'Early contours of'}
                    </p>
                    <h2 className="font-cormorant text-[24px] font-medium text-ink tracking-[0.08em] uppercase leading-tight">
                      Your pattern
                    </h2>
                  </div>

                  {/* Shape / Map toggle — segmented control language. */}
                  <VizToggle viz={portraitViz} onChange={setPortraitViz} />

                  {/* Radar/map — the ref lets the share path read the active <svg>. */}
                  <div ref={portraitCardRef}>
                    {portraitViz === 'radar' ? (
                      <PortraitRadar
                        scores={portrait.theme_scores ?? []}
                        watermarkUrl={portraitWatermarkUrl}
                      />
                    ) : (
                      <PortraitMap
                        scores={portrait.theme_scores ?? []}
                        watermarkUrl={portraitWatermarkUrl}
                      />
                    )}
                  </div>

                  {/* Observation cards — TOP-3 axes, deterministic frozen copy (no counts).
                      3-across, thin bronze border, transparent bg. */}
                  {observationCards.length > 0 && (
                    <div className="grid grid-cols-3 gap-3">
                      {observationCards.map((c) => {
                        const Icon = CARD_ICONS[c.icon]
                        return (
                          <div
                            key={c.key}
                            className="rounded-lg border-[0.5px] border-bronze/30 bg-transparent px-3 py-4 flex flex-col items-center text-center gap-2"
                          >
                            <Icon size={20} strokeWidth={1.5} className="text-bronze" aria-hidden="true" />
                            <p className="font-cormorant text-[15px] font-medium text-ink leading-snug">
                              {c.headline}
                            </p>
                            <p className="font-lora text-[11px] text-charcoal leading-[1.45]">
                              {c.support}
                            </p>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}

              {portraitLoading && portrait === null ? (
                // First open / generation in progress — make the wait feel like a moment.
                <div className="rounded-lg border-[0.5px] border-bronze/30 px-5 py-6 text-center">
                  <p className="font-lora text-[14px] text-charcoal leading-[1.65]">
                    Putting your portrait together&hellip;
                  </p>
                </div>
              ) : portrait && portrait.state === 'ready' && portrait.summary ? (
                <>
                  <div className="rounded-lg border-[0.5px] border-bronze/30 px-5 py-5">
                    <div className="flex flex-col gap-[14px]">
                      {portrait.summary
                        .split(/\n\n|\n/)
                        .filter(Boolean)
                        .map((para, i) => (
                          <p key={i} className="font-lora text-[15px] text-charcoal leading-[1.7]">
                            {para}
                          </p>
                        ))}
                    </div>
                  </div>

                  {portrait.best_fit.length > 0 && (
                    <div className="space-y-3">
                      <div className="flex justify-center">
                        <BronzeDivider width={56} />
                      </div>
                      <h2 className="font-cormorant text-[18px] font-medium text-ink text-center">
                        Minds you lean toward
                      </h2>
                      {portrait.best_fit.map((p) => (
                        <div
                          key={p.slug}
                          className="rounded-lg border-[0.5px] border-bronze/30 px-4 py-4 flex items-start gap-[14px]"
                        >
                          <PersonaAvatar portraitUrl={p.portrait_url} name={p.name} />
                          <div className="flex-1 min-w-0">
                            <p className="font-cormorant text-[19px] font-medium text-ink leading-tight">
                              {p.name}
                            </p>
                            {p.bio && (
                              <p className="font-lora text-[13px] text-charcoal mt-[3px] leading-[1.55]">
                                {p.bio}
                              </p>
                            )}
                            {p.why && (
                              <p className="font-lora italic text-[13px] text-bronze mt-[6px] leading-[1.5]">
                                {p.why}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : portrait && portrait.preview.length > 0 ? (
                // Forming (or ready without a cached summary yet): "a pattern is
                // emerging" — genuine observation lines from the user's own answers.
                <div className="rounded-lg border-[0.5px] border-bronze/30 overflow-hidden">
                  <PatternArtwork />
                  <div className="px-5 py-5 space-y-3 text-center">
                    <h2 className="font-cormorant text-[19px] font-medium text-ink leading-snug">
                      A pattern is emerging
                    </h2>
                    {portrait.preview.map((line, i) => (
                      <p key={i} className="font-lora text-[14px] text-charcoal leading-[1.65]">
                        {line}
                      </p>
                    ))}
                  </div>
                </div>
              ) : (
                // No content yet, or the fetch failed — never an error or spinner trap.
                <div className="rounded-lg border-[0.5px] border-bronze/30 px-5 py-6 text-center">
                  <p className="font-lora text-[14px] text-charcoal leading-[1.65]">
                    Your portrait is still forming. It appears here as you answer — a quiet
                    reflection of how you tend to weigh things, drawn from your own words.
                  </p>
                </div>
              )}

              {/* Footer line — what the early contours are for. */}
              <p className="font-lora text-[13px] text-sepia leading-[1.6] text-center">
                These early contours will help guide the Room&rsquo;s thinkers, ideas, and
                conversations you&rsquo;ll explore.
              </p>

              {/* Primary CTA — full-width bronze pill back to the questions. */}
              <button
                type="button"
                onClick={() => setView('questions')}
                className="w-full h-12 rounded-full font-lora text-[16px] font-medium bg-bronze text-vellum transition-colors"
              >
                Keep shaping the portrait
              </button>

              {/* Share + Save — same pill language as the CTA, side by side spanning its
                  width. Gated on real signal; handlers unchanged this PR. */}
              {portraitHasSignal && (
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={openShare}
                    className="flex-1 h-12 rounded-full font-lora text-[16px] font-medium bg-bronze text-vellum transition-colors disabled:opacity-60"
                  >
                    Share
                  </button>
                  <button
                    type="button"
                    onClick={savePortrait}
                    disabled={saveBusy}
                    className="flex-1 h-12 rounded-full font-lora text-[16px] font-medium bg-bronze text-vellum transition-colors disabled:opacity-60"
                  >
                    {saveBusy ? 'Saving…' : 'Save'}
                  </button>
                </div>
              )}

              {/* A different lens, not a primary CTA — quiet cross-link to You-vs-You. */}
              <div className="text-center pt-1">
                <Link
                  href="/app/you-vs-you"
                  className="font-lora text-[13px] text-sepia underline underline-offset-2"
                >
                  See how your thinking has shifted over time
                </Link>
              </div>
            </section>
          )}

        </div>
      </div>

      {/* B3: simple LOCAL share preview — shows exactly what will be posted before it
          leaves the device. Not the server-coupled SharePreviewModal. */}
      {shareOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Share your portrait"
          className="fixed inset-0 z-50 flex items-center justify-center px-4"
        >
          <div
            className="absolute inset-0 bg-[rgba(31,27,20,0.5)]"
            aria-hidden="true"
            onClick={() => {
              if (!shareBusy) closeShare()
            }}
          />
          <div className="relative z-10 w-full max-w-[360px] bg-paper rounded-lg p-5 shadow-[0_8px_32px_rgba(31,27,20,0.18)] max-h-[85svh] overflow-y-auto">
            <div
              className="relative w-full rounded-sm overflow-hidden mb-4 bg-vellum"
              style={{ aspectRatio: '4/5' }}
            >
              {sharePreviewUrl ? (
                // eslint-disable-next-line @next/next/no-img-element -- local blob preview, not an optimizable asset
                <img
                  src={sharePreviewUrl}
                  alt="Your shareable portrait card"
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center">
                  <p className="font-lora text-[13px] text-charcoal">Preparing your card&hellip;</p>
                </div>
              )}
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={closeShare}
                disabled={shareBusy}
                className="flex-1 font-lora text-[13px] text-charcoal border border-edge rounded-sm py-2.5 px-4 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmShare}
                disabled={shareBusy || !sharePreviewUrl}
                className="flex-1 font-lora text-[13px] text-vellum bg-bronze rounded-sm py-2.5 px-4 flex items-center justify-center disabled:opacity-70"
              >
                {shareBusy ? (
                  <span
                    className="inline-block w-3.5 h-3.5 border-[0.8px] border-vellum/30 border-t-vellum rounded-full animate-spin-slow"
                    aria-label="Working…"
                  />
                ) : (
                  'Share'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
