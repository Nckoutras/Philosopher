// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait radar (Phase B, mock restyle). A pure-SVG pentagon of the user's
// FIVE strongest theme axes — the founder-approved payoff shape. No charting library.
//
// • TOP-5 axes only: the 5 highest-scoring axes are selected (tie-break by frozen
//   axis order), then arranged in their FROZEN relative order around the circle at
//   72° spacing (first at −90°/top). Deterministic + stable on reopen. The Map view
//   still shows all 8 — only the radar filters.
// • Guides are CIRCLES: one solid bronze outer ring + two dashed inner rings (0.4R,
//   0.7R). Spokes + endpoint dots on the ring; a bronze data pentagon (fill 0.3);
//   an 8-point compass rose behind the polygon (decorative, shows through the fill).
// • The κάδρο/frame texture is retained behind USE_RADAR_FRAME, but that flag is now
//   OFF (Artwork.tsx) — clean vellum, no frame. The flag + asset stay for later use.
// • Faint persona watermark sits BEHIND everything, screen-only, ready-state only.
// • No signal → the skeleton (rings/spokes/rose) + a calm line, never a count.
// ─────────────────────────────────────────────────────────────────────────────
import Image from 'next/image'
import type { SelfPortraitThemeScore } from '@/lib/api'
import { USE_RADAR_FRAME, radarFrameSrc } from './Artwork'

// Geometry in a 360×264 viewBox (aspect kept so the shared card — untouched this PR —
// draws the svg undistorted). CX/CY centered; R = outer ring; LABEL_R = label anchor
// radius, bounded so all 5 labels fit the viewBox even in the 5-longest worst case
// (verified: min x 34, max x 326, min y 24, max y 225 at fontSize 13 — see PR table).
const CX = 180
const CY = 134
const R = 82
const LABEL_R = 98
const TOP_N = 5
const INNER_RINGS = [0.4, 0.7] as const

// Angle for pentagon position k (0..4): start at top (−90°), step 72° clockwise.
function angleRadAt(k: number): number {
  return ((-90 + k * 72) * Math.PI) / 180
}

function pointAt(radius: number, k: number): { x: number; y: number } {
  const a = angleRadAt(k)
  return { x: CX + radius * Math.cos(a), y: CY + radius * Math.sin(a) }
}

// "x,y x,y …" over the selected axes' per-position radii (closed pentagon).
function polygonPoints(radii: number[]): string {
  return radii.map((r, k) => { const p = pointAt(r, k); return `${p.x.toFixed(1)},${p.y.toFixed(1)}` }).join(' ')
}

// Decorative 8-point compass rose, same-file + currentColor-compatible (the parent <g>
// sets `color`, so stroke="currentColor" tints to bronze). Drawn behind the polygon.
function CompassRose({ cx, cy, radius }: { cx: number; cy: number; radius: number }) {
  const inner = radius * 0.4
  const pts: string[] = []
  for (let i = 0; i < 16; i++) {
    const rr = i % 2 === 0 ? radius : inner
    const a = ((-90 + i * 22.5) * Math.PI) / 180
    pts.push(`${(cx + rr * Math.cos(a)).toFixed(1)},${(cy + rr * Math.sin(a)).toFixed(1)}`)
  }
  return (
    <g aria-hidden="true" style={{ color: '#B89968' }}>
      <polygon points={pts.join(' ')} fill="none" stroke="currentColor" strokeWidth={1} strokeLinejoin="round" opacity={0.5} />
      <circle cx={cx} cy={cy} r={radius * 0.16} fill="none" stroke="currentColor" strokeWidth={1} opacity={0.5} />
    </g>
  )
}

