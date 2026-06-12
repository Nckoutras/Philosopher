'use client'

import { useEffect, useRef, useState } from 'react'
import { usePathname } from 'next/navigation'

// Same API base the app already uses (lib/api.ts / auth/page.tsx re-derive this
// exact expression; the constant there is not exported). NEXT_PUBLIC_API_URL
// already ENDS in /api/v1 in every environment, so the beacon path below appends
// only `/_diag_viewport` to land the request line as `/api/v1/_diag_viewport`.
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  'https://philosopher-api-z9l9.onrender.com/api/v1'

/**
 * DIAGNOSTIC-ONLY overlay — lives on branch `diag/viewport-hud` and is NEVER
 * merged to main.
 *
 * Purpose: confirm or kill the "trapped viewport offset" hypothesis for the
 * mid-screen bottom tab bar (and hidden Letter-sheet submit) by printing live
 * scroll / visual-viewport / geometry numbers from the real device.
 *
 * In-flow strategy: position:absolute INSIDE the (tabs) shell at top-0/left-0,
 * NOT position:fixed. A fixed overlay would escape the bug's coordinate space;
 * an in-flow absolute child shares it, so its numbers reflect what the tab bar
 * actually experiences. z-index is maxed so the HUD stays visible above an open
 * BottomSheet (which is `fixed z-[60]`) WITHOUT touching BottomSheet.
 * pointer-events:none so it never intercepts taps.
 *
 * Reads the shell + tab bar via DOM query (no edits to existing elements):
 *   tab bar  = nav[aria-label="Main navigation"]
 *   shell    = that nav's parentElement (the (tabs) container div)
 */
