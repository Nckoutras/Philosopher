export interface RitualMeta { slug: string; name: string; src: string }

export const RITUALS: RitualMeta[] = [
  { slug: 'mirror',        name: 'The Mirror',                    src: '/personas/mirror.webp' },
  { slug: 'council',       name: 'The Council',                   src: '/personas/boardroom.webp' },
  { slug: 'you-vs-you',    name: 'You vs You',                    src: '/personas/youvsyou.webp' },
  { slug: 'sunday-letter', name: 'The Sunday Letter',             src: '/personas/sundayletter.webp' },
  { slug: 'counterview',   name: 'The Counterview',               src: '/personas/thecounterview.png' },
  { slug: 'future-self',   name: 'A Message to Your Future Self',  src: '/personas/messagetomyfutureself.png' },
]

export interface RitualInfo { tagline: string; body: string; onItsOwn: string; overTime: string }

export const RITUAL_INFO: Record<string, RitualInfo> = {
  'mirror': {
    tagline: 'Your week, read back to you.',
    body: 'Once a week, the room holds a mirror to your conversations — not advice, but a reflection of what you said, in the voice of the mind you spent the week with, so you can hear your own thinking from the outside.',
    onItsOwn: 'Seed one any time from an insight you want to sit with.',
    overTime: 'Each weekly Mirror builds on the last, tracing how your thinking shifts.' },
  'council': {
    tagline: 'One matter, four minds.',
    body: 'Bring a single question to a fixed table of thinkers. Each gives a short reading from its own school, then the room draws the through-line across all four.',
    onItsOwn: 'Pose anything that deserves more than one perspective.',
    overTime: 'The matters you keep bringing reveal what truly occupies you.' },
  'you-vs-you': {
    tagline: 'Who you were, who you are.',
    body: 'The room holds two versions of you in the same frame — the one who first raised something, and the one reading now — and shows you what moved between them.',
    onItsOwn: 'Revisit a belief and see how it has changed.',
    overTime: 'It surfaces the shifts you’d never catch day to day.' },
  'sunday-letter': {
    tagline: 'A letter, every Sunday.',
    body: 'Each week the room writes you a letter — not a summary, a letter: the themes it noticed, the questions you left open, one line worth keeping.',
    onItsOwn: 'Read it when it arrives, or any time from your readings.',
    overTime: 'The letters become a record of where your attention has been.' },
  'counterview': {
    tagline: 'The case against.',
    body: 'Take a belief you hold and let two sharp minds argue the case against it — not to wound, but to test whether it holds. Two readings side by side, attacking the idea, never you.',
    onItsOwn: 'Type any conviction and put it under pressure.',
    overTime: 'The room flags the beliefs you lean on, and offers to doubt them with you.' },
  'future-self': {
    tagline: 'Who you are, who you want to become.',
    body: 'Set down, in your own words, who you are now — who you want to become, and what you want to bring about. It isn’t sent anywhere; the room keeps it as your stated direction.',
    onItsOwn: 'Make one clear declaration of intent.',
    overTime: 'It feeds your Sunday and monthly readings — the room measures your weeks against the person you said you wanted to be.' },
}
