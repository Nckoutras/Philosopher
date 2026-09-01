// The web half of the event taxonomy, and its source of truth.
//
// The backend half is apps/api/constants.py ANALYTICS_EVENTS, under the same
// rule: enforced by tests rather than at runtime (lib/__tests__/
// analyticsRegistry.test.ts walks every track('...') literal in the app).
// Both directions are checked — a fired name must be declared, and a declared
// name must have at least one call site. A name with no caller is deleted, not
// left as an aspiration.
//
// Enforcement is not a runtime check on purpose: an unknown event name must
// never throw inside a click handler. Analytics is an observer and may not
// change what the product does.
//
// Names shared with the backend half must carry the same property list. Today
// none are shared: every event below fires only from the browser, because each
// one is a fact only the browser knows (what was rendered, what was tapped).
//
// PROPERTIES ARE IDS, ENUMS, COUNTS AND BUCKETS. Never conversation text,
// memory text, letter text, an email, or free-text matter. utm_* and $referrer
// are NOT listed here: posthog-js attaches them to every event by itself
// (save_campaign_params and save_referrer both default to true, and neither is
// affected by autocapture being off), so declaring them would duplicate what
// the SDK already sends.

export const ANALYTICS_EVENTS = {
  // Reserved PostHog event, fired manually by PageviewTracker because the App
  // Router does no full page load between routes.
  $pageview: ['$current_url'],

  // ── Acquisition ──────────────────────────────────────────────────────────
  // The landing page itself. No custom utm props — see the note above.
  landing_view: [],
  // The moment an email is submitted, NOT the moment it verifies. The
  // completion half is server-side (signup_completed) because only the server
  // knows whether the account was created or merely signed in to.
  signup_started: ['source', 'device'],

  // ── Engagement ───────────────────────────────────────────────────────────
  // "Rendered" is a client fact: the server knows when it finished streaming,
  // only the browser knows when the reply was on screen.
  first_reply_rendered: ['persona', 'latency_bucket', 'origin'],
  letter_action: ['week', 'host', 'action'],

  // ── Monetisation ─────────────────────────────────────────────────────────
  // Shipped in #576, before this taxonomy existed. Listed here because the
  // registry test requires every fired name to be declared.
  //
  // upgrade_clicked fires from DELIBERATE CTAs only — a button or link whose
  // whole purpose is "upgrade": PaywallModal, the persona detail page, and the
  // account / counterview / self_portrait / share / locked-mind CTAs. It does
  // NOT fire from the ten guard redirects that push a user to /app/upgrade
  // because they tried to do something else. Those are the user being STOPPED,
  // not choosing; counting them would inflate the numerator of the
  // upgrade_clicked → checkout_started ratio this exists to measure. They stay
  // visible through $pageview's $current_url, which carries ?source=.
  paywall_viewed: ['surface', 'reason'],
  upgrade_clicked: ['surface', 'reason'],
} as const

export type AnalyticsEventName = keyof typeof ANALYTICS_EVENTS

/** Coarse buckets, deliberately not milliseconds. The decision these inform is
 *  "is this slow enough to lose people", which a bucket answers and a raw
 *  number obscures — and a raw latency is a weak fingerprint besides. */
export function latencyBucket(ms: number): string {
  if (ms < 1000) return 'under_1s'
  if (ms < 3000) return '1_3s'
  if (ms < 8000) return '3_8s'
  if (ms < 20000) return '8_20s'
  return 'over_20s'
}

/** 'mobile' | 'tablet' | 'desktop' from the UA. Coarse on purpose: a full UA
 *  string is a fingerprint, and the decision this informs is only ever "which
 *  form factor is the funnel losing". Safe during SSR. */
export function deviceClass(): string {
  if (typeof navigator === 'undefined') return 'unknown'
  const ua = navigator.userAgent
  if (/iPad|Tablet/i.test(ua)) return 'tablet'
  if (/Mobi|Android|iPhone/i.test(ua)) return 'mobile'
  return 'desktop'
}
