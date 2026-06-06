'use client'
import { useRouter } from 'next/navigation'
import { ChevronLeft, Home } from 'lucide-react'

export default function SubPageNav({
  fallbackHref,
  showHome = true,
}: { fallbackHref: string; showHome?: boolean }) {
  const router = useRouter()
  const goBack = () => {
    if (typeof window !== 'undefined' && window.history.length > 1) router.back()
    else router.push(fallbackHref)
  }
  return (
    <div className="flex items-center justify-between"
         style={{ paddingTop: 'max(0.5rem, env(safe-area-inset-top))' }}>
      <button type="button" onClick={goBack} aria-label="Back"
        className="min-h-[44px] min-w-[44px] flex items-center justify-center -ml-[10px] text-ink active:opacity-50 [touch-action:manipulation] [-webkit-tap-highlight-color:transparent]">
        <ChevronLeft size={24} strokeWidth={1.5} />
      </button>
      {showHome ? (
        <button type="button" onClick={() => router.push('/app/today')} aria-label="Home"
          className="min-h-[44px] min-w-[44px] flex items-center justify-center -mr-[10px] text-ink active:opacity-50 [touch-action:manipulation] [-webkit-tap-highlight-color:transparent]">
          <Home size={20} strokeWidth={1.5} />
        </button>
      ) : <span className="w-[44px]" />}
    </div>
  )
}
