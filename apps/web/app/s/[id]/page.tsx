import Link from 'next/link'
import type { Metadata } from 'next'

// The public share landing page (PR-1). The FIRST server component in this app,
// and the first use of generateMetadata — both for reasons, below.
//
// IT IS A SERVER COMPONENT BECAUSE OF THE LINK PREVIEW. The entire purpose of a
// share link is that it unfurls in WhatsApp, iMessage and Slack, and those
// crawlers do not run JavaScript. A 'use client' page would hand them an empty
// shell — the loop would look like it worked to everyone except the people it
// was built for.
//
// IT IS NOT PROTECTED BY MIDDLEWARE AND THAT IS DELIBERATE. middleware.ts guards
// by prefix allowlist — only /app and /admin — so /s/... falls through to
// NextResponse.next() with nothing to configure. Worth stating plainly because
// "which routes are public" is the kind of thing a reader should not have to
// derive from a negative.

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? 'https://philosopher-api-z9l9.onrender.com/api/v1'

type Voice = { persona_slug: string; persona_name: string; text: string }

type Snapshot = {
  v: number
  artifact_type: string
  headline: string
  attribution: string
  persona_slug: string | null
  persona_name: string | null
  occurred_at: string | null
  voices: Voice[]
}

type SharePayload = {
  artifact_type: string
  revoked: boolean
  snapshot: Snapshot | null
}

// Three outcomes, and they are not the same thing — the whole shape of this page
// is the difference between them.
//
//   payload  → a live share. Render it.
//   'revoked'→ the link was turned off. Say so (copy 1).
//   'gone'   → no such link, ever. 404.
//   null     → we could not reach the API. Say so (copy 8) — NOT the same as
//              revoked, and conflating them would tell a reader their friend
//              withdrew something when in fact our server is down.
async function loadShare(id: string): Promise<SharePayload | 'gone' | null> {
  try {
    const res = await fetch(`${API_BASE}/s/${encodeURIComponent(id)}`, {
      // Never cached. A revoked link that still renders from a CDN edge for
      // minutes afterwards makes revocation a lie in the one window where
      // someone is most likely to be checking that it worked.
      cache: 'no-store',
    })
    if (res.status === 404) return 'gone'
    if (!res.ok) return null
    return (await res.json()) as SharePayload
  } catch {
    return null
  }
}

// STATIC METADATA, PER FOUNDER RULING, AND IT IS THE BETTER FAILURE MODE.
// og:title and og:description never carry snapshot content. Two consequences,
// both good:
//
//   1. No reflection text is handed to Slack, WhatsApp or iMessage unfurl
//      caches, which are third parties we do not control and which would keep
//      that text long after a link was revoked.
//   2. This function makes no network call, so the link preview is correct even
//      when the API is unreachable and the page itself is showing copy 8.
//
// The canonical is the only per-id value here, which is why generateMetadata is
// still required rather than a static `metadata` export. It is RELATIVE, so it
// resolves against the root layout's metadataBase and the single BASE_URL const
// there — an absolute URL would freeze the host into the source, which is what
// metadataBase.test.ts exists to prevent.
export async function generateMetadata({
  params,
}: {
  params: { id: string }
}): Promise<Metadata> {
  return {
    title: 'A reflection from The Wise Room',
    description: 'Eleven minds. One long conversation.',
    alternates: { canonical: `/s/${params.id}` },
    // UNLISTED, NOT SECRET — and robots.txt alone does not achieve it. A
    // Disallow stops CRAWLING; a URL discovered elsewhere (a referrer, a public
    // post) can still be indexed as a bare link. This meta tag is what actually
    // keeps the page out of results, and together with the /s/ rule in
    // app/robots.ts it is what stops a shared reflection becoming a permanent
    // searchable copy that outlives its own revocation.
    robots: { index: false, follow: false },
    openGraph: {
      title: 'A reflection from The Wise Room',
      description: 'Eleven minds. One long conversation.',
      images: ['/og-share.jpg'],
    },
    twitter: {
      card: 'summary_large_image',
      title: 'A reflection from The Wise Room',
      description: 'Eleven minds. One long conversation.',
      images: ['/og-share.jpg'],
    },
  }
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-7 py-12">
        <div className="w-full max-w-[520px]">{children}</div>
      </div>
    </main>
  )
}

function Wordmark() {
  return (
    <Link
      href="/"
      className="font-cormorant text-[20px] font-medium text-ink hover:underline underline-offset-2 decoration-[0.5px]"
    >
      The Wise Room
    </Link>
  )
}

