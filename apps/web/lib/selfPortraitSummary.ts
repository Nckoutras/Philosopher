// ─────────────────────────────────────────────────────────────────────────────────────
// Self-Portrait summary line (v2). ONE deterministic, second-person sentence that names
// the user's two strongest theme leanings — shown below the viz on screen AND on the
// share/save card. Replaces the old Pull/Edge strip everywhere it appeared.
//
// • FROZEN, hand-authored. Keys are the 8 PORTRAIT_AXES slugs (services/self_portrait.py).
//   NO LLM, NO counts, NO scores, NO cross-theme relationship claim.
// • Each essence clause is a lowercase, second-person clause (6–12 words) that reads
//   cleanly after a dash — "what this leaning means about how you move". Same calm,
//   present-tense register as the observation cards' support lines
//   (selfPortraitObservationCards.ts). No flattery, no therapy voice.
// • buildSummary derives the top-2 axes by score (tie-break = frozen incoming order) and
//   returns the single assembled sentence. Returns null when there is no signal (no axis
//   with score > 0), so the caller renders nothing.
// ─────────────────────────────────────────────────────────────────────────────────────

/** axis slug → its frozen essence clause. All 8 PORTRAIT_AXES slugs are covered. */
export const SUMMARY_CLAUSES: Readonly<Record<string, string>> = {
  identity: 'you move from a steady sense of who you are',
  fear: 'you stay alert to what could go wrong',
  freedom: 'you need room to choose your own way',
  desire: 'you follow a clear pull toward what you want',
  doubt: 'you stay with hard questions instead of rushing to close them',
  duty: 'you hold yourself to the standards you carry',
  connection: 'you keep the people you love close to your choices',
  meaning: 'you weigh things against what ultimately matters',
}

/**
 * The deterministic summary sentence for the two strongest axes. Takes the top-2 by score
 * (desc, tie-break by frozen/incoming order), and returns exactly:
 *
 *   "You lean toward {A} and {B} — {clauseA}, and {clauseB}."
 *
 * where {A}/{B} are the axes' display labels and the clauses are their frozen essence
 * clauses. The "The Wise Room says" header is NOT part of this value — it is rendered
 * separately (an on-screen <p> above this sentence, and a manual card line) so the phrase
 * never doubles up. Returns null when there is no signal (no axis with score > 0) or when
 * fewer than two axes carry a clause, so the caller renders nothing.
 */
export function buildSummary(
  scores: { key: string; label: string; score: number }[] | null | undefined,
): string | null {
  const axes = scores ?? []
  const top = axes
    .map((s, i) => ({ s, i }))
    .filter((e) => e.s.score > 0 && SUMMARY_CLAUSES[e.s.key])
    .sort((a, b) => b.s.score - a.s.score || a.i - b.i)
    .slice(0, 2)
    .map((e) => e.s)

  if (top.length < 2) return null

  const [a, b] = top
  return `You lean toward ${a.label} and ${b.label} — ${SUMMARY_CLAUSES[a.key]}, and ${SUMMARY_CLAUSES[b.key]}.`
}
