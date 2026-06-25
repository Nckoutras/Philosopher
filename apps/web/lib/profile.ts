// Canonical profile pill slugs — single source of truth for the onboarding
// profile step and the /app/profile editor. Slugs mirror the backend
// schemas.ProfileIn Literals; do not edit without updating it.

export const VALUE_OPTIONS: { slug: string; label: string }[] = [
  { slug: 'honesty', label: 'Honesty' },
  { slug: 'freedom', label: 'Freedom' },
  { slug: 'loyalty', label: 'Loyalty' },
  { slug: 'justice', label: 'Justice' },
  { slug: 'growth', label: 'Growth' },
  { slug: 'security', label: 'Security' },
  { slug: 'connection', label: 'Connection' },
  { slug: 'achievement', label: 'Achievement' },
]

export const MAX_VALUES = 3

export const DISAGREEMENT_OPTIONS: { slug: string; label: string }[] = [
  { slug: 'stand_firm', label: 'Stand firm in my position' },
  { slug: 'seek_the_middle', label: 'Look for the middle ground' },
  { slug: 'avoid_conflict', label: 'Step back from the conflict' },
  { slug: 'probe_their_view', label: "Probe the other person's view" },
  { slug: 'heat_then_reflect', label: 'React with heat, then reflect' },
]
