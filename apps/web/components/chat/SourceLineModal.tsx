'use client'

import Image from 'next/image'

interface Props {
  open: boolean
  personaName: string
  personaPortraitUrl: string
  content: string
  onClose: () => void
}

export default function SourceLineModal({
  open,
  personaName,
  personaPortraitUrl,
  content,
  onClose,
}: Props) {
  if (!open) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-[rgba(31,27,20,0.5)]"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal card */}
      <div className="relative z-10 w-full max-w-[400px] bg-paper rounded-lg px-6 py-6 shadow-[0_8px_32px_rgba(31,27,20,0.18)]">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute top-4 right-4 font-lora text-[20px] text-sepia hover:text-ink transition-colors leading-none"
        >
          ×
        </button>

        <p className="font-lora text-[11px] uppercase tracking-[0.18em] text-sepia mb-3">
          Saved reflection
        </p>

        <p className="font-cormorant text-[17px] italic text-ink leading-[1.5] mb-5">
          &ldquo;{content}&rdquo;
        </p>

        <div className="flex items-center gap-2">
          {personaPortraitUrl ? (
            <Image
              src={personaPortraitUrl}
              alt={personaName}
              width={24}
              height={24}
              className="rounded-[2px] object-cover flex-shrink-0"
            />
          ) : (
            <div className="w-6 h-6 bg-linen rounded-[2px] flex-shrink-0" />
          )}
          <span className="font-lora text-[11px] text-sepia">{personaName}</span>
        </div>
      </div>
    </div>
  )
}
