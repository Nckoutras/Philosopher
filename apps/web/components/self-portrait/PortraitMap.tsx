// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait map (Phase B2, territorial rewrite). A SECOND view of the SAME
// theme_scores the radar uses — an old-world "territories around a capital" map the
// user can toggle to. Pure SVG over a parchment terrain image, no library.
//
// • The DOMINANT axis (rank 1 by score) is the CENTRAL "capital" node. Ties resolve to
//   the FIRST axis in the frozen octagon order (stable on reopen).
// • The other 7 axes ring around it. Angular position comes from the frozen axis order
//   (layout-only, carries NO meaning). Distance from center is driven by ORDINAL RANK
//   (2nd-highest closest … 8th-highest farthest), stepped evenly — ranks read cleaner on
//   a map than raw-score distances, and no single number is decodable from a radius.
// • The terrain (map-terrain.webp) is a FULL background — an HTML sibling OUTSIDE the
//   <svg> (like the radar's frame/watermark), so it never enters the share-card canvas
//   or taints it. This view carries NO walnut frame — the frame is Shape-view only.
// • Dashed connector paths are DECORATIVE ONLY, aria-hidden. We have no theme-to-theme
//   relationship data; nothing here (and no UI copy anywhere) implies one.
// • Empty / all-zero → the same calm "keep answering" line, never a degenerate blob.
// ─────────────────────────────────────────────────────────────────────────────
import Image from 'next/image'
import type { SelfPortraitThemeScore } from '@/lib/api'

// Same-origin parchment terrain (B2 asset). Inlined like portraitShareCard's FRAME_SRC.
const MAP_TERRAIN_SRC = '/self-portrait/map-terrain.webp'

// Geometry — centered in the 360×264 viewBox (no frame to align to on this view).
const CX = 180
const CY = 132
const R_MIN = 36 // radius of the rank-2 node (closest ring to the capital)
const R_MAX = 88 // radius of the rank-8 node (farthest ring)
const OUTER_COUNT = 7
const STEP = 360 / OUTER_COUNT // even angular spacing for the 7 ring nodes
const LABEL_GAP = 11 // radial offset of a node's label, outward from the node

