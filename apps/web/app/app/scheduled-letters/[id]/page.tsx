'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import SubPageNav from '@/components/layout/SubPageNav'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { ScheduledEmailDetail } from '@/lib/api'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function ScheduledLetterDetailPage() {
  const router = useRouter()
  const params = useParams()
  const id = String(params.id)
  const token = useStore((s) => s.token)
  // undefined = loading · null = not found (404 / pending / foreign) · object = the letter
  const [letter, setLetter] = useState<ScheduledEmailDetail | null | undefined>(undefined)
  const [reviewDraft, setReviewDraft] = useState('')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth')
      return
    }
    if (!token) return
    api.getScheduledEmail(id)
      .then(setLetter)
      .catch(() => setLetter(null))
  }, [token, id, router])

  async function handleSaveReview() {
    if (!letter) return
    const text = reviewDraft.trim()
    if (!text || saving) return
    setSaving(true)
    try {
      const updated = await api.reviewScheduledEmail(letter.id, text)
      setLetter(updated)
      setEditing(false)
      toast.success('Saved.')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not save. Try again.')
    } finally {
      setSaving(false)
    }
  }

  // ── Loading ──
  if (letter === undefined) {
    return (
      <main className="min-h-screen [min-height:100svh] bg-vellum px-[24px] pt-[22px]">
        <p className="font-lora text-[13px] text-sepia italic text-center py-16">Loading…</p>
      </main>
    )
  }

  // ── 404 fallback (bad id, pending, or foreign) ──
  if (letter === null) {
    return (
      <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
        <div className="px-[24px] pt-[22px] pb-[16px] flex items-center gap-[12px]">
          <SubPageNav fallbackHref="/app/scheduled-letters" />
        </div>
        <div className="px-[24px] pt-[40px] text-center">
          <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
            This letter isn&rsquo;t here.
          </h1>
          <p className="font-lora text-[15px] text-charcoal mt-[10px] leading-[1.7] max-w-[320px] mx-auto">
            It may not have arrived yet. Your delivered letters are waiting in your messages.
          </p>
          <button
            type="button"
            onClick={() => router.push('/app/scheduled-letters')}
            className="mt-[20px] font-lora text-[13px] text-sepia underline underline-offset-2"
          >
            Back to your messages &rarr;
          </button>
        </div>
      </main>
    )
  }

  // ── The delivered letter ──
  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <div className="px-[24px] pt-[22px] pb-[8px] flex items-center gap-[12px]">
        <SubPageNav fallbackHref="/app/scheduled-letters" />
      </div>

      <div className="px-[24px] pt-[12px]">
        {/* Eyebrow */}
        <p className="font-lora text-[12px] uppercase tracking-[0.14em] text-sepia mb-[8px]">
          A letter to your future self
        </p>

        {/* Header line */}
        <h1 className="font-cormorant text-[28px] font-medium text-ink leading-tight">
          It arrived.
        </h1>

        {/* Bronze divider */}
        <div className="w-[40px] h-[1px] bg-bronze mt-[16px] mb-[20px]" />

        {/* Persona attribution + thumbnail */}
        <div className="flex items-center gap-[12px] mb-[6px]">
          {letter.persona_portrait_url && (
            <img
              src={letter.persona_portrait_url}
              alt={letter.persona_name}
              width={44}
              height={44}
              className="w-[44px] h-[44px] rounded-[4px] object-cover flex-shrink-0"
            />
          )}
          <p className="font-lora text-[14px] text-charcoal">
            Written with {letter.persona_name}.
          </p>
        </div>

        {/* Written / arrived dates */}
        <p className="font-lora text-[12px] text-sepia leading-[1.7]">
          Written {formatDate(letter.created_at)}.<br />
          Arrived {formatDate(letter.sent_at ?? letter.scheduled_for)}.
        </p>

        {/* The note */}
        {letter.note && (
          <div className="mt-[28px]">
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze mb-[10px]">
              Your note
            </p>
            <p className="font-lora text-[16px] text-charcoal leading-[1.7] whitespace-pre-wrap">
              {letter.note}
            </p>
          </div>
        )}

        {/* Prediction + review (043) — only when a prediction was written */}
        {letter.prediction && (
          <div className="mt-[32px] pt-[24px] border-t border-[0.5px] border-edge">
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze mb-[10px]">
              What you predicted
            </p>
            <p className="font-lora text-[16px] text-charcoal leading-[1.7] whitespace-pre-wrap">
              {letter.prediction}
            </p>

            {letter.review_text && !editing ? (
              <div className="mt-[24px]">
                <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-bronze mb-[10px]">
                  What happened
                </p>
                <p className="font-lora text-[16px] text-charcoal leading-[1.7] whitespace-pre-wrap">
                  {letter.review_text}
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setReviewDraft(letter.review_text ?? '')
                    setEditing(true)
                  }}
                  className="mt-[12px] font-lora text-[13px] text-sepia underline underline-offset-2"
                >
                  Edit
                </button>
              </div>
            ) : (
              <div className="mt-[24px]">
                <p className="font-cormorant text-[20px] text-ink leading-snug mb-[12px]">
                  You predicted this. What happened?
                </p>
                <textarea
                  value={reviewDraft}
                  onChange={(e) => setReviewDraft(e.target.value)}
                  maxLength={2000}
                  rows={4}
                  placeholder="What happened — and what did it teach you?"
                  className="w-full bg-paper border border-[0.5px] border-edge rounded-sm px-[12px] py-[10px] font-lora text-[15px] text-ink placeholder:text-charcoal/40 resize-none transition-[border-color,box-shadow] duration-200 focus:outline-none focus:border-bronze focus:ring-1 focus:ring-bronze/20"
                />
                <button
                  type="button"
                  onClick={handleSaveReview}
                  disabled={saving || reviewDraft.trim() === ''}
                  className="mt-[12px] px-[18px] py-[10px] bg-ink text-vellum rounded-sm font-cormorant text-[16px] font-medium disabled:opacity-40"
                >
                  {saving ? 'Saving…' : 'Save'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  )
}
