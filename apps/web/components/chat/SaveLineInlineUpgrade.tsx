'use client'

import { useStore } from '@/lib/store'

interface Props {
  onUpgrade: () => void
  onDismiss: () => void
}

export default function SaveLineInlineUpgrade({ onUpgrade, onDismiss }: Props) {
  const freeSaveCount = useStore((s) => s.freeSaveCount)
  const freeTierLimit = useStore((s) => s.freeTierLimit) ?? 3

  return (
    <div className="ml-[32px] mt-[4px] bg-paper border border-[0.5px] border-edge rounded-sm px-[12px] py-[10px]">
      <p className="font-cormorant text-[17px] font-medium text-ink leading-tight">
        You&apos;ve reached your free reflections ({freeSaveCount} of {freeTierLimit}).
      </p>
      <p className="font-lora text-[13px] text-charcoal leading-[1.55] mt-[6px]">
        Upgrade to Pro to keep saving.
      </p>
      <div className="flex items-center gap-[12px] mt-[12px]">
        <button
          type="button"
          onClick={onUpgrade}
          className="flex-1 bg-ink text-vellum font-cormorant text-[17px] font-medium py-[10px] rounded-sm"
        >
          Continue with Pro
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="font-lora text-[12px] text-charcoal underline underline-offset-2 shrink-0 whitespace-nowrap"
        >
          Maybe later
        </button>
      </div>
    </div>
  )
}
