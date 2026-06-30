// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait map (Phase B2). A SECOND view of the SAME theme_scores the radar
// uses — a spatial arrangement the user can toggle to. Pure SVG, no library.
//
// • The DOMINANT axis (highest score) is the CENTRAL node at (CX,CY), r=0. On a tie
//   the FIRST axis in the frozen octagon order wins (axes arrive already ordered, so
//   a strict `>` keeps the earliest max) — deterministic, stable on reopen.
// • The other 7 axes ring around it at even angular spacing, with distance-from-center
//   INVERSELY proportional to score: radius = R_FLOOR + (R_OUTER−R_FLOOR)·(1−score).
//   Closer = higher score. This distance IS the data — the same numbers as the radar.
//   Angular position is layout-only and carries NO meaning; only distance is data.
// • Same 360×264 viewBox / center as PortraitRadar, so it sits in the SAME κάδρο with
//   the same frame (USE_RADAR_FRAME + radarFrameSrc at 85%) and watermark treatment.
// • Empty / all-zero → the same calm "keep answering" line, never a degenerate blob.
// ─────────────────────────────────────────────────────────────────────────────
import Image from 'next/image'
import type { SelfPortraitThemeScore } from '@/lib/api'
import { USE_RADAR_FRAME, radarFrameSrc } from './Artwork'

// Geometry — identical viewBox/center to PortraitRadar so the frame lines up.
const CX = 180
const CY = 124
const R_OUTER = 84 // distance for a score-0 outer node (farthest from center)
const R_FLOOR = 22 // distance for a score-1 outer node (closest, never on the center)
const OUTER_COUNT = 7
const STEP = 360 / OUTER_COUNT // even angular spacing for the 7 ring nodes
const LABEL_GAP = 10 // radial offset of a node's label, outward from the node

function pointAt(radius: number, angleDeg: number): { x: number; y: number } {
  const a = (angleDeg * Math.PI) / 180
  return { x: CX + radius * Math.cos(a), y: CY + radius * Math.sin(a) }
}

export function PortraitMap({
  scores,
  watermarkUrl = null,
}: {
  scores: SelfPortraitThemeScore[]
  watermarkUrl?: string | null
}) {
  const axes = scores ?? []
  const hasSignal = axes.length > 0 && axes.some((s) => s.score > 0)

  // Same derived-string watermark gate as the radar: blank/whitespace URL → nothing,
  // so next/image never renders a broken/"?" placeholder.
  const watermark =
    typeof watermarkUrl === 'string' && watermarkUrl.trim().length > 0 ? watermarkUrl : null

  // Dominant axis = highest score; tie → first in frozen order (strict `>`). It is the
  // central node and is excluded from the ring.
  let dominantIdx = 0
  for (let i = 1; i < axes.length; i++) {
    if (axes[i].score > axes[dominantIdx].score) dominantIdx = i
  }
  const center = axes[dominantIdx]

  // The 7 outer nodes, in frozen order minus the dominant, at even angles; radius
  // inversely proportional to score (closer = higher). Angle is layout-only, not data.
  const outer = axes
    .map((s, i) => ({ s, i }))
    .filter((e) => e.i !== dominantIdx)
    .map((e, k) => {
      const angle = -90 + k * STEP
      const score = Math.max(0, Math.min(1, e.s.score))
      const radius = R_FLOOR + (R_OUTER - R_FLOOR) * (1 - score)
      return { key: e.s.key, label: e.s.label, angle, radius, node: pointAt(radius, angle) }
    })

  return (
    <div className="relative w-full max-w-[320px] mx-auto">
      {/* Faint persona watermark — ready-state only, behind everything, screen-only.
          Gated on a non-empty URL so an absent/blank portrait never shows a "?". */}
      {watermark && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="relative w-[58%] aspect-square rounded-full overflow-hidden opacity-[0.07]">
            <Image src={watermark} alt="" fill sizes="200px" className="object-cover" />
          </div>
        </div>
      )}

      {/* Same optional watercolor frame as the radar (USE_RADAR_FRAME + 85% opacity). */}
      {USE_RADAR_FRAME && (
        <div className="absolute inset-0 pointer-events-none">
          {/* eslint-disable-next-line @next/next/no-img-element -- decorative texture, no optimization needed */}
          <img src={radarFrameSrc()} alt="" className="w-full h-full object-contain opacity-[0.85]" />
        </div>
      )}

      <svg viewBox="0 0 360 264" className="relative w-full block" role="img" aria-label="Your theme map">
        {hasSignal && center && (
          <>
            {/* DECORATIVE radial tethers (center → each outer node). Purely aesthetic:
                we have NO theme-to-theme relationship data, so these imply nothing and
                are aria-hidden. No UI copy references them. */}
            <g aria-hidden="true">
              {outer.map((o) => (
                <line
                  key={`tether-${o.key}`}
                  x1={CX}
                  y1={CY}
                  x2={o.node.x}
                  y2={o.node.y}
                  stroke="#B89968"
                  strokeWidth={0.6}
                  strokeDasharray="2 3"
                  opacity={0.4}
                />
              ))}
            </g>

            {/* Outer nodes + labels */}
            {outer.map((o) => {
              const cos = Math.cos((o.angle * Math.PI) / 180)
              const sin = Math.sin((o.angle * Math.PI) / 180)
              const anchor = cos > 0.3 ? 'start' : cos < -0.3 ? 'end' : 'middle'
              const dy = sin > 0.3 ? '0.9em' : sin < -0.3 ? '-0.4em' : '0.32em'
              const lp = pointAt(o.radius + LABEL_GAP, o.angle)
              return (
                <g key={o.key}>
                  <circle cx={o.node.x} cy={o.node.y} r={3.4} fill="#8A7340" />
                  <text
                    x={lp.x}
                    y={lp.y}
                    dy={dy}
                    textAnchor={anchor}
                    className="font-lora"
                    fontSize={10}
                    fill="#8A7E6A"
                  >
                    {o.label}
                  </text>
                </g>
              )
            })}

            {/* Central (dominant) node — larger, ink label below it. */}
            <circle cx={CX} cy={CY} r={5} fill="#B89968" stroke="#8A7340" strokeWidth={1} />
            <text
              x={CX}
              y={CY}
              dy="1.7em"
              textAnchor="middle"
              className="font-lora"
              fontSize={11}
              fill="#1F1B14"
            >
              {center.label}
            </text>
          </>
        )}
      </svg>

      {/* No-signal calm line — same treatment as the radar, never a count. */}
      {!hasSignal && (
        <p className="font-lora text-[13px] text-charcoal leading-[1.6] text-center mt-1">
          Keep answering — your portrait takes its shape as you go.
        </p>
      )}
    </div>
  )
}
