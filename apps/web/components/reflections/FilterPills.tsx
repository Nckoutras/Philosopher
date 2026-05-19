'use client'

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
    'bg-paper text-ink border border-[0.5px] border-edge px-[14px] py-[6px] font-lora text-[12px] rounded-[4px] whitespace-nowrap flex-shrink-0'
  const pillActive =
    'bg-linen-deep text-ink border border-ink px-[14px] py-[6px] font-lora text-[12px] font-medium rounded-[4px] whitespace-nowrap flex-shrink-0'

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
          disabled
          className={`${pillBase} opacity-[0.75] cursor-default`}
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
