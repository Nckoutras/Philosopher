'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChevronLeft } from 'lucide-react'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { SelfComparisonStatus } from '@/lib/api'
import WiseMark from '@/components/ui/WiseMark'

export default function YouVsYouPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const [status, setStatus] = useState<SelfComparisonStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    async function load() {
      try {
        setStatus(await api.getSelfComparisonStatus())
      } catch {
        setStatus(null)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token, router])

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum px-[24px] pt-[24px] pb-[60px] flex flex-col gap-[20px]">
      <button
        type="button"
        onClick={() => router.push('/app/rituals')}
        aria-label="Back to rituals"
        className="flex items-center gap-[4px] text-sepia self-start"
      >
        <ChevronLeft size={18} strokeWidth={1.5} />
        <span className="font-lora text-[13px]">Rituals</span>
      </button>

      <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark text-center">
        YOU VS. YOU
      </p>

      {loading && (
        <p className="font-lora text-[14px] text-sepia text-center mt-[40px]">Gathering&hellip;</p>
      )}

      {!loading && status && !status.unlocked && (
        <div className="bg-paper border-[0.5px] border-edge rounded-[18px] shadow-card px-[20px] py-[32px] text-center flex flex-col gap-[16px]">
          <p className="font-cormorant text-[24px] font-medium text-ink leading-snug">
            Your other self is still forming.
          </p>
          <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
            Keep talking with the minds. As your words gather, a second you takes shape &mdash;
            who you were, beside who you&rsquo;re becoming. When there&rsquo;s enough, you&rsquo;ll meet them here.
          </p>
          {status.forming_preview.length > 0 && (
            <div className="mt-[8px] pt-[16px] border-t border-edge flex flex-col gap-[12px]">
              <div className="flex items-center justify-center gap-[8px]">
                <WiseMark size={22} />
                <p className="font-lora text-[11px] uppercase tracking-[0.2em] text-bronze-dark">
                  What&rsquo;s beginning to take shape
                </p>
              </div>
              <div className="flex flex-col gap-[8px]">
                {status.forming_preview.map((line, i) => (
                  <p key={i} className="font-cormorant italic text-[16px] text-charcoal leading-snug">
                    {line}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!loading && status && status.unlocked && (
        <div className="bg-paper border-[0.5px] border-edge rounded-[18px] shadow-card px-[20px] py-[32px] text-center flex flex-col gap-[16px]">
          <p className="font-cormorant text-[24px] font-medium text-ink leading-snug">
            Your other self is ready.
          </p>
          <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
            Soon you&rsquo;ll ask a question and hear it answered by who you were and who you are now.
            This is arriving shortly.
          </p>
        </div>
      )}

      {!loading && !status && (
        <p className="font-lora text-[15px] text-charcoal text-center mt-[40px]">
          Couldn&rsquo;t load this right now. Try again in a moment.
        </p>
      )}
    </main>
  )
}