export function PortraitRadar({
  scores,
  watermarkUrl = null,
}: {
  scores: SelfPortraitThemeScore[]
  watermarkUrl?: string | null
}) {
  const axes = scores ?? []
  const hasSignal = axes.length > 0 && axes.some((s) => s.score > 0)

  // Resolve to a usable URL (non-empty string) or null — used as BOTH the gate and the
  // <Image src>, so an absent/blank portrait renders nothing (no broken "?" placeholder).
  const watermark =
    typeof watermarkUrl === 'string' && watermarkUrl.trim().length > 0 ? watermarkUrl : null

  // Select the TOP-5 axes (score desc, tie-break frozen order), then restore FROZEN order
  // for placement so position k is stable for the same scores on reopen.
  const selected = axes
    .map((s, i) => ({ s, i }))
    .sort((a, b) => (b.s.score - a.s.score) || (a.i - b.i))
    .slice(0, TOP_N)
    .sort((a, b) => a.i - b.i)
    .map((e) => e.s)

  return (
    <div className="relative w-full max-w-[320px] mx-auto">
      {/* Faint persona watermark — ready-state only, behind everything, screen-only. */}
      {watermark && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="relative w-[50%] aspect-square rounded-full overflow-hidden opacity-[0.06]">
            <Image src={watermark} alt="" fill sizes="200px" className="object-cover" />
          </div>
        </div>
      )}

      {/* OPTIONAL κάδρο/frame texture — retained but gated on USE_RADAR_FRAME (now OFF),
          so it never renders a broken <img> and can be re-enabled later without code. */}
      {USE_RADAR_FRAME && (
        <div className="absolute inset-0 pointer-events-none">
          {/* eslint-disable-next-line @next/next/no-img-element -- decorative texture, no optimization needed */}
          <img src={radarFrameSrc()} alt="" className="w-full h-full object-contain" />
        </div>
      )}

      <svg viewBox="0 0 360 264" className="relative w-full block" role="img" aria-label="Your theme radar">
        {/* Guide rings — 2 dashed inner circles + 1 solid bronze outer ring. */}
        {INNER_RINGS.map((frac) => (
          <circle
            key={frac}
            cx={CX}
            cy={CY}
            r={R * frac}
            fill="none"
            stroke="#B89968"
            strokeWidth={0.8}
            strokeDasharray="2 3"
            opacity={0.5}
          />
        ))}
        <circle cx={CX} cy={CY} r={R} fill="none" stroke="#B89968" strokeWidth={1} opacity={0.85} />

        {/* Compass rose — decorative, behind the data polygon (fill shows it through). */}
        <CompassRose cx={CX} cy={CY} radius={R * 0.25} />

        {/* Spokes + endpoint dots + axis labels, one per selected axis. */}
        {selected.map((s, k) => {
          const outer = pointAt(R, k)
          const lp = pointAt(LABEL_R, k)
          const a = angleRadAt(k)
          const cos = Math.cos(a)
          const sin = Math.sin(a)
          const anchor = cos > 0.3 ? 'start' : cos < -0.3 ? 'end' : 'middle'
          const dy = sin > 0.3 ? '0.7em' : sin < -0.3 ? '-0.2em' : '0.32em'
          return (
            <g key={s.key}>
              <line x1={CX} y1={CY} x2={outer.x} y2={outer.y} stroke="#B89968" strokeWidth={0.8} opacity={0.4} />
              <circle cx={outer.x} cy={outer.y} r={2.5} fill="#B89968" />
              <text
                x={lp.x}
                y={lp.y}
                dy={dy}
                textAnchor={anchor}
                className="font-lora"
                fontSize={13}
                fontWeight={500}
                fill="#1F1B14"
              >
                {s.label}
              </text>
            </g>
          )
        })}

        {/* Data pentagon — only when there's real signal. */}
        {hasSignal && (
          <>
            <polygon
              points={polygonPoints(selected.map((s) => R * Math.max(0, Math.min(1, s.score))))}
              fill="#B89968"
              fillOpacity={0.3}
              stroke="#8A7340"
              strokeWidth={1.2}
              strokeLinejoin="round"
            />
            {selected.map((s, k) => {
              const p = pointAt(R * Math.max(0, Math.min(1, s.score)), k)
              return <circle key={s.key} cx={p.x} cy={p.y} r={2.5} fill="#8A7340" />
            })}
          </>
        )}
      </svg>

      {/* No-signal calm line (never a count). */}
      {!hasSignal && (
        <p className="font-lora text-[13px] text-charcoal leading-[1.6] text-center mt-1">
          Keep answering — your portrait takes its shape as you go.
        </p>
      )}
    </div>
  )
}
