'use client'

import Image from 'next/image'
import { useRouter } from 'next/navigation'
import type { Persona } from '@/lib/api'

interface Props {
  personas: Persona[] | null
  loading: boolean
}

export default function BrowseMindsView({ personas, loading }: Props) {
  const router = useRouter()

  if (loading && personas === null) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="font-lora text-[13px] text-sepia italic">Loading…</p>
      </div>
    )
  }

  if (!personas || personas.length === 0) {
    return (
      <div className="flex items-center justify-center py-16 px-7 text-center">
        <p className="font-lora text-[13px] text-charcoal">No minds available.</p>
      </div>
    )
  }

  return (
    <div className="px-5 pt-2 pb-[80px] space-y-2">
      {personas.map((p) => (
        <button
          key={p.slug}
          type="button"
          onClick={() => router.push(`/app/persona/${p.slug}`)}
          className="w-full text-left p-4 rounded-md border-[0.5px] bg-paper border-edge flex items-center gap-4 transition-colors active:bg-linen"
        >
          <div className="w-14 h-14 rounded-full overflow-hidden bg-linen-deep flex-shrink-0">
            {p.portrait_url && (
              <Image
                src={p.portrait_url}
                alt={p.name}
                width={56}
                height={56}
                className="w-full h-full object-cover object-top"
              />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-cormorant text-[20px] font-medium text-ink leading-tight mb-1">
              {p.name}
            </p>
            {p.tagline && (
              <p className="font-lora text-[12px] text-charcoal leading-[1.45]">{p.tagline}</p>
            )}
          </div>
          {p.tier !== 'free' && (
            <span className="font-lora text-[10px] uppercase tracking-[0.18em] text-bronze flex-shrink-0">
              🔒 {p.tier}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}
