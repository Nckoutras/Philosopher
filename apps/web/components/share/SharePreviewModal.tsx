'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { api, ShareLimitError } from '@/lib/api'
import { useStore } from '@/lib/store'
import { dynamicFontSize } from '@/lib/shareUtils'

interface SharePreviewModalProps {
  isOpen: boolean
  onClose: () => void
  kind?: 'line' | 'council' | 'mirror' | 'letter' | 'counterview'
  // 'line' variant
  savedLineId?: string
  personaName?: string
  portraitUrl?: string
  conversationId?: string
  // 'council' variant
  councilSessionId?: string
  councilPortraits?: string[]   // participating-persona portrait URLs (preview thumbnails)
  // 'counterview' variant
  counterviewId?: string
  counterviewPortraits?: string[]   // the two personas' portrait URLs (preview thumbnails)
  // 'mirror' variant (personaName = host name, portraitUrl = host portrait)
  mirrorId?: string
  // 'letter' variant
  weeklyLetterId?: string
  letterTitle?: string
  // Monthly 'season' letter only: show the real generated PNG as the preview
  // (falls back to the HTML preview until the blob is ready). Does not affect
  // the weekly/line/council/mirror previews.
  seasonImagePreview?: boolean
  // all variants
  quote: string
  onShareComplete?: () => void
}

