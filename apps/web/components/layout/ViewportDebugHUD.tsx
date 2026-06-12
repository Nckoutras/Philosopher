'use client'

import { useEffect, useState } from 'react'

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

  return (
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
  )
}
