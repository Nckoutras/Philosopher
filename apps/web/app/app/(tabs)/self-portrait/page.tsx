'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { SelfPortraitQuestion } from '@/lib/api'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

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

// Quiet, in-voice acknowledgements shown once every ACK_EVERY new answers. These
// are OBSERVATIONS about what the room is starting to see — never encouragement,
// never a count, %, or streak.
const ACK_EVERY = 7
const ACK_LINES = [
  'The room is starting to see how you weigh things.',
  'A shape is forming — how you lean when it isn’t simple.',
  'Patterns are surfacing in what you reach for first.',
  'The room is learning where you hold firm and where you bend.',
  'Something of your particular way of seeing is coming through.',
]

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

  // #8 entry shell: the question flow stays behind "Start the journey".
  const [started, setStarted] = useState(false)
  const [showPortrait, setShowPortrait] = useState(false)
  // #6.2 / #7: independent category filters for the question flow and the
  // revisit list (same component, separate state so they don't cross-filter).
  const [questionCategory, setQuestionCategory] = useState('all')
  const [revisitOpen, setRevisitOpen] = useState(false)
  const [revisitCategory, setRevisitCategory] = useState('all')
  // #6.3: count NEW answers this session (edits excluded) to time the quiet
  // acknowledgement. A ref so it never triggers a render on its own.
  const newAnswerCount = useRef(0)
  const [ackLine, setAckLine] = useState<string | null>(null)

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
  const activeQuestion = useMemo(() => {
    const pool =
      questionCategory === 'all'
        ? questions
        : questions.filter((q) => q.category === questionCategory)
    return pool.find((q) => answers[q.id] === undefined) ?? null
  }, [questions, answers, questionCategory])

  // #7: the revisit list respects its own category filter.
  const revisitAnswered = useMemo(
    () =>
      revisitCategory === 'all'
        ? answered
        : answered.filter((q) => q.category === revisitCategory),
    [answered, revisitCategory],
  )

  const choose = async (qid: string, pillIndex: number) => {
    if (inFlight) return
    setInFlight(true)
    setError(null)
    const prev = answers
    const isNew = prev[qid] === undefined
    setAckLine(null) // clear any prior acknowledgement on the next answer
    // Optimistic: show the choice and advance immediately.
    setAnswers({ ...answers, [qid]: pillIndex })
    setEditingId(null)
    try {
      await api.updateSelfPortrait(qid, pillIndex)
      // #6.3: only NEW answers move the count; re-editing an answer does not.
      if (isNew) {
        newAnswerCount.current += 1
        if (newAnswerCount.current % ACK_EVERY === 0) {
          const idx = (newAnswerCount.current / ACK_EVERY - 1) % ACK_LINES.length
          setAckLine(ACK_LINES[idx] ?? null)
        }
      }
    } catch (err) {
      setAnswers(prev) // revert on failure
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

          <div className="flex justify-center">
            <BronzeDivider width={80} />
          </div>

          <header className="space-y-3 text-center">
            <h1 className="font-cormorant text-[28px] font-medium text-ink leading-tight">
              Self-Portrait
            </h1>
            {!started && (
              <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
                A long set of small questions about how you actually move through life. Answer
                as many or as few as you like — even a handful sharpens how the room understands
                you. Come back whenever; it keeps your place.
              </p>
            )}
          </header>

          {/* #8 entry shell: two calm doors before the questions. */}
          {!started && (
            <section className="space-y-4">
              <div className="flex flex-col gap-3">
                <button
                  type="button"
                  onClick={() => setStarted(true)}
                  className="w-full py-3 rounded-full font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
                >
                  Start the journey
                </button>
                <button
                  type="button"
                  onClick={() => setShowPortrait((v) => !v)}
                  aria-expanded={showPortrait}
                  className="w-full py-3 rounded-full font-cormorant text-[16px] font-medium border-[0.5px] border-bronze/60 text-ink bg-white transition-colors"
                >
                  Your portrait
                </button>
              </div>

              {/* INERT placeholder this PR — the real portrait payoff arrives in PR5.
                  Copy stays qualitative: no threshold, no count. */}
              {showPortrait && (
                <div className="rounded-lg border-[0.5px] border-bronze/30 bg-white shadow-card px-5 py-5 text-center">
                  <p className="font-lora text-[14px] text-charcoal leading-[1.65]">
                    Your portrait is still forming. It appears here as you answer — a quiet
                    reflection of how you tend to weigh things, drawn from your own words.
                  </p>
                </div>
              )}
            </section>
          )}

          {/* The question flow, picker, feedback and revisit live behind the gate. */}
          {started && (
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

              {/* One question at a time, respecting the selected category. */}
              {activeQuestion && (
                <section className="space-y-4">
                  <h2 className="font-cormorant text-[21px] font-medium text-ink leading-snug text-center">
                    {activeQuestion.question}
                  </h2>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {activeQuestion.pills.map((pill, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => choose(activeQuestion.id, idx)}
                        disabled={inFlight}
                        className="px-4 py-2 rounded-full font-lora text-[13px] border-[0.5px] bg-white border-bronze/60 text-charcoal shadow-card transition-colors disabled:opacity-40"
                      >
                        {pill}
                      </button>
                    ))}
                  </div>
                </section>
              )}

              {/* #6.3 quiet acknowledgement — one line, no metric. */}
              {ackLine && (
                <p className="font-cormorant italic text-[16px] text-bronze text-center leading-snug">
                  {ackLine}
                </p>
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
                                className="w-full text-left"
                                aria-expanded={isEditing}
                              >
                                <p className="font-lora text-[13px] text-charcoal leading-[1.55]">
                                  {q.question}
                                </p>
                                <p className="font-lora text-[13px] text-ink mt-1 font-medium">
                                  {q.pills[chosen]}
                                </p>
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
                                        className={`px-4 py-2 rounded-full font-lora text-[13px] border-[0.5px] transition-colors disabled:opacity-40 ${
                                          isSelected
                                            ? 'bg-bronze border-bronze-dark text-ink'
                                            : 'bg-white border-bronze/60 text-charcoal shadow-card'
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

        </div>
      </div>
    </main>
  )
}
