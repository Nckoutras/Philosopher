import type { MetadataRoute } from 'next'

// BUG-025. /robots.txt returned the custom 404 page — 404 status, content-type
// text/html — because no robots file existed in any form: no public/robots.txt,
// no app/robots.ts, no _redirects, and netlify.toml carries no rewrites.
//
// A Metadata Route rather than public/robots.txt, so the sitemap URL resolves
// against metadataBase (app/layout.tsx:40) instead of being a second hardcoded
// host that can drift from it. TD-69 was exactly that drift.
//
// PREFIX RULES, NOT AN ENUMERATION. There are 39 non-public routes today. A
// literal list of them goes stale the first time someone adds a page, and the
// prefix is the actual invariant: everything under /app/ needs a session and
// everything under /auth/ is the door to one. The trailing slash matters —
// '/app' would also match a future '/application'.
//
// THIS IS NOT ACCESS CONTROL. Every route below is already protected by auth;
// disallowing it stops indexing, not access. A crawler that ignores robots.txt
// reaches a login wall, not content. Nothing here is a security boundary, and
// nothing security-relevant should ever be inferred from it.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: [
        '/',              // landing page — renders for signed-out visitors
        '/legal/terms',
        '/legal/privacy',
      ],
      disallow: [
        '/app/',          // 33 routes: today, chat, council, counterview, mirror,
                          // letters, insights, reflections, quotes, library, rituals,
                          // self-portrait, account, profile, upgrade, onboarding/*,
                          // persona/[slug], ritual/[slug], scheduled-letters/*,
                          // you-vs-you, discuss, welcome
        '/auth/',         // 6 routes: sign-in, verify, disclaimer, trouble, welcome,
                          // oauth/finish
        '/s/',            // PUBLIC SHARE PAGES (PR-1), AND THE ONE ENTRY HERE THAT
                          // IS NOT ABOUT AUTH. These pages return 200 to anyone with
                          // the link — that is their purpose — but they hold something
                          // a person wrote and sent to ONE reader. Indexed, a share
                          // posted in any public place becomes a permanent, searchable
                          // copy that outlives revocation in Google's cache, which is
                          // precisely the promise the withdrawn-link page makes and
                          // cannot keep on its own. Unlisted, not secret: the 128-bit
                          // token is what keeps it private, and this keeps it unlisted.
        '/home',          // placeholder — app/home/page.tsx renders "D1 coming soon".
                          // Public in the sense that it returns 200; asking Google to
                          // index a coming-soon stub under the brand is worse than
                          // not being indexed.
      ],
    },
    // Absolute by requirement: the sitemap directive does not accept a relative
    // path. Resolved against metadataBase so there is one host in one place.
    sitemap: new URL(
      '/sitemap.xml',
      process.env.NEXT_PUBLIC_BASE_URL ?? 'https://thewiseroom.app',
    ).toString(),
    // `host` is deliberately absent: non-standard, read only by Yandex, and
    // another place for a hostname to go stale.
  }
}
