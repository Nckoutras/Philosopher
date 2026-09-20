'use client'

import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

import { api, type ShareListItem } from '@/lib/api'
import DeleteConfirmModal from '@/components/ui/DeleteConfirmModal'

// "Your links" — the surface that makes revocation real.
//
// WHY THIS EXISTS AT ALL. The API could revoke before this shipped, and the
// withdrawn page could render, but nothing in the product could reach either:
// a share's id is known to the client only in the moment its card is returned,
// so a person could turn a link off during that one modal and never again.
// Revocation would have been true of the code and false of the product, which
// is the same lie as a revocation that does not revoke.
//
// NO VIEW COUNTS, AND THE ABSENCE IS A RULING. This is an inventory, not a
// dashboard. Nothing here says who opened a link or how often.
//
// REVOKED ROWS STAY, MUTED AND ACTIONLESS. Seeing that you turned it off IS the
// confirmation that you did; a list that silently dropped them would leave a
// person wondering whether the tap registered — the exact uncertainty this
// screen exists to remove.

const TYPE_LABELS: Record<ShareListItem['artifact_type'], string> = {
  line: 'Reflection',
  quote: 'Quote',
  council: 'Council',
  mirror: 'Mirror',
  letter: 'Letter',
  counterview: 'Counterview',
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
}

/** The card's printed form: bare host and path, no scheme. Mirrors the server's
 *  _share_stamp_text so what a person reads here is what is on the card. */
function shortUrl(url: string): string {
  return url.split('://', 2).pop() ?? url
}

export default function YourLinks() {
  const [items, setItems] = useState<ShareListItem[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [pending, setPending] = useState<ShareListItem | null>(null)
  const [revoking, setRevoking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .listMyShares()
      .then((rows) => {
        if (!cancelled) setItems(rows)
      })
      .catch(() => {
        if (!cancelled) {
          setItems([])
          setFailed(true)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleConfirm() {
    if (!pending) return
    setRevoking(true)
    setError(null)
    try {
      await api.revokeShare(pending.public_id)
      // Update in place rather than refetching: the row must STAY, muted. A
      // refetch would do the same thing more slowly, and a filter would remove
      // the confirmation the person just asked for.
      setItems((rows) =>
        (rows ?? []).map((r) =>
          r.public_id === pending.public_id ? { ...r, revoked: true } : r,
        ),
      )
      setPending(null)
      toast('Link turned off.')
    } catch {
      setError('Could not turn the link off. Try again.')
    } finally {
      setRevoking(false)
    }
  }

  return (
    <div className="bg-paper border border-bronze/70 rounded-md overflow-hidden">
      <div className="px-[16px] pt-[14px] pb-[2px]">
        <p className="font-lora text-[12px] uppercase tracking-[0.18em] text-charcoal">
          Your links
        </p>
      </div>

      {items === null ? (
        <p className="px-[16px] py-[14px] font-lora text-[14px] text-sepia italic">
          Loading…
        </p>
      ) : items.length === 0 ? (
        <div className="px-[16px] py-[14px]">
          <p className="font-cormorant text-[17px] font-medium text-ink">
            {failed ? 'This isn’t loading right now.' : 'No links yet.'}
          </p>
          <p className="mt-[2px] font-lora text-[13px] text-charcoal leading-relaxed">
            {failed
              ? 'Something on our side. Try again in a moment.'
              : 'When you share a reflection, the link will appear here.'}
          </p>
        </div>
      ) : (
        <ul>
          {items.map((row) => (
            <li
              key={row.public_id}
              className="px-[16px] py-[14px] border-t border-[0.5px] border-edge first:border-t-0"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p
                    className={`font-cormorant text-[17px] font-medium ${
                      row.revoked ? 'text-sepia' : 'text-ink'
                    }`}
                  >
                    {TYPE_LABELS[row.artifact_type] ?? row.artifact_type}
                  </p>
                  <p
                    className={`mt-[2px] font-lora text-[12px] truncate ${
                      row.revoked ? 'text-sepia/70 line-through' : 'text-charcoal'
                    }`}
                  >
                    {shortUrl(row.url)}
                  </p>
                  <p className="mt-[2px] font-lora text-[11px] text-sepia">
                    {formatDate(row.created_at)}
                    {row.revoked && ' · Turned off'}
                  </p>
                </div>

                {/* No action on a revoked row. There is nothing left to do to it,
                    and an inert-looking button that does nothing is worse than
                    none at all. */}
                {!row.revoked && (
                  <button
                    type="button"
                    onClick={() => setPending(row)}
                    className="flex-shrink-0 font-lora text-[12px] text-bronze-dark underline underline-offset-2"
                  >
                    Turn off this link
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* The confirm dialog. Its body is the one piece of copy in this feature
          that carries the whole truth about what revocation can and cannot do —
          it must never be shortened into a claim that the card is recalled. */}
      <DeleteConfirmModal
        open={pending !== null}
        title="Turn off this link?"
        body={
          'Anyone who opens it will see that it was withdrawn. ' +
          'The card itself may already have been saved or forwarded — ' +
          'turning off the link does not recall it.'
        }
        confirmLabel="Turn it off"
        cancelLabel="Keep it on"
        loading={revoking}
        error={error}
        onConfirm={handleConfirm}
        onClose={() => {
          if (revoking) return
          setPending(null)
          setError(null)
        }}
      />
    </div>
  )
}
