// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait radar (Phase B, art polish). A pure-SVG pentagon of the user's FIVE
// strongest theme axes. No charting library.
//
// • TOP-5 axes only: the 5 highest-scoring axes (tie-break frozen order), arranged in
//   FROZEN relative order at 72° spacing (first at −90°/top). Deterministic + stable.
// • Guides are CIRCLES: 2 dashed inner rings (0.4R, 0.7R) + 1 solid bronze outer ring.
//   Spokes + endpoint dots; a bronze data pentagon (fill 0.3) + vertex dots.
// • CENTER: a raster compass rose (/self-portrait/rose.webp), same-origin, centered,
//   width ≈0.55R, drawn BEHIND the data polygon (the 0.3 fill lets it show through).
// • overflow:visible — the outer labels (fontSize 17) intentionally extend BEYOND the
//   tight viewBox into the wrapper's padding, so the ring fills the plate instead of
//   floating. The wrapper padding (px-4) + the page's perimeter frame padding hold the
//   worst-case label overflow inside the bronze border. NOTE: the share card
//   (portraitShareCard.ts) serializes by viewBox and will clip these overflow labels
//   until its MANDATORY next-PR recomposition — coordinated debt, accepted.
// • κάδρο/frame texture still gated behind USE_RADAR_FRAME (OFF). Watermark ready-only.
// • No signal → the skeleton (rings/spokes/rose) + a calm line, never a count.
// ─────────────────────────────────────────────────────────────────────────────
import Image from 'next/image'
import type { SelfPortraitThemeScore } from '@/lib/api'
import { USE_RADAR_FRAME, radarFrameSrc } from './Artwork'

// Geometry in a 360×270 viewBox sized TIGHT to the ring; labels overflow into padding
// (svg overflow:visible). Verified: with fontSize 17 all 5 labels fit the container
// (viewBox + left-40/right-10/top-4 padding) even in the Connection@198° worst case.
const CX = 180
const CY = 140
const R = 116
const LABEL_R = 126
const TOP_N = 5
const INNER_RINGS = [0.4, 0.7] as const
const ROSE_SRC = '/self-portrait/rose.webp' // same-origin raster compass rose
const ROSE_W = R * 0.55

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
    // px-4 holds the worst-case label overflow (svg overflow:visible) inside the page's
    // perimeter frame; no max-width cap so the ring uses the full plate width.
    <div className="relative w-full mx-auto px-4">
      {/* Faint persona watermark — ready-state only, behind everything, screen-only. */}
      {watermark && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="relative w-[50%] aspect-square rounded-full overflow-hidden opacity-[0.06]">
            <Image src={watermark} alt="" fill sizes="220px" className="object-cover" />
          </div>
        </div>
      )}

      {/* OPTIONAL κάδρο/frame texture — retained but gated on USE_RADAR_FRAME (OFF). */}
      {USE_RADAR_FRAME && (
        <div className="absolute inset-0 pointer-events-none">
          {/* eslint-disable-next-line @next/next/no-img-element -- decorative texture, no optimization needed */}
          <img src={radarFrameSrc()} alt="" className="w-full h-full object-contain" />
        </div>
      )}

      {/* overflow-visible so the outer labels can extend past the tight viewBox. */}
      <svg
        viewBox="0 0 360 270"
        className="relative w-full block overflow-visible"
        style={{ overflow: 'visible' }}
        role="img"
        aria-label="Your theme radar"
      >
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

        {/* Raster compass rose — decorative, centered, BEHIND the data polygon. Same-origin
            so the (next-PR) share canvas won't taint; aria-hidden. */}
        <image
          href={ROSE_SRC}
          x={CX - ROSE_W / 2}
          y={CY - ROSE_W / 2}
          width={ROSE_W}
          height={ROSE_W}
          opacity={0.9}
          preserveAspectRatio="xMidYMid meet"
          aria-hidden="true"
        />

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
                fontSize={17}
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
              fillOpacity={0.4}
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
