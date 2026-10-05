'use client'

import { useState } from 'react'
import { api } from '@/lib/api'

// MEM2-C-3a. A quiet "That's not right" under a reply that used a callback (the
// messages endpoint sets callback_id only then). One tap rejects it — Ruling 5:
// the memory and its chain are retired — and the control becomes one line. No
// modal, no explanation. Copy approved by the founder, 2026-10-05.

// Greek + Greek Extended, as CrisisBubble: the reply is already in the
// conversation's language, so it decides which strings to show.
const GREEK = /[Ͱ-Ͽἀ-῿]/

const COPY = {
  en: { control: "That's not right", done: "Noted. It won't come up again." },
  el: { control: 'Δεν ισχύει αυτό', done: 'Εντάξει. Δεν θα ξαναναφερθεί.' },
} as const

interface Props {
  callbackId: string
  replyText: string
}

export default function CallbackRejectLine({ callbackId, replyText }: Props) {
  const [state, setState] = useState<'idle' | 'sending' | 'done'>('idle')
  const lang = GREEK.test(replyText) ? 'el' : 'en'
  const copy = COPY[lang]

  if (state === 'done') {
    return (
      <p lang={lang} role="status" className="mt-1 font-lora text-[12px] text-sepia">
        {copy.done}
      </p>
    )
  }

  async function reject() {
    setState('sending')
    try {
      await api.rejectCallback(callbackId)
      setState('done')
    } catch {
      // Nothing changed server-side that the person can see; let them try again.
      setState('idle')
    }
  }

  return (
    <button
      type="button"
      lang={lang}
      onClick={reject}
      disabled={state === 'sending'}
      className="mt-1 font-lora text-[12px] text-sepia underline-offset-2 hover:underline disabled:opacity-60"
    >
      {copy.control}
    </button>
  )
}
