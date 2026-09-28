import { useStore } from '@/lib/store'
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
 * The app-voice crisis bubble. Persona is dropped; this is never attributed to a
 * thinker.
 *
 * ONE SOURCE OF TRUTH (SAFETY-003, founder ruling 2026-09-28). The server writes
 * the crisis text in the language the person wrote in
 * (prompt_builder.build_safety_response -> prompts/safety_response*.jinja2),
 * saves it, and streams it; useStream collects it into safetyText. This renders
 * it, in every language. Until SAFETY-003 the English path rendered four
 * hardcoded paragraphs here instead, which drifted from the saved text and named
 * no helpline at all. No crisis copy is written in the web any more.
 *
 * Every approved resource in the text (988, 116 123, findahelpline.com, 112, 1018,
 * 10306) is a tappable link — see lib/crisisLinks.
 *
 * THE TEXT ARRIVES WITH THE EVENT. The server puts the whole crisis text inside
 * the 'safety' / 'safety_override' event, and useStream renders it the moment the
 * event lands, so a connection dropped before the chunks cannot leave this empty.
 * If safetyText is somehow still empty (an older server whose chunks never came),
 * this renders nothing rather than an empty bubble: there is no hardcoded fallback.
 */
export default function SafetyBubble() {
  const safetyText = useStore((s) => s.safetyText)
  const serverText = safetyText.trim()

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
        className="max-w-[80%] bg-linen text-ink font-lora text-[18px] leading-relaxed rounded-lg px-4 py-3.5 whitespace-pre-wrap"
        role="alert"
        lang={GREEK.test(serverText) ? 'el' : 'en'}
      >
        {linkifyCrisisText(serverText)}
      </div>
    </div>
  )
}
