'use client'

import Image from 'next/image'
import Link from 'next/link'
import { BronzeDivider } from '@/components/ui/BronzeDivider'
import { RITUALS } from '@/lib/rituals'

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

const RITUAL_LINES = [
  'The Mirror — once a week, your conversations read back to you in the voice of the mind you spent it with.',
  'The Council (Pro) — one question, four thinkers, then the through-line across them. Save any reading.',
  'You vs You (Pro) — the you who first raised something, beside the you reading it now, and what moved between them.',
  'The Sunday Letter (Pro) — each week the room writes you a letter on where your attention has been. Write back, and your reply shapes the next one; read them in your Readings.',
  'The Counterview — put a belief under pressure: two minds argue the case against it, never against you. Save the ones worth keeping.',
  'A Message to Your Future Self — write to yourself now, set a date, and the room delivers it by email when that day comes.',
]

export default function ExplorePage() {
  return (
    <main
      className="min-h-screen [min-height:100svh] bg-vellum"
      // Top-level tab: no back chrome. Reserve the safe area the removed SubPageNav
      // previously provided so content clears the status bar.
      style={{ paddingTop: 'max(0.5rem, env(safe-area-inset-top))' }}
    >
      <div className="px-7 pb-safe">
        <div className="w-full max-w-[380px] mx-auto pt-2 pb-12">

          <div className="flex justify-center mb-7">
            <BronzeDivider width={80} />
          </div>

          <header className="text-center space-y-2">
            <h1 className="font-cormorant text-[26px] font-semibold text-ink leading-tight">
              Explore The Wise Room
            </h1>
            <p className="font-lora text-[15px] italic text-charcoal leading-[1.65]">
              What each part does &mdash; and where your words are kept.
            </p>
          </header>

          <div className="mt-6 rounded-[16px] overflow-hidden shadow-card">
            <Image src="/personas/wise-room-hero.webp" alt="The Wise Room" width={760} height={300}
              className="w-full h-[240px] object-cover object-bottom" priority />
          </div>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <section className="space-y-3">
            <h2 className="font-cormorant text-[20px] font-semibold text-ink leading-tight">The minds</h2>
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
              Eleven thinkers, each with a distinct voice and way of seeing. Choose who you
              need; tap a face to read who they are.
            </p>
          </section>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <Link href="/app/explore/conversations" className="block transition-transform duration-150 active:scale-[0.99]">
            <section className="space-y-3">
              <h2 className="font-cormorant text-[20px] font-semibold text-ink leading-tight">The conversations</h2>
              <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
                Bring what&rsquo;s on your mind. Speak plainly; they listen, then press back
                until you see an angle you&rsquo;d missed. Every conversation is saved, so you
                can pick any one back up.
              </p>
              <div className="rounded-[12px] overflow-hidden shadow-card">
                <Image src="/self-portrait/theconversations.webp" alt="The conversations"
                  width={1200} height={675} className="w-full h-auto" />
              </div>
              <p className="font-lora text-[13px] text-bronze">See how the tools work &rarr;</p>
            </section>
          </Link>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <section className="space-y-2">
            <h2 className="font-cormorant text-[20px] font-semibold text-ink leading-tight">The reflections</h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              What you keep by hand collects here &mdash; lines that landed, verdicts worth
              returning to &mdash; to revisit, share, or carry to another mind.
            </p>
          </section>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <section className="space-y-3">
            <h2 className="font-cormorant text-[20px] font-semibold text-ink leading-tight">The rituals</h2>
            <div className="grid grid-cols-2 gap-3">
              {RITUALS.map((r) => (
                <Link key={r.slug} href={`/app/ritual/${r.slug}`} className="flex flex-col gap-1.5 transition-transform duration-150 active:scale-95">
                  <div className="rounded-[12px] overflow-hidden shadow-card">
                    <Image src={r.src} alt={r.name} width={360} height={180} className="w-full h-[88px] object-cover" />
                  </div>
                  <span className="font-lora text-[11px] text-sepia text-center leading-tight">{r.name}</span>
                </Link>
              ))}
            </div>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Beyond conversation, the room has its set practices. Tap any card to see how it works.
            </p>
            <ul className="space-y-2">
              {RITUAL_LINES.map((line) => (
                <li key={line} className="font-lora text-[14px] text-charcoal leading-[1.55]">
                  {line}
                </li>
              ))}
            </ul>
          </section>

          <div className="flex justify-center my-7"><BronzeDivider width={64} /></div>
          <section className="space-y-2">
            <h2 className="font-cormorant text-[20px] font-semibold text-ink leading-tight">The room remembers</h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Some things the room keeps on its own. It notes the beliefs and patterns that
              recur across your conversations and reflects them back as insights &mdash; then
              uses them, week to week, to write your letters and sharpen what it asks.
            </p>
          </section>

        </div>
      </div>
    </main>
  )
}
