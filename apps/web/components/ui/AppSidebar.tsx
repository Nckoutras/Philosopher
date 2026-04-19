'use client'

import { useRouter, usePathname } from 'next/navigation'
import { LayoutDashboard, Brain, Scroll, Settings, LogOut, Zap } from 'lucide-react'
import { clsx } from 'clsx'
import { useStore } from '@/lib/store'
import { api } from '@/lib/api'

const NAV = [
  { href: '/app/dashboard', icon: LayoutDashboard, label: 'Conversations' },
  { href: '/app/memory',    icon: Brain,           label: 'Memory'        },
  { href: '/app/rituals',   icon: Scroll,          label: 'Rituals'       },
  { href: '/app/settings',  icon: Settings,        label: 'Settings'      },
]

export function AppSidebar() {
  const router = useRouter()
  const pathname = usePathname()
  const { user, clearAuth, subscription } = useStore()
  const plan = subscription?.plan ?? 'free'

  const handleLogout = () => {
    api.setToken(null)
    clearAuth()
    router.replace('/login')
  }

  return (
    <aside
      className="hidden md:flex flex-col w-56 h-full py-6 px-3"
      style={{ borderRight: '1px solid var(--border)', background: 'var(--bg-primary)' }}
    >
      {/* Logo */}
      <div className="px-3 mb-8 flex items-center gap-2">
        <span className="text-xl">⚗️</span>
        <span
          className="font-medium text-base"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}
        >
          Philosopher
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = pathname.startsWith(href)
          return (
            <button
              key={href}
              onClick={() => router.push(href)}
              className={clsx(
                'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors text-left',
                active
                  ? 'bg-[var(--bg-surface)]'
                  : 'hover:bg-[var(--bg-surface)]',
              )}
              style={{
                color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: active ? 500 : 400,
              }}
            >
              <Icon size={15} />
              {label}
            </button>
          )
        })}
      </nav>

      {/* Plan chip */}
      {plan === 'free' && (
        <button
          onClick={() => router.push('/upgrade')}
          className="mx-1 mb-3 flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs transition-opacity hover:opacity-80"
          style={{
            background: 'rgba(201,169,110,0.1)',
            color: 'var(--gold)',
            border: '1px solid rgba(201,169,110,0.2)',
          }}
        >
          <Zap size={11} />
          Upgrade to Pro
        </button>
      )}

      {/* User + logout */}
      <div
        className="mt-1 flex items-center gap-2.5 px-3 py-2.5 rounded-lg"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>
            {user?.full_name ?? user?.email?.split('@')[0]}
          </p>
          <p className="text-[10px] truncate capitalize" style={{ color: 'var(--text-muted)' }}>
            {plan}
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="p-1 rounded hover:opacity-70"
          style={{ color: 'var(--text-muted)' }}
          title="Sign out"
        >
          <LogOut size={13} />
        </button>
      </div>
    </aside>
  )
}
