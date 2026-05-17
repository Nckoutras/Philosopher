'use client'

import { usePathname, useRouter } from 'next/navigation'
import { Home, BookOpen, Archive, User } from 'lucide-react'
import toast from 'react-hot-toast'

const TABS = [
  {
    label: 'Today',
    icon: Home,
    href: '/app/today',
    activePattern: /^\/app\/today/,
    exists: false,
  },
  {
    label: 'Reflections',
    icon: BookOpen,
    href: '/app/reflections',
    activePattern: /^\/app\/reflections/,
    exists: true,
  },
  {
    label: 'Library',
    icon: Archive,
    href: '/app/library',
    activePattern: /^\/app\/library/,
    exists: true,
  },
  {
    label: 'Account',
    icon: User,
    href: '/app/account',
    activePattern: /^\/app\/account/,
    exists: false,
  },
] as const

export default function BottomTabBar() {
  const pathname = usePathname()
  const router = useRouter()

  function handleTap(tab: (typeof TABS)[number]) {
    if (!tab.exists) {
      toast('Coming soon', { duration: 2000 })
      return
    }
    router.push(tab.href)
  }

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 h-16 bg-paper border-t border-[0.5px] border-edge flex items-stretch z-50"
      aria-label="Main navigation"
    >
      {TABS.map((tab) => {
        const Icon = tab.icon
        const isActive = tab.activePattern.test(pathname)
        const isDimmed = !tab.exists

        return (
          <button
            key={tab.label}
            type="button"
            onClick={() => handleTap(tab)}
            aria-label={tab.label}
            aria-current={isActive ? 'page' : undefined}
            className={[
              'flex-1 flex flex-col items-center justify-center gap-[3px] transition-colors',
              isActive ? 'text-ink' : isDimmed ? 'text-sepia/50' : 'text-sepia',
            ].join(' ')}
          >
            <Icon
              size={20}
              strokeWidth={1.5}
              className={isActive ? 'text-ink' : ''}
            />
            <span
              className={[
                'font-lora text-[10px] leading-none',
                isActive ? 'text-ink font-medium' : '',
              ].join(' ')}
            >
              {tab.label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}
