'use client'

import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { api, ShareLimitError } from '@/lib/api'
import { dynamicFontSize, stripEmoji } from '@/lib/shareUtils'

interface SharePreviewModalProps {
  isOpen: boolean
  onClose: () => void
  savedLineId: string
  personaName: string
  portraitUrl?: string
  quote: string
  conversationId: string
  onShareComplete?: () => void
}

export default function SharePreviewModal({
  isOpen,
  onClose,
  savedLineId,
  personaName,
  portraitUrl,
  quote,
  conversationId,
  onShareComplete,
}: SharePreviewModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  const [annotation, setAnnotation]     = useState('')
  const [shareLoading, setShareLoading] = useState(false)
  const [shareError, setShareError]     = useState<string | null>(null)

  // Reset state on each open
  useEffect(() => {
    if (isOpen) {
      setAnnotation('')
      setShareError(null)
    }
  }, [isOpen])

  // Push history entry so the back button closes the modal
  useEffect(() => {
    if (!isOpen) return
    window.history.pushState({ modal: 'share-preview' }, '')
    return () => {
      if (window.history.state?.modal === 'share-preview') {
        window.history.back()
      }
    }
  }, [isOpen])

  // Keyboard (Escape + Tab trap) and popstate handlers
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
    function handlePopState() { onClose() }
    document.addEventListener('keydown', handleKeyDown)
    window.addEventListener('popstate', handlePopState)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('popstate', handlePopState)
    }
  }, [isOpen, shareLoading, onClose])

  // Initial focus on Cancel
  useEffect(() => {
    if (isOpen) cancelRef.current?.focus()
  }, [isOpen])

  function handleAnnotationChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const cleaned = stripEmoji(e.target.value)
    setAnnotation(cleaned.slice(0, 140))
  }

  async function handleSend() {
    setShareLoading(true)
    setShareError(null)
    const shortShareText = `${personaName} told me:\nthegreatminds.app`
    const fullShareText  = `${personaName} told me:\n\n${quote}\n\nthegreatminds.app`
    const origin = typeof window !== 'undefined' ? window.location.origin : ''
    const url    = `${origin}/app/chat/conv/${conversationId}`

    try {
      const blob = await api.createShareScreenshot(
        savedLineId,
        annotation.trim() || undefined,
      )
      const file = new File([blob], 'reflection.png', { type: 'image/png' })

      if (typeof navigator !== 'undefined' && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], text: shortShareText })
      } else {
        const blobUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = blobUrl
        a.download = 'reflection.png'
        a.click()
        URL.revokeObjectURL(blobUrl)
        await navigator.clipboard.writeText(fullShareText + '\n' + url).catch(() => {})
        toast('Image saved — share it from your downloads')
      }

      onClose()
      onShareComplete?.()
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
        return
      }
      // navigator.share cancelled by user — not an error
      if (err instanceof DOMException && err.name === 'AbortError') {
        onClose()
        return
      }
      setShareError('Could not generate image. Please try again.')
    } finally {
      setShareLoading(false)
    }
  }

  if (!isOpen) return null

  // Scale factor: preview card width (320px) / canvas width (1080px)
  const previewFontSize    = (dynamicFontSize(quote.length) * 0.296).toFixed(1)
  const displayAnnotation  = annotation.trim()

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
        <div
          className="w-full bg-vellum rounded-sm overflow-hidden mb-4 flex flex-col items-center px-6 pt-5 pb-4"
          style={{ aspectRatio: '4/5' }}
          aria-hidden="true"
        >
          {/* Portrait circle */}
          <div className="w-[52px] h-[52px] rounded-full overflow-hidden flex-shrink-0 mb-2 bg-edge flex items-center justify-center">
            {portraitUrl ? (
              <img src={portraitUrl} alt="" className="w-full h-full object-cover" />
            ) : (
              <span className="font-cormorant text-[22px] font-medium text-charcoal">
                {personaName[0]?.toUpperCase()}
              </span>
            )}
          </div>

          {/* Intro */}
          <p className="font-cormorant text-[11px] font-medium text-ink text-center mb-2">
            {personaName} told me:
          </p>

          {/* Quote — scaled dynamic font */}
          <p
            className="font-cormorant italic text-ink text-center leading-[1.4] flex-1 overflow-hidden"
            style={{ fontSize: `${previewFontSize}px` }}
          >
            {quote}
          </p>

          {/* Annotation preview */}
          {displayAnnotation && (
            <p className="font-lora text-[9px] text-bronze text-center mt-2 italic">
              &ldquo;{displayAnnotation}&rdquo;
            </p>
          )}

          {/* Mini footer */}
          <div className="mt-3 pt-2 border-t border-bronze/20 w-full text-center flex-shrink-0">
            <p className="font-cormorant italic text-[9px] text-bronze">Great Minds</p>
            <p className="font-lora text-[7px] text-bronze/60 mt-0.5">thegreatminds.app</p>
          </div>
        </div>

        {/* ── Annotation input ── */}
        <textarea
          value={annotation}
          onChange={handleAnnotationChange}
          placeholder="Add your thought…"
          maxLength={140}
          rows={1}
          disabled={shareLoading}
          className="w-full font-lora text-[13px] text-ink bg-transparent border border-edge rounded-sm px-3 py-2 resize-none overflow-hidden placeholder:text-sepia/60 focus:outline-none focus:border-bronze/50 disabled:opacity-50"
          style={{ minHeight: '38px', maxHeight: '60px' }}
          onInput={(e) => {
            const el = e.currentTarget
            el.style.height = 'auto'
            el.style.height = `${Math.min(el.scrollHeight, 60)}px`
          }}
        />

        {/* Character counter */}
        <p className="font-lora text-[11px] text-sepia text-right mt-1 mb-4">
          {annotation.length}/140
        </p>

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
            disabled={shareLoading}
            className="flex-1 font-lora text-[13px] text-vellum bg-bronze rounded-sm py-2.5 px-4 flex items-center justify-center disabled:opacity-70"
          >
            {shareLoading ? (
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
