// ─────────────────────────────────────────────────────────────────────────────────────
// Self-Portrait deterministic caption (Phase B). One calm 1–2 line sentence naming the
// user's TWO strongest theme axes, shown under the portrait viz.
//
// • FROZEN, hand-authored — a static slug → soft-phrase map (the 8 PORTRAIT_AXES keys).
//   NO LLM call, NO counts, NO scores in the copy. Only the two axis LABELS + their
//   phrases appear.
// • Top-2 by score, tie-broken by frozen axis order (the order theme_scores arrives in),
//   so the sentence is stable on reopen.
// • Renders only when there's real signal (the caller gates on portraitHasSignal). If
//   only one axis has any signal, it degrades to a single-axis sentence; with none it
//   returns null and nothing renders.
// ─────────────────────────────────────────────────────────────────────────────────────
import type { SelfPortraitThemeScore } from '@/lib/api'

// axis slug → one soft descriptive clause (lowercase, no trailing punctuation). Keys are
// the 8 frozen PORTRAIT_AXES slugs (services/self_portrait.py). A slug missing here just
// falls back to the axis's own label, so the sentence never renders blank.
const AXIS_PHRASE: Record<string, string> = {
  identity: 'how you see yourself',
  fear: 'what you guard against',
  freedom: 'the room you need to breathe',
  desire: 'what pulls at you',
  doubt: 'the questions you sit with',
  duty: 'what you feel you owe',
  connection: 'who you hold close',
  meaning: 'what you are reaching for',
}

function phraseFor(axis: SelfPortraitThemeScore): string {
  return AXIS_PHRASE[axis.key] ?? axis.label.toLowerCase()
}

/**
 * A calm sentence naming the top-2 axes by score (tie-break: frozen order). Returns null
 * when there's no signal (no axis with score > 0) so the caller renders nothing.
 */
export function portraitCaption(scores: SelfPortraitThemeScore[] | null | undefined): string | null {
  const axes = scores ?? []
  // Keep only axes with real signal, ranked by score desc; equal scores keep their frozen
  // (incoming) order via a stable index tie-break.
  const ranked = axes
    .map((s, i) => ({ s, i }))
    .filter((e) => e.s.score > 0)
    .sort((a, b) => (b.s.score - a.s.score) || (a.i - b.i))
    .map((e) => e.s)

  if (ranked.length === 0) return null

  const a = ranked[0]
  if (ranked.length === 1) {
    return `Your answers lean toward ${a.label} — ${phraseFor(a)}.`
  }
  const b = ranked[1]
  return `Your answers lean toward ${a.label} and ${b.label} — ${phraseFor(a)}, and ${phraseFor(b)}.`
}
