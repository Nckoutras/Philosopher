import type { ReactNode } from 'react'

/**
 * The crisis resources the app-voice crisis text may name, and where each one
 * goes when tapped (SAFETY-003, founder ruling 2026-09-28).
 *
 * A WHITELIST, deliberately. The crisis text is written server-side
 * (apps/api/prompts/safety_response*.jinja2); this only turns the approved
 * resources in it into links. It never guesses that some other number is a
 * phone number, so no stray digits in the copy become a call button.
 *
 * Every entry is on the ROTATION RE-CHECK LIST in the SAFETY-003 backlog entry:
 * a dead number or link is launch-blocking. The backend test
 * test_crisis_resources_are_linked_and_listed pins this map against both
 * templates, so a number added to the copy without a link here (or a link here
 * for a number the copy no longer names) fails CI.
 *
 * tel: URIs carry no spaces (RFC 3966), so "116 123" dials tel:116123.
 */
export const CRISIS_LINKS: Record<string, string> = {
  '988': 'tel:988',                                  // US: 988 Suicide & Crisis Lifeline (call or text)
  '116 123': 'tel:116123',                           // UK & Ireland: Samaritans
  'findahelpline.com': 'https://findahelpline.com',  // everywhere else: directory by ThroughLine
  '112': 'tel:112',                                  // EU emergency (Greek text)
  '1018': 'tel:1018',                                // Greece: suicide intervention line (ΚΛΙΜΑΚΑ)
  '10306': 'tel:10306',                              // Greece: psychosocial support line
}

// Longest first, so a longer entry always wins over a shorter one at the same spot.
// Bounded by anything that is not a letter or digit on both sides, so "112" never
// matches inside "1123" and "988" never inside "988lifeline". NO LOOKBEHIND: it
// throws a SyntaxError at load on iOS Safari before 16.4, which would take the
// crisis bubble down with it. The left boundary is captured as group 1 instead.
const PATTERN = new RegExp(
  '(^|[^0-9A-Za-z])(' +
    Object.keys(CRISIS_LINKS)
      .sort((a, b) => b.length - a.length)
      .map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      .join('|') +
    ')(?![0-9A-Za-z])',
  'g',
)

/** The crisis text with every approved resource rendered as a tappable link. */
export function linkifyCrisisText(text: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  for (const match of text.matchAll(PATTERN)) {
    const start = (match.index ?? 0) + match[1].length
    if (start > last) out.push(text.slice(last, start))
    const label = match[2]
    const href = CRISIS_LINKS[label]
    const external = href.startsWith('https:')
    out.push(
      <a
        key={`${start}-${label}`}
        href={href}
        className="underline underline-offset-2 font-medium text-ink"
        {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
      >
        {label}
      </a>,
    )
    last = start + label.length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}
