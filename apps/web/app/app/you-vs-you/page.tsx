'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChevronLeft, ChevronDown } from 'lucide-react'
import { useStore } from '@/lib/store'
import { api, RateLimitError } from '@/lib/api'
import type { SelfComparisonStatus, SavedLineRead } from '@/lib/api'
import WiseMark from '@/components/ui/WiseMark'

type Quote = { text: string; date: string }
type ClosingData = { observation: string; question: string; then_quote: Quote | null; now_quote: Quote | null }
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
  comparison_id?: string
}

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
function fmtSpan(startISO: string, endISO: string): string {
  const s = new Date(startISO), e = new Date(endISO)
  return `${MONTHS[s.getUTCMonth()]} ${s.getUTCDate()} – ${MONTHS[e.getUTCMonth()]} ${e.getUTCDate()}`
}
function fmtDate(iso: string): string {
  const d = new Date(iso)
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`
}

export default function YouVsYouPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const [status, setStatus] = useState<SelfComparisonStatus | null>(null)
  const [loading, setLoading] = useState(true)

  const [mode, setMode] = useState<'input' | 'streaming'>('input')
  const [prompt, setPrompt] = useState('')
  const [savedLines, setSavedLines] = useState<SavedLineRead[]>([])
  const [showLines, setShowLines] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const [thenText, setThenText] = useState('')
  const [nowText, setNowText] = useState('')
  const [thenDates, setThenDates] = useState<{ start: string; end: string } | null>(null)
  const [nowDates, setNowDates] = useState<{ start: string; end: string } | null>(null)
  const [streamError, setStreamError] = useState<string | null>(null)
  const [closing, setClosing] = useState<ClosingData | null>(null)
  const [comparisonId, setComparisonId] = useState<string | null>(null)
  const [ringTrue, setRingTrue] = useState<string | null>(null)
  const [ringSubmitting, setRingSubmitting] = useState(false)

  useEffect(() => {
    if (token === null) { router.replace('/auth?mode=signin'); return }
    async function load() {
      try {
        const s = await api.getSelfComparisonStatus()
        setStatus(s)
        if (s.unlocked) {
          try { const r = await api.listSavedLines(); setSavedLines(r.items) } catch { /* optional */ }
        }
      } catch { setStatus(null) } finally { setLoading(false) }
    }
    load()
  }, [token, router])

  async function ask() {
    const p = prompt.trim()
    if (!p || submitting) return
    setSubmitting(true)
    setMode('streaming')
    setThenText(''); setNowText(''); setThenDates(null); setNowDates(null); setStreamError(null)
    setClosing(null); setComparisonId(null); setRingTrue(null)
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
          } else if (ev.type === 'safety') {
            setStreamError('safety')
          } else if (ev.type === 'error') {
            setStreamError(ev.error_code ?? 'error')
          } else if (ev.type === 'closing') {
            setClosing({
              observation: ev.observation ?? '',
              question: ev.question ?? '',
              then_quote: ev.then_quote ?? null,
              now_quote: ev.now_quote ?? null,
            })
          } else if (ev.type === 'done') {
            if (ev.comparison_id) setComparisonId(ev.comparison_id)
          }
        }
      }
    } catch (e) {
      setStreamError(e instanceof RateLimitError ? 'rate_limit' : 'error')
    } finally {
      setSubmitting(false)
    }
  }

  async function submitRingTrue(value: string) {
    if (!comparisonId || ringSubmitting) return
    setRingSubmitting(true)
    setRingTrue(value)
    try { await api.setSelfComparisonRingTrue(comparisonId, value) }
    catch { /* best-effort signal */ }
    finally { setRingSubmitting(false) }
  }

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum px-[24px] pt-[24px] pb-[60px] flex flex-col gap-[20px]">
      <button type="button" onClick={() => router.push('/app/rituals')} aria-label="Back to rituals"
        className="flex items-center gap-[4px] text-sepia self-start">
        <ChevronLeft size={18} strokeWidth={1.5} />
        <span className="font-lora text-[13px]">Rituals</span>
      </button>

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
              <div className="flex flex-col gap-[8px]">
                {status.forming_preview.map((line, i) => (
                  <p key={i} className="font-cormorant italic text-[16px] text-charcoal leading-snug">{line}</p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Unlocked — input */}
      {!loading && status && status.unlocked && mode === 'input' && (
        <div className="flex flex-col gap-[16px]">
          <p className="font-cormorant text-[22px] font-medium text-ink text-center leading-snug">
            Ask one question — and hear it answered by who you were, and who you are now.
          </p>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={3} maxLength={600}
            placeholder="Ask both of you something — about loneliness, about doomscrolling, about anything."
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
          <button type="button" onClick={ask} disabled={!prompt.trim() || submitting}
            className="self-center mt-[4px] bg-ink text-vellum rounded-[6px] px-[24px] py-[12px] font-cormorant text-[17px] font-medium disabled:opacity-40">
            Ask both selves
          </button>
        </div>
      )}

      {/* Unlocked — streaming reveal */}
      {!loading && status && status.unlocked && mode === 'streaming' && (
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

                  {comparisonId && (
                    <div className="flex flex-col gap-[8px] mt-[2px]">
                      <p className="font-lora text-[11px] text-sepia">Does this ring true?</p>
                      <div className="flex gap-[8px]">
                        {([['yes','Rings true'],['partly','Partly'],['no','Not really']] as const).map(([val, label]) => (
                          <button key={val} type="button" onClick={() => submitRingTrue(val)} disabled={ringSubmitting}
                            className={`flex-1 min-h-[40px] rounded-[6px] border-[0.5px] font-lora text-[12px] transition-colors disabled:opacity-50
                              ${ringTrue === val ? 'bg-ink text-vellum border-ink' : 'bg-paper text-charcoal border-edge active:bg-linen/60'}`}>
                            {label}
                          </button>
                        ))}
                      </div>
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
    </main>
  )
}
