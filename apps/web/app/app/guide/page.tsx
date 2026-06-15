'use client'

import Image from 'next/image'
import SubPageNav from '@/components/layout/SubPageNav'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

const MINDS = [
  { src: '/personas/socrates.jpg', name: 'Socrates' },
  { src: '/personas/marcus_aurelius.jpg', name: 'Marcus Aurelius' },
  { src: '/personas/epictetus.webp', name: 'Epictetus' },
  { src: '/personas/sigmund_freud.webp', name: 'Sigmund Freud' },
  { src: '/personas/carl_jung.png', name: 'Carl Jung' },
  { src: '/personas/simone_de_beauvoir.webp', name: 'Simone de Beauvoir' },
  { src: '/personas/lao_tzu.png', name: 'Lao Tzu' },
  { src: '/personas/machiavelli.png', name: 'Machiavelli' },
  { src: '/personas/oscar_wilde.png', name: 'Oscar Wilde' },
]

const RITUALS = [
  { src: '/personas/mirror.png', name: 'The Mirror' },
  { src: '/personas/boardroom.webp', name: 'The Council' },
  { src: '/personas/youvsyou.webp', name: 'You vs You' },
  { src: '/personas/messagetomyfutureself.png', name: 'A Letter' },
]

export default function GuidePage() {
  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum">
      <div className="px-7">
        <SubPageNav fallbackHref="/app/today" showHome={false} />
      </div>

      <div className="px-7 pb-safe">
        <div className="w-full max-w-[380px] mx-auto pt-2 pb-12">

          <div className="flex justify-center mb-7">
            <BronzeDivider width={80} />
          </div>

          <header className="text-center space-y-2">
            <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
              Explore The Wise Room
            </h1>
            <p className="font-lora text-[15px] italic text-charcoal leading-[1.65]">
              A room where the great minds listen — and remember.
            </p>
          </header>

          <div className="mt-6 rounded-[16px] overflow-hidden shadow-card">
            <Image src="/personas/wise-room-hero.webp" alt="The Wise Room" width={760} height={300}
              className="w-full h-[150px] object-cover" priority />
          </div>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <section className="space-y-3">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">The minds.</h2>
            <div className="grid grid-cols-3 gap-3">
              {MINDS.map((m) => (
                <div key={m.name} className="flex flex-col items-center gap-1.5">
                  <div className="w-[88px] h-[88px] rounded-full overflow-hidden bg-linen shadow-card">
                    <Image src={m.src} alt={m.name} width={88} height={88} className="object-cover w-full h-full" />
                  </div>
                  <span className="font-lora text-[10px] text-sepia text-center leading-tight">{m.name}</span>
                </div>
              ))}
            </div>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Nine thinkers, each with their own voice, temperament, and way of
              seeing. Socrates will question you. Marcus will steady you. Choose
              who you need — or let the room choose for you.
            </p>
          </section>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <section className="space-y-2">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">The conversations.</h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Bring what&rsquo;s on your mind. Speak plainly; they will not. When a
              line strikes you, save it — it becomes part of your reflections.
            </p>
          </section>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <section className="space-y-2">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">The reflections.</h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Everything worth keeping lives here: lines that moved you, verdicts
              worth returning to. Revisit them, share them, or carry one to
              another mind.
            </p>
          </section>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <section className="space-y-3">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">The rituals.</h2>
            <div className="grid grid-cols-2 gap-3">
              {RITUALS.map((r) => (
                <div key={r.name} className="flex flex-col gap-1.5">
                  <div className="rounded-[12px] overflow-hidden shadow-card">
                    <Image src={r.src} alt={r.name} width={360} height={180} className="w-full h-[88px] object-cover" />
                  </div>
                  <span className="font-lora text-[11px] text-sepia text-center leading-tight">{r.name}</span>
                </div>
              ))}
            </div>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Beyond conversation, the room has its practices. <span className="italic">The Mirror</span> reads
              your week back to you. <span className="italic">The Council</span> convenes four minds on one
              matter. <span className="italic">A Letter</span> travels to your future self.
            </p>
          </section>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <section className="space-y-2">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">The room remembers.</h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              What you say stays with it. Week after week, it learns the shape of
              your thinking — and reflects back what you couldn&rsquo;t see alone.
            </p>
          </section>

        </div>
      </div>
    </main>
  )
}
