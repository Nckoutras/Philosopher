'use client'

import { Bookmark, SlidersHorizontal, Archive, Sparkles } from 'lucide-react'

interface Props {
  onStartConversation: () => void
}

export default function EmptyReflections({ onStartConversation }: Props) {
  return (
    <div className="bg-white border border-[0.5px] border-dashed border-edge rounded-md px-[20px] py-[24px] mx-[16px] mt-[12px]">
      {/* Top ornament — §3.26 */}
      <div className="flex items-center gap-[8px] mb-[14px]">
        <div className="flex-1 h-[0.5px] bg-edge" />
        <Sparkles size={14} strokeWidth={0.7} className="text-bronze flex-shrink-0" />
        <div className="flex-1 h-[0.5px] bg-edge" />
      </div>

      <h2 className="font-cormorant text-[19px] font-normal text-ink text-center leading-snug">
        Nothing saved yet.
      </h2>
      <p className="font-lora text-[13px] text-charcoal leading-[1.6] text-center mt-[8px]">
        When a reply lands, tap Save line below it. The line will live here.
      </p>

      <div className="border-t border-[0.5px] border-linen mt-[16px] mb-[16px]" />

      <div className="flex flex-col gap-[13px]">
        {[
          {
            Icon: Bookmark,
            label: 'Save what resonates',
            desc: 'Tap Save line below any response that lands.',
          },
          {
            Icon: SlidersHorizontal,
            label: 'Group by mind or theme',
            desc: 'Filter by who said it or what it touched.',
          },
          {
            Icon: Archive,
            label: 'Return when you need them',
            desc: 'Saved lines remain until you remove them.',
          },
        ].map(({ Icon, label, desc }) => (
          <div key={label} className="flex items-start gap-[10px]">
            <div className="w-[24px] h-[24px] border border-[0.5px] border-edge flex items-center justify-center flex-shrink-0 rounded-[2px]">
              <Icon size={12} strokeWidth={1.5} className="text-sepia" />
            </div>
            <div>
              <p className="font-lora text-[13px] font-medium text-ink leading-none">{label}</p>
              <p className="font-lora text-[12px] text-charcoal leading-[1.45] mt-[2px]">{desc}</p>
            </div>
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={onStartConversation}
        className="bg-ink text-vellum font-cormorant text-[17px] font-medium w-full py-[14px] rounded-sm mt-[16px]"
      >
        Choose a mind
      </button>
    </div>
  )
}
