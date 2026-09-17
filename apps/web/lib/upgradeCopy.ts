// Which paywall sent the user here, and what the upgrade page should say about it.
//
// Every paywall used to arrive at the same "Unlimited minds. Persistent memory.
// Deeper reflection." A user who hit the message cap, one who opened a locked
// mind and one who tapped the Council all read the same sentence. #576 started
// putting source and reason in the URL; this is the half that reads them.
//
// THE ALLOWLIST IS THE POINT. Both values arrive from a query string, which
// anyone can edit. Nothing here interpolates a query value into rendered copy:
// `source` and `reason` only ever select a fixed string, and an unknown value
// selects the fallback. That is why a hand-typed
// ?source=<script> renders the generic line rather than anything at all.
//
// The persona NAME is the one piece of copy that varies, and it never comes
// from the URL either — see benefitLine's personaName parameter, which the page
// fills only from a name matched in the API's persona list.

/** Every surface allowed to identify itself. A value not in this list renders
 *  the fallback line, and is still recorded on $pageview via the query string. */
export const UPGRADE_SOURCES = [
  'council',
  'letter',
  // Its own identifier, NOT 'letter'. The Future Self ritual and the Sunday
  // Letter are different products bought for different reasons, and until
  // BUG-004 they shared a source: the Future Self door sent `source=letter`, so
  // its reader was told "Your Sunday Letter arrives on Pro", and every
  // checkout_started and Stripe metadata row from either ritual landed in one
  // bucket. Splitting the identifier is what makes the two separable in
  // PostHog; splitting the copy below is what stops the wall lying to a reader.
  'future_self',
  // Same reasoning, second instance. You vs You is Pro-gated
  // (routers/self_comparison.py) and had no source of its own, so the only
  // available spelling was the generic 'ritual' -- which would have recreated
  // BUG-004 in a second place rather than fixing it once.
  'you_vs_you',
  'ritual',
  'counterview',
  'self_portrait',
  'account',
  'share',
  'insight_door',
  'persona_locked',
  'go_deeper',
  'paywall_modal',
  'persona_detail',
] as const

export type UpgradeSource = (typeof UPGRADE_SOURCES)[number]

/** The reasons PaywallModal already emits (#576), plus nothing new. */
export const UPGRADE_REASONS = [
  'daily',
  'go_deeper_depth',
  'deep_mode',
  'save_limit',
  'persona_locked',
] as const

export type UpgradeReason = (typeof UPGRADE_REASONS)[number]

export const FALLBACK_LINE = 'Unlimited minds. Persistent memory. Deeper reflection.'

export function isUpgradeSource(v: string | null): v is UpgradeSource {
  return v !== null && (UPGRADE_SOURCES as readonly string[]).includes(v)
}

export function isUpgradeReason(v: string | null): v is UpgradeReason {
  return v !== null && (UPGRADE_REASONS as readonly string[]).includes(v)
}

/**
 * The line under "Choose your plan."
 *
 * REASON WINS OVER SOURCE. A reason describes the specific wall the user hit
 * ("you have used today's conversations"); a source only describes which screen
 * they were on. When both are present the more specific one is the truer
 * sentence, and every reason-carrying arrival comes from PaywallModal, whose
 * source is the less informative of the two.
 *
 * `personaName` is used only by the persona_locked line, and only when the page
 * has resolved it against the API's persona list. Absent — not yet loaded, not
 * found, or the request failed — the no-name variant reads correctly on its own,
 * so there is no error state to render.
 */
export function benefitLine(opts: {
  source?: string | null
  reason?: string | null
  personaName?: string | null
}): string {
  const source = isUpgradeSource(opts.source ?? null) ? opts.source : null
  const reason = isUpgradeReason(opts.reason ?? null) ? opts.reason : null

  switch (reason) {
    case 'daily':
      return "Today's free conversations are spent. Pro has no daily cap — and a memory that holds what you've said."
    case 'go_deeper_depth':
    case 'deep_mode':
      return 'Go as deep as the question needs. Pro removes the depth limits.'
    case 'save_limit':
      return 'Keep every line worth keeping. Pro lifts the three-line limit.'
    case 'persona_locked':
      return personaLockedLine(opts.personaName)
    default:
      break
  }

  switch (source) {
    case 'persona_locked':
      return personaLockedLine(opts.personaName)
    case 'council':
      return 'The Council convenes on Pro: four minds, one verdict.'
    case 'letter':
      return 'Your Sunday Letter arrives on Pro — a reading of your week, in the voice you spoke with most.'
    case 'future_self':
      return "Write to the person you'll be in a year. Pro delivers it."
    case 'you_vs_you':
      return 'Set what you said then against what you say now. Pro opens the comparison.'
    default:
      // ritual, counterview, self_portrait, account, share, insight_door,
      // go_deeper, paywall_modal and persona_detail have no approved line of
      // their own yet. The source is still recorded; only the copy falls back.
      return FALLBACK_LINE
  }
}

function personaLockedLine(personaName?: string | null): string {
  return personaName
    ? `${personaName} speaks on Pro — along with all eleven minds.`
    : 'All eleven minds speak on Pro.'
}
