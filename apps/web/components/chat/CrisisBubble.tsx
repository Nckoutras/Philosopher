import { linkifyCrisisText } from '@/lib/crisisLinks'

// Bronze lozenge avatar — 24×24 circle (Vellum bg, Edge border) with Bronze diamond inside
function LozengePip() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="11.5" fill="#EFE3CC" stroke="#D4C8B0" />
      <polygon points="12,6 18,12 12,18 6,12" fill="#B89968" />
    </svg>
  )
}

// Greek + Greek Extended, the same codepoint ranges text_utils.dominant_language
// counts server-side. Only used to set lang= for screen readers: the server has
// already made the language decision.
const GREEK = /[\u0370-\u03FF\u1F00-\u1FFF]/

/**
 * The app-voice crisis bubble, as every surface shows it: chat (via SafetyBubble),
 * Council and You-vs-You (SAFETY-003 part 2). Persona is dropped; this is never
 * attributed to a thinker.
 *
 * `text` is the server's crisis text, written in the language the person wrote in
 * (prompts/safety_response*.jinja2) and carried on the safety event itself. No
 * crisis copy is written in the web. Every approved resource in it (988, 116 123,
 * findahelpline.com, 112, 1018, 10306) is a tappable link — see lib/crisisLinks.
 *
 * Empty text renders NOTHING rather than an empty bubble: there is no hardcoded
 * fallback, by ruling.
 */
export default function CrisisBubble({ text }: { text: string }) {
  const serverText = text.trim()
  if (!serverText) return null

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <LozengePip />
        <span
          className="font-lora text-[9px] text-sepia uppercase tracking-[0.18em]"
          aria-label="The Wise Room app voice"
        >
          The Wise Room
        </span>
      </div>
      {/* whitespace-pre-wrap: the template's paragraph breaks are real newlines,
          and there is no markdown renderer in this bubble. */}
      <div
        className="max-w-[80%] bg-linen text-ink font-lora text-[18px] leading-relaxed rounded-lg px-4 py-3.5 whitespace-pre-wrap text-left"
        role="alert"
        lang={GREEK.test(serverText) ? 'el' : 'en'}
      >
        {linkifyCrisisText(serverText)}
      </div>
    </div>
  )
}
