'use client'

import Link from 'next/link'
import { useEffect, type CSSProperties } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Home, Compass, User, Sparkle, Quote } from 'lucide-react'
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
    label: 'Portrait',
    icon: EaselIcon,
    href: '/app/self-portrait',
    activePattern: /^\/app\/self-portrait/,
  },
  {
    label: 'Quotes',
    icon: Quote,
    href: '/app/quotes',
    activePattern: /^\/app\/quotes/,
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

  // Which tab the liquid-glass lens slides under. Exactly one pattern matches on
  // the (tabs) routes; -1 (no match) hides the lens without affecting the
  // color-based active state, which remains the source of truth for a11y.
  const activeIndex = TABS.findIndex((tab) => tab.activePattern.test(pathname))

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
        {/* Liquid-glass lens: slides (spring) under the active tab, magnifying its
            icon. Purely decorative — the color active state (text-ink) is the a11y
            signal and the no-backdrop-filter fallback, so the lens never gates it. */}
        <span
          className="tabbar-lens"
          aria-hidden="true"
          style={{ '--active': Math.max(0, activeIndex), opacity: activeIndex < 0 ? 0 : 1 } as CSSProperties}
        />
        {TABS.map((tab) => {
          const Icon = tab.icon
          const isActive = tab.activePattern.test(pathname)

          // The magnify scales the GLYPH only. For Home, this wrapper sits inside
          // the .relative span alongside the Sparkle badge, so the badge keeps its
          // corner position and size while the icon grows.
          const glyph = (
            <span className={`tabbar-glyph${isActive ? ' is-active' : ''}`}>
              <Icon size={20} strokeWidth={1.5} />
            </span>
          )

          return (
            <Link
              key={tab.label}
              href={tab.href}
              aria-label={tab.label}
              aria-current={isActive ? 'page' : undefined}
              className={[
                'relative z-[2] flex-1 flex flex-col items-center justify-center gap-[3px] transition-[color,opacity,transform] active:opacity-50 active:scale-95 select-none [touch-action:manipulation] [-webkit-tap-highlight-color:transparent]',
                isActive ? 'text-ink -translate-y-px' : 'text-sepia',
              ].join(' ')}
            >
              {tab.label === 'Home' ? (
                <span className="relative">
                  {glyph}
                  {hasHomeNew && (
                    <Sparkle size={11} strokeWidth={1.5} className="absolute -top-[3px] -right-[5px] text-bronze fill-bronze drop-shadow-[0_0_5px_rgba(184,153,104,0.95)] motion-safe:animate-soft-pulse" aria-hidden="true" />
                  )}
                </span>
              ) : (
                glyph
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

      <style jsx>{`
        /* Lens geometry: width is one tab minus a 3px inset; translateX moves it a
           whole tab-step per active index. Because the lens is (20% − 3px) wide,
           100% of its own width + 3px == 20% of the bar, so k·(100% + 3px) lands it
           centered under tab k (with the 1.5px left seed centering it under tab 0). */
        .tabbar-lens {
          position: absolute;
          top: 6px;
          left: 1.5px;
          height: 52px;
          width: calc(20% - 3px);
          border-radius: 999px;
          z-index: 1;
          pointer-events: none;
          transform: translateX(calc(var(--active) * (100% + 3px)));
          will-change: transform;
          transition: transform 0.42s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.42s ease;
          background: radial-gradient(120% 90% at 34% 22%, rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.28) 46%, rgba(255, 255, 255, 0.05) 78%);
          backdrop-filter: blur(1px) brightness(1.18) saturate(1.15);
          -webkit-backdrop-filter: blur(1px) brightness(1.18) saturate(1.15);
          border: 1px solid rgba(255, 255, 255, 0.75);
          box-shadow: inset 0 2px 2px rgba(255, 255, 255, 0.95), inset 0 -3px 6px rgba(184, 153, 104, 0.25), 0 3px 10px rgba(31, 27, 20, 0.16);
        }
        /* Specular highlight strip near the top of the lens. */
        .tabbar-lens::after {
          content: '';
          position: absolute;
          top: 4px;
          left: 14%;
          right: 30%;
          height: 9px;
          border-radius: 999px;
          background: linear-gradient(90deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0));
          filter: blur(1px);
        }
        .tabbar-glyph {
          display: inline-flex;
          transform-origin: center;
          transition: transform 0.42s cubic-bezier(0.34, 1.56, 0.64, 1), filter 0.42s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        .tabbar-glyph.is-active {
          transform: scale(1.34);
          filter: drop-shadow(0 1px 1px rgba(255, 255, 255, 0.7));
        }
        /* Motion-safety: lens appears instantly (no travel), glyph magnifies without
           the spring overshoot. The Sparkle soft-pulse is already motion-safe. */
        @media (prefers-reduced-motion: reduce) {
          .tabbar-lens,
          .tabbar-glyph {
            transition: none;
          }
        }
      `}</style>
    </nav>
  )
}
