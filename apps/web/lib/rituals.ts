import type { UpgradeSource } from './upgradeCopy'

/**
 * `entry`, `pro` and `source` exist so the ritual detail page can offer ONE
 * state-aware action instead of being a page that explains a thing and then
 * leaves the reader on it (BUG-018). Data rather than a switch statement in the
 * component: six rituals, six rows, and a seventh cannot be added without
 * deciding what its button does.
 *
 * `pro` MIRRORS THE SERVER, and each value was read off the router rather than
 * assumed -- the gate is the API's, and this field only decides which button a
 * reader sees first:
 *   mirror       free to view. routers/mirrors.py gates only /share; /latest,
 *                which is what the page reads, is open to every tier.
 *   council      routers/council.py — plan not in (pro, premium) -> 403.
 *   you-vs-you   routers/self_comparison.py — same shape, admin bypass.
 *   sunday-letter routers/weekly_letters.py — same shape.
 *   counterview  free, metered at 2/day (rate_limit_service.FREE_DAILY_
 *                COUNTERVIEW_LIMIT). The wall is inside the ritual, not on the
 *                door, so the door opens.
 *   future-self  routers/scheduled_emails.py — `tier == "free"` rather than the
 *                `plan not in (...)` idiom every other router uses, which is why
 *                a first grep for the house pattern found nothing here.
 *
 * `source` is required exactly when `pro` is true: it is the identifier the
 * paywall reads for its line and the one PostHog and Stripe split on. A gated
 * ritual without its own source is the BUG-004 defect, so the type says so.
 */
export type RitualMeta =
  | { slug: string; name: string; src: string; entry: string; pro: false }
  | { slug: string; name: string; src: string; entry: string; pro: true; source: UpgradeSource }

export const RITUALS: RitualMeta[] = [
  { slug: 'mirror',        name: 'The Mirror',                    src: '/personas/mirror.webp',                   entry: '/app/mirror',                    pro: false },
  { slug: 'council',       name: 'The Council',                   src: '/personas/boardroom.webp',                entry: '/app/council',                   pro: true,  source: 'council' },
  { slug: 'you-vs-you',    name: 'You vs You',                    src: '/personas/youvsyou.webp',                 entry: '/app/you-vs-you',                pro: true,  source: 'you_vs_you' },
  { slug: 'sunday-letter', name: 'The Sunday Letter',             src: '/personas/sundayletter.webp',             entry: '/app/letters',                   pro: true,  source: 'letter' },
  { slug: 'counterview',   name: 'The Counterview',               src: '/personas/thecounterview.webp',           entry: '/app/counterview',               pro: false },
  // The deep link the rituals tab already honours: ?open=future-self opens the
  // schedule sheet once, Pro-guarded (app/app/(tabs)/rituals/page.tsx). Reused
  // rather than duplicating that sheet behind a second door.
  { slug: 'future-self',   name: 'A Message to Your Future Self',  src: '/personas/messagetomyfutureself.webp',    entry: '/app/rituals?open=future-self',  pro: true,  source: 'future_self' },
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
  // REPLACED 2026-09-17, founder-locked. The previous four fields described a
  // feature this product does not have: "Set down ... who you want to become
  // ... It isn't sent anywhere; the room keeps it as your stated direction."
  // The shipped ritual asks for a saved line, a note, a prediction and a DATE,
  // and workers/cron.py's send_pending_future_self_emails delivers it by email
  // every five minutes. The rituals-tab card ("Seal a thought now. Let it find
  // you changed.") always described the real thing; this page did not, and
  // BUG-018 put a button under it.
  'future-self': {
    tagline: 'A letter only time can deliver.',
    body: 'Write to yourself as you’ll be months from now — what you’re carrying, what you hope will have shifted. You choose the date. The room holds it until then, and sends it.',
    onItsOwn: 'Write one, choose its date, and let it go.',
    overTime: 'Several become a correspondence with your own past.' },
}
