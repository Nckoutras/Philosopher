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

export default function SafetyBubble() {
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
