'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import SubPageNav from '@/components/layout/SubPageNav'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import type { ScheduledEmailListItem } from '@/lib/api'

function formatDeliverDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function ScheduledLettersPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const [items, setItems] = useState<ScheduledEmailListItem[] | null>(null)
  const [cancelling, setCancelling] = useState<string | null>(null)

  useEffect(() => {
    if (token === null) {
      router.replace('/auth')
      return
    }
    api.listScheduledEmails()
      .then(setItems)
      .catch(() => setItems([]))
  }, [token, router])

  async function handleCancel(id: string) {
    if (cancelling) return
    setCancelling(id)
    try {
      await api.cancelScheduledEmail(id)
      setItems((prev) => prev?.filter((item) => item.id !== id) ?? null)
      toast.success('Message cancelled.')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not cancel. Try again.')
    } finally {
      setCancelling(null)
    }
  }

  const pending = items?.filter((i) => i.status === 'pending') ?? []
  const past = items?.filter((i) => i.status !== 'pending') ?? []

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      {/* ── Header ── */}
      <div className="px-[24px] pt-[22px] pb-[16px] flex items-center gap-[12px]">
        <SubPageNav fallbackHref="/app/letters" />
        <div>
          <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
            Account
          </p>
          <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
            Messages to future self.
          </h1>
        </div>
      </div>

      <div className="px-[16px] flex flex-col gap-[12px]">
        {items === null ? (
          <p className="font-lora text-[13px] text-sepia italic text-center py-12">Loading…</p>
        ) : items.length === 0 ? (
          <div className="bg-paper border border-[0.5px] border-edge rounded-md px-[16px] py-[24px] text-center">
            <p className="font-cormorant text-[19px] font-normal text-ink">No messages scheduled.</p>
            <p className="font-lora text-[15px] text-charcoal mt-[6px] leading-[1.6]">
              Schedule a reflection from the Rituals card on Today.
            </p>
          </div>
        ) : (
          <>
            {pending.length > 0 && (
              <div className="bg-paper border border-[0.5px] border-edge rounded-md overflow-hidden">
                <div className="px-[16px] pt-[14px] pb-[2px]">
                  <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
                    Pending
                  </p>
                </div>
                {pending.map((item) => (
                  <div
                    key={item.id}
                    className="border-t border-[0.5px] border-edge px-[16px] py-[14px] flex items-start justify-between gap-[12px]"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-cormorant text-[17px] font-medium text-ink leading-tight">
                        {item.persona_name}
                      </p>
                      <p className="font-lora text-[12px] text-charcoal mt-[2px]">
                        Delivers {formatDeliverDate(item.scheduled_for)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleCancel(item.id)}
                      disabled={cancelling === item.id}
                      className="font-lora text-[12px] text-sepia underline underline-offset-2 flex-shrink-0 disabled:opacity-50"
                    >
                      {cancelling === item.id ? 'Cancelling…' : 'Cancel'}
                    </button>
                  </div>
                ))}
              </div>
            )}

            {past.length > 0 && (
              <div className="bg-paper border border-[0.5px] border-edge rounded-md overflow-hidden">
                <div className="px-[16px] pt-[14px] pb-[2px]">
                  <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
                    Sent
                  </p>
                </div>
                {past.map((item) => {
                  const meta = (
                    <>
                      <p className="font-cormorant text-[17px] font-medium text-ink leading-tight">
                        {item.persona_name}
                      </p>
                      <p className="font-lora text-[12px] text-charcoal mt-[2px]">
                        {item.status === 'sent'
                          ? `Sent ${formatDeliverDate(item.sent_at ?? item.scheduled_for)}`
                          : item.status === 'cancelled'
                            ? 'Cancelled'
                            : `Failed · ${formatDeliverDate(item.scheduled_for)}`}
                      </p>
                    </>
                  )
                  // Only delivered letters open a detail (the endpoint 404s otherwise).
                  return item.status === 'sent' ? (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => router.push(`/app/scheduled-letters/${item.id}`)}
                      className="w-full text-left border-t border-[0.5px] border-edge px-[16px] py-[14px]"
                    >
                      {meta}
                    </button>
                  ) : (
                    <div
                      key={item.id}
                      className="border-t border-[0.5px] border-edge px-[16px] py-[14px]"
                    >
                      {meta}
                    </div>
                  )
                })}
              </div>
            )}
          </>
        )}
      </div>
    </main>
  )
}
