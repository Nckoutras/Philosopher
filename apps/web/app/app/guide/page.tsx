'use client'

import Image from 'next/image'
import Link from 'next/link'
import SubPageNav from '@/components/layout/SubPageNav'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

const MINDS = [
  { slug: 'socrates', src: '/personas/socrates.webp', name: 'Socrates' },
  { slug: 'marcus_aurelius', src: '/personas/marcus_aurelius.webp', name: 'Marcus Aurelius' },
  { slug: 'epictetus', src: '/personas/epictetus.webp', name: 'Epictetus' },
  { slug: 'sigmund_freud', src: '/personas/sigmund_freud.webp', name: 'Sigmund Freud' },
  { slug: 'carl_jung', src: '/personas/carl_jung.webp', name: 'Carl Jung' },
  { slug: 'simone_de_beauvoir', src: '/personas/simone_de_beauvoir.webp', name: 'Simone de Beauvoir' },
  { slug: 'lao_tzu', src: '/personas/lao_tzu.webp', name: 'Lao Tzu' },
  { slug: 'niccolo_machiavelli', src: '/personas/machiavelli.webp', name: 'Machiavelli' },
  { slug: 'oscar_wilde', src: '/personas/oscar_wilde.webp', name: 'Oscar Wilde' },
  { slug: 'george_orwell', src: '/personas/george_orwell.webp', name: 'George Orwell' },
  { slug: 'miyamoto_musashi', src: '/personas/miyamoto_musashi.webp', name: 'Miyamoto Musashi' },
]

const RITUALS = [
  { src: '/personas/mirror.png', name: 'The Mirror' },
  { src: '/personas/boardroom.webp', name: 'The Council' },
  { src: '/personas/youvsyou.webp', name: 'You vs You' },
  { src: '/personas/messagetomyfutureself.png', name: 'Message to Your Future Self' },
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
              Reflect with great thinkers — and meet who you were, and who you&rsquo;re becoming.
            </p>
          </header>

          <div className="mt-6 rounded-[16px] overflow-hidden shadow-card">
            <Image src="/personas/wise-room-hero.webp" alt="The Wise Room" width={760} height={300}
              className="w-full h-[240px] object-cover object-bottom" priority />
          </div>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <section className="space-y-3">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">The minds.</h2>
            <div className="grid grid-cols-3 gap-4">
              {MINDS.map((m) => (
                <Link key={m.name} href={`/app/persona/${m.slug}`} className="flex flex-col items-center gap-1.5 transition-transform duration-150 active:scale-95">
                  <div className="w-full aspect-square rounded-full overflow-hidden bg-linen shadow-card">
                    <Image src={m.src} alt={m.name} width={88} height={88} className="object-cover w-full h-full" />
                  </div>
                  <span className="font-lora text-[10px] text-sepia text-center leading-tight">{m.name}</span>
                </Link>
              ))}
            </div>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Eleven thinkers, each with their own voice, temperament, and way of
              seeing. Socrates will question you. Marcus will steady you. Choose
              who you need — or let the room choose for you.
            </p>
          </section>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <section className="space-y-2">
            <h2 className="font-cormorant text-[20px] font-medium text-ink leading-tight">The conversations.</h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Bring what&rsquo;s on your mind. Speak plainly; they will not — they
              listen closely, then press back, until you see an angle you&rsquo;d
              missed: in the matter, and in yourself.
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
              matter. <span className="italic">A Message to Your Future Self</span> carries your words forward in time.
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
