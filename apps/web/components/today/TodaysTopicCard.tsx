'use client'

import { useState } from 'react'
import { deriveInitials } from '@/lib/initials'

interface Props {
  user: { full_name: string | null; email: string }
  dailyQuestion: string
  onReflect: (topicText: string) => void
}

export default function TodaysTopicCard({ user, dailyQuestion, onReflect }: Props) {
  const [topic, setTopic] = useState('')
  const initials = deriveInitials(user)

  function handleReflect() {
    onReflect(topic.trim() || dailyQuestion)
  }

  return (
    <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] pt-[14px] pb-[16px]">
      <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-[10px]">
        Today's topic.
      </p>
      <div className="flex items-start gap-[10px]">
        <div className="w-[40px] h-[40px] rounded-full flex-shrink-0 flex items-center justify-center bg-bronze mt-[2px]">
          <span className="font-cormorant text-[16px] font-medium text-vellum">
            {initials}
          </span>
        </div>
        <textarea
          rows={3}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder={dailyQuestion}
          className="flex-1 resize-none bg-transparent outline-none font-cormorant italic text-[13px] text-ink leading-snug placeholder:opacity-35 placeholder:italic placeholder:font-cormorant"
        />
      </div>
      <div className="mt-[12px] flex justify-end">
        <button
          type="button"
          onClick={handleReflect}
          className="h-[32px] px-[18px] bg-ink text-vellum rounded-[4px] font-cormorant text-[17px] font-medium"
        >
          Reflect
        </button>
      </div>
    </div>
  )
}
