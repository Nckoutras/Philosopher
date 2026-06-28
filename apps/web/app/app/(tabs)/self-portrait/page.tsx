'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { SelfPortraitQuestion } from '@/lib/api'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

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

  // First question with no stored answer, in the server's stable order.
  const nextQuestion = useMemo(
    () => questions.find((q) => answers[q.id] === undefined) ?? null,
    [questions, answers],
  )
  const answered = useMemo(
    () => questions.filter((q) => answers[q.id] !== undefined),
    [questions, answers],
  )
  const allAnswered = questions.length > 0 && nextQuestion === null

  const choose = async (qid: string, pillIndex: number) => {
    if (inFlight) return
    setInFlight(true)
    setError(null)
    const prev = answers
    // Optimistic: show the choice and advance immediately.
    setAnswers({ ...answers, [qid]: pillIndex })
    setEditingId(null)
    try {
      await api.updateSelfPortrait(qid, pillIndex)
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
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              A long set of small questions about how you actually move through life. There are
              far more here than you need — answer as many or as few as you like. Even a handful
              sharpens how the room understands you, and it grows truer the more you answer. Come
              back whenever; it keeps your place.
            </p>
          </header>

          {error && (
            <p className="font-lora text-[12px] text-safety text-center">{error}</p>
          )}

          {/* Next unanswered question — one at a time. */}
          {nextQuestion && (
            <section className="space-y-4">
              <h2 className="font-cormorant text-[21px] font-medium text-ink leading-snug text-center">
                {nextQuestion.question}
              </h2>
              <div className="flex flex-wrap gap-2 justify-center">
                {nextQuestion.pills.map((pill, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => choose(nextQuestion.id, idx)}
                    disabled={inFlight}
                    className="px-4 py-2 rounded-full font-lora text-[13px] border-[0.5px] bg-white border-bronze/60 text-charcoal shadow-card transition-colors disabled:opacity-40"
                  >
                    {pill}
                  </button>
                ))}
              </div>
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

          {/* Your answers — review and revise. */}
          {answered.length > 0 && (
            <section className="space-y-3 pt-2">
              <div className="flex justify-center">
                <BronzeDivider width={56} />
              </div>
              <h2 className="font-cormorant text-[18px] font-medium text-ink text-center">
                Your answers
              </h2>
              <ul className="space-y-2">
                {answered.map((q) => {
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
            </section>
          )}

        </div>
      </div>
    </main>
  )
}
