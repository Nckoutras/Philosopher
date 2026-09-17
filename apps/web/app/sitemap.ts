import type { MetadataRoute } from 'next'

// BUG-026. /sitemap.xml returned the custom 404 page, for the same reason
// /robots.txt did: no sitemap existed in any form.
//
// THE PUBLIC SURFACE IS THREE URLS. That is the enumeration of what exists, not
// of what should — a full route inventory is 41 pages, of which 37 sit behind
// auth and one is a placeholder. BUG-030 tracks the thinness itself; this file
// is not the place to fix it, and adding a URL here would not create a page.
//
// WHAT IS DELIBERATELY ABSENT:
//   /home        app/home/page.tsx renders "Home — D1 coming soon". It returns
//                200, so it is technically public, but submitting a stub to be
//                indexed under the brand is worse than being absent.
//   /app/*       33 authenticated routes. A crawler gets a redirect, never content.
//   /auth/*      6 routes. Same.
//
// NO lastModified. `new Date()` regenerates on every build and would tell Google
// the legal pages changed whenever anything else did — a small false claim, of
// the same family as the structured-data fields refused in layout.tsx. A real
// value would have to come from the content's own history, and there is nowhere
// honest to read it from today.
export default function sitemap(): MetadataRoute.Sitemap {
  const base = process.env.NEXT_PUBLIC_BASE_URL ?? 'https://thewiseroom.app'

  return [
    {
      url: new URL('/', base).toString(),
      changeFrequency: 'monthly',
      priority: 1,
    },
    {
      url: new URL('/legal/terms', base).toString(),
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: new URL('/legal/privacy', base).toString(),
      changeFrequency: 'yearly',
      priority: 0.3,
    },
  ]
}
