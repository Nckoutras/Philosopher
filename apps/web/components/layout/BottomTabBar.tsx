'use client'

import Link from 'next/link'
import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Home, Compass, User, Sparkle } from 'lucide-react'
import { useStore } from '@/lib/store'

// Artist's easel — local icon matching the lucide consumption contract used by
// the tab bar: accepts `size` and `strokeWidth`, strokes with `currentColor` so
// active/inactive tinting flows from the parent Link's text color unchanged.
function EaselIcon({
  size = 24,
  strokeWidth = 2,
}: {
  size?: number
  strokeWidth?: number
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {/* top pin */}
      <line x1="12" y1="2.5" x2="12" y2="5" />
      <line x1="10.4" y1="4.6" x2="13.6" y2="4.6" />
      {/* canvas */}
      <rect x="5.5" y="5" width="13" height="9.5" rx="0.5" />
      {/* tray */}
      <line x1="4" y1="15.2" x2="20" y2="15.2" />
      {/* three legs, splayed */}
      <line x1="7.8" y1="15.8" x2="5" y2="21.5" />
      <line x1="12" y1="15.8" x2="12" y2="21.5" />
      <line x1="16.2" y1="15.8" x2="19" y2="21.5" />
    </svg>
  )
}

const TABS = [
  {
    label: 'Home',
    icon: Home,
    href: '/app/today',
    activePattern: /^\/app\/today/,
  },
  {
    label: 'Explore',
    icon: Compass,
    href: '/app/explore',
    activePattern: /^\/app\/explore/,
  },
  {
    label: 'Self Portrait',
    icon: EaselIcon,
    href: '/app/self-portrait',
    activePattern: /^\/app\/self-portrait/,
  },
  {
    label: 'Account',
    icon: User,
    href: '/app/account',
    activePattern: /^\/app\/account/,
  },
] as const

export default function BottomTabBar() {
  const pathname = usePathname()
  const router = useRouter()

  const activeInsights = useStore((s) => s.activeInsights)
  const seenInsightIds = useStore((s) => s.seenInsightIds)
  const unreadLetterIds = useStore((s) => s.unreadLetterIds)
  const hasUnseenInsight = activeInsights.some((i) => !seenInsightIds.includes(i.id))
  // Home star fires for an unseen insight OR a waiting Sunday/season letter.
  const hasHomeNew = hasUnseenInsight || unreadLetterIds.length > 0

  // Warm the sibling tab route chunks on idle so the first navigation to each
  // is instant rather than waiting on the on-tap chunk download. Non-visual;
  // relies only on Next's router prefetch cache.
  useEffect(() => {
    const warm = () => TABS.forEach((tab) => router.prefetch(tab.href))
    const ric = typeof window !== 'undefined' ? window.requestIdleCallback : undefined
    if (ric) {
      const id = ric(warm)
      return () => window.cancelIdleCallback?.(id)
    }
    const id = window.setTimeout(warm, 200)
    return () => window.clearTimeout(id)
  }, [router])

  return (
    // Floating frosted pill (Design System v5, Instagram-style). Fixed to the visible
    // viewport bottom directly rather than computed from the shell height — the top-down
    // height-computed shell could not reliably place the bar across
    // zoom/svh/browser-chrome/banner variations. Inset from the edges and lifted off the
    // bottom so it reads as floating; the safe-area is an OFFSET below the pill (single
    // source of truth) rather than padding inside it. (tabs)/layout.tsx pads the scroll
    // area to match so nothing is covered. BodyScrollLock keeps `fixed` safe here.
    <nav
      className="fixed left-4 right-4 z-50 bg-paper/80 backdrop-blur-md border border-bronze/30 rounded-full shadow-card overflow-hidden"
      style={{ bottom: 'calc(env(safe-area-inset-bottom) + 12px)' }}
      aria-label="Main navigation"
    >
      <div className="h-16 flex items-stretch">
        {TABS.map((tab) => {
          const Icon = tab.icon
          const isActive = tab.activePattern.test(pathname)

          return (
            <Link
              key={tab.label}
              href={tab.href}
              aria-label={tab.label}
              aria-current={isActive ? 'page' : undefined}
              className={[
                'flex-1 flex flex-col items-center justify-center gap-[3px] transition-[color,opacity,transform] active:opacity-50 active:scale-95 select-none [touch-action:manipulation] [-webkit-tap-highlight-color:transparent]',
                isActive ? 'text-ink' : 'text-sepia',
              ].join(' ')}
            >
              {tab.label === 'Home' ? (
                <span className="relative">
                  <Icon size={20} strokeWidth={1.5} />
                  {hasHomeNew && (
                    <Sparkle size={11} strokeWidth={1.5} className="absolute -top-[3px] -right-[5px] text-bronze fill-bronze drop-shadow-[0_0_5px_rgba(184,153,104,0.95)] motion-safe:animate-soft-pulse" aria-hidden="true" />
                  )}
                </span>
              ) : (
                <Icon size={20} strokeWidth={1.5} />
              )}
              <span
                className={[
                  'font-lora text-[10px] leading-none whitespace-nowrap',
                  isActive ? 'font-medium' : '',
                ].join(' ')}
              >
                {tab.label}
              </span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
