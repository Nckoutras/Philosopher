'use client'

import { useEffect, useLayoutEffect, useState } from 'react'

// useLayoutEffect logs an SSR warning when run on the server. We start with
// h === null on both server and client, so the first committed render is
// identical (classname-only) on both sides — no hydration mismatch. The
// effect only runs client-side; this alias just silences the warning.
const useIsoLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect

/**
 * Tabs container height shell.
 *
 * The steady-state position of the bottom tab bar is correct via the CSS
 * `calc(100dvh/1.15)` fallback. The problem this fixes is the FIRST
 * authenticated mount: after `router.replace('/app/today')`, the `dvh`
 * unit can resolve from a pre-settled viewport, making the container too
 * short and floating the tab bar above the screen bottom until the next
 * viewport change.
 *
 * We measure `window.innerHeight` in useLayoutEffect (fires before first
 * paint) and apply it inline, overriding the stale `dvh` for the initial
 * render. The `/1.15` divisor is preserved to match the intentional
 * `body { zoom: 1.15 }`.
 *
 * NOTE: this disables `dvh` for the session in favour of innerHeight +
 * listeners. iOS Safari does not reliably fire `window.resize` for
 * address-bar show/hide, so we also listen on `visualViewport` to keep
 * toolbar transitions tracked. Tracking is discrete (event-driven), not
 * continuous like native `dvh`.
 */
export default function TabsShell({ children }: { children: React.ReactNode }) {
  const [h, setH] = useState<string | null>(null)

  useIsoLayoutEffect(() => {
    function update() {
      setH(`${window.innerHeight / 1.15}px`)
    }
    update()

    window.addEventListener('resize', update)
    // iOS Safari toolbar show/hide: window 'resize' is unreliable, but
    // visualViewport 'resize' fires. Read innerHeight regardless of trigger.
    const vv = window.visualViewport
    vv?.addEventListener('resize', update)

    return () => {
      window.removeEventListener('resize', update)
      vv?.removeEventListener('resize', update)
    }
  }, [])

  return (
    <div
      className="relative h-[calc(100dvh/1.15)] overflow-hidden flex flex-col"
      style={h !== null ? { height: h } : undefined}
    >
      {children}
    </div>
  )
}
