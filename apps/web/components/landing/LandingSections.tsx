import Image from 'next/image'
import Link from 'next/link'
import { BronzeDivider } from '@/components/ui/BronzeDivider'
import { LANDING_COPY as C } from '@/lib/landing-copy'

// The eleven minds, reusing the canonical list and portrait treatment from the
// in-app Explore screen (app/app/(tabs)/explore/page.tsx) rather than a second
// hand-typed roster that could drift from it.
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

// Both CTAs go where fold 1's "Begin your Reflection" goes. Destinations are not
// this PR's to change; they are read from one constant so they cannot drift apart.
const SIGNUP_HREF = '/auth?mode=signup'

// Shared focus ring. No hover-dependent affordance anywhere on this page: hover
// does not exist on the phone this page is designed for, so nothing may depend on
// it. :focus-visible is keyboard-only and costs nothing on touch.
const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bronze-dark focus-visible:ring-offset-2 focus-visible:ring-offset-vellum'

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-lora text-[12px] tracking-[0.18em] uppercase text-bronze-dark">
      {children}
    </p>
  )
}

export function LandingSections() {
  return (
    // Hard cut to Vellum — a deliberate edge against the photograph above, not a
    // gradient fade. Gradients are forbidden outside portrait artwork (v5 §1.7).
    <div className="bg-vellum">
      {/* ── What happens inside ─────────────────────────────────────────── */}
      <section className="px-6 pt-[56px] pb-[48px]">
        <div className="max-w-[1040px] mx-auto">
          <div className="text-center space-y-3">
            <Eyebrow>{C.offer.eyebrow}</Eyebrow>
            <h2 className="font-cormorant text-[30px] sm:text-[38px] font-medium text-ink leading-tight">
              {C.offer.title}
            </h2>
            <p className="font-lora text-[15px] sm:text-[16px] text-charcoal leading-[1.65] max-w-[620px] mx-auto">
              {C.offer.intro}
            </p>
            <p className="font-cormorant italic text-[17px] sm:text-[19px] text-sepia leading-snug max-w-[620px] mx-auto">
              {C.offer.distinction}
            </p>
          </div>

          <div className="mt-[36px] grid grid-cols-1 md:grid-cols-3 gap-[16px]">
            {C.offer.cards.map((card) => (
              <div
                key={card.title}
                className="bg-paper rounded-lg shadow-card border-0.5 border-edge p-[22px] space-y-2.5"
              >
                <h3 className="font-cormorant text-[21px] font-semibold text-ink leading-tight">
                  {card.title}
                </h3>
                <p className="font-lora text-[15px] text-charcoal leading-[1.65]">{card.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Mid-page CTA ────────────────────────────────────────────────── */}
      <section className="px-6 pb-[52px]">
        <div className="max-w-[420px] mx-auto flex flex-col items-center gap-[12px]">
          <Link
            href={SIGNUP_HREF}
            className={`w-full py-[16px] rounded-full bg-ink text-vellum font-cormorant text-[18px] font-medium text-center ${FOCUS_RING}`}
          >
            {C.midCta.button}
          </Link>
          <p className="font-lora text-[15px] text-sepia text-center">{C.midCta.note}</p>
        </div>
      </section>

      {/* ── From a Sunday letter ────────────────────────────────────────── */}
      <section className="px-6 pb-[52px]">
        <div className="max-w-[720px] mx-auto">
          <div className="text-center mb-[20px]">
            <Eyebrow>{C.letter.eyebrow}</Eyebrow>
          </div>
          <div className="bg-paper rounded-lg shadow-card border-0.5 border-edge px-[26px] py-[32px] text-center">
            <blockquote className="font-cormorant italic text-[22px] sm:text-[27px] text-ink leading-[1.45]">
              {C.letter.quote}
            </blockquote>
            <div className="flex justify-center my-[20px]">
              <BronzeDivider width={64} />
            </div>
            <p className="font-cormorant text-[17px] text-charcoal leading-snug">
              {C.letter.signatureLine1}
              <br />
              {C.letter.signatureLine2}
            </p>
          </div>
          <p className="mt-[16px] font-lora text-[15px] text-sepia text-center leading-[1.65]">
            {C.letter.contextNote}
          </p>
        </div>
      </section>

      {/* ── The minds ───────────────────────────────────────────────────── */}
      <section className="px-6 pb-[52px]">
        <div className="max-w-[720px] mx-auto text-center">
          <Eyebrow>{C.minds.eyebrow}</Eyebrow>
          <ul className="mt-[24px] grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-x-[14px] gap-y-[20px] list-none">
            {MINDS.map((m) => (
              <li key={m.slug} className="flex flex-col items-center gap-1.5">
                <div className="w-full aspect-square rounded-full overflow-hidden bg-linen shadow-card">
                  <Image
                    src={m.src}
                    alt=""
                    width={88}
                    height={88}
                    loading="lazy"
                    sizes="(min-width: 768px) 88px, 25vw"
                    className="object-cover w-full h-full"
                  />
                </div>
                <span className="font-cormorant text-[15px] text-charcoal text-center leading-tight">
                  {m.name}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-[26px] font-cormorant italic text-[17px] sm:text-[19px] text-sepia">
            {C.minds.caption}
          </p>
        </div>
      </section>

      {/* ── Pricing ─────────────────────────────────────────────────────── */}
      <section className="px-6 pb-[52px]">
        <div className="max-w-[460px] mx-auto text-center">
          <Eyebrow>{C.pricing.eyebrow}</Eyebrow>
          <div className="mt-[20px] bg-paper rounded-lg shadow-card border-0.5 border-edge px-[26px] py-[30px]">
            <p className="font-cormorant text-[34px] sm:text-[40px] font-medium text-ink leading-none">
              {C.pricing.price}
            </p>
            <p className="mt-[8px] font-lora text-[15px] text-sepia">{C.pricing.annual}</p>

            <div className="flex justify-center my-[22px]">
              <BronzeDivider width={64} />
            </div>

            <ul className="space-y-[10px] text-left list-none">
              {C.pricing.inclusions.map((row) => (
                <li key={row} className="flex items-start gap-[10px]">
                  <span aria-hidden="true" className="mt-[9px] w-[5px] h-[5px] rounded-full bg-bronze shrink-0" />
                  <span className="font-lora text-[15px] text-charcoal leading-[1.6]">{row}</span>
                </li>
              ))}
            </ul>

            <p className="mt-[20px] font-lora text-[15px] text-charcoal">{C.pricing.includedLine}</p>

            <Link
              href={SIGNUP_HREF}
              className={`mt-[22px] block w-full py-[16px] rounded-full bg-ink text-vellum font-cormorant text-[18px] font-medium text-center ${FOCUS_RING}`}
            >
              {C.pricing.button}
            </Link>

            <p className="mt-[12px] font-lora text-[15px] text-sepia">{C.pricing.checkoutNote}</p>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="px-6 pb-[40px]">
        <div className="max-w-[720px] mx-auto text-center space-y-[14px]">
          <div className="flex justify-center">
            <BronzeDivider width={48} />
          </div>
          {/* Disclaimer is load-bearing, not fine print: 13px, charcoal on vellum. */}
          <p className="font-lora text-[13px] text-charcoal leading-[1.6]">
            {C.footer.disclaimer}
          </p>
          <p className="font-lora text-[12px] tracking-[0.18em] uppercase text-sepia">
            {C.footer.label}
          </p>
        </div>
      </footer>
    </div>
  )
}
