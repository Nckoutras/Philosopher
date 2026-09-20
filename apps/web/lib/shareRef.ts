// The share reference: how a share_id travels from a landing page to a signup.
//
// WHY localStorage AND NOT A QUERY PARAMETER. The OAuth path leaves our origin
// entirely — /auth hands off to the API, which hands off to Google, which comes
// back to the API's callback. A query parameter on /auth does not survive that;
// the start endpoint forwards only `next`, and `next` is validated to be an
// /app/ path so nothing else can ride inside it. localStorage does survive,
// because Google returns us to FRONTEND_URL/auth/oauth/finish — our origin, our
// storage, intact.
//
// WHAT THIS BUYS AND WHAT IT DOES NOT. It carries a reference across a
// multi-hop signup in ONE browser. It carries nothing across devices, across
// browsers, or across a cleared cache. That is a floor on the whole funnel and
// it is stated at the registry entry for share_signup, which is where someone
// reading a number will be standing.
//
// EVERY ACCESS IS WRAPPED. localStorage does not merely return null when it is
// unavailable — it THROWS, on read and on write both, in Safari private mode,
// under storage-disabled policies, and in some embedded webviews. lib/analytics
// already establishes this idiom for the consent key; this file follows it. A
// throw here must read as "no reference", never as an error a caller handles.

const KEY = 'wr_share_ref'

/** 30 days. Beyond this a stored reference is treated as absent and deleted. */
export const SHARE_REF_TTL_MS = 30 * 24 * 60 * 60 * 1000

/** The alphabet and length secrets.token_urlsafe(16) produces. */
const ID_RE = /^[A-Za-z0-9_-]{22}$/

interface StoredRef {
  v: 1
  id: string
  /** Epoch ms at write. What makes the 30-day window enforceable. */
  t: number
}

/**
 * Remember the share a visitor arrived from.
 *
 * Called only when a LIVE share renders — never for a withdrawn one, an unknown
 * id, or the API-unreachable state. Known-dead references are not worth carrying
 * to a signup that would only have them rejected.
 */
export function setShareRef(id: string): void {
  if (!ID_RE.test(id)) return
  try {
    const ref: StoredRef = { v: 1, id, t: Date.now() }
    localStorage.setItem(KEY, JSON.stringify(ref))
  } catch {
    // Storage unavailable. The visit is simply unattributable — which costs a
    // funnel row and nothing else. Never surfaced to the reader: they did not
    // ask to be counted and cannot act on the failure.
  }
}

/**
 * The stored share id, or null.
 *
 * ANY problem yields null AND deletes the key: not JSON, not an object, wrong
 * version, an id that is not 22 characters of the right alphabet, a missing or
 * non-finite timestamp, a timestamp in the future, or one older than 30 days.
 * Deleting on a bad read matters as much as returning null — a value that can
 * never be used should not sit in a person's browser for a month.
 */
export function getShareRef(): string | null {
  let raw: string | null
  try {
    raw = localStorage.getItem(KEY)
  } catch {
    return null
  }
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as unknown
    if (
      typeof parsed !== 'object' ||
      parsed === null ||
      (parsed as StoredRef).v !== 1
    ) {
      clearShareRef()
      return null
    }
    const { id, t } = parsed as StoredRef
    if (typeof id !== 'string' || !ID_RE.test(id)) {
      clearShareRef()
      return null
    }
    // A future timestamp is as broken as an expired one — a clock change or a
    // hand-edited value — and treating it as fresh would make it immortal.
    if (typeof t !== 'number' || !Number.isFinite(t) || t > Date.now()) {
      clearShareRef()
      return null
    }
    if (Date.now() - t > SHARE_REF_TTL_MS) {
      clearShareRef()
      return null
    }
    return id
  } catch {
    clearShareRef()
    return null
  }
}

/**
 * Forget it. Called at every signup terminus, not only the successful one.
 *
 * THREE CLEARING POINTS, and the second is the one that is easy to miss:
 *
 *   1. after an attribution attempt — success OR rejection. A rejected
 *      reference must not wait around for the next signup in this browser.
 *   2. on a sign-in that did NOT create an account. Without this, a returning
 *      user's sign-in leaves the reference alive to credit a DIFFERENT person's
 *      signup later on a shared device.
 *   3. on any malformed or expired read, above.
 *
 * The rule underneath all three: reaching a signup outcome at all consumes the
 * reference. A stale id must never survive to credit an unrelated signup.
 */
export function clearShareRef(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // Nothing to do. If storage throws on removal it threw on write too, so
    // there is no value there to strand.
  }
}
