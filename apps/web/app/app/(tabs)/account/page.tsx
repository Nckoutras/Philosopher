'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'
import { signOut } from '@/lib/auth'
import AppHeader from '@/components/layout/AppHeader'
import Switch from '@/components/ui/Switch'
import DeleteConfirmModal from '@/components/ui/DeleteConfirmModal'
import { DELETE_ACCOUNT_COPY } from '@/lib/accountDeletionCopy'
import { DATA_EXPORT_COPY, exportFilename } from '@/lib/dataExportCopy'
import {
  getConsent,
  setConsent,
  initAnalytics,
  optOutAnalytics,
  track,
} from '@/lib/analytics'

function useHydrated() {
  const [hydrated, setHydrated] = useState(false)
  useEffect(() => {
    if (useStore.persist.hasHydrated()) {
      setHydrated(true)
      return
    }
    const unsub = useStore.persist.onFinishHydration(() => setHydrated(true))
    void useStore.persist.rehydrate()
    return unsub
  }, [])
  return hydrated
}

export default function AccountPage() {
  const router = useRouter()
  const token = useStore((s) => s.token)
  const user = useStore((s) => s.user)
  const storeSubscription = useStore((s) => s.subscription)
  const setSubscription = useStore((s) => s.setSubscription)

  const hydrated = useHydrated()
  const [portalLoading, setPortalLoading] = useState(false)
  // Read in an effect, not in the initializer: localStorage does not exist
  // during SSR, and the toggle must reflect the stored choice rather than a
  // default. Until it resolves the row renders in its stored-off position.
  const [analyticsOn, setAnalyticsOn] = useState(false)

  useEffect(() => {
    setAnalyticsOn(getConsent() === 'granted')
  }, [])

  useEffect(() => {
    if (!hydrated) return
    if (token === null) {
      router.replace('/auth?mode=signin')
      return
    }
    if (!storeSubscription) {
      api.getSubscription().then(setSubscription).catch(() => {})
    }
    // Show success toast when returning from Stripe Checkout
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      if (params.get('checkout') === 'success') {
        toast.success('Welcome to Pro.')
        api.getSubscription().then(setSubscription).catch(() => {})
        // Remove the query param without a full reload
        window.history.replaceState({}, '', window.location.pathname)
      }
    }
  }, [hydrated, token, router, storeSubscription, setSubscription])

  const displayName = user?.full_name ?? user?.email ?? ''
  const initial = displayName.charAt(0).toUpperCase()
  const plan = storeSubscription
    ? ['active', 'trialing'].includes(storeSubscription.status) && storeSubscription.plan !== 'free'
      ? storeSubscription.plan.charAt(0).toUpperCase() + storeSubscription.plan.slice(1)
      : 'Free'
    : 'Free'

  async function handleSubscriptionTap() {
    if (plan === 'Free') {
      // A deliberate CTA: the user tapped the subscription row to change plan.
      track('upgrade_clicked', { surface: 'account', reason: 'none' })
      router.push('/app/upgrade?source=account')
      return
    }
    setPortalLoading(true)
    try {
      const { portal_url } = await api.getPortalUrl()
      window.open(portal_url, '_blank', 'noopener,noreferrer')
    } catch {
      toast.error('Could not open subscription portal. Try again.')
    } finally {
      setPortalLoading(false)
    }
  }

  function handleAnalyticsToggle(next: boolean) {
    setAnalyticsOn(next)
    setConsent(next ? 'granted' : 'denied')
    // Withdrawal is immediate and local: opt_out_capturing() stops the SDK and
    // drops its cookie in this browser. It does not delete events already sent
    // — that is an erasure request, which §7 (Your Rights) of the policy covers.
    if (next) void initAnalytics()
    else optOutAnalytics()
  }

  // ── Data export ───────────────────────────────────────────────────────────
  const [exportLoading, setExportLoading] = useState(false)

  async function handleExport() {
    if (exportLoading) return
    setExportLoading(true)
    try {
      const data = await api.exportData()
      // Same download mechanism as the portrait share card
      // (lib/portraitShareCard.ts): object URL, synthetic anchor, revoke.
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = exportFilename()
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      // The server's message is shown as-is where it has one: 429 and 413 both
      // say something specific (once an hour / too large, contact support) that
      // a generic string would throw away.
      const message = e instanceof Error && e.message ? e.message : DATA_EXPORT_COPY.genericError
      toast.error(message)
    } finally {
      setExportLoading(false)
    }
  }

  // ── Account deletion ──────────────────────────────────────────────────────
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  async function handleDeleteConfirm() {
    setDeleteLoading(true)
    setDeleteError(null)
    try {
      await api.deleteAccount()
      // Only after a 204. A 502 means Stripe refused to cancel and NOTHING was
      // deleted, so the account is still there and signing out would hide that.
      signOut()
    } catch (e) {
      // The server's message is shown as-is: it distinguishes "your account was
      // not deleted" (502) from a generic failure, and that difference is the
      // only thing the user needs from this screen.
      setDeleteError(e instanceof Error ? e.message : DELETE_ACCOUNT_COPY.genericError)
      setDeleteLoading(false)
    }
  }

  function handleDeleteClose() {
    if (deleteLoading) return
    setDeleteOpen(false)
    setDeleteError(null)
  }

  function handleSignOut() {
    // Shared helper clears all three token stores (cookie + localStorage + Zustand)
    // and redirects to sign-in — the same definition the 401 self-heal handler uses.
    signOut()
  }

  if (!hydrated || token === null) {
    return <div className="min-h-screen [min-height:100svh] bg-vellum" />
  }

  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum pb-[80px]">
      <AppHeader />
      {/* ── Header ── */}
      <div className="px-[24px] pt-[22px] pb-[16px]">
        <p className="font-lora text-[12px] uppercase tracking-[0.18em] text-charcoal mb-[4px]">
          Account
        </p>
        <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
          Your account.
        </h1>
      </div>

      <div className="px-[16px] flex flex-col gap-[12px]">
        {/* ── Profile card ── */}
        <div className="bg-paper border border-bronze/70 rounded-md px-[16px] py-[20px] flex flex-col items-center gap-[6px]">
          <div className="w-[48px] h-[48px] rounded-full bg-linen flex items-center justify-center">
            <span className="font-cormorant text-[24px] font-medium text-charcoal leading-none">
              {initial}
            </span>
          </div>
          {user.full_name && (
            <p className="font-cormorant text-[19px] font-medium text-ink leading-tight mt-[4px]">
              {user.full_name}
            </p>
          )}
          <p className="font-lora text-[14px] text-charcoal">{user.email}</p>
        </div>

        {/* ── Subscription card ── */}
        <div className="bg-paper border border-bronze/70 rounded-md overflow-hidden">
          <div className="px-[16px] pt-[14px] pb-[2px]">
            <p className="font-lora text-[12px] uppercase tracking-[0.18em] text-charcoal">
              Subscription
            </p>
          </div>
          <button
            type="button"
            onClick={handleSubscriptionTap}
            disabled={portalLoading}
            className="w-full flex items-center justify-between px-[16px] py-[14px]"
          >
            <span className="font-cormorant text-[17px] font-medium text-ink">{plan}</span>
            <ChevronRight size={16} strokeWidth={1.5} className="text-sepia" />
          </button>
        </div>

        {/* ── Analytics card ── */}
        <div className="bg-paper border border-bronze/70 rounded-md overflow-hidden">
          <div className="px-[16px] pt-[14px] pb-[2px]">
            <p className="font-lora text-[12px] uppercase tracking-[0.18em] text-charcoal">
              Analytics
            </p>
          </div>
          <div className="w-full flex items-center justify-between px-[16px] py-[14px]">
            <span className="font-cormorant text-[17px] font-medium text-ink">
              {analyticsOn ? 'On' : 'Off'}
            </span>
            <Switch
              checked={analyticsOn}
              onChange={handleAnalyticsToggle}
              label="Analytics"
            />
          </div>
        </div>

        {/* ── Sign out card ── */}
        <button
          type="button"
          onClick={handleSignOut}
          className="w-full bg-paper border border-bronze/70 rounded-md py-[16px] text-center font-cormorant text-[17px] font-medium text-ink"
        >
          Sign out
        </button>

        {/* ── Data export ── */}
        <div className="bg-paper border border-bronze/70 rounded-md overflow-hidden">
          <div className="px-[16px] pt-[14px] pb-[2px]">
            <p className="font-lora text-[12px] uppercase tracking-[0.18em] text-charcoal">
              {DATA_EXPORT_COPY.sectionLabel}
            </p>
          </div>
          <button
            type="button"
            onClick={handleExport}
            disabled={exportLoading}
            className="w-full flex items-center justify-between px-[16px] py-[14px] disabled:opacity-60"
          >
            <span className="font-cormorant text-[17px] font-medium text-ink">
              {exportLoading ? DATA_EXPORT_COPY.loading : DATA_EXPORT_COPY.trigger}
            </span>
            <ChevronRight size={16} strokeWidth={1.5} className="text-sepia" />
          </button>
        </div>

        {/* ── Delete account ── */}
        {/* Below Sign out, and visually quieter than it: this is not a thing to
            reach for by accident, and it is not a thing to hide either. */}
        <button
          type="button"
          onClick={() => setDeleteOpen(true)}
          className="w-full mt-3 py-[14px] text-center font-lora text-[13px] text-danger"
        >
          {DELETE_ACCOUNT_COPY.trigger}
        </button>
      </div>

      <DeleteConfirmModal
        open={deleteOpen}
        title={DELETE_ACCOUNT_COPY.title}
        body={DELETE_ACCOUNT_COPY.body}
        confirmLabel={DELETE_ACCOUNT_COPY.confirmLabel}
        requireTypedConfirmation={DELETE_ACCOUNT_COPY.typedToken}
        typedConfirmationLabel={DELETE_ACCOUNT_COPY.typedLabel}
        loading={deleteLoading}
        error={deleteError}
        onConfirm={handleDeleteConfirm}
        onClose={handleDeleteClose}
      />
    </main>
  )
}
