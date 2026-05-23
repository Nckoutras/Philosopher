'use client'

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import { api, ShareLimitError } from '@/lib/api'
import type { SavedLineRead } from '@/lib/api'

interface Props {
  item: SavedLineRead
  portraitUrl: string
  onClick: () => void
  onAskAnotherMind?: () => void
}

export default function SavedLineCard({ item, portraitUrl, onClick, onAskAnotherMind }: Props) {
  const [shareLoading, setShareLoading] = useState(false)

  async function handleShare() {
    const shortShareText = `${item.persona_display_name} told me:\nthegreatminds.app`
    const fullShareText  = `${item.persona_display_name} told me:\n\n${item.message_content}\n\nthegreatminds.app`
    const origin = typeof window !== 'undefined' ? window.location.origin : ''
    const url = `${origin}/app/chat/conv/${item.conversation_id}`

    setShareLoading(true)
    try {
      const blob = await api.createShareScreenshot(item.id)
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
    } catch (err) {
      if (err instanceof ShareLimitError) {
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
      // Fallback: text-only share
      try {
        if (typeof navigator !== 'undefined' && navigator.share) {
          await navigator.share({ title: 'Great Minds', text: fullShareText, url })
        } else {
          await navigator.clipboard.writeText(fullShareText + '\n' + url)
          toast('Copied to clipboard')
        }
      } catch {
        // user cancelled
      }
    } finally {
      setShareLoading(false)
    }
  }

  return (
    // W2: outer div handles the Revisit tap (whole-card navigation).
    // "Ask another mind" is an explicit inner button with stopPropagation.
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick() }}
      className="w-full text-left bg-paper border border-[0.5px] border-edge rounded-md shadow-card px-[18px] py-[16px] cursor-pointer"
    >
      <p className="font-cormorant text-[17px] font-normal italic text-ink leading-[1.45]">
        {item.message_content}
      </p>
      <div className="mt-[8px] flex items-center gap-[6px]">
        {portraitUrl ? (
          <img
            src={portraitUrl}
            alt={item.persona_display_name}
            width={28}
            height={28}
            className="object-cover rounded-[2px] flex-shrink-0"
          />
        ) : (
          <div className="w-[28px] h-[28px] bg-edge rounded-[2px] flex-shrink-0" aria-hidden="true" />
        )}
        <span className="font-lora text-[11px] text-sepia">
          {item.persona_display_name} · {formatDistanceToNow(new Date(item.saved_at), { addSuffix: true })}
        </span>
      </div>

      {onAskAnotherMind && (
        <div className="mt-[10px] flex items-center gap-[8px] flex-wrap">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onClick()
            }}
            className="px-[12px] min-h-[44px] flex items-center border border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal"
          >
            Revisit
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onAskAnotherMind()
            }}
            className="px-[12px] min-h-[44px] flex items-center border border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal"
          >
            Ask another mind
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              handleShare()
            }}
            disabled={shareLoading}
            className="px-[12px] min-h-[44px] flex items-center border border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal disabled:opacity-50"
          >
            {shareLoading ? 'Sharing…' : 'Share'}
          </button>
        </div>
      )}
    </div>
  )
}