export default async function SharePage({ params }: { params: { id: string } }) {
  const result = await loadShare(params.id)

  // ── The API is unreachable. Distinct from revoked, deliberately. ──────────
  if (result === null) {
    return (
      <Shell>
        <Wordmark />
        <div className="mt-10 space-y-3">
          <h1 className="font-cormorant text-[28px] font-medium text-ink leading-tight">
            This isn&rsquo;t loading right now.
          </h1>
          <p className="font-lora text-[15px] text-charcoal leading-relaxed">
            Something on our side. Try again in a moment.
          </p>
          {/* A plain link to self, not a router refresh: this page is a server
              component and the thing that failed is the fetch inside it, so the
              only useful retry is a fresh request. */}
          <Link
            href={`/s/${params.id}`}
            prefetch={false}
            className="inline-block mt-2 font-lora text-[13px] text-bronze-dark underline underline-offset-2"
          >
            Reload
          </Link>
        </div>
      </Shell>
    )
  }

  // ── No such link, ever. Nothing to say about it. ──────────────────────────
  if (result === 'gone') {
    return (
      <Shell>
        <Wordmark />
        <div className="mt-10 space-y-3">
          <h1 className="font-cormorant text-[28px] font-medium text-ink leading-tight">
            This link has been withdrawn.
          </h1>
          <p className="font-lora text-[15px] text-charcoal leading-relaxed">
            The person who shared this has since turned the link off.
            <br />
            The reflection itself was always theirs.
          </p>
          <Link
            href="/"
            className="inline-block mt-2 font-lora text-[13px] text-bronze-dark underline underline-offset-2"
          >
            See what The Wise Room is
          </Link>
        </div>
      </Shell>
    )
  }

  // ── Turned off by its owner. Same words as an unknown id, on purpose. ─────
  //
  // A stranger cannot tell "withdrawn" from "never existed", and should not be
  // able to: the difference is only interesting to someone probing the
  // keyspace. The sharer knows which of the two they did.
  if (result.revoked || !result.snapshot) {
    return (
      <Shell>
        <Wordmark />
        <div className="mt-10 space-y-3">
          <h1 className="font-cormorant text-[28px] font-medium text-ink leading-tight">
            This link has been withdrawn.
          </h1>
          <p className="font-lora text-[15px] text-charcoal leading-relaxed">
            The person who shared this has since turned the link off.
            <br />
            The reflection itself was always theirs.
          </p>
          <Link
            href="/"
            className="inline-block mt-2 font-lora text-[13px] text-bronze-dark underline underline-offset-2"
          >
            See what The Wise Room is
          </Link>
        </div>
      </Shell>
    )
  }

  const snap = result.snapshot

  return (
    <Shell>
      <Wordmark />

      <p className="mt-8 font-lora text-[11px] uppercase tracking-[0.18em] text-sepia">
        Shared from The Wise Room
      </p>

      <article className="mt-4 bg-paper border border-[0.5px] border-edge rounded-sm shadow-card px-6 py-7">
        <blockquote className="font-cormorant italic text-[24px] text-ink leading-snug whitespace-pre-wrap">
          {snap.headline}
        </blockquote>

        <p className="mt-5 font-lora text-[12px] uppercase tracking-[0.16em] text-bronze-dark">
          {snap.attribution}
        </p>

        {/* Multi-voice kinds (council, counterview). Rendered from the snapshot's
            own voices — never resolved from a persona table, which is the whole
            point of freezing them. A voice with no text is a seat, not a line:
            the council card shows its synthesis, and a landing page that showed
            more than the card would be a different artifact wearing the same
            link. */}
        {snap.voices.filter((v) => v.text).length > 0 && (
          <div className="mt-6 pt-5 border-t border-bronze/20 space-y-4">
            {snap.voices
              .filter((v) => v.text)
              .map((v) => (
                <div key={v.persona_slug} className="border-l border-bronze/25 pl-3">
                  <p className="font-lora text-[11px] uppercase tracking-[0.14em] text-bronze-dark">
                    {v.persona_name}
                  </p>
                  <p className="mt-1 font-cormorant italic text-[17px] text-charcoal leading-snug">
                    {v.text}
                  </p>
                </div>
              ))}
          </div>
        )}
      </article>

      <div className="mt-9 text-center space-y-2">
        <Link
          href="/auth?mode=signin"
          className="inline-block px-7 py-3 rounded-sm bg-ink text-vellum font-cormorant text-[17px] font-medium"
        >
          Begin your own
        </Link>
        <p className="font-lora text-[12px] text-sepia">
          Eleven minds. One long conversation.
        </p>
      </div>
    </Shell>
  )
}
