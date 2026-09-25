import type { Metadata, Viewport } from 'next'
import localFont from 'next/font/local'
import { ThemeProvider } from 'next-themes'
import { Toaster } from 'react-hot-toast'
import QueryProvider from '@/components/ui/QueryProvider'
import AnalyticsProvider from '@/components/analytics/AnalyticsProvider'
import './globals.css'

// SELF-HOSTED, so `next build` makes no network call for fonts.
//
// These were next/font/google. At build time that loader downloads every subset
// file Google lists and reads each URL's extension with /\.(woff2|…)$/.exec(url)[1].
// Google intermittently serves some subsets as fonts.gstatic.com/l/font?kit=…
// URLs with no extension (measured 2026-09-25: 4 of 60 Cormorant responses), and
// the build dies with "TypeError: Cannot read properties of null (reading '1')" —
// ~3% of CI builds, and Netlify production deploys run the same build.
//
// The files in ./fonts are Google's own latin-subset woff2 files, byte-identical
// to what the Google loader embedded (sha256 checked). Both are VARIABLE fonts:
// one file covers every weight, so each weight below points at the same file,
// exactly as the generated CSS did before. Latin only, by ruling: characters
// outside it (Ł, ş, Cyrillic, Vietnamese) now fall back to the serif stack;
// neither font has Greek, so Greek text is unchanged. Licences: ./fonts/OFL-*.txt.
//
// adjustFontFallback 'Times New Roman' matches what the Google loader chose for
// these serif faces; the local loader otherwise defaults to Arial.
const cormorant = localFont({
  src: [
    { path: './fonts/cormorant-garamond-latin.woff2', weight: '300', style: 'normal' },
    { path: './fonts/cormorant-garamond-latin.woff2', weight: '400', style: 'normal' },
    { path: './fonts/cormorant-garamond-latin.woff2', weight: '500', style: 'normal' },
  ],
  variable: '--font-cormorant',
  display: 'swap',
  adjustFontFallback: 'Times New Roman',
})

const lora = localFont({
  src: [
    { path: './fonts/lora-latin.woff2', weight: '400', style: 'normal' },
    { path: './fonts/lora-latin.woff2', weight: '500', style: 'normal' },
  ],
  variable: '--font-lora',
  display: 'swap',
  adjustFontFallback: 'Times New Roman',
})

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  // Chrome/Android defaults to 'resizes-visual': the keyboard shrinks the VISUAL
  // viewport only, so a bottom-anchored composer in a full-height column sits behind it
  // with nowhere to scroll. 'resizes-content' shrinks the LAYOUT viewport instead, which
  // dvh-sized shells (chat pages, (tabs)/layout) track — lifting the composer clear.
  interactiveWidget: 'resizes-content',
  // Android address bar / task switcher chrome when installed. Lives here, not in
  // `metadata`: the App Router moved themeColor onto the viewport export.
  themeColor: '#B89968',
}

// ONE HOST, DEFINED ONCE. metadataBase, the canonical and the JSON-LD all resolve
// from here. TD-69 was a hostname drifting between two places; a third copy in the
// structured data would be the same defect with a longer fuse, because nothing
// renders a JSON-LD host where a human would notice it.
const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL ?? 'https://thewiseroom.app'

export const metadata: Metadata = {
  title: 'The Wise Room — Your Reflective Companion',
  description: 'Think deeper with the greatest thinkers of history.',
  metadataBase: new URL(BASE_URL),
  // BUG-027. Self-referencing canonical, resolved against metadataBase above.
  // Relative on purpose — one host, defined once.
  //
  // INHERITED BY CHILDREN, which is why /legal/terms and /legal/privacy each
  // declare their own. Without that, both would inherit '/' and tell Google the
  // two legal pages ARE the homepage — a worse defect than the missing canonical
  // this fixes.
  alternates: {
    canonical: '/',
  },
  openGraph: {
    title: 'The Wise Room',
    description: 'A premium AI reflective companion grounded in historical philosophy.',
    type: 'website',
    // 1200x630 JPEG. JPEG, not WebP: some social scrapers still refuse WebP, and a
    // link that unfurls with no image costs more than the ~25 KB the format saves.
    // Cropped from the council-chamber asset — the 9:16 splash hero cannot yield a
    // 1.91:1 frame that still reads as a room, only a close-up of the armchair.
    images: [
      {
        url: '/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'The Wise Room — a quiet council chamber',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'The Wise Room',
    description: 'A premium AI reflective companion grounded in historical philosophy.',
    images: ['/og-image.jpg'],
  },
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'The Wise Room',
  },
}

// BUG-027. Minimal and TRUE. `name` and `description` are verbatim from
// public/manifest.json; the logo is public/icons/icon-512.png, which exists at
// 512x512.
//
// WHAT IS NOT HERE, because each would be a false claim in machine-readable form:
//
//   aggregateRating / reviewCount — there are no reviews. Inventing them is what
//     earns a manual action.
//   offers / price — BLOCKED, and not hypothetically. app/app/upgrade/page.tsx
//     displays EUR 99.99/year while OPS-006 records Stripe charging EUR 149
//     against a locked price of 99.99. The displayed price and the charged price
//     disagree today, so publishing either as structured data broadcasts a price
//     the payment system does not honour — to aggregators that cache it. Must not
//     be added until OPS-006 closes and the two agree.
//   SearchAction — there is no site search; it would advertise a /search endpoint
//     that 404s.
//   SoftwareApplication — the product is entirely behind auth. There is no public
//     page for such an entity to describe.
//   sameAs — no social profiles to point at.
//
// A schema error is recoverable. A false claim in structured data is not.
const JSON_LD = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: 'The Wise Room',
  url: BASE_URL,
  description: 'Think deeper with the greatest thinkers of history.',
  publisher: {
    '@type': 'Organization',
    name: 'The Wise Room',
    url: BASE_URL,
    logo: new URL('/icons/icon-512.png', BASE_URL).toString(),
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${cormorant.variable} ${lora.variable} font-lora antialiased`}>
        {/* JSON.stringify, never a template literal: a raw string could carry a
            `</script>` sequence and break out of the tag. The object above is a
            frozen literal with no user input in it, so this is belt-and-braces —
            but the next person to add a field may not check. */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }}
        />
        <ThemeProvider attribute="class" forcedTheme="light" enableSystem={false}>
          <QueryProvider>
            {children}
            {/* Consent-gated: loads no SDK and sets no cookie until Accept. */}
            <AnalyticsProvider />
            <Toaster
              position="bottom-right"
              toastOptions={{
                style: {
                  background: 'var(--ink)',
                  color: 'var(--vellum)',
                  border: '0.5px solid var(--ink)',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontFamily: 'var(--font-lora), Georgia, serif',
                },
              }}
            />
          </QueryProvider>
        </ThemeProvider>
        {/* HTTPS only: registration is skipped on http://localhost so the worker
            never shadows the dev server. See public/sw.js for the cache policy. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
      if ('serviceWorker' in navigator && location.protocol === 'https:') {
        window.addEventListener('load', function() {
          navigator.serviceWorker.register('/sw.js');
        });
      }
    `,
          }}
        />
      </body>
    </html>
  )
}
