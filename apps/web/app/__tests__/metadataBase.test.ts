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
// `metadata.metadataBase`. That import pulls in `next/font/google` and
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
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const LAYOUT = readFileSync(join(__dirname, '..', 'layout.tsx'), 'utf8')

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
})
