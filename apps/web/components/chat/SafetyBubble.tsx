import { useStore } from '@/lib/store'

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
// counts server-side. Deliberately a script test, not a language detector: the
// only question here is "did the server send Greek copy", and the server already
// made the language decision.
const GREEK = /[\u0370-\u03FF\u1F00-\u1FFF]/

/**
 * The app-voice crisis bubble. Persona is dropped; this is never attributed to a
 * thinker.
 *
 * WHAT THIS FIXES. The server builds the crisis response in the language the user
 * wrote in (prompt_builder.build_safety_response -> safety_response_el.jinja2 for
 * Greek), saves it, and streams it. This component used to ignore all of that and
 * render four hardcoded ENGLISH paragraphs, so a Greek speaker in crisis got the
 * English bubble in the moment and only ever saw the Greek text if they reloaded.
 * That is the exact failure the Greek template was written to prevent.
 *
 * WHY GREEK ONLY SWITCHES. When the streamed text is Greek we render it, because
 * the alternative is demonstrably the wrong language. When it is not, we keep the
 * English paragraphs below verbatim: they are founder-locked and say MORE than the
 * English template does (immediate danger, and the not-a-crisis-service line). So
 * this change cannot alter what an English speaker sees. Collapsing the two onto
 * one source of truth needs a copy lock on the fuller English text and is its own PR.
 */
export default function SafetyBubble() {
  const safetyText = useStore((s) => s.safetyText)
  const serverText = safetyText.trim()

  if (serverText && GREEK.test(serverText)) {
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
        {/* whitespace-pre-wrap: the template's paragraph break is a real newline,
            and there is no markdown renderer in this bubble. */}
        <div
          className="max-w-[80%] bg-linen text-ink font-lora text-[18px] leading-relaxed rounded-lg px-4 py-3.5 whitespace-pre-wrap"
          role="alert"
          lang="el"
        >
          {serverText}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1">
      {/* Eyebrow + avatar row */}
      <div className="flex items-center gap-2">
        <LozengePip />
        <span
          className="font-lora text-[9px] text-sepia uppercase tracking-[0.18em]"
          aria-label="The Wise Room app voice"
        >
          The Wise Room
        </span>
      </div>

      {/* Safety bubble */}
      <div
        className="max-w-[80%] bg-linen text-ink font-lora text-[18px] leading-relaxed rounded-lg px-4 py-3.5"
        role="alert"
      >
        <p className="mb-3">
          Some of what you&apos;ve shared sounds heavy. I want to make sure you&apos;re safe right now.
        </p>
        <p className="mb-3 font-medium">
          If you may be in immediate danger, please contact local emergency services or a crisis support line now.
        </p>
        <p className="mb-3">
          If you can, reach out to a trusted person near you or a qualified mental health professional.
        </p>
        <p>
          The Wise Room can offer reflection, but it cannot provide crisis support, diagnosis, or medical treatment.
        </p>
      </div>
    </div>
  )
}
