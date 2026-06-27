'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { DailyQuestion } from '@/lib/api'
import { useTopicConversation } from '@/lib/useTopicConversation'
import TodaysTopicCard from '@/components/today/TodaysTopicCard'
import PersonaPickerSheet from '@/components/personas/PersonaPickerSheet'
import SubPageNav from '@/components/layout/SubPageNav'

export default function DiscussPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const user = useStore((s) => s.user)

  const [question, setQuestion] = useState<DailyQuestion | null>(null)
  const [loading, setLoading] = useState(true)

  const { topicPickerOpen, setTopicPickerOpen, startWithTopic, handlePersonaSelected } =
    useTopicConversation()

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    async function load() {
      try {
        setQuestion(await api.getTodayQuestion())
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token, router])

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <div className="px-7">
        <SubPageNav fallbackHref="/app/today" />
      </div>

      <header className="px-[24px] pt-[12px] pb-[16px]">
        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-1">
          Discussion
        </p>
        <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
          What brings you here?
        </h1>
      </header>

      <div className="px-[16px]">
        {!loading && question && user && (
          <TodaysTopicCard
            user={user}
            dailyQuestion={question.question_text}
            onReflect={startWithTopic}
          />
        )}
      </div>

      <PersonaPickerSheet
        open={topicPickerOpen}
        onClose={() => setTopicPickerOpen(false)}
        onSelect={handlePersonaSelected}
      />
    </main>
  )
}