export default function ViewportDebugHUD() {
  const [lines, setLines] = useState<string[]>([])
  const pathname = usePathname()
  const pathnameRef = useRef(pathname)
  pathnameRef.current = pathname

  // Decisive unit probes: hidden, out-of-flow divs sized to 100svh / 100dvh /
  // 100lvh. Their measured getBoundingClientRect().height reveals exactly how
  // this engine resolves each viewport unit under body zoom + dynamic chrome,
  // ending the guesswork. Zero layout impact (absolute, 1px wide, clipped by the
  // shell's overflow-hidden, visibility:hidden).
  const pSvhRef = useRef<HTMLDivElement>(null)
  const pDvhRef = useRef<HTMLDivElement>(null)
  const pLvhRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fmt = (n: number | undefined | null) =>
      n === undefined || n === null || Number.isNaN(n)
        ? 'n/a'
        : String(Math.round(n * 10) / 10)

    const read = () => {
      const vv = window.visualViewport
      const tabBar = document.querySelector(
        'nav[aria-label="Main navigation"]',
      ) as HTMLElement | null
      const shell = tabBar?.parentElement ?? null
      const shellRect = shell?.getBoundingClientRect()
      const barRect = tabBar?.getBoundingClientRect()

      setLines([
        `window.scrollY      ${fmt(window.scrollY)}`,
        `docEl.scrollTop     ${fmt(document.documentElement.scrollTop)}`,
        `body.scrollTop      ${fmt(document.body.scrollTop)}`,
        `vv.offsetTop        ${fmt(vv?.offsetTop)}`,
        `vv.height           ${fmt(vv?.height)}  scale ${fmt(vv?.scale)}`,
        `window.innerHeight  ${fmt(window.innerHeight)}`,
        `shell rect.height   ${fmt(shellRect?.height)}`,
        `tabbar rect.top     ${fmt(barRect?.top)}`,
        `tabbar rect.bottom  ${fmt(barRect?.bottom)}`,
      ])
    }

    read()
    const intervalId = window.setInterval(read, 250)
    const onEvent = () => read()
    window.addEventListener('scroll', onEvent, true)
    window.addEventListener('resize', onEvent)
    window.visualViewport?.addEventListener('scroll', onEvent)
    window.visualViewport?.addEventListener('resize', onEvent)

    return () => {
      window.clearInterval(intervalId)
      window.removeEventListener('scroll', onEvent, true)
      window.removeEventListener('resize', onEvent)
      window.visualViewport?.removeEventListener('scroll', onEvent)
      window.visualViewport?.removeEventListener('resize', onEvent)
    }
  }, [])

  // Self-reporting beacon: the founder cannot screenshot the HUD, so we fire the
  // same measurements at the production API every 3s (plus on mount and on
  // visualViewport events, throttled to >=500ms apart). There is NO such endpoint;
  // the request 404s and that is fine — Render's access log records the full query
  // string, which IS the data channel. Fire-and-forget; errors swallowed.
  useEffect(() => {
    const lastBeacon = { t: 0 }
    const ri = (n: number | undefined | null) =>
      n === undefined || n === null || Number.isNaN(n) ? '' : String(Math.round(n))

    const beacon = (force: boolean) => {
      const now = Date.now()
      if (!force && now - lastBeacon.t < 500) return
      lastBeacon.t = now

      const vv = window.visualViewport
      const tabBar = document.querySelector(
        'nav[aria-label="Main navigation"]',
      ) as HTMLElement | null
      const shell = tabBar?.parentElement ?? null
      const shellRect = shell?.getBoundingClientRect()
      const barRect = tabBar?.getBoundingClientRect()
      const sheetOpen = !!document.querySelector('[role="dialog"][aria-modal="true"]')
      const probeH = (el: HTMLDivElement | null) =>
        el ? el.getBoundingClientRect().height : null

      const params = new URLSearchParams({
        sy: ri(window.scrollY),
        det: ri(document.documentElement.scrollTop),
        bst: ri(document.body.scrollTop),
        vvo: ri(vv?.offsetTop),
        vvh: ri(vv?.height),
        vvs: ri(vv?.scale),
        ih: ri(window.innerHeight),
        sh: ri(shellRect?.height),
        tbt: ri(barRect?.top),
        tbb: ri(barRect?.bottom),
        p_svh: ri(probeH(pSvhRef.current)),
        p_dvh: ri(probeH(pDvhRef.current)),
        p_lvh: ri(probeH(pLvhRef.current)),
        dch: ri(document.documentElement.clientHeight),
        route: pathnameRef.current ?? '',
        sheet: sheetOpen ? '1' : '0',
      })
      fetch(`${API_BASE}/_diag_viewport?${params.toString()}`).catch(() => {})
    }

    beacon(true)
    const intervalId = window.setInterval(() => beacon(true), 3000)
    const onVV = () => beacon(false)
    window.visualViewport?.addEventListener('scroll', onVV)
    window.visualViewport?.addEventListener('resize', onVV)

    return () => {
      window.clearInterval(intervalId)
      window.visualViewport?.removeEventListener('scroll', onVV)
      window.visualViewport?.removeEventListener('resize', onVV)
    }
  }, [])

  // Hidden unit probes — out of flow, 1px wide, invisible, clipped by the shell's
  // overflow-hidden. Only their resolved height is read (getBoundingClientRect).
  const probeStyle = {
    position: 'absolute' as const,
    top: 0,
    left: 0,
    width: 1,
    visibility: 'hidden' as const,
    pointerEvents: 'none' as const,
    zIndex: -1,
  }

  return (
    <>
      <div ref={pSvhRef} aria-hidden="true" style={{ ...probeStyle, height: '100svh' }} />
      <div ref={pDvhRef} aria-hidden="true" style={{ ...probeStyle, height: '100dvh' }} />
      <div ref={pLvhRef} aria-hidden="true" style={{ ...probeStyle, height: '100lvh' }} />
      <div
        aria-hidden="true"
        className="absolute top-0 left-0 z-[2147483647] pointer-events-none whitespace-pre px-2 py-1"
        style={{
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          fontSize: '10px',
          lineHeight: 1.35,
          color: '#7CFC00',
          background: 'rgba(0,0,0,0.8)',
        }}
      >
        {lines.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </div>
    </>
  )
}
