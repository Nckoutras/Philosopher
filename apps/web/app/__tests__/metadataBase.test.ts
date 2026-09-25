// @vitest-environment node
//
// TD-69. `metadataBase` is the base every absolute `og:image` URL is resolved
// against, so whatever host it names is the host that appears in a shared link's
// unfurl. Until 2026-09-08 both of its branches named a domain the product does not
// use: `apps/web/.env.production` was tracked and pinned a stale Vercel preview
// host, and the code fallback here was `https://philosopher.app`. The file is now
// untracked (it matches `.gitignore`'s `.env.*`), so on any build without a
// dashboard value this fallback IS the answer — which is what this test pins.
//
// WHY A SOURCE ASSERTION rather than importing `../layout.tsx` and reading
// `metadata.metadataBase`. That import pulls in `next/font/local` and
// `./globals.css`, and this vitest config handles neither — no CSS plugin, no font
// mock, `environment: 'node'`. The same reasoning as #578: pin the DECISION in the
// source rather than a value the runner has to construct, because a test that
// depends on the runner's ability to build a Next layout is testing the runner.
// `lib/__tests__/analyticsRegistry.test.ts` scans source for the same reason.
//
// HOW THIS CAN FAIL. Changing the fallback to any other host fails the first test.
// Reintroducing any of the three dead hosts anywhere in the layout — including in a
// comment, where it would mislead the next reader exactly as it did here — fails the
// second.
import { describe, it, expect } from 'vitest'
import { readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

const LAYOUT = readFileSync(join(__dirname, '..', 'layout.tsx'), 'utf8')

// The two other user-facing pages that carry their own metadata. The DEAD_HOSTS
// sweep covers them too (BUG-028): a stale host in a legal page reaches a reader
// as a broken link in a document they were sent to for accuracy.
const LEGAL_PAGES = ['terms', 'privacy'].map((name) => ({
  name: `legal/${name}`,
  src: readFileSync(join(__dirname, '..', 'legal', name, 'page.tsx'), 'utf8'),
}))

// The hosts this PR removed. `philosopher.app` was the code fallback;
// `thinkalike-…vercel.app` was the value in the untracked `.env.production`.
const DEAD_HOSTS = ['philosopher.app', 'thinkalike', 'vercel.app']

describe('metadataBase', () => {
  it('falls back to the live domain when NEXT_PUBLIC_BASE_URL is unset', () => {
    const match = LAYOUT.match(/NEXT_PUBLIC_BASE_URL\s*\?\?\s*'([^']+)'/)
    expect(match, 'metadataBase fallback not found in app/layout.tsx').not.toBeNull()
    expect(match![1]).toBe('https://thewiseroom.app')
  })

  it('names no dead host anywhere in the layout, comments included', () => {
    const found = DEAD_HOSTS.filter((host) => LAYOUT.includes(host))
    expect(found).toEqual([])
  })

  // Extended to the legal pages (BUG-028). `thinkalike` is still the LIVE Netlify
  // site name — it appears in every PR's check names — so this is not asserting
  // the word is dead everywhere. It asserts that no USER-FACING URL carries it,
  // which is precisely the failure BUG-028 was.
  it.each(LEGAL_PAGES)('names no dead host in $name', ({ src }) => {
    expect(DEAD_HOSTS.filter((host) => src.includes(host))).toEqual([])
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// BUG-028's shape rulings. READ WHAT THESE DO AND DO NOT PROVE.
//
// They pin the SHAPE of the metadata — that the OG image paths are relative, so
// metadataBase is what resolves them, and that the file those paths point at
// exists at the declared size. They do NOT pin the DEPLOYED value: metadataBase
// still comes from NEXT_PUBLIC_BASE_URL at build time, set in a dashboard these
// tests cannot read.
//
// So this suite WOULD NOT HAVE CAUGHT THE BUG-028 INCIDENT, and is not claimed
// to. That was a wrong value in an environment, not a wrong shape in the source.
// What it does catch is the regression that would make such a value unfixable:
// an absolute URL hardcoded into the images, at which point correcting the
// dashboard changes nothing.
describe('OG image metadata shape', () => {
  it('declares og and twitter image paths as RELATIVE, not absolute', () => {
    // Absolute URLs here would bypass metadataBase entirely — the host would be
    // frozen in the source and no environment change could correct it.
    const paths = [...LAYOUT.matchAll(/['"](\/og-image\.jpg)['"]/g)].map((m) => m[1])
    expect(paths.length, 'expected og-image.jpg referenced in openGraph and twitter').toBe(2)
    for (const p of paths) expect(p.startsWith('/')).toBe(true)
    expect(LAYOUT).not.toMatch(/https?:\/\/[^'"\s]*og-image\.jpg/)
  })

  it('points at a file that exists, at the 1200x630 it declares', () => {
    const file = join(__dirname, '..', '..', 'public', 'og-image.jpg')
    expect(statSync(file).isFile()).toBe(true)

    const buf = readFileSync(file)
    // JPEG magic, then walk the segments to the SOF marker for the real size.
    // Parsed from the FILE, deliberately — reading the width/height declared in
    // layout.tsx back out of layout.tsx would assert the claim against itself.
    expect(buf.subarray(0, 3).toString('hex')).toBe('ffd8ff')

    let i = 2
    let dims: { w: number; h: number } | null = null
    while (i < buf.length - 9) {
      if (buf[i] !== 0xff) { i += 1; continue }
      const marker = buf[i + 1]
      if ([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf].includes(marker)) {
        dims = { h: buf.readUInt16BE(i + 5), w: buf.readUInt16BE(i + 7) }
        break
      }
      if (marker === 0xd8 || marker === 0xd9 || (marker >= 0xd0 && marker <= 0xd7)) { i += 2; continue }
      i += 2 + buf.readUInt16BE(i + 2)
    }

    expect(dims, 'no SOF marker found - not a parseable JPEG').not.toBeNull()
    expect(dims).toEqual({ w: 1200, h: 630 })

    // And the declaration in the source agrees with the file.
    expect(LAYOUT).toMatch(/width:\s*1200/)
    expect(LAYOUT).toMatch(/height:\s*630/)
  })
})