export default function SharePreviewModal({
  isOpen,
  onClose,
  kind = 'line',
  savedLineId,
  personaName,
  portraitUrl,
  conversationId,
  councilSessionId,
  councilPortraits,
  counterviewId,
  counterviewPortraits,
  mirrorId,
  weeklyLetterId,
  letterTitle,
  seasonImagePreview = false,
  quote,
  onShareComplete,
}: SharePreviewModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  const [annotation, setAnnotation]     = useState('')
  const [shareLoading, setShareLoading] = useState(false)
  const [shareError, setShareError]     = useState<string | null>(null)
  const [preparedBlob, setPreparedBlob] = useState<Blob | null>(null)
  const [preparing, setPreparing]       = useState(false)
  const [previewUrl, setPreviewUrl]     = useState<string | null>(null)
  const plan  = useStore((s) => s.plan)
  const isPro = plan === 'pro' || plan === 'premium'

  const isCouncil = kind === 'council'
  const isMirror  = kind === 'mirror'
  const isLetter  = kind === 'letter'
  const isCounterview = kind === 'counterview'

  const generateBlob = useCallback((): Promise<Blob> => {
    if (kind === 'council') return api.shareCouncil(councilSessionId!)
    if (kind === 'mirror')  return api.shareMirror(mirrorId!)
    if (kind === 'letter')  return api.shareWeeklyLetter(weeklyLetterId!)
    if (kind === 'counterview') return api.shareCounterview(counterviewId!)
    return api.createShareScreenshot(savedLineId!)
  }, [kind, councilSessionId, mirrorId, weeklyLetterId, counterviewId, savedLineId])

  // Reset on open; pre-generate the image for pro/premium so the Send tap opens
  // the native share sheet synchronously (iOS needs navigator.share inside the
  // gesture). Retry on failure (e.g. a council synthesis row that just committed,
  // or a transient error) so a blob is ready before Send enables — never let the
  // user tap into an await, which would strip the iOS user-activation.
  // Free users keep generate-on-send (pre-gen would spend a 3/90 credit).
  useEffect(() => {
    if (!isOpen) {
      setPreparedBlob(null)
      setPreparing(false)
      return
    }
    setAnnotation('')
    setShareError(null)
    setPreparedBlob(null)
    if (!isPro) return
    let cancelled = false
    setPreparing(true)

    ;(async () => {
      const MAX_ATTEMPTS = 3
      for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
        try {
          const b = await generateBlob()
          if (!cancelled) { setPreparedBlob(b); setShareError(null) }
          return
        } catch (err) {
          if (err instanceof ShareLimitError) return // limit is handled on Send
          if (cancelled) return
          if (attempt < MAX_ATTEMPTS - 1) {
            await new Promise((r) => setTimeout(r, 600 * (attempt + 1)))
          } else {
            setShareError('Could not prepare image. Tap Send to retry.')
          }
        }
      }
    })().finally(() => { if (!cancelled) setPreparing(false) })

    return () => { cancelled = true }
  }, [isOpen, isPro, generateBlob])

  // Monthly 'season' letter: turn the prepared PNG into an object URL so the
  // preview can show the real card. Scoped to seasonImagePreview; revoked on
  // change/unmount.
  useEffect(() => {
    if (!(seasonImagePreview || isCounterview) || !preparedBlob) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(preparedBlob)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [seasonImagePreview, isCounterview, preparedBlob])

  // Keyboard (Escape + Tab trap) handlers
  useEffect(() => {
    if (!isOpen) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape' && !shareLoading) { onClose(); return }
      if (e.key !== 'Tab') return
      const modal = cancelRef.current?.closest('[role="dialog"]') as HTMLElement | null
      if (!modal) return
      const focusable = Array.from(
        modal.querySelectorAll<HTMLElement>('textarea, button:not([disabled])')
      )
      if (!focusable.length) return
      const first = focusable[0]
      const last  = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, shareLoading, onClose])

  // Initial focus on Cancel
  useEffect(() => {
    if (isOpen) cancelRef.current?.focus()
  }, [isOpen])

  async function handleSend() {
    setShareLoading(true)
    setShareError(null)

    const lead = isCouncil
      ? `The Council's reading:`
      : isMirror
      ? `The mirror reflected:`
      : isLetter
      ? `My Sunday Letter:`
      : isCounterview
      ? `The case against:`
      : `${personaName} told me:`
    const shortShareText = `${lead}\nthewiseroom.app`
    const fullShareText  = `${lead}\n\n${quote}\n\nthewiseroom.app`
    const origin = typeof window !== 'undefined' ? window.location.origin : ''
    const url    = isCouncil
      ? `${origin}/app/council`
      : isMirror
      ? `${origin}/app/mirror`
      : isLetter
      ? `${origin}/app/letters`
      : isCounterview
      ? `${origin}/app/counterview`
      : `${origin}/app/chat/conv/${conversationId}`
    const filename = isCouncil
      ? 'council-reading.png'
      : isMirror
      ? 'mirror-reflection.png'
      : isLetter
      ? 'sunday-letter.png'
      : isCounterview
      ? 'counterview.png'
      : 'reflection.png'

    const downloadFallback = (b: Blob) => {
      const blobUrl = URL.createObjectURL(b)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = filename
      a.click()
      URL.revokeObjectURL(blobUrl)
      void navigator.clipboard?.writeText(`${fullShareText}\n${url}`).catch(() => {})
      toast('Image saved — share it from your downloads')
    }

    // If a pre-generated blob is ready (pro/premium), there is NO await before
    // navigator.share below → iOS keeps the activation and the sheet opens.
    let blob = preparedBlob
    if (!blob) {
      try {
        blob = await generateBlob()
      } catch (err) {
        if (err instanceof ShareLimitError) {
          onClose()
          toast((t) => (
            <span>
              Free share limit reached (3/90 days).{' '}
              <a
                href="/app/upgrade"
                onClick={() => toast.dismiss(t.id)}
                style={{ textDecoration: 'underline' }}
              >
                Upgrade
              </a>
            </span>
          ))
        } else {
          setShareError('Could not generate image. Please try again.')
        }
        setShareLoading(false)
        return
      }
    }

    try {
      const file = new File([blob], filename, { type: 'image/png' })
      if (typeof navigator !== 'undefined' && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], text: shortShareText })
      } else {
        downloadFallback(blob)
      }
      onClose()
      onShareComplete?.()
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        onClose()
      } else {
        downloadFallback(blob)
        onClose()
        onShareComplete?.()
      }
    } finally {
      setShareLoading(false)
    }
  }

  if (!isOpen) return null

  // Scale factor: preview card width (320px) / canvas width (1080px)
  const previewFontSize    = (dynamicFontSize(quote.length) * 0.296).toFixed(1)

  // Approximate date stamp for the line/mirror-variant preview (mm/dd/yyyy).
  // The real card uses the record's timestamp; preview uses today.
  const now = new Date()
  const previewDate = `${String(now.getMonth() + 1).padStart(2, '0')}/${String(now.getDate()).padStart(2, '0')}/${now.getFullYear()}`

  // Line + mirror share the reflection layout; mirror swaps the hero + intro.
  const heroSrc     = isLetter ? '/personas/sundayletter.webp' : isMirror ? '/personas/mirror.webp' : '/personas/wise-room-hero.webp'
  const heroOpacity = (isMirror || isLetter) ? 'opacity-[0.10]' : 'opacity-[0.06]'
  const introLine   = isLetter
    ? (letterTitle || 'The Sunday Letter')
    : isMirror
    ? (personaName ? `${personaName} reflects` : 'The mirror reflects')
    : `${personaName} told me`

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Share reflection"
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
    >
      {/* Scrim */}
      <div
        className="absolute inset-0 bg-[rgba(31,27,20,0.5)]"
        aria-hidden="true"
        onClick={() => { if (!shareLoading) onClose() }}
      />

      {/* Dialog */}
      <div className="relative z-10 w-full max-w-[360px] bg-paper rounded-lg p-5 shadow-[0_8px_32px_rgba(31,27,20,0.18)] max-h-[85svh] overflow-y-auto">

        {/* ── Preview card (4:5 aspect ratio) ── */}
        {(seasonImagePreview || isCounterview) && previewUrl ? (
          /* Monthly 'season' letter & counterview — show the actual generated
             PNG. Falls back to the HTML preview below until the blob is ready. */
          <div
            className="relative w-full bg-vellum rounded-sm overflow-hidden mb-4"
            style={{ aspectRatio: '4/5' }}
            aria-hidden="true"
          >
            <img src={previewUrl} alt="" className="w-full h-full object-cover" />
          </div>
        ) : isCouncil ? (
          /* Council variant — redesigned to match the server PNG: faint
             boardroom hero, top wordmark+date, centred row of participating-
             persona thumbnails, "The Council", synthesis, bold stamp.
             Approximation of the server-rendered PNG. */
          <div
            className="relative w-full bg-vellum rounded-sm overflow-hidden mb-4"
            style={{ aspectRatio: '4/5' }}
            aria-hidden="true"
          >
            {/* Faint boardroom hero — resize-to-cover, very low opacity */}
            <img
              src="/personas/boardroom.webp"
              alt=""
              className="pointer-events-none absolute inset-0 w-full h-full object-cover opacity-[0.10]"
            />

            <div className="relative z-10 flex flex-col items-center h-full px-6 pt-4 pb-3">
              {/* "The Wise Room" + date — pinned top */}
              <p className="font-cormorant italic text-[12px] text-bronze text-center">The Wise Room</p>
              <p className="font-lora text-[9px] text-bronze text-center mt-0.5">{previewDate}</p>

              {/* Participating-persona thumbnail row (omitted when none supplied —
                  e.g. the council ritual screen, which degrades to bg-only) */}
              {councilPortraits && councilPortraits.length > 0 && (
                <div className="flex items-center gap-[6px] mt-3 mb-2">
                  {councilPortraits.slice(0, 4).map((src, i) => (
                    <div
                      key={i}
                      className="w-[40px] h-[40px] rounded-full overflow-hidden flex-shrink-0 bg-edge"
                    >
                      <img src={src} alt="" className="w-full h-full object-cover" />
                    </div>
                  ))}
                </div>
              )}

              {/* "The Council" */}
              <p className="font-cormorant text-[11px] font-medium text-ink text-center mt-2 mb-1">
                The Council
              </p>

              {/* Synthesis — centred in the leftover band */}
              <p
                className="font-cormorant italic text-ink text-center leading-[1.4] flex-1 flex items-center justify-center overflow-hidden"
                style={{ fontSize: `${previewFontSize}px` }}
              >
                {quote}
              </p>

              {/* Bold "thewiseroom.app" stamp */}
              <p className="font-lora text-[9px] font-bold text-bronze text-center mt-2">
                thewiseroom.app
              </p>
            </div>
          </div>
        ) : isCounterview ? (
          /* Counterview variant — HTML fallback shown until the real PNG is
             ready (free users always see this; pro pre-gen swaps to the PNG
             via the first branch). Approximation of the server-rendered card. */
          <div
            className="relative w-full bg-vellum rounded-sm overflow-hidden mb-4"
            style={{ aspectRatio: '4/5' }}
            aria-hidden="true"
          >
            <div className="relative z-10 flex flex-col items-center h-full px-6 pt-5 pb-4">
              <p className="font-cormorant italic text-[12px] text-bronze text-center">The Wise Room</p>
              {counterviewPortraits && counterviewPortraits.length > 0 && (
                <div className="flex items-center gap-[10px] mt-4 mb-3">
                  {counterviewPortraits.slice(0, 2).map((src, i) => (
                    <div key={i} className="w-[64px] h-[80px] rounded-sm overflow-hidden bg-edge">
                      <img src={src} alt="" className="w-full h-full object-cover" />
                    </div>
                  ))}
                </div>
              )}
              <p className="font-lora text-[9px] tracking-[0.18em] text-bronze-dark font-bold text-center mt-2">THE CASE AGAINST</p>
              <p
                className="font-cormorant italic text-ink text-center leading-[1.4] flex-1 flex items-center justify-center overflow-hidden"
                style={{ fontSize: `${previewFontSize}px` }}
              >
                {quote}
              </p>
              <p className="font-lora text-[9px] font-bold text-bronze text-center mt-2">thewiseroom.app</p>
            </div>
          </div>
        ) : (
          /* Line + mirror variant — redesigned: faint ritual hero bg, top
             wordmark+date, larger portrait, intro, auto-centred reflection,
             bold stamp. Approximation of the server-rendered PNG. */
          <div
            className="relative w-full bg-vellum rounded-sm overflow-hidden mb-4"
            style={{ aspectRatio: '4/5' }}
            aria-hidden="true"
          >
            {/* Faint ritual hero — resize-to-cover, very low opacity */}
            <img
              src={heroSrc}
              alt=""
              className={`pointer-events-none absolute inset-0 w-full h-full object-cover ${heroOpacity}`}
            />

            <div className="relative z-10 flex flex-col items-center h-full px-6 pt-4 pb-3">
              {/* "The Wise Room" + date — pinned top */}
              <p className="font-cormorant italic text-[12px] text-bronze text-center">The Wise Room</p>
              <p className="font-lora text-[9px] text-bronze text-center mt-0.5">{previewDate}</p>

              {/* Portrait — 10% larger (52 → 57px) */}
              <div className="w-[57px] h-[57px] rounded-full overflow-hidden flex-shrink-0 mt-3 mb-2 bg-edge flex items-center justify-center">
                {portraitUrl ? (
                  <img src={portraitUrl} alt="" className="w-full h-full object-cover" />
                ) : (
                  <span className="font-cormorant text-[24px] font-medium text-charcoal">
                    {personaName?.[0]?.toUpperCase()}
                  </span>
                )}
              </div>

              {/* Intro — "{Persona} told me" / "{Host} reflects" */}
              <p className="font-cormorant text-[11px] font-medium text-ink text-center mb-1">
                {introLine}
              </p>

              {/* Reflection — centred in the leftover band */}
              <p
                className="font-cormorant italic text-ink text-center leading-[1.4] flex-1 flex items-center justify-center overflow-hidden"
                style={{ fontSize: `${previewFontSize}px` }}
              >
                {quote}
              </p>

              {/* Bold "thewiseroom.app" stamp */}
              <p className="font-lora text-[9px] font-bold text-bronze text-center mt-2">
                thewiseroom.app
              </p>
            </div>
          </div>
        )}

        {/* Spacer where the (removed) annotation input used to live. The
            redesigned share cards — line, mirror, and council — no longer
            render a caption, so no variant takes annotation input. */}
        <div className="mb-4" />

        {/* ── Buttons ── */}
        <div className="flex gap-3">
          <button
            ref={cancelRef}
            type="button"
            onClick={onClose}
            disabled={shareLoading}
            className="flex-1 font-lora text-[13px] text-charcoal border border-edge rounded-sm py-2.5 px-4 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSend}
            disabled={shareLoading || preparing || (isPro && !preparedBlob && !shareError)}
            className="flex-1 font-lora text-[13px] text-vellum bg-bronze rounded-sm py-2.5 px-4 flex items-center justify-center disabled:opacity-70"
          >
            {(shareLoading || preparing) ? (
              <span
                className="inline-block w-3.5 h-3.5 border-[0.8px] border-vellum/30 border-t-vellum rounded-full animate-spin-slow"
                aria-label="Generating…"
              />
            ) : (
              'Send'
            )}
          </button>
        </div>

        {/* Error */}
        {shareError && (
          <p role="alert" className="font-lora text-[12px] text-danger mt-3 text-center">
            {shareError}
          </p>
        )}
      </div>
    </div>
  )
}
