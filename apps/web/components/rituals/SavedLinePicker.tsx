'use client'

import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import type { SavedLineRead } from '@/lib/api'

interface Props {
  savedLines: SavedLineRead[]
  selectedLineId: string
  onChange: (id: string) => void
  portraitUrlsBySlug: Record<string, string>
}

function AvatarCircle({ url, name }: { url?: string; name: string }) {
  const [failed, setFailed] = useState(false)
  const initial = name[0]?.toUpperCase() ?? '?'

  if (url && !failed) {
    return (
      <div className="w-7 h-7 rounded-full overflow-hidden flex-shrink-0 bg-linen-deep">
        <img
          src={url}
          alt={name}
          onError={() => setFailed(true)}
          className="w-full h-full object-cover object-top"
        />
      </div>
    )
  }
  return (
    <div className="w-7 h-7 rounded-full bg-bronze flex items-center justify-center flex-shrink-0">
      <span className="font-lora text-[11px] text-vellum font-medium">{initial}</span>
    </div>
  )
}

export default function SavedLinePicker({ savedLines, selectedLineId, onChange, portraitUrlsBySlug }: Props) {
  const [expanded, setExpanded] = useState(false)

  const selectedLine = savedLines.find((sl) => sl.id === selectedLineId) ?? savedLines[0]

  return (
    <div>
      {/* Compact summary row */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-3 min-h-[44px] py-[10px] bg-paper border border-[0.5px] border-edge rounded-sm transition-[border-color,box-shadow] duration-200 focus:outline-none focus:border-bronze focus:ring-1 focus:ring-bronze/20"
      >
        <AvatarCircle
          url={portraitUrlsBySlug[selectedLine.persona_slug]}
          name={selectedLine.persona_display_name}
        />
        <span className="font-lora text-[14px] font-medium text-ink flex-1 min-w-0 truncate text-left">
          {selectedLine.message_content}
        </span>
        <ChevronDown
          size={15}
          strokeWidth={1.5}
          className={`text-sepia flex-shrink-0 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Expanded list */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            className="overflow-hidden mt-1"
          >
            <div className="border border-[0.5px] border-edge rounded-sm overflow-hidden">
              {savedLines.map((sl) => (
                <button
                  key={sl.id}
                  type="button"
                  onClick={() => { onChange(sl.id); setExpanded(false) }}
                  className={`w-full flex items-center gap-3 px-3 min-h-[44px] py-[10px] text-left border-b border-[0.5px] border-edge last:border-b-0 transition-colors
                    ${sl.id === selectedLineId ? 'bg-linen' : 'bg-paper active:bg-linen/60'}`}
                >
                  <AvatarCircle
                    url={portraitUrlsBySlug[sl.persona_slug]}
                    name={sl.persona_display_name}
                  />
                  <span className={`font-lora text-[14px] text-ink flex-1 min-w-0 line-clamp-2 leading-snug ${sl.id === selectedLineId ? 'font-medium' : ''}`}>
                    {sl.message_content}
                  </span>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
