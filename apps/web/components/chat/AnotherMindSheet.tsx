'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { api, type Persona } from '@/lib/api'
import BottomSheet from '@/components/ui/BottomSheet'

interface Props {
  open: boolean
  onClose: () => void
  excludeSlugs: string[]
  onSelect: (slug: string) => void
}

export default function AnotherMindSheet({ open, onClose, excludeSlugs, onSelect }: Props) {
  const router = useRouter()
  const [personas, setPersonas] = useState<Persona[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!open || personas !== null) return
    api.getPersonas()
      .then(setPersonas)
      .catch(() => { setPersonas([]); setError(true) })
  }, [open, personas])

  useEffect(() => {
    if (!open) setError(false)
  }, [open])

  const filtered = personas?.filter((p) => !excludeSlugs.includes(p.slug)) ?? []

  return (
    <BottomSheet open={open} onClose={onClose}>
      <div className="px-6 pt-5 pb-3 border-b border-[0.5px] border-edge flex-shrink-0">
        <p className="font-cormorant text-[19px] font-medium text-ink">Bring another mind</p>
        <p className="font-lora text-[12px] text-charcoal mt-[2px]">
          Choose who should look at this from another angle.
        </p>
      </div>

      <div className="overflow-y-auto flex-1 px-5 py-4 space-y-2">
        {personas === null ? (
          <p className="font-lora text-[13px] text-sepia italic text-center py-8">Loading…</p>
        ) : error || filtered.length === 0 ? (
          <p className="font-lora text-[13px] text-charcoal text-center py-8">
            No other minds available.
          </p>
        ) : (
          filtered.map((p) => (
            <button
              key={p.slug}
              type="button"
              onClick={() => {
                if (p.is_accessible) {
                  onSelect(p.slug)
                } else {
                  router.push('/app/upgrade')
                }
              }}
              className="w-full text-left p-3 rounded-md border-[0.5px] border-edge bg-linen
                         flex items-center gap-3 transition-colors active:bg-linen-deep"
            >
              <div className="w-10 h-10 rounded-full overflow-hidden bg-linen-deep flex-shrink-0">
                {p.portrait_url && (
                  <Image
                    src={p.portrait_url}
                    alt={p.name}
                    width={40}
                    height={40}
                    className="w-full h-full object-cover object-top"
                  />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-cormorant text-[17px] font-medium text-ink leading-tight">
                  {p.name}
                </p>
                {p.tagline && (
                  <p className="font-lora text-[12px] text-charcoal leading-[1.45] truncate">
                    {p.tagline}
                  </p>
                )}
              </div>
              {p.tier !== 'free' && (
                <span className="font-lora text-[10px] uppercase tracking-[0.18em] text-bronze flex-shrink-0">
                  🔒 {p.tier}
                </span>
              )}
            </button>
          ))
        )}
      </div>
    </BottomSheet>
  )
}
