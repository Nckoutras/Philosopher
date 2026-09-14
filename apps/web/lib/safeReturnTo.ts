// Where a post-sign-in redirect is allowed to land.
//
// THE THREAT. `next` arrives in a link — the middleware writes it, but nothing
// stops someone sending a reader a crafted /auth?next=… URL. The classic payloads
// are protocol-relative: `//evil.com` and `/\evil.com` are both read by browsers
// as "go to evil.com", and both pass a naive startsWith('/') check. So this is an
// ALLOW-LIST by prefix, never a deny-list of bad shapes.
//
// DECODE BEFORE DECIDING, and decide on both forms. URLSearchParams has already
// decoded once by the time a caller reads `next`, so `%2f%2fevil.com` arrives as
// `//evil.com` and is caught. A doubly-encoded `%252f%252fevil.com` arrives as
// `%2f%2fevil.com`, which is not a valid path either but reads as harmless text —
// so the rule is applied to the value AND to one further decode of it, and both
// must pass. Layering another encoding on top cannot get anywhere that a single
// decode would not already have reached.
//
// FALL THROUGH, NEVER THROW. A bad `next` costs the user their destination. It
// must never cost them their sign-in, so every rejection path returns the default
// and nothing here can raise — decodeURIComponent throws on a lone '%'.
//
// NOT REJECTED, deliberately: a traversal like /app/../../auth. It normalises to
// a SAME-ORIGIN path, so it is not an open redirect — the threat this guards
// against. The worst it can do is land somewhere unhelpful, which the user fixes
// by navigating. Adding a `..` rule would widen this helper past the one job it
// has; if a redirect loop ever shows up in practice, that is the moment to revisit.

export const DEFAULT_RETURN_TO = '/app/today'

/** The rule, applied to one concrete string. */
function isSafePath(value: string): boolean {
  if (value.length === 0 || value.length > 512) return false
  // Protocol-relative, in both spellings a browser accepts.
  if (value.startsWith('//') || value.startsWith('/\\')) return false
  if (value.includes('\\')) return false
  if (value.includes('://')) return false
  // The allow-list itself. Everything above is defence in depth behind this line.
  return value.startsWith('/app/')
}

/** One more decode, or null when the input is not decodable. */
function decodeOnce(value: string): string | null {
  try {
    return decodeURIComponent(value)
  } catch {
    return null
  }
}

/**
 * The validated destination for a post-sign-in redirect.
 *
 * Returns `next` when it is a relative path inside /app/, and DEFAULT_RETURN_TO
 * for everything else — absent, empty, absolute, protocol-relative, over-long,
 * or undecodable.
 */
export function safeReturnTo(next: string | null | undefined): string {
  if (!next) return DEFAULT_RETURN_TO
  if (!isSafePath(next)) return DEFAULT_RETURN_TO

  const decoded = decodeOnce(next)
  if (decoded === null) return DEFAULT_RETURN_TO
  // Equal is the common case (no encoding left); when it differs, the decoded
  // form must clear the same bar.
  if (decoded !== next && !isSafePath(decoded)) return DEFAULT_RETURN_TO

  return next
}
