'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { track } from '@/lib/analytics'
import { api, type Persona, type Conversation } from '@/lib/api'
import BottomSheet from '@/components/ui/BottomSheet'
import { isPersonaLockedError, lockedPersonaUpgradeHref } from '@/lib/personaLock'

interface Props {
  open: boolean
  excludeSlug?: string
  savedLineId?: string
  sourceContent?: string
  revisitLetterId?: string
  onClose: () => void
  onCreated?: (conversationId: string) => void
  onSelect?: (slug: string) => void
}

export default function PersonaPickerSheet({
  open,
  excludeSlug,
  savedLineId,
  sourceContent,
  revisitLetterId,
  onClose,
  onCreated,
  onSelect,
}: Props) {
  const router = useRouter()
  const [personas, setPersonas] = useState<Persona[] | null>(null)
  const [loadingSlug, setLoadingSlug] = useState<string | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!open || personas !== null) return
    api.getPersonas()
      .then(setPersonas)
      .catch(() => { setPersonas([]); setError(true) })
  }, [open, personas])

  useEffect(() => {
    if (!open) {
      setLoadingSlug(null)
      setError(false)
    }
  }, [open])

  async function handleSelect(persona: Persona) {
    if (loadingSlug) return
    const slug = persona.slug

    // A locked mind is a conversion moment, not an error. Gate on `is_accessible`
    // — the server's entitlement answer — and NOT on `tier !== 'free'`, which is
    // only the badge: a Pro subscriber has is_accessible true on a Pro mind and
    // must open it normally. Routing before the API call also means the free user
    // never waits on a request that exists to refuse them. Same destination and
    // same event as AnotherMindSheet, which had this wired already.
    if (!persona.is_accessible) {
      track('upgrade_clicked', { surface: 'persona_locked', reason: 'persona_locked' })
      onClose()
      router.push(lockedPersonaUpgradeHref(slug))
      return
    }

    if (onSelect) {
      onSelect(slug)
      onClose()
      return
    }
    setLoadingSlug(slug)
    // Close the sheet BEFORE navigating. BottomSheet pops its own history entry
    // via history.back() on close; if we navigate first, that back() reverts the
    // pushed route. Closing first lets back() settle before the post-await push.
    onClose()
    try {
      let conv: Conversation
      if (revisitLetterId) {
        conv = await api.createReadingRevisit(revisitLetterId, slug)
      } else {
        conv = await api.createCrossPersonaConversation(savedLineId!, slug)
        if (sourceContent) {
          localStorage.setItem(`cross_persona_draft_${conv.id}`, sourceContent)
        }
      }
      onCreated!(conv.id)
    } catch (err) {
      // Fallback for a race: the list said accessible, the server disagreed (tier
      // changed under a loaded sheet). Still the paywall, never a toast quoting the
      // refusal — which is where the raw slug came from.
      if (isPersonaLockedError(err)) {
        track('upgrade_clicked', { surface: 'persona_locked', reason: 'persona_locked' })
        router.push(lockedPersonaUpgradeHref(slug))
        return
      }
      toast.error('Could not open conversation. Try again.')
      // eslint-disable-next-line no-console
      console.error('persona picker create failed:', err)
    }
  }

  const filtered = personas?.filter((p) => p.slug !== excludeSlug) ?? []

  return (
    <BottomSheet open={open} onClose={onClose}>
      {/* Header */}
      <div className="px-6 pt-5 pb-3 border-b border-[0.5px] border-edge flex items-center justify-between flex-shrink-0">
        <p className="font-cormorant text-[19px] font-medium text-ink">Choose a mind</p>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="p-2 font-lora text-[22px] text-sepia leading-none"
        >
          ×
        </button>
      </div>

      {/* Persona list */}
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
              onClick={() => handleSelect(p)}
              disabled={loadingSlug !== null}
              className="w-full text-left p-3 rounded-md border-[0.5px] border-edge bg-linen
                         flex items-center gap-3 transition-colors active:bg-linen-deep
                         disabled:opacity-50"
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
                  {loadingSlug === p.slug ? 'Opening…' : p.name}
                </p>
                {p.tagline && (
                  <p className="font-lora text-[12px] text-charcoal leading-[1.45] truncate">
                    {p.tagline}
                  </p>
                )}
              </div>
              {p.tier !== 'free' && (
                <span className="font-lora text-[12px] uppercase tracking-[0.18em] text-bronze flex-shrink-0">
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
