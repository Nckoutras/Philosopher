'use client'

import type { ReactNode } from 'react'
import { Sparkle } from 'lucide-react'
import SubPageNav from '@/components/layout/SubPageNav'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

// Static, non-interactive replica of the REAL insight chip, mirrored verbatim
// from QuickActionsRow via the conversations guide (the source of truth). Kept in
// sync by hand — we render a static replica here rather than touch the chat tool.
const CHIP_INSIGHT =
  'bg-paper text-ink border-[0.5px] border-bronze px-[10px] py-[6px] font-lora text-[13px] rounded-sm inline-flex items-center gap-[5px] shadow-[0_0_8px_rgba(184,153,104,0.45)]'

function Tool({ chip, title, children }: { chip?: ReactNode; title: string; children: ReactNode }) {
  return (
    <section className="space-y-[10px]">
      {chip && <div>{chip}</div>}
      <h3 className="font-cormorant text-[20px] font-medium text-ink leading-tight">{title}</h3>
      <p className="font-lora text-[15px] text-charcoal leading-[1.65]">{children}</p>
    </section>
  )
}

export default function MemoryGuidePage() {
  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum">
      <div className="px-7">
        <SubPageNav fallbackHref="/app/explore" />
      </div>

      <div className="px-7 pb-safe">
        <div className="w-full max-w-[380px] mx-auto pt-2 pb-12">
          <header className="space-y-2">
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
              The room remembers
            </p>
            <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
              Nothing you say here is said into the air.
            </h1>
            <p className="font-lora text-[15px] italic text-charcoal leading-[1.65]">
              The room holds what you bring &mdash; and hands it back exactly when it&rsquo;s
              useful. Here is what it keeps, where it returns, and when it opens a door.
            </p>
          </header>

          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>

          {/* ── Section 1 — What it holds ── */}
          <section className="space-y-2">
            <h2 className="font-cormorant text-[22px] font-medium text-ink leading-tight">
              What it holds
            </h2>
          </section>

          <div className="mt-7 space-y-7">
            <Tool title="Who you are.">
              Your first answers &mdash; what you hold dear, how you meet disagreement &mdash;
              reach every mind before your first word. No introductions twice.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool title="What you&rsquo;ve said.">
              As you talk, the room keeps the ground you&rsquo;ve covered: the situations, the
              people, the questions you carry in. A mind can reach back to it when it matters
              &mdash; not recite it, use it.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool title="What repeats.">
              Some things you say once. Some you keep saying, in different words. The room
              notices the difference &mdash; including the beliefs you&rsquo;ve put under
              pressure that keep coming back.
            </Tool>
          </div>

          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>

          {/* ── Section 2 — Where it returns ── */}
          <section className="space-y-2">
            <h2 className="font-cormorant text-[22px] font-medium text-ink leading-tight">
              Where it returns
            </h2>
          </section>

          <div className="mt-7 space-y-7">
            <Tool title="From the first word.">
              Every conversation opens with a mind that already knows the basics. You start
              from where you are, not from zero.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool
              chip={
                <span className={CHIP_INSIGHT}>
                  <Sparkle size={11} strokeWidth={1.5} className="text-bronze" aria-hidden="true" />
                  <span>Insight</span>
                </span>
              }
              title="In the glow."
            >
              When a pattern crosses from one conversation into another, the room marks it with
              a quiet glow. Follow it, and the room shows you what it noticed &mdash; then offers
              a way to reflect on it.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool title="In the Sunday Letter.">
              Each week the room writes you a letter from everything you brought it. Write back,
              and your reply shapes the next one. Part of Pro.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool title="In You vs You.">
              The you who first raised something, placed beside the you reading it now &mdash;
              drawn from what the room kept along the way. Part of Pro.
            </Tool>
          </div>

          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>

          {/* ── Section 3 — When it opens a door ── */}
          <section className="space-y-2">
            <h2 className="font-cormorant text-[22px] font-medium text-ink leading-tight">
              When it opens a door
            </h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              The room doesn&rsquo;t advertise. It watches for the moment something you said
              calls for a particular door &mdash; then opens it, once, and lets you decide.
            </p>
          </section>

          <div className="mt-7 space-y-7">
            <Tool title="In the letter.">
              Each Sunday Letter names one mind you haven&rsquo;t spoken with &mdash; chosen from
              your week, with the reason why. One tap, and you&rsquo;re in the room with them.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool title="After the Portrait.">
              Answer a few more questions and the room returns the favor: the mind that has
              worked hardest on what weighs on you most, and a first sentence ready in the field.
              You cross the threshold yourself.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool title="At the door of a conversation.">
              When what you&rsquo;re weighing sounds like a decision with two sides, the room
              points to the Council. When a belief keeps trembling, it points to the Counterview.
              Quietly, after the reply &mdash; never interrupting.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool title="On the Home screen.">
              Some days &mdash; not most &mdash; a card waits: something the room noticed across
              your conversations, and the one door worth opening for it. Its rarity is the point.
            </Tool>
          </div>

          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>

          <p className="font-lora text-[14px] text-charcoal text-center leading-[1.65]">
            The more you bring it, the sharper it listens.
          </p>
        </div>
      </div>
    </main>
  )
}
