'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChevronDown, Bookmark, BookmarkCheck } from 'lucide-react'
import SubPageNav from '@/components/layout/SubPageNav'
import { useStore } from '@/lib/store'
import { useAuthGate } from '@/lib/useAuthGate'
import { api, RateLimitError } from '@/lib/api'
import type { SelfComparisonStatus, SavedLineRead, SelfComparisonListItem } from '@/lib/api'
import Image from 'next/image'
import WiseMark from '@/components/ui/WiseMark'

type Quote = { text: string; date: string }
type ClosingData = {
  observation: string
  question: string
  then_quote: Quote | null
  now_quote: Quote | null
  hidden_continuity: string | null
  sentence_owed: string | null
}
type YvYEvent = {
  type: string
  which?: 'then' | 'now'
  data?: string
  start?: string
  end?: string
  error_code?: string
  observation?: string
  question?: string
  then_quote?: Quote | null
  now_quote?: Quote | null
  hidden_continuity?: string | null
  sentence_owed?: string | null
  comparison_id?: string
}

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
function fmtSpan(startISO: string, endISO: string): string {
  const s = new Date(startISO), e = new Date(endISO)
  return `${MONTHS[s.getUTCMonth()]} ${s.getUTCDate()} \u2013 ${MONTHS[e.getUTCMonth()]} ${e.getUTCDate()}`
}
function fmtDate(iso: string): string {
  const d = new Date(iso)
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`
}

export default function YouVsYouPage() {
  const router = useRouter()
  const authed = useAuthGate()
  const [status, setStatus] = useState<SelfComparisonStatus | null>(null)
  const [loading, setLoading] = useState(true)

  // 'reading' replays a PAST run through the same view 'streaming' renders live.
  // One tree, not two: that is what makes "shows what generation showed" true by
  // construction rather than by care.
  const [mode, setMode] = useState<'input' | 'streaming' | 'reading'>('input')
  const [prompt, setPrompt] = useState('')
  const [past, setPast] = useState<SelfComparisonListItem[]>([])
  // Distinct from `past.length === 0`: until the list has actually come back,
  // empty means "unknown", and rendering the empty-state on it would flash the
  // "will gather here" line at someone who has ten.
  const [pastLoaded, setPastLoaded] = useState(false)
  const [showAllPast, setShowAllPast] = useState(false)
  const [opening, setOpening] = useState(false)
  const [savedLines, setSavedLines] = useState<SavedLineRead[]>([])
  const [showLines, setShowLines] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const [thenText, setThenText] = useState('')
  const [nowText, setNowText] = useState('')
  const [thenDates, setThenDates] = useState<{ start: string; end: string } | null>(null)
  const [nowDates, setNowDates] = useState<{ start: string; end: string } | null>(null)
  const [streamError, setStreamError] = useState<string | null>(null)
  const [remaining, setRemaining] = useState<number | null>(null)
  const [closing, setClosing] = useState<ClosingData | null>(null)
  const [comparisonId, setComparisonId] = useState<string | null>(null)
  const [ringTrue, setRingTrue] = useState<string | null>(null)
  const [ringSubmitting, setRingSubmitting] = useState(false)
  const [ringTrueConfirmed, setRingTrueConfirmed] = useState(false)
  const [sentenceSaved, setSentenceSaved] = useState(false)
  const [sentenceSaving, setSentenceSaving] = useState(false)

  useEffect(() => {
    if (!authed) return
    async function load() {
      try {
        const s = await api.getSelfComparisonStatus()
        setStatus(s)
        setRemaining(s.weekly_remaining ?? null)
        if (s.unlocked) {
          try { const r = await api.listSavedLines(); setSavedLines(r.items) } catch { /* optional */ }
          // Best-effort, exactly as the saved lines above: a failed list must not
          // cost the person the ability to ask a new question.
          try { setPast(await api.listSelfComparisons()) } catch { /* optional */ }
          finally { setPastLoaded(true) }
        }
      } catch { setStatus(null) } finally { setLoading(false) }
    }
    load()
  }, [authed, router])

  async function ask() {
    const p = prompt.trim()
    if (!p || submitting) return
    setSubmitting(true)
    setMode('streaming')
    setThenText(''); setNowText(''); setThenDates(null); setNowDates(null); setStreamError(null)
    setClosing(null); setComparisonId(null); setRingTrue(null); setSentenceSaved(false)
    try {
      const res = await api.streamSelfComparison({ prompt: p })
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let active: 'then' | 'now' | null = null
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const parts = buf.split('\n')
        buf = parts.pop() ?? ''
        for (const line of parts) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue
          let ev: YvYEvent
          try { ev = JSON.parse(raw) as YvYEvent } catch { continue }
          if (ev.type === 'self') {
            active = ev.which ?? null
            if (ev.which === 'then' && ev.start && ev.end) setThenDates({ start: ev.start, end: ev.end })
            else if (ev.which === 'now' && ev.start && ev.end) setNowDates({ start: ev.start, end: ev.end })
          } else if (ev.type === 'chunk') {
            const w = ev.which ?? active
            if (w === 'then') setThenText((t) => t + (ev.data ?? ''))
            else if (w === 'now') setNowText((t) => t + (ev.data ?? ''))
          } else if (ev.type === 'safety' || ev.type === 'safety_override') {
            // safety_override: an answer that already streamed was withheld
            // after the fact (post-generation check, TD-101 pattern). The
            // safety state unmounts both answers, so the text goes too.
            setStreamError('safety')
          } else if (ev.type === 'error') {
            setStreamError(ev.error_code ?? 'error')
          } else if (ev.type === 'closing') {
            setClosing({
              observation: ev.observation ?? '',
              question: ev.question ?? '',
              then_quote: ev.then_quote ?? null,
              now_quote: ev.now_quote ?? null,
              hidden_continuity: ev.hidden_continuity ?? null,
              sentence_owed: ev.sentence_owed ?? null,
            })
          } else if (ev.type === 'done') {
            if (ev.comparison_id) setComparisonId(ev.comparison_id)
            setRemaining((r) => (r !== null ? Math.max(0, r - 1) : r))
            // The run just became listable. Re-pull rather than splicing it in
            // locally, so the list stays the server's answer and the newest row
            // carries the same created_at everything else is ordered by.
            api.listSelfComparisons().then(setPast).catch(() => {})
          }
        }
      }
    } catch (e) {
      setStreamError(e instanceof RateLimitError ? 'rate_limit' : 'error')
    } finally {
      setSubmitting(false)
    }
  }

  // Reopen a past run: pull the stored payload by id and pour it into the same
  // state the stream fills, then switch the view to 'reading'. No generation, no
  // write — this is the whole of the read path on the client.
  async function openPast(id: string) {
    if (opening) return
    setOpening(true)
    try {
      const run = await api.getSelfComparison(id)
      setPrompt(run.prompt)
      setThenText(run.then.answer)
      setNowText(run.now.answer)
      // Both ends or neither: fmtSpan needs the pair, and a half-window would
      // render a dash with nothing on one side of it.
      setThenDates(run.then.start && run.then.end ? { start: run.then.start, end: run.then.end } : null)
      setNowDates(run.now.start && run.now.end ? { start: run.now.start, end: run.now.end } : null)
      setClosing(run.closing)
      setComparisonId(run.id)
      setRingTrue(run.ring_true)
      // The server already holds this verdict, so "Noted." is earned on arrival —
      // the same contract submitRingTrue applies to a fresh one. A run judged
      // months ago must not reopen looking unanswered.
      setRingTrueConfirmed(run.ring_true !== null)
      setSentenceSaved(run.saved)
      setStreamError(null)
      setMode('reading')
    } catch {
      // Leave the person on the input screen rather than opening an empty run.
    } finally {
      setOpening(false)
    }
  }

  async function submitRingTrue(value: string) {
    if (!comparisonId || ringSubmitting) return
    // Selection optimistic, confirmation earned (Γ-2b). "Noted." renders off
    // ringTrueConfirmed, which is set only once the server has the verdict; a
    // failed write reverts the selection and asks again rather than claiming an
    // answer that never landed.
    const previous = ringTrue
    setRingSubmitting(true)
    setRingTrue(value)
    try {
      await api.setSelfComparisonRingTrue(comparisonId, value)
      setRingTrueConfirmed(true)
    } catch {
      setRingTrue(previous)
    } finally { setRingSubmitting(false) }
  }

  // Save/unsave the "sentence you owe yourself" → Reflections feed. Optimistic,
  // mirroring the counterview Save toggle; reverts on failure.
  async function toggleSaveSentence() {
    if (!comparisonId || sentenceSaving) return
    const next = !sentenceSaved
    setSentenceSaving(true)
    setSentenceSaved(next)
    try {
      if (next) await api.saveSelfComparison(comparisonId)
      else await api.unsaveSelfComparison(comparisonId)
    } catch {
      setSentenceSaved(!next)
    } finally {
      setSentenceSaving(false)
    }
  }

  return (
    <main className="relative min-h-screen [min-height:100svh] overflow-hidden">
      <div className="fixed inset-0 z-0">
        <Image src="/personas/youvsyou.webp" alt="" fill className="object-cover object-center" priority />
        <div className="absolute inset-0" style={{ backgroundColor: '#EFE3CC', opacity: 0.75 }} />
      </div>
      <div
        className="relative z-10 min-h-screen [min-height:100svh] overflow-y-auto px-[24px] pt-[24px] pb-[60px] flex flex-col gap-[20px]"
        style={{ background: 'linear-gradient(to bottom, rgba(239,227,204,0.10) 0%, rgba(239,227,204,0.22) 100%)' }}
      >
      <SubPageNav fallbackHref="/app/rituals" />

      <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark text-center">YOU VS. YOU</p>

      {loading && <p className="font-lora text-[14px] text-sepia text-center mt-[40px]">Gathering&hellip;</p>}

      {/* Forming (locked) */}
      {!loading && status && !status.unlocked && (
        <div className="bg-paper border-[0.5px] border-edge rounded-[18px] shadow-card px-[20px] py-[32px] text-center flex flex-col gap-[16px]">
          <p className="font-cormorant text-[24px] font-medium text-ink leading-snug">Your other self is still forming.</p>
          <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
            Keep talking with the minds. As your words gather, a second you takes shape &mdash;
            who you were, beside who you&rsquo;re becoming. When there&rsquo;s enough, you&rsquo;ll meet them here.
          </p>
          {status.forming_preview.length > 0 && (
            <div className="mt-[8px] pt-[16px] border-t border-edge flex flex-col gap-[12px]">
              <div className="flex items-center justify-center gap-[8px]">
                <WiseMark size={22} />
                <p className="font-lora text-[11px] uppercase tracking-[0.2em] text-bronze-dark">What&rsquo;s beginning to take shape</p>
              </div>
              <ul className="flex flex-col gap-[8px] text-left">
                {status.forming_preview.map((line, i) => (
                  <li key={i} className="flex gap-[8px] font-cormorant italic text-[16px] text-charcoal leading-snug">
                    <span className="text-bronze not-italic flex-shrink-0" aria-hidden="true">&bull;</span>
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Unlocked - input */}
      {!loading && status && status.unlocked && mode === 'input' && (
        <div className="flex flex-col gap-[16px]">
          <p className="font-cormorant text-[22px] font-medium text-ink text-center leading-snug">
            Ask one question &mdash; and hear it answered by who you were, and who you are now.
          </p>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={3} maxLength={600}
            placeholder="Ask both of you something &mdash; about loneliness, about doomscrolling, about anything."
            className="w-full resize-none bg-white border border-[0.5px] border-edge rounded-sm px-[14px] py-[12px] font-lora text-[15px] text-ink leading-[1.5] placeholder:text-sepia/60 focus:outline-none focus:border-bronze/50" />
          {savedLines.length > 0 && (
            <div>
              <button type="button" onClick={() => setShowLines((v) => !v)} className="flex items-center gap-[6px] font-lora text-[13px] text-sepia">
                <span>Or start from something you&rsquo;ve said</span>
                <ChevronDown size={14} strokeWidth={1.5} className={`transition-transform ${showLines ? 'rotate-180' : ''}`} />
              </button>
              {showLines && (
                <div className="mt-[8px] border border-[0.5px] border-edge rounded-sm overflow-hidden">
                  {savedLines.slice(0, 8).map((sl) => (
                    <button key={sl.id} type="button" onClick={() => { setPrompt(sl.message_content); setShowLines(false) }}
                      className="w-full text-left px-[12px] py-[10px] border-b border-[0.5px] border-edge last:border-b-0 bg-paper active:bg-linen/60">
                      <span className="font-lora text-[13px] text-ink line-clamp-2 leading-snug">{sl.message_content}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          <button type="button" onClick={ask} disabled={!prompt.trim() || submitting || remaining === 0}
            className="self-center mt-[4px] bg-ink text-vellum rounded-[6px] px-[24px] py-[12px] font-cormorant text-[17px] font-medium disabled:opacity-40">
            Ask both selves
          </button>
          {status.weekly_limit != null && (
            <p className="font-lora text-[12px] text-sepia text-center">
              {remaining === 0
                ? <>You&rsquo;ve used all {status.weekly_limit} this week.</>
                : <>{remaining ?? status.weekly_remaining} of {status.weekly_limit} left this week</>}
            </p>
          )}

          {/* Earlier comparisons — the revisit list, in the shape the counterview
              page established. It sits INSIDE the input block on purpose, which
              means it stays reachable when remaining === 0: a capped reader can
              still return to what they already have. */}
          {pastLoaded && (
            <section className="mt-[20px]">
              <p className="font-lora text-[11px] uppercase tracking-[0.22em] text-bronze-dark mb-[10px]">
                Earlier comparisons
              </p>
              {past.length === 0 ? (
                <p className="font-lora text-[13px] text-sepia">Your past comparisons will gather here.</p>
              ) : (
                <>
                  <ul className="space-y-[8px]">
                    {(showAllPast ? past : past.slice(0, 3)).map((item) => (
                      <li key={item.id}>
                        <button
                          type="button"
                          onClick={() => openPast(item.id)}
                          disabled={opening}
                          className="w-full text-left bg-paper/60 border-[0.5px] border-edge rounded-[8px] px-[12px] py-[9px] active:scale-[0.99] transition-transform disabled:opacity-60"
                        >
                          <span className="flex items-baseline gap-[10px]">
                            {/* The question they typed, which is what makes one row
                                tell itself apart from another. */}
                            <span className="flex-1 font-cormorant text-[15px] text-ink leading-snug line-clamp-2">{item.prompt}</span>
                            {/* Dated, unlike the counterview list: the whole subject
                                of this ritual is time, so an undated list would be odd. */}
                            <span className="flex-shrink-0 font-lora text-[11px] text-sepia">{fmtDate(item.created_at)}</span>
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                  {past.length > 3 && (
                    <button
                      type="button"
                      onClick={() => setShowAllPast((v) => !v)}
                      className="mt-[12px] font-lora text-[11px] uppercase tracking-[0.22em] text-bronze-dark active:opacity-60 transition-opacity"
                    >
                      {showAllPast ? 'Show fewer' : `Show earlier (${past.length - 3})`}
                    </button>
                  )}
                </>
              )}
            </section>
          )}
        </div>
      )}

      {/* Unlocked - the result view: streaming reveal, or a past run replayed */}
      {!loading && status && status.unlocked && mode !== 'input' && (
        <div className="flex flex-col gap-[20px]">
          <p className="font-cormorant italic text-[18px] text-charcoal text-center leading-snug">{prompt}</p>
          {streamError && (
            <p className="font-lora text-[14px] text-charcoal text-center">
              {streamError === 'rate_limit' ? 'You\u2019ve reached this week\u2019s limit. Try again next week.'
                : streamError === 'safety' ? 'Let\u2019s set this one aside for now.'
                : 'Something went wrong. Try again in a moment.'}
            </p>
          )}
          {!streamError && (
            <>
              <div className="bg-paper border-[0.5px] border-edge rounded-[16px] shadow-card px-[18px] py-[20px] flex flex-col gap-[8px]">
                <div className="flex items-baseline justify-between">
                  <span className="font-lora text-[11px] uppercase tracking-[0.2em] text-bronze-dark">Then</span>
                  {thenDates && <span className="font-lora text-[11px] text-sepia">{fmtSpan(thenDates.start, thenDates.end)}</span>}
                </div>
                <p className="font-cormorant text-[17px] text-ink leading-snug whitespace-pre-wrap">{thenText}</p>
              </div>
              <div className="bg-paper border-[0.5px] border-edge rounded-[16px] shadow-card px-[18px] py-[20px] flex flex-col gap-[8px]">
                <div className="flex items-baseline justify-between">
                  <span className="font-lora text-[11px] uppercase tracking-[0.2em] text-bronze-dark">Now</span>
                  {nowDates && <span className="font-lora text-[11px] text-sepia">{fmtSpan(nowDates.start, nowDates.end)}</span>}
                </div>
                <p className="font-cormorant text-[17px] text-ink leading-snug whitespace-pre-wrap">{nowText}</p>
              </div>

              {closing && closing.observation && (
                <div className="bg-linen border-[0.5px] border-bronze/30 rounded-[16px] shadow-card px-[18px] py-[20px] flex flex-col gap-[14px]">
                  <div className="flex items-center gap-[8px]">
                    <WiseMark size={22} />
                    <span className="font-lora text-[11px] uppercase tracking-[0.2em] text-bronze-dark">The Wise Room says</span>
                  </div>
                  <p className="font-cormorant text-[18px] text-ink leading-snug">{closing.observation}</p>

                  {(closing.then_quote || closing.now_quote) && (
                    <div className="flex flex-col gap-[10px]">
                      {closing.then_quote && (
                        <div className="border-l-2 border-bronze/40 pl-[12px]">
                          <p className="font-cormorant italic text-[15px] text-charcoal leading-snug">&ldquo;{closing.then_quote.text}&rdquo;</p>
                          <p className="font-lora text-[10px] uppercase tracking-[0.16em] text-sepia mt-[3px]">Then · {fmtDate(closing.then_quote.date)}</p>
                        </div>
                      )}
                      {closing.now_quote && (
                        <div className="border-l-2 border-bronze/40 pl-[12px]">
                          <p className="font-cormorant italic text-[15px] text-charcoal leading-snug">&ldquo;{closing.now_quote.text}&rdquo;</p>
                          <p className="font-lora text-[10px] uppercase tracking-[0.16em] text-sepia mt-[3px]">Now · {fmtDate(closing.now_quote.date)}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {closing.question && (
                    <p className="font-cormorant text-[16px] text-ink leading-snug">{closing.question}</p>
                  )}

                  {/* R1a closing beats — the last substantive lines before the user is
                      asked to judge, so sentence_owed lands with full weight. Rendered
                      only when the server grounded them (null → omitted silently). */}
                  {closing.hidden_continuity && (
                    <div className="flex flex-col gap-[6px] pt-[12px] border-t border-bronze/20">
                      <span className="font-lora text-[11px] uppercase tracking-[0.2em] text-bronze-dark">What hasn&rsquo;t moved</span>
                      <p className="font-cormorant text-[17px] text-ink leading-snug">{closing.hidden_continuity}</p>
                    </div>
                  )}
                  {closing.sentence_owed && (
                    <div className="flex flex-col gap-[6px] pt-[12px] border-t border-bronze/20">
                      <span className="font-lora text-[11px] uppercase tracking-[0.2em] text-bronze-dark">A sentence you owe yourself</span>
                      <p className="font-cormorant italic text-[19px] text-ink leading-snug">{closing.sentence_owed}</p>
                      {comparisonId && (
                        <button
                          type="button"
                          onClick={toggleSaveSentence}
                          disabled={sentenceSaving}
                          className="self-start mt-[6px] min-h-[40px] flex items-center gap-[7px] px-[14px] border-[0.5px] border-charcoal rounded-[6px] font-cormorant text-[15px] text-charcoal disabled:opacity-50"
                        >
                          {sentenceSaved ? <BookmarkCheck size={16} strokeWidth={1.5} /> : <Bookmark size={16} strokeWidth={1.5} />}
                          {sentenceSaved ? 'Saved' : 'Save'}
                        </button>
                      )}
                    </div>
                  )}

                  {comparisonId && (
                    <div className="flex flex-col gap-[8px] mt-[2px]">
                      <p className="font-lora text-[11px] text-sepia">Does this ring true?</p>
                      <div className="flex gap-[8px]">
                        {([['yes','Rings true'],['partly','Partly'],['no','No']] as const).map(([val, label]) => (
                          <button key={val} type="button" onClick={() => submitRingTrue(val)} disabled={ringSubmitting}
                            className={`flex-1 min-h-[40px] rounded-[6px] border-[0.5px] font-lora text-[12px] transition-colors disabled:opacity-50
                              ${ringTrue === val ? 'bg-ink text-vellum border-ink' : 'bg-paper text-charcoal border-edge active:bg-linen/60'}`}>
                            {label}
                          </button>
                        ))}
                      </div>
                      {ringTrueConfirmed && (
                        <p className="font-lora text-[12px] text-sepia italic">Noted.</p>
                      )}
                    </div>
                  )}

                  <p className="font-lora text-[11px] text-sepia italic leading-snug">
                    This is only what your words suggest &mdash; you&rsquo;re the one who knows.
                  </p>
                </div>
              )}
            </>
          )}
          <button type="button" onClick={() => { setMode('input'); setPrompt('') }}
            className="self-center font-lora text-[13px] text-sepia underline underline-offset-2">Ask another</button>
        </div>
      )}

      {!loading && !status && (
        <p className="font-lora text-[15px] text-charcoal text-center mt-[40px]">Couldn&rsquo;t load this right now. Try again in a moment.</p>
      )}
      </div>
    </main>
  )
}
