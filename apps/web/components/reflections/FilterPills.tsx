'use client'

import toast from 'react-hot-toast'

export type FilterOption = 'all' | 'by-mind' | 'by-theme'

interface PersonaOption {
  slug: string
  display_name: string
}

interface Props {
  active: FilterOption
  personas: PersonaOption[]
  selectedPersonaSlug: string | null
  onChange: (filter: FilterOption, personaSlug?: string) => void
}

export default function FilterPills({ active, personas, selectedPersonaSlug, onChange }: Props) {
  const pillBase =
    'bg-white text-ink border border-[0.5px] border-edge px-[14px] py-[6px] font-lora text-[12px] rounded-sm whitespace-nowrap flex-shrink-0'
  const pillActive =
    'bg-ink text-paper border-transparent px-[14px] py-[6px] font-lora text-[12px] rounded-sm whitespace-nowrap flex-shrink-0'

  return (
    <div className="flex flex-col gap-[8px]">
      <div className="flex gap-[6px] overflow-x-auto pb-[2px] px-[16px]">
        <button
          type="button"
          onClick={() => onChange('all')}
          className={active === 'all' ? pillActive : pillBase}
        >
          All
        </button>
        <button
          type="button"
          onClick={() => onChange('by-mind')}
          className={active === 'by-mind' ? pillActive : pillBase}
        >
          By mind
        </button>
        <button
          type="button"
          onClick={() => toast('Coming soon', { duration: 2000 })}
          className={`${pillBase} opacity-50`}
          aria-label="By theme (coming soon)"
        >
          By theme
        </button>
      </div>
      {active === 'by-mind' && personas.length > 0 && (
        <div className="flex gap-[6px] overflow-x-auto pb-[2px] px-[16px]">
          {personas.map((p) => (
            <button
              key={p.slug}
              type="button"
              onClick={() => onChange('by-mind', p.slug)}
              className={selectedPersonaSlug === p.slug ? pillActive : pillBase}
            >
              {p.display_name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
