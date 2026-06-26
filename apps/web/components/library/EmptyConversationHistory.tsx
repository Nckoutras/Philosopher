'use client'

import { useRouter } from 'next/navigation'

export default function EmptyConversationHistory() {
  const router = useRouter()

  return (
    <div className="mx-4 mt-3 bg-paper border border-[0.5px] border-edge rounded-md p-5">
      {/* Bronze star ornament row */}
      <div className="flex items-center gap-0 mb-4">
        <div className="flex-1 h-px bg-edge" />
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          className="mx-3 text-bronze"
          aria-hidden="true"
        >
          <path
            d="M7 1L8.39 5.26H13L9.3 7.74L10.69 12L7 9.52L3.31 12L4.7 7.74L1 5.26H5.61L7 1Z"
            stroke="currentColor"
            strokeWidth="0.7"
            strokeLinejoin="round"
          />
        </svg>
        <div className="flex-1 h-px bg-edge" />
      </div>

      {/* Headline */}
      <p className="font-cormorant text-[19px] font-normal text-ink text-center leading-snug mb-2">
        Past conversations gather here.
      </p>

      {/* Body */}
      <p className="font-lora text-[13px] text-charcoal text-center leading-[1.6] mb-4">
        Every conversation you start is saved here. Return to any of them when you need to.
      </p>

      {/* Top divider */}
      <div className="h-px bg-linen mb-4" />

      {/* 3-item instruction list */}
      <div className="flex flex-col gap-3 mb-5">
        <InstructionRow
          label="Saved automatically"
          description="No need to save conversations manually."
        />
        <InstructionRow
          label="Resume where you left off"
          description="Tap any card to return to the exact place."
        />
        <InstructionRow
          label="Organized by recency"
          description="Grouped by week, with the most recent at the top."
        />
      </div>

      {/* CTA */}
      <button
        type="button"
        onClick={() => router.push('/app/library?mode=browse')}
        className="w-full bg-ink text-vellum font-cormorant text-[17px] font-medium rounded-sm py-[14px] text-center"
      >
        Explore minds
      </button>
    </div>
  )
}

function InstructionRow({ label, description }: { label: string; description: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-6 h-6 flex-shrink-0 border border-[0.5px] border-edge rounded-sm flex items-center justify-center">
        <div className="w-2 h-2 rounded-full bg-sepia/40" />
      </div>
      <div>
        <span className="font-lora text-[13px] font-medium text-ink">{label}</span>
        <span className="font-lora text-[12px] text-charcoal leading-[1.45]"> {description}</span>
      </div>
    </div>
  )
}
