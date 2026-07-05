'use client'

import type { ReactNode } from 'react'
import Link from 'next/link'
import { Bookmark, Users, MessageCircle } from 'lucide-react'
import { MirrorIcon } from '@/components/icons/RitualIcons'
import SubPageNav from '@/components/layout/SubPageNav'
import { BronzeDivider } from '@/components/ui/BronzeDivider'

// Static, non-interactive replicas of the REAL Reflections controls, mirrored by
// hand so this teaching page shows exactly what the user meets in the feed:
//  - EYEBROW = each feed card's header (icon + uppercase bronze-dark label), from
//    components/reflections/*VerdictCard + SavedLineCard.
//  - FILTER_* / SHARE_PILL = FilterPills + the per-card Share button.
//  - VIZ_* = the self-portrait Shape/Map VizToggle.
// The real cards/controls are the source of truth; keep these in sync by hand.
const EYEBROW_LABEL =
  'font-lora text-[11px] uppercase tracking-[0.18em] text-bronze-dark font-bold'
const FILTER_ACTIVE =
  'bg-linen-deep text-ink border border-ink px-[14px] py-[6px] font-lora text-[12px] font-medium rounded-[4px]'
const FILTER_BASE =
  'bg-paper text-ink border border-[0.5px] border-edge px-[14px] py-[6px] font-lora text-[12px] rounded-[4px]'
const SHARE_PILL =
  'px-[12px] py-[8px] inline-flex items-center border border-[0.5px] border-charcoal rounded-[4px] font-cormorant text-[13px] font-medium text-charcoal'
const VIZ_WRAP = 'inline-flex rounded-full border-[0.5px] border-bronze/40 bg-white p-[3px]'
const VIZ_ON = 'px-6 py-1.5 rounded-full font-lora text-[13px] bg-bronze text-vellum'
const VIZ_OFF = 'px-6 py-1.5 rounded-full font-lora text-[13px] text-sepia'

function Tool({ chip, title, children }: { chip: ReactNode; title: string; children: ReactNode }) {
  return (
    <section className="space-y-[10px]">
      <div>{chip}</div>
      <h3 className="font-cormorant text-[20px] font-medium text-ink leading-tight">{title}</h3>
      <p className="font-lora text-[15px] text-charcoal leading-[1.65]">{children}</p>
    </section>
  )
}

// The real feed-card eyebrow: an icon + uppercase bronze-dark label.
function Eyebrow({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span className="flex items-center gap-[6px]">
      {icon}
      <span className={EYEBROW_LABEL}>{label}</span>
    </span>
  )
}

