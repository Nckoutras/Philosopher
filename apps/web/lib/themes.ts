// Canonical lowercase theme slugs — single source of truth for the
// onboarding/themes screen and the Today consolidated card.
// Slugs mirror the backend Pydantic enum; do not edit without updating it.
export const THEME_OPTIONS: { slug: string; label: string }[] = [
  { slug: 'separation', label: 'Separation' },
  { slug: 'anxiety', label: 'Anxiety' },
  { slug: 'fear', label: 'Fear' },
  { slug: 'grief', label: 'Grief' },
  { slug: 'acceptance', label: 'Acceptance' },
  { slug: 'work', label: 'Work' },
  { slug: 'relationships', label: 'Relationships' },
  { slug: 'purpose', label: 'Purpose' },
  { slug: 'dilemma', label: 'Dilemma' },
  { slug: 'controversy', label: 'Controversy' },
  { slug: 'doubt', label: 'Doubt' },
  { slug: 'freedom', label: 'Freedom' },
]
