// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait MAP sub-captions (PortraitMap v3). One calm, second-person line per
// theme axis, shown BELOW the theme name inside its territory on the "stable-world"
// map, and reused verbatim by the single-axis strip ("Pull — …" / "Edge — …").
//
// • FROZEN, hand-authored. Keys are the 8 frozen PORTRAIT_AXES slugs
//   (services/self_portrait.py). NO counts, NO scores, NO cross-theme claims.
// • Each line is a complete second-person sentence (capitalized, trailing period) so it
//   reads cleanly both under the territory name AND after the strip's "Pull —"/"Edge —".
// • A slug missing here falls back to the axis's own label at the call site, so nothing
//   ever renders blank.
// ─────────────────────────────────────────────────────────────────────────────

export const MAP_CAPTIONS: Record<string, string> = {
  identity: 'How you see yourself.',
  fear: 'What you guard against.',
  freedom: 'The space you need to breathe.',
  desire: 'What pulls at you.',
  doubt: 'The questions you sit with.',
  duty: 'What you feel responsible for.',
  connection: 'Who you hold close.',
  meaning: "What you're reaching for.",
}