export default function ReflectionsGuidePage() {
  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum">
      <div className="px-7">
        <SubPageNav fallbackHref="/app/explore" />
      </div>

      <div className="px-7 pb-safe">
        <div className="w-full max-w-[380px] mx-auto pt-2 pb-12">
          <header className="space-y-2">
            <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
              Reflections
            </p>
            <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
              What you keep &mdash; and what the room shows you.
            </h1>
            <p className="font-lora text-[15px] italic text-charcoal leading-[1.65]">
              Some things you keep by hand; some the room draws on its own. Here is what
              gathers, and how to find your way back to it.
            </p>
          </header>

          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>

          {/* ── Category A — What you keep → the Reflections feed ── */}
          <section className="space-y-2">
            <h2 className="font-cormorant text-[22px] font-medium text-ink leading-tight">
              What you keep
            </h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              These collect in Reflections, saved by your own hand &mdash; newest first, ready
              to revisit or share.
            </p>
          </section>

          <div className="mt-7 space-y-7">
            <Tool
              chip={
                <Eyebrow
                  icon={<Bookmark size={13} strokeWidth={1.5} className="text-bronze-dark" aria-hidden="true" />}
                  label="FROM YOUR CONVERSATIONS"
                />
              }
              title="A line worth keeping."
            >
              When a reply lands, keep it. The line gathers in Reflections under the mind who
              said it &mdash; return to the conversation it came from, carry it to another mind,
              or share it as an image card. Free accounts keep a handful; Pro keeps them all.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool
              chip={
                <Eyebrow
                  icon={<Users size={13} strokeWidth={1.5} className="text-bronze-dark" aria-hidden="true" />}
                  label="COUNCIL VERDICT"
                />
              }
              title="The through-line from four minds."
            >
              Take a matter to the Council and they answer in turn, then the room draws the line
              that runs through them. Keep that synthesis and it waits in Reflections, the four
              minds beside it &mdash; to return to or share as a card. The Council is part of Pro.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool
              chip={
                <Eyebrow
                  icon={<MessageCircle size={13} strokeWidth={1.5} className="text-bronze-dark" aria-hidden="true" />}
                  label="COUNTERVIEW"
                />
              }
              title="The case against a belief."
            >
              Put a belief under pressure and two minds argue the case against it &mdash; never
              against you. Keep the verdicts worth holding and they gather here beside the belief
              that drew them, ready to revisit or share.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool
              chip={
                <Eyebrow
                  icon={<MirrorIcon size={13} strokeWidth={1.5} className="text-bronze-dark" />}
                  label="FROM THE MIRROR"
                />
              }
              title="The room, read back to you."
            >
              Each week the Mirror reads your conversations back in the voice of the mind you
              spent them with &mdash; what you said, what it may have meant, the thread beneath.
              Keep a reading and it stays in Reflections to return to, or share as a card.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool
              chip={
                <div className="space-y-2">
                  {/* FilterPills replica — All active; By mind selectable; By theme dimmed (coming soon) */}
                  <div className="flex gap-[6px]">
                    <span className={FILTER_ACTIVE}>All</span>
                    <span className={FILTER_BASE}>By mind</span>
                    <span className={`${FILTER_BASE} opacity-[0.75]`}>By theme</span>
                  </div>
                  {/* Share pill replica (real per-card control) */}
                  <span className={SHARE_PILL}>Share</span>
                </div>
              }
              title="Finding your way back."
            >
              Everything you keep gathers newest-first. Filter <em>By mind</em> to see one
              thinker&rsquo;s lines, or search across all of it. Every kept card carries a{' '}
              <em>Share</em> that renders an image you can post or save: a few are free, unlimited
              on Pro.
            </Tool>
          </div>

          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>

          {/* ── Category B — What the room reflects back → share / download (NOT the feed) ── */}
          <section className="space-y-2">
            <h2 className="font-cormorant text-[22px] font-medium text-ink leading-tight">
              What the room reflects back
            </h2>
            <p className="font-lora text-[15px] text-charcoal leading-[1.65]">
              Your Self-Portrait, drawn from your own answers. These aren&rsquo;t kept in
              Reflections &mdash; you share or download them as an image.
            </p>
          </section>

          <div className="mt-7 space-y-7">
            <Tool
              chip={
                <span className={VIZ_WRAP}>
                  <span className={VIZ_OFF}>Shape</span>
                  <span className={VIZ_ON}>Map</span>
                </span>
              }
              title="The map of your themes."
            >
              The map lays your answers out as territory &mdash; each theme a region, the ones you
              return to most drawn largest, a marker set on the axis you lean into hardest. Share
              or download it as an image card; it doesn&rsquo;t join Reflections.
            </Tool>

            <div className="flex justify-center"><BronzeDivider width={64} /></div>

            <Tool
              chip={
                <span className={VIZ_WRAP}>
                  <span className={VIZ_ON}>Shape</span>
                  <span className={VIZ_OFF}>Map</span>
                </span>
              }
              title="The shape of your answers."
            >
              The same theme scores drawn as a radar &mdash; one continuous shape showing, at a
              glance, where you&rsquo;re weighted and where you&rsquo;re spare. Share or download
              it as an image; like the map, it stays yours to send, not something the feed keeps.
            </Tool>
          </div>

          <div className="flex justify-center my-7">
            <BronzeDivider width={64} />
          </div>

          {/* Insight — one-line pointer only (taught in full on the conversations guide). */}
          <p className="font-lora text-[14px] text-charcoal leading-[1.65]">
            The room also marks patterns on its own, as a quiet glow in the conversation &mdash;{' '}
            <Link href="/app/explore/conversations" className="text-bronze underline underline-offset-2">
              see <em>The conversations</em>
            </Link>
            .
          </p>
        </div>
      </div>
    </main>
  )
}
