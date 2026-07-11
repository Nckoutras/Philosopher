import type { Quote } from '@/lib/api'

// The 5 founder-approved opening lines — FROZEN, verbatim. Do NOT alter
// punctuation, casing, or quotes. `{quote}` is replaced with the quote's text_en.
const TEMPLATES = [
  'Something you said stays with me: "{quote}". I want to understand it better.',
  'You once said: "{quote}". I\'m not sure how it applies to my life — can we talk it through?',
  'You said "{quote}". Part of me resists it. Help me see what I\'m missing.',
  'This line of yours keeps returning to me: "{quote}". Where would you begin?',
  'I keep thinking about this: "{quote}". What did you really mean by it?',
] as const

// Deterministic: the variant is seeded from the STABLE quote UUID (not the shuffled
// carousel position), so the same quote.id ALWAYS yields the same opening line.
export function openingFor(quote: Quote): string {
  const variant = [...quote.id].reduce((s, c) => s + c.charCodeAt(0), 0) % 5
  return TEMPLATES[variant].replace('{quote}', quote.text_en)
}
