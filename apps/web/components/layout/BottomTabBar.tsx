'use client'

import Link from 'next/link'
import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Home, Archive, User } from 'lucide-react'
import { ReturningPathIcon } from '@/components/icons/RitualIcons'

const TABS = [
  {
    label: 'Today',
    icon: Home,
    href: '/app/today',
    activePattern: /^\/app\/today/,
  },
  {
    label: 'Rituals',
    icon: ReturningPathIcon,
    href: '/app/rituals',
    activePattern: /^\/app\/rituals/,
  },
  {
    label: 'Library',
    icon: Archive,
    href: '/app/library',
    activePattern: /^\/app\/library/,
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
      className="fixed left-4 right-4 z-50 bg-paper/80 backdrop-blur-md border border-bronze/30 rounded-2xl shadow-card overflow-hidden"
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
              <Icon size={20} strokeWidth={1.5} />
              <span
                className={[
                  'font-lora text-[10px] leading-none',
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
