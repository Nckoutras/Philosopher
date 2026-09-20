// @vitest-environment jsdom
/**
 * The public share landing page (PR-1).
 *
 * FOUR OUTCOMES, AND THE TESTS EXIST BECAUSE THREE OF THEM LOOK ALIKE IN CODE
 * AND MEAN COMPLETELY DIFFERENT THINGS TO A READER:
 *
 *   live      → the frozen text
 *   revoked   → "withdrawn" (NOT a 404 — that reads as a broken app to someone
 *               who just scanned a friend's card)
 *   unknown   → also "withdrawn", deliberately: a stranger must not be able to
 *               tell a withdrawn link from one that never existed
 *   API down  → "isn't loading", which must NEVER be confused with withdrawn.
 *               Conflating them tells a reader their friend took something back
 *               when in fact our server is down.
 *
 * The metadata tests pin the ruling that og:title and og:description carry NO
 * snapshot content. That is a privacy property, not a styling one: an unfurl
 * cache at Slack or WhatsApp is a third party we do not control, and text put
 * there survives revocation entirely.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'

import SharePage, { generateMetadata } from '../page'

const ID = 'AbCdEfGhIjKlMnOpQrStUv'
const HEADLINE = 'You are not choosing stability for them.'
// U+2019, not U+0027. The locked copy is typed with a straight apostrophe;
// the app renders &rsquo; in every user-facing string and this page follows
// that. Same words, house typography — asserted against what a reader sees.
const ERROR_HEADING = 'This isn’t loading right now.'

const LIVE = {
  artifact_type: 'line',
  revoked: false,
  snapshot: {
    v: 1,
    artifact_type: 'line',
    headline: HEADLINE,
    attribution: 'Marcus Aurelius, in conversation',
    persona_slug: 'marcus_aurelius',
    persona_name: 'Marcus Aurelius',
    occurred_at: null,
    voices: [],
  },
}

function mockFetch(impl: () => Promise<Response> | Response) {
  vi.stubGlobal('fetch', vi.fn(impl))
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response
}

beforeEach(() => vi.unstubAllGlobals())
afterEach(() => vi.unstubAllGlobals())

async function renderPage(id = ID) {
  const ui = await SharePage({ params: { id } })
  return render(ui)
}

describe('a live share', () => {
  it('renders the frozen text and its landing attribution', async () => {
    mockFetch(() => jsonResponse(LIVE))
    await renderPage()

    expect(screen.getByText(HEADLINE)).toBeTruthy()
    // The LANDING wording, not the card's first-person "Marcus Aurelius told me".
    expect(screen.getByText('Marcus Aurelius, in conversation')).toBeTruthy()
    expect(screen.getByText('Shared from The Wise Room')).toBeTruthy()
    expect(screen.getByText('Begin your own')).toBeTruthy()
    expect(screen.getByText('Eleven minds. One long conversation.')).toBeTruthy()
  })

  it('never renders the card wording on the landing page', async () => {
    mockFetch(() => jsonResponse(LIVE))
    const { container } = await renderPage()
    expect(container.textContent).not.toContain('told me')
  })

  it('reads the snapshot and makes exactly one request', async () => {
    const f = vi.fn(() => jsonResponse(LIVE))
    vi.stubGlobal('fetch', f)
    await renderPage()

    expect(f).toHaveBeenCalledTimes(1)
    const [url, opts] = f.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toContain(`/s/${ID}`)
    // A revoked link that still renders from an edge cache for minutes makes
    // revocation a lie in exactly the window someone is checking that it worked.
    expect(opts.cache).toBe('no-store')
  })
})

describe('a revoked share', () => {
  it('says it was withdrawn and shows none of the text', async () => {
    mockFetch(() => jsonResponse({ artifact_type: 'line', revoked: true, snapshot: null }))
    const { container } = await renderPage()

    expect(screen.getByText('This link has been withdrawn.')).toBeTruthy()
    expect(container.textContent).toContain('The person who shared this has since turned the link off.')
    expect(container.textContent).not.toContain(HEADLINE)
  })

  it('never claims the image was deleted or recalled', async () => {
    mockFetch(() => jsonResponse({ artifact_type: 'line', revoked: true, snapshot: null }))
    const { container } = await renderPage()
    const text = container.textContent ?? ''
    for (const forbidden of ['deleted', 'recalled', 'removed', 'erased']) {
      expect(text.toLowerCase()).not.toContain(forbidden)
    }
  })
})

describe('an unknown id', () => {
  it('is indistinguishable from a withdrawn one', async () => {
    mockFetch(() => jsonResponse({ detail: 'Share not found' }, 404))
    await renderPage()
    expect(screen.getByText('This link has been withdrawn.')).toBeTruthy()
  })
})

describe('the API being unreachable', () => {
  it('is its own state, not withdrawn', async () => {
    mockFetch(() => {
      throw new Error('network down')
    })
    const { container } = await renderPage()

    expect(screen.getByText(ERROR_HEADING)).toBeTruthy()
    expect(container.textContent).toContain('Something on our side. Try again in a moment.')
    expect(container.textContent).not.toContain('withdrawn')
  })

  it('treats a 500 the same way as a thrown fetch', async () => {
    mockFetch(() => jsonResponse({}, 500))
    await renderPage()
    expect(screen.getByText(ERROR_HEADING)).toBeTruthy()
  })
})

describe('metadata', () => {
  it('carries no snapshot content and makes no request', async () => {
    const f = vi.fn(() => jsonResponse(LIVE))
    vi.stubGlobal('fetch', f)

    const meta = await generateMetadata({ params: { id: ID } })

    // THE POINT: an unfurl cache at Slack or WhatsApp never receives the text,
    // so revoking a link cannot leave it readable in a third party's preview.
    expect(f).not.toHaveBeenCalled()
    expect(JSON.stringify(meta)).not.toContain(HEADLINE)
    expect(meta.title).toBe('A reflection from The Wise Room')
    expect(meta.description).toBe('Eleven minds. One long conversation.')
  })

  it('declares a per-id RELATIVE canonical', async () => {
    const meta = await generateMetadata({ params: { id: ID } })
    // Relative, so it resolves against the root layout's metadataBase and the
    // single BASE_URL const there. An absolute URL would freeze the host into
    // the source — the regression metadataBase.test.ts exists to prevent.
    expect(meta.alternates?.canonical).toBe(`/s/${ID}`)
    expect(String(meta.alternates?.canonical)).not.toMatch(/^https?:\/\//)
  })

  it('points at an og image that exists at the size it declares', async () => {
    const { statSync, readFileSync } = await import('node:fs')
    const { join } = await import('node:path')
    const file = join(__dirname, '..', '..', '..', '..', 'public', 'og-share.jpg')
    expect(statSync(file).isFile()).toBe(true)

    // JPEG SOF parse — the declared 1200x630 must be the real one. A wrong-sized
    // og image is cropped by every platform differently and looks like nothing
    // is wrong until someone sees the preview.
    const buf = readFileSync(file)
    let i = 2
    let dims: [number, number] | null = null
    while (i < buf.length) {
      if (buf[i] !== 0xff) { i++; continue }
      const marker = buf[i + 1]
      if (marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc) {
        dims = [buf.readUInt16BE(i + 7), buf.readUInt16BE(i + 5)]
        break
      }
      i += 2 + buf.readUInt16BE(i + 2)
    }
    expect(dims).toEqual([1200, 630])
  })
})

describe('the share reference (PR-2)', () => {
  const KEY = 'wr_share_ref'

  beforeEach(() => localStorage.clear())

  it('is recorded when a live share renders', async () => {
    mockFetch(() => jsonResponse(LIVE))
    await renderPage()

    const raw = localStorage.getItem(KEY)
    expect(raw).not.toBeNull()
    expect(JSON.parse(raw!).id).toBe(ID)
  })

  it('is NOT recorded for a withdrawn share', async () => {
    // A reference to something already dead would be carried through a signup
    // only to be rejected there, and would sit in a person's storage for thirty
    // days to do it.
    mockFetch(() => jsonResponse({ artifact_type: 'line', revoked: true, snapshot: null }))
    await renderPage()
    expect(localStorage.getItem(KEY)).toBeNull()
  })

  it('is NOT recorded for an unknown id', async () => {
    mockFetch(() => jsonResponse({ detail: 'Share not found' }, 404))
    await renderPage()
    expect(localStorage.getItem(KEY)).toBeNull()
  })

  it('is NOT recorded when the API is unreachable', async () => {
    // The share may well be live — we simply do not know, and recording a
    // reference we could not verify is how garbage accumulates.
    mockFetch(() => {
      throw new Error('network down')
    })
    await renderPage()
    expect(localStorage.getItem(KEY)).toBeNull()
  })
})
