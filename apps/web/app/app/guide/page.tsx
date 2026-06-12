'use client'

import SubPageNav from '@/components/layout/SubPageNav'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

export default function GuidePage() {
  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum">
      <div className="px-7">
        <SubPageNav fallbackHref="/app/today" showHome={false} />
      </div>

      <div className="px-7 pb-safe">
        <div className="w-full max-w-[380px] mx-auto pt-2 pb-12">

          {/* Crown ornament */}
          <div className="flex justify-center mb-7">
            <BronzeDivider width={80} />
          </div>

          {/* Title + subtitle */}
          <header className="text-center space-y-2">
            <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
              Living in the Wise Room
            </h1>
            <p className="font-lora text-[15px] italic text-charcoal leading-[1.65]">
              A room where the great minds listen — and remember.
            </p>
          </header>

          {/* The minds. */}
          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>
          <section className="space-y-2">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">
              The minds.
            </h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Nine thinkers, each with their own voice, temperament, and way of
              seeing. Socrates will question you. Marcus will steady you. Choose
              who you need — or let the room choose for you.
            </p>
          </section>

          {/* The conversations. */}
          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>
          <section className="space-y-2">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">
              The conversations.
            </h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Bring what's on your mind. Speak plainly; they will not. When a
              line strikes you, save it — it becomes part of your reflections.
            </p>
          </section>

          {/* The reflections. */}
          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>
          <section className="space-y-2">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">
              The reflections.
            </h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Everything worth keeping lives here: lines that moved you, verdicts
              worth returning to. Revisit them, share them, or carry one to
              another mind.
            </p>
          </section>

          {/* The rituals. */}
          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>
          <section className="space-y-2">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">
              The rituals.
            </h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Beyond conversation, the room has its practices. <span className="italic">The Mirror</span> reads
              your week back to you. <span className="italic">The Council</span> convenes four minds on one
              matter. <span className="italic">A Letter</span> travels to your future self.
            </p>
          </section>

          {/* The room remembers. */}
          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>
          <section className="space-y-2">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">
              The room remembers.
            </h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              What you say stays with it. Week after week, it learns the shape of
              your thinking — and reflects back what you couldn't see alone.
            </p>
          </section>

        </div>
      </div>
    </main>
  )
}
