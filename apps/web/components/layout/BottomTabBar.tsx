'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Compass, Archive, User } from 'lucide-react'

const TABS = [
  {
    label: 'Today',
    icon: Home,
    href: '/app/today',
    activePattern: /^\/app\/today/,
  },
  {
    label: 'Rituals',
    icon: Compass,
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

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 h-16 bg-paper border-t border-[0.5px] border-edge flex items-stretch z-50"
      aria-label="Main navigation"
    >
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
              'flex-1 flex flex-col items-center justify-center gap-[3px] transition-colors',
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
    </nav>
  )
}
