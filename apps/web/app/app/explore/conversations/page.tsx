'use client'

import type { ReactNode } from 'react'
import { Zap, Users, Bookmark, Sparkle } from 'lucide-react'
import SubPageNav from '@/components/layout/SubPageNav'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

// Chip class strings mirrored verbatim from QuickActionsRow (the real in-chat
// controls) so this teaching page shows the EXACT same visual the user meets in
// chat. QuickActionsRow is the source of truth; keep these in sync by hand — we
// render static, non-interactive replicas here rather than touch the chat tool.
const CHIP =
  'bg-paper text-ink border border-[0.5px] border-edge px-[10px] py-[6px] font-lora text-[13px] rounded-sm inline-flex items-center gap-[5px]'
const CHIP_INSIGHT =
  'bg-paper text-ink border-[0.5px] border-bronze px-[10px] py-[6px] font-lora text-[13px] rounded-sm inline-flex items-center gap-[5px] shadow-[0_0_8px_rgba(184,153,104,0.45)]'

function Tool({ chip, title, children }: { chip: ReactNode; title: string; children: ReactNode }) {
  return (
    <section className="space-y-[10px]">
      <div>{chip}</div>
      <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">{title}</h2>
      <p className="font-lora text-[15px] text-charcoal leading-[1.65]">{children}</p>
    </section>
  )
}

export default function ConversationsGuidePage() {
  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum">
      <div className="px-7">
        <SubPageNav fallbackHref="/app/explore" />
      </div>

      <div className="px-7 pb-safe">
        <div className="w-full max-w-[380px] mx-auto pt-2 pb-12">
          <header className="space-y-2">
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
              The Conversations
            </p>
            <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
              The tools of the talk.
            </h1>
            <p className="font-lora text-[15px] italic text-charcoal leading-[1.65]">
              A handful of quiet controls sit beneath each reply. Here is what they
              do, and when to reach for them.
            </p>
          </header>

          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>

          <div className="space-y-7">
            <Tool
              chip={
                <span className={CHIP}>
                  <Zap size={11} strokeWidth={1.5} aria-hidden="true" />
                  <span>Go deeper</span>
                </span>
              }
              title="Go deeper."
            >
              Press the same thread further. The mind takes its own last reply and digs
              beneath it — another layer, not a new subject. Reach for it when an answer
              lands but you sense there is more underneath.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool
              chip={
                <span className={CHIP}>
                  <Users size={11} strokeWidth={1.5} aria-hidden="true" />
                  <span>Bring another mind</span>
                </span>
              }
              title="Bring another mind."
            >
              Invite a second thinker onto the very same point — a different temperament,
              a different angle. Use it when you want contrast, or to test what you just
              heard against another voice. Some minds are part of Pro.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool
              chip={
                <span className={CHIP}>
                  <Bookmark size={11} strokeWidth={1.5} fill="none" aria-hidden="true" />
                  <span>Save line</span>
                </span>
              }
              title="Save a line."
            >
              Keep a line that lands. Saved lines gather in your Reflections, ready to
              revisit, share, or carry to another mind. Free accounts keep a handful; Pro
              keeps them all.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool
              chip={
                <span className={CHIP_INSIGHT}>
                  <Sparkle size={11} strokeWidth={1.5} className="text-bronze" aria-hidden="true" />
                  <span>Insight</span>
                </span>
              }
              title="The insight glow."
            >
              Now and then the room notices a pattern across what you have said and marks
              it with a quiet glow. You do not summon it — it appears on its own. Follow
              the glow to see what it noticed, and reflect on it.
            </Tool>
          </div>
        </div>
      </div>
    </main>
  )
}