// Decorative compass rose overlay (same-origin asset shared with the radar) + a dynamic
// needle. Lower-right, clear of the outer node rings — verified: dist capital→rose ≈
// 154.8 > R_MAX 88 + rose-half 22. The rose+needle group is tagged data-share-omit so
// the share pipeline strips it (the <image> can't resolve there — avoids an orphaned
// needle on the shared card).
const ROSE_SRC = '/self-portrait/rose.webp'
const ROSE_CX = 310.7 // 86.3% of the 360-wide viewBox
const ROSE_CY = 214.9 // 81.4% of the 264-tall viewBox
const ROSE_W = 44 // decorative scale (half-width 22)
const NEEDLE_LEN = 22 // reaches the rose's outer edge

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

  // Ordinal rank of every axis: sort indices by score desc, tie-break by frozen order
  // (lower index first) so it's deterministic and stable on reopen. rankOf[i] === 0 is
  // the dominant (capital); 1..7 are the outer nodes' ranks.
  const rankOf = new Array<number>(axes.length)
  axes
    .map((_s, i) => i)
    .sort((a, b) => {
      const d = axes[b].score - axes[a].score
      return d !== 0 ? d : a - b
    })
    .forEach((idx, r) => {
      rankOf[idx] = r
    })
  const dominantIdx = axes.length > 0 ? axes.findIndex((_s, i) => rankOf[i] === 0) : -1
  const center = dominantIdx >= 0 ? axes[dominantIdx] : null

  // The 7 outer nodes in FROZEN order minus the dominant, at even angles (layout-only).
  // Radius steps evenly by ordinal RANK: rank 1 (2nd overall) closest, rank 7 farthest.
  const outer = axes
    .map((s, i) => ({ s, i }))
    .filter((e) => e.i !== dominantIdx)
    .map((e, k) => {
      const angle = -90 + k * STEP
      const t = (rankOf[e.i] - 1) / (OUTER_COUNT - 1) // 0 (closest) … 1 (farthest)
      const radius = R_MIN + (R_MAX - R_MIN) * t
      return { key: e.s.key, label: e.s.label, score: e.s.score, angle, radius, node: pointAt(radius, angle) }
    })

  // Compass needle → the highest-scoring OUTER node (the capital's runner-up). Decorative:
  // null when there's no signal or no outer node has any score, so it never points at
  // nothing. atan2 from the rose center toward that node's actual position.
  const needleTarget = outer.reduce<(typeof outer)[number] | null>(
    (best, o) => (best && best.score >= o.score ? best : o),
    null,
  )
  const showCompass = hasSignal && !!needleTarget && needleTarget.score > 0
  let needle: { bx: number; by: number; tip: string } | null = null
  if (showCompass && needleTarget) {
    const theta = Math.atan2(needleTarget.node.y - ROSE_CY, needleTarget.node.x - ROSE_CX)
    const baseLen = NEEDLE_LEN - 6 // line stops short; a triangle forms the tip
    const bx = ROSE_CX + baseLen * Math.cos(theta)
    const by = ROSE_CY + baseLen * Math.sin(theta)
    const tipX = ROSE_CX + NEEDLE_LEN * Math.cos(theta)
    const tipY = ROSE_CY + NEEDLE_LEN * Math.sin(theta)
    const perp = theta + Math.PI / 2
    const hw = 3 // tip half-width
    const pt = (x: number, y: number) => `${x.toFixed(1)},${y.toFixed(1)}`
    const tip = `${pt(tipX, tipY)} ${pt(bx + hw * Math.cos(perp), by + hw * Math.sin(perp))} ${pt(bx - hw * Math.cos(perp), by - hw * Math.sin(perp))}`
    needle = { bx, by, tip }
  }

  return (
    <div className="relative w-full max-w-[320px] mx-auto">
      {/* FULL parchment terrain — background layer, sibling OUTSIDE the <svg> so it never
          enters the share canvas. No frame on this view. */}
      <div className="absolute inset-0 rounded-md overflow-hidden pointer-events-none">
        {/* eslint-disable-next-line @next/next/no-img-element -- decorative full-bleed terrain, no optimization needed */}
        <img src={MAP_TERRAIN_SRC} alt="" className="w-full h-full object-cover" />
      </div>

      {/* Faint persona watermark — ready-state only, above the terrain, screen-only.
          Gated on a non-empty URL so an absent/blank portrait never shows a "?". */}
      {watermark && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="relative w-[52%] aspect-square rounded-full overflow-hidden opacity-[0.07]">
            <Image src={watermark} alt="" fill sizes="200px" className="object-cover" />
          </div>
        </div>
      )}

      <svg viewBox="0 0 360 264" className="relative w-full block" role="img" aria-label="Your theme map">
        {hasSignal && center && (
          <>
            {/* DECORATIVE radial tethers (capital → each outer node). Purely aesthetic:
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
                  stroke="#8A7340"
                  strokeWidth={0.7}
                  strokeDasharray="2 3"
                  opacity={0.45}
                />
              ))}
            </g>

            {/* Outer nodes + labels. Labels carry a soft vellum halo (paint-order stroke)
                so they stay readable over the textured parchment. */}
            {outer.map((o) => {
              const cos = Math.cos((o.angle * Math.PI) / 180)
              const sin = Math.sin((o.angle * Math.PI) / 180)
              const anchor = cos > 0.3 ? 'start' : cos < -0.3 ? 'end' : 'middle'
              const dy = sin > 0.3 ? '0.9em' : sin < -0.3 ? '-0.4em' : '0.32em'
              const lp = pointAt(o.radius + LABEL_GAP, o.angle)
              return (
                <g key={o.key}>
                  <circle cx={o.node.x} cy={o.node.y} r={3.4} fill="#8A7340" stroke="#EFE3CC" strokeWidth={0.8} />
                  <text
                    x={lp.x}
                    y={lp.y}
                    dy={dy}
                    textAnchor={anchor}
                    className="font-lora"
                    fontSize={12}
                    fontWeight={500}
                    fill="#5C4A2E"
                    stroke="#EFE3CC"
                    strokeWidth={2.6}
                    strokeLinejoin="round"
                    paintOrder="stroke"
                  >
                    {o.label}
                  </text>
                </g>
              )
            })}

            {/* Central (dominant) "capital" node — larger, with its label below. */}
            <circle cx={CX} cy={CY} r={5.5} fill="#B89968" stroke="#8A7340" strokeWidth={1.2} />
            <text
              x={CX}
              y={CY}
              dy="1.8em"
              textAnchor="middle"
              className="font-lora"
              fontSize={13}
              fontWeight={600}
              fill="#5C4A2E"
              stroke="#EFE3CC"
              strokeWidth={2.8}
              strokeLinejoin="round"
              paintOrder="stroke"
            >
              {center.label}
            </text>

            {/* Decorative compass rose + needle. data-share-omit → the share pipeline
                removes the whole group (rose <image> + needle) so the shared map card
                shows neither, never an orphaned needle. No copy references it. */}
            {needle && (
              <g data-share-omit aria-hidden="true">
                <image
                  href={ROSE_SRC}
                  x={ROSE_CX - ROSE_W / 2}
                  y={ROSE_CY - ROSE_W / 2}
                  width={ROSE_W}
                  height={ROSE_W}
                  opacity={0.9}
                  preserveAspectRatio="xMidYMid meet"
                />
                <line
                  x1={ROSE_CX}
                  y1={ROSE_CY}
                  x2={needle.bx}
                  y2={needle.by}
                  stroke="#8A7340"
                  strokeWidth={1.2}
                  strokeLinecap="round"
                />
                <polygon points={needle.tip} fill="#8A7340" />
                <circle cx={ROSE_CX} cy={ROSE_CY} r={1.6} fill="#8A7340" />
              </g>
            )}
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
