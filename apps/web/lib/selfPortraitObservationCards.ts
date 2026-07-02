// ─────────────────────────────────────────────────────────────────────────────────────
// Self-Portrait observation cards (Phase B, mock restyle). A FROZEN, hand-authored map
// keyed on the 8 PORTRAIT_AXES slugs (services/self_portrait.py). The portrait view shows
// the TOP-3 axes by score (tie-break frozen order) as a 3-across row of small cards.
//
// • Deterministic: no LLM, no counts, no scores — only the authored headline + support.
// • `icon` is a lucide-react icon NAME (rendered page-side by a CardIcon→component map),
//   so this stays a plain-data .ts file (no JSX).
// • Voice: calm, second-person, present-tense. Headline = one bold Cormorant line;
//   support = one short Lora line.
// ─────────────────────────────────────────────────────────────────────────────────────

/** lucide-react icon names used by the cards (page maps these to components). */
export type CardIcon =
  | 'User'
  | 'Shield'
  | 'Feather'
  | 'Flame'
  | 'HelpCircle'
  | 'Anchor'
  | 'Users'
  | 'Compass'

export interface ObservationCard {
  icon: CardIcon
  headline: string
  support: string
}

/** axis slug → its frozen card. All 8 PORTRAIT_AXES slugs are covered. */
export const OBSERVATION_CARDS: Readonly<Record<string, ObservationCard>> = {
  identity: {
    icon: 'User',
    headline: 'You return to who you are.',
    support: 'A steady sense of self runs beneath your choices.',
  },
  fear: {
    icon: 'Shield',
    headline: 'You notice what’s at risk.',
    support: 'An eye for what could go wrong keeps you prepared.',
  },
  freedom: {
    icon: 'Feather',
    headline: 'You need room to move.',
    support: 'Space to choose your own way matters deeply to you.',
  },
  desire: {
    icon: 'Flame',
    headline: 'You know what draws you.',
    support: 'A clear pull toward what you want shapes your path.',
  },
  doubt: {
    icon: 'HelpCircle',
    headline: 'You sit with the hard questions.',
    support: 'Uncertainty doesn’t scare you off — you stay with it.',
  },
  duty: {
    icon: 'Anchor',
    headline: 'You carry your standards.',
    support: 'A strong sense of principle guides your choices.',
  },
  connection: {
    icon: 'Users',
    headline: 'You hold your people close.',
    support: 'The bonds you keep are central to how you live.',
  },
  meaning: {
    icon: 'Compass',
    headline: 'You reach for what matters.',
    support: 'A search for purpose gives your days their direction.',
  },
}

/**
 * Top-3 axes by score (desc, tie-break frozen/incoming order) mapped to their frozen
 * cards. Skips any score of 0 and any slug missing from the map. Returns [] when there's
 * no signal, so the caller renders nothing.
 */
export function topObservationCards(
  scores: { key: string; score: number }[] | null | undefined,
): (ObservationCard & { key: string })[] {
  const axes = scores ?? []
  return axes
    .map((s, i) => ({ s, i }))
    .filter((e) => e.s.score > 0 && OBSERVATION_CARDS[e.s.key])
    .sort((a, b) => (b.s.score - a.s.score) || (a.i - b.i))
    .slice(0, 3)
    .map((e) => ({ key: e.s.key, ...OBSERVATION_CARDS[e.s.key] }))
}
