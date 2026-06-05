'use client'

import { useEffect, useRef, useState } from 'react'
import { deriveInitials } from '@/lib/initials'

interface Props {
  user: { full_name: string | null; email: string }
  dailyQuestion: string
  onReflect: (topicText: string) => void
  onStartFresh: () => void
}

const REFLECT_TAIL = " Let's think through this together — where would you start?"

export default function TodaysTopicCard({ user, dailyQuestion, onReflect, onStartFresh }: Props) {
  const [topic, setTopic] = useState('')
  const heavyPhrase = dailyQuestion.split(/\s+—\s+/)[0]
  const initials = deriveInitials(user)
  const cardRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    function handleOutsideTap(e: MouseEvent | TouchEvent) {
      if (cardRef.current && !cardRef.current.contains(e.target as Node)) {
        textareaRef.current?.blur()
      }
    }
    document.addEventListener('mousedown', handleOutsideTap)
    document.addEventListener('touchstart', handleOutsideTap, { passive: true })
    return () => {
      document.removeEventListener('mousedown', handleOutsideTap)
      document.removeEventListener('touchstart', handleOutsideTap)
    }
  }, [])

  function handleReflect() {
    onReflect((topic.trim() || dailyQuestion) + REFLECT_TAIL)
  }

  return (
    <div ref={cardRef} className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] pt-[14px] pb-[16px]">
      <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[10px]">
        What's on your mind?
      </p>
      <div className="flex items-start gap-[10px]">
        <div className="w-[64px] h-[64px] rounded-full flex-shrink-0 flex items-center justify-center bg-bronze mt-[2px]">
          <span className="font-cormorant text-[24px] font-medium text-vellum">
            {initials}
          </span>
        </div>
        <textarea
          ref={textareaRef}
          rows={3}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder={heavyPhrase}
          className="flex-1 resize-none bg-transparent outline-none font-cormorant italic text-[16px] text-ink leading-snug placeholder:opacity-60 placeholder:italic placeholder:font-cormorant border border-bronze/40 rounded-[2px] focus:border-bronze focus:ring-1 focus:ring-bronze/20 pl-[10px] pr-3 py-2"
        />
      </div>
      {!topic && (
        <p className="font-lora text-[11px] italic text-sepia/70 mt-[8px] pl-[74px]">
          (or tap in to write your own)
        </p>
      )}
      <div className="mt-[12px] flex gap-[10px]">
        <button
          type="button"
          onClick={handleReflect}
          className="flex-1 h-[44px] bg-ink text-vellum rounded-[4px] font-cormorant text-[17px] font-medium"
        >
          Reflect on this
        </button>
        <button
          type="button"
          onClick={onStartFresh}
          className="flex-1 h-[44px] bg-transparent border border-ink text-ink rounded-[4px] font-cormorant text-[17px] font-medium"
        >
          Start fresh
        </button>
      </div>
    </div>
  )
}
