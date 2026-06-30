// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait radar (Phase B1). A pure-SVG spiderweb of the user's REAL theme
// scores — 8 curated axes (fixed octagon order from the API), each vertex at
// radius = score (0–1, already per-user max-normalized server-side so the polygon
// fills the frame). No charting library.
//
// • Renders fully WITHOUT any asset. The κάδρο/frame is CSS + SVG; an OPTIONAL
//   watercolor texture overlays only when USE_REAL_ARTWORK is on (Artwork seam).
// • Faint persona watermark sits BEHIND the frame, screen-only, and is passed in
//   ONLY for the ready state (never forming). It is deliberately NOT part of any
//   share canvas (that's B3 — keeping the persona out avoids canvas taint).
// • If every score is ~0 (too few answers / no curated hits yet), we draw the bare
//   spokes + a calm line — never a collapsed polygon, never a count.
// ─────────────────────────────────────────────────────────────────────────────
import Image from 'next/image'
import type { SelfPortraitThemeScore } from '@/lib/api'
import { USE_REAL_ARTWORK, radarFrameSrc } from './Artwork'

// Geometry in a 360×264 viewBox. The width carries ~90px of horizontal padding each
// side of the R=88 web so the longest side labels ("Connection" at pure-left, anchored
// `end`; "Freedom"/"Desire" at right, anchored `start`) sit fully inside LABEL_R and
// never clip on a narrow phone frame. CY is shifted up slightly for the bottom label.
const CX = 180
const CY = 124
const R = 88
const LABEL_R = 106
const RINGS = [0.25, 0.5, 0.75, 1] as const

// Angle for axis i: start at top (−90°), step 45° clockwise. Frozen to match the
// server's PORTRAIT_AXES order (Identity at top, then Fear, Freedom, …).
function angleRad(i: number): number {
  return ((-90 + i * 45) * Math.PI) / 180
}

function point(radius: number, i: number): { x: number; y: number } {
  const a = angleRad(i)
  return { x: CX + radius * Math.cos(a), y: CY + radius * Math.sin(a) }
}

// "x,y x,y …" for a closed polygon over all 8 axes at the given per-axis radii.
function polygonPoints(radii: number[]): string {
  return radii.map((r, i) => { const p = point(r, i); return `${p.x.toFixed(1)},${p.y.toFixed(1)}` }).join(' ')
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

  // Concentric guide octagons (the "web"), drawn at every axis count we actually have
  // so the frame still reads even if the API sent a different number of axes.
  const n = axes.length || 8
  const ring = (frac: number) =>
    Array.from({ length: n }, (_, i) => {
      const p = point(R * frac, i)
      return `${p.x.toFixed(1)},${p.y.toFixed(1)}`
    }).join(' ')

  return (
    <div className="relative w-full max-w-[320px] mx-auto">
      {/* Faint persona watermark — ready-state only, behind everything, screen-only. */}
      {watermarkUrl && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="relative w-[58%] aspect-square rounded-full overflow-hidden opacity-[0.07]">
            <Image src={watermarkUrl} alt="" fill sizes="200px" className="object-cover" />
          </div>
        </div>
      )}

      {/* OPTIONAL watercolor frame texture — only when the real asset is present. */}
      {USE_REAL_ARTWORK && (
        <div className="absolute inset-0 pointer-events-none">
          {/* eslint-disable-next-line @next/next/no-img-element -- decorative texture, no optimization needed */}
          <img src={radarFrameSrc()} alt="" className="w-full h-full object-contain opacity-40" />
        </div>
      )}

      <svg viewBox="0 0 360 264" className="relative w-full block" role="img" aria-label="Your theme radar">
        {/* Guide rings */}
        {RINGS.map((frac) => (
          <polygon
            key={frac}
            points={ring(frac)}
            fill="none"
            stroke="#D4C8B0"
            strokeWidth={frac === 1 ? 1.1 : 0.6}
            opacity={frac === 1 ? 0.9 : 0.55}
          />
        ))}

        {/* Spokes + axis labels */}
        {axes.map((s, i) => {
          const outer = point(R, i)
          const lp = point(LABEL_R, i)
          const cos = Math.cos(angleRad(i))
          const sin = Math.sin(angleRad(i))
          const anchor = cos > 0.3 ? 'start' : cos < -0.3 ? 'end' : 'middle'
          const dy = sin > 0.3 ? '0.7em' : sin < -0.3 ? '-0.2em' : '0.32em'
          return (
            <g key={s.key}>
              <line x1={CX} y1={CY} x2={outer.x} y2={outer.y} stroke="#D4C8B0" strokeWidth={0.6} opacity={0.55} />
              <text
                x={lp.x}
                y={lp.y}
                dy={dy}
                textAnchor={anchor}
                className="font-lora"
                fontSize={10}
                fill="#8A7E6A"
              >
                {s.label}
              </text>
            </g>
          )
        })}

        {/* Data polygon — only when there's real signal. */}
        {hasSignal && (
          <>
            <polygon
              points={polygonPoints(axes.map((s) => R * Math.max(0, Math.min(1, s.score))))}
              fill="#B89968"
              fillOpacity={0.28}
              stroke="#8A7340"
              strokeWidth={1.4}
              strokeLinejoin="round"
            />
            {axes.map((s, i) => {
              const p = point(R * Math.max(0, Math.min(1, s.score)), i)
              return <circle key={s.key} cx={p.x} cy={p.y} r={2.1} fill="#8A7340" />
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
