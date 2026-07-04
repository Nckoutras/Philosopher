// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait map (v3 — data-driven "stable-world" territories). A SECOND view of the
// SAME theme_scores the radar uses. Each theme is a COUNTRY at a FIXED anchor forever
// ("stable world" — a theme never relocates, only grows/shrinks), so the user recognizes
// their map over time and a future then-vs-now view is trivial. Pure SVG path math over a
// parchment terrain image, no library.
//
// • FIXED LAYOUT: the 8 frozen PORTRAIT_AXES slugs each own a hardcoded viewBox anchor
//   (ANCHORS). A theme's territory always centers on its anchor.
// • TERRITORY: a seeded, deterministic organic closed path around the anchor. Vertex radii
//   are jittered by a hash of the theme SLUG (stable across reopens — a coastline never
//   changes shape), smoothed catmull-rom → cubic bezier. AREA ∝ score (radius ∝ √score),
//   so area — not radius — reads proportional. Zero-score themes DO NOT render.
// • CAPS (applied to the MAX jittered extent JITTER_MAX×baseR, never just baseR):
//     – overlap: territories may touch, never swallow — capped so no vertex reaches within
//       (1 − OVERLAP_FRAC) of a neighbour's anchor.
//     – rose: no vertex enters the lower-right compass-rose disc (+ margin).
// • The terrain (map-terrain.webp) is a FULL background — an HTML sibling OUTSIDE the
//   <svg> (like the radar's frame/watermark), so it never enters the share-card canvas or
//   taints it. This view carries NO walnut frame — the frame is Shape-view only.
// • NO connector paths between territories — we have NO theme-to-theme relationship data,
//   and no UI copy anywhere may imply one.
// • Compass rose + needle: UNCHANGED behaviour — the rose+needle group is tagged
//   data-share-omit so the share pipeline strips it (the <image> can't resolve there —
//   avoids an orphaned needle on the shared card).
// • Empty / all-zero → the same calm "keep answering" line, never a degenerate blob.
// ─────────────────────────────────────────────────────────────────────────────
import Image from 'next/image'
import type { SelfPortraitThemeScore } from '@/lib/api'
import { MAP_CAPTIONS } from '@/lib/selfPortraitMapCaptions'

// Same-origin parchment terrain (B2 asset). Inlined like portraitShareCard's FRAME_SRC.
const MAP_TERRAIN_SRC = '/self-portrait/map-terrain.webp'

// ── FIXED anchors (viewBox 360×264) ───────────────────────────────────────────
// The 8 frozen PORTRAIT_AXES slugs → their permanent territory centers. A balanced
// spread whose lower-right corner is deliberately left empty for the compass rose.
// These positions NEVER change: the "stable world" contract.
const ANCHORS: Record<string, { x: number; y: number }> = {
  identity: { x: 80, y: 60 },
  fear: { x: 188, y: 54 },
  freedom: { x: 294, y: 66 },
  desire: { x: 74, y: 142 },
  doubt: { x: 186, y: 128 },
  duty: { x: 290, y: 136 },
  connection: { x: 108, y: 210 },
  meaning: { x: 216, y: 206 },
}

// ── Territory geometry ─────────────────────────────────────────────────────────
const MAX_R = 44 // baseR of a score-1.0 (dominant) territory before caps
const VERTS = 10 // polygon vertices per coastline (before bezier smoothing)
const JITTER_MIN = 0.82 // per-vertex radius factor lower bound
const JITTER_MAX = 1.18 // …upper bound — a vertex can reach 1.18×baseR, so ALL caps
//                          divide by JITTER_MAX to bound the MAX jittered extent.
const OVERLAP_FRAC = 0.9 // a territory's farthest vertex may reach at most 90% of the
//                          way to its nearest neighbour's anchor (touch, never swallow).
const ROSE_MARGIN = 6 // px clearance between the farthest vertex and the rose disc edge.

// Decorative compass rose overlay (same-origin asset shared with the radar) + a dynamic
// needle, lower-right. The rose+needle group is tagged data-share-omit so the share
// pipeline strips it (the <image> can't resolve there — avoids an orphaned needle).
const ROSE_SRC = '/self-portrait/rose.webp'
const ROSE_CX = 310.7 // 86.3% of the 360-wide viewBox
const ROSE_CY = 214.9 // 81.4% of the 264-tall viewBox
const ROSE_W = 44 // decorative scale (half-width 22)
const ROSE_HALF = ROSE_W / 2
const NEEDLE_LEN = 22 // reaches the rose's outer edge

// Deterministic [0,1) hash of a string (xfnv1a + avalanche). Seeded by `${slug}:${vertex}`
// so a theme's coastline is identical on every reopen — only its scale (baseR) changes.
// No Math.random(): stable-world shapes must be reproducible forever.
function hash01(str: string): number {
  let h = 2166136261 >>> 0
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  h += h << 13
  h ^= h >>> 7
  h += h << 3
  h ^= h >>> 17
  h += h << 5
  return ((h >>> 0) % 100000) / 100000
}

// Organic closed territory path: VERTS jittered radial points around (cx,cy), smoothed
// with a closed Catmull-Rom → cubic-bezier conversion. Pure path math — no dependency.
function territoryPath(cx: number, cy: number, baseR: number, slug: string): string {
  const pts: Array<{ x: number; y: number }> = []
  for (let i = 0; i < VERTS; i++) {
    const ang = (i / VERTS) * Math.PI * 2
    const j = JITTER_MIN + (JITTER_MAX - JITTER_MIN) * hash01(`${slug}:${i}`)
    const r = baseR * j
    pts.push({ x: cx + r * Math.cos(ang), y: cy + r * Math.sin(ang) })
  }
  const n = pts.length
  let d = `M ${pts[0].x.toFixed(2)} ${pts[0].y.toFixed(2)}`
  for (let i = 0; i < n; i++) {
    const p0 = pts[(i - 1 + n) % n]
    const p1 = pts[i]
    const p2 = pts[(i + 1) % n]
    const p3 = pts[(i + 2) % n]
    const c1x = p1.x + (p2.x - p0.x) / 6
    const c1y = p1.y + (p2.y - p0.y) / 6
    const c2x = p2.x - (p3.x - p1.x) / 6
    const c2y = p2.y - (p3.y - p1.y) / 6
    d += ` C ${c1x.toFixed(2)} ${c1y.toFixed(2)} ${c2x.toFixed(2)} ${c2y.toFixed(2)} ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`
  }
  return `${d} Z`
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
  // (lower index first) so it's deterministic and stable on reopen. rankOf[i] === 0 is the
  // dominant. Drives the dominant's slightly stronger fill and the strip's Pull/Edge lines.
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

  // Anchored axes that actually have a signal — the only ones that produce a territory.
  const placed = axes.filter((s) => s.score > 0 && ANCHORS[s.key])

  // Distance from an anchor to its NEAREST other placed anchor — the overlap cap basis.
  const nearestAnchorDist = (key: string): number => {
    const a = ANCHORS[key]
    let min = Infinity
    for (const o of placed) {
      if (o.key === key) continue
      const b = ANCHORS[o.key]
      const d = Math.hypot(a.x - b.x, a.y - b.y)
      if (d < min) min = d
    }
    return min === Infinity ? MAX_R : min
  }

  // Build each territory. AREA ∝ score → radius ∝ √score. Both caps bound the MAX jittered
  // extent (JITTER_MAX × baseR), NOT baseR — a vertex can reach 1.18×baseR, so we divide
  // each cap by JITTER_MAX before clamping baseR.
  const territories = axes
    .map((s, i) => ({ s, i }))
    .filter((e) => e.s.score > 0 && ANCHORS[e.s.key])
    .map((e) => {
      const a = ANCHORS[e.s.key]
      const wantR = Math.sqrt(e.s.score) * MAX_R
      const overlapCap = (OVERLAP_FRAC * nearestAnchorDist(e.s.key)) / JITTER_MAX
      const roseDist = Math.hypot(a.x - ROSE_CX, a.y - ROSE_CY)
      const roseCap = (roseDist - ROSE_HALF - ROSE_MARGIN) / JITTER_MAX
      const baseR = Math.max(0, Math.min(wantR, overlapCap, roseCap))
      return {
        key: e.s.key,
        label: e.s.label,
        score: e.s.score,
        isDominant: e.i === dominantIdx,
        anchor: a,
        path: territoryPath(a.x, a.y, baseR, e.s.key),
      }
    })

  // Compass needle → the highest-scoring NON-dominant territory's anchor (a 1:1 port of the
  // prior "highest outer node" target; dominant excluded, best of the rest). Decorative:
  // null when nothing qualifies, so it never points at nothing. Needle math UNCHANGED.
  const needleTarget = territories
    .filter((t) => !t.isDominant)
    .reduce<(typeof territories)[number] | null>(
      (best, o) => (best && best.score >= o.score ? best : o),
      null,
    )
  const showCompass = hasSignal && !!needleTarget && needleTarget.score > 0
  let needle: { bx: number; by: number; tip: string } | null = null
  if (showCompass && needleTarget) {
    const theta = Math.atan2(needleTarget.anchor.y - ROSE_CY, needleTarget.anchor.x - ROSE_CX)
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

  // Single-axis strip lines (Pull = dominant, Edge = runner-up) from the SAME caption map.
  // No cross-theme sentence: the data cannot support theme-to-theme relationships.
  const ranked = axes
    .map((s, i) => ({ s, i }))
    .filter((e) => e.s.score > 0)
    .sort((a, b) => b.s.score - a.s.score || a.i - b.i)
    .map((e) => e.s)
  const pullCaption = ranked[0] ? (MAP_CAPTIONS[ranked[0].key] ?? null) : null
  const edgeCaption = ranked[1] ? (MAP_CAPTIONS[ranked[1].key] ?? null) : null

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
        {hasSignal && territories.length > 0 && (
          <>
            {/* Territories — pure vector paths (serialize fine into the share card). The
                dominant carries a slightly stronger fill; every border is the same bold
                sepia. Drawn first so labels (next pass) always sit on top. */}
            {territories.map((t) => (
              <path
                key={`terr-${t.key}`}
                d={t.path}
                fill="#B89968"
                fillOpacity={t.isDominant ? 0.12 : 0.09}
                stroke="#8A7340"
                strokeWidth={1.4}
                strokeLinejoin="round"
              />
            ))}

            {/* Labels pass — name (ink) + sub-caption (sepia) at the anchor, each with a
                vellum halo (paint-order stroke) so they read over fill and parchment. */}
            {territories.map((t) => (
              <g key={`label-${t.key}`}>
                <text
                  x={t.anchor.x}
                  y={t.anchor.y}
                  textAnchor="middle"
                  className="font-lora"
                  fontSize={t.isDominant ? 14 : 13}
                  fontWeight={t.isDominant ? 600 : 500}
                  fill="#1F1B14"
                  stroke="#EFE3CC"
                  strokeWidth={2.8}
                  strokeLinejoin="round"
                  paintOrder="stroke"
                >
                  {t.label}
                </text>
                {MAP_CAPTIONS[t.key] && (
                  <text
                    x={t.anchor.x}
                    y={t.anchor.y}
                    dy="1.35em"
                    textAnchor="middle"
                    className="font-lora"
                    fontSize={10}
                    fill="#8A7E6A"
                    stroke="#EFE3CC"
                    strokeWidth={2.2}
                    strokeLinejoin="round"
                    paintOrder="stroke"
                  >
                    {MAP_CAPTIONS[t.key]}
                  </text>
                )}
              </g>
            ))}

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

      {/* Single-axis strip — two lines, inside the card, below the map. Each line names ONE
          theme via its own caption; NO cross-theme relationship is implied or stated. */}
      {hasSignal && pullCaption && (
        <div className="relative mt-3 space-y-1 text-center">
          <p className="font-lora text-[12px] text-charcoal leading-[1.5]">
            <span className="text-sepia uppercase tracking-[0.14em] text-[10px]">Pull</span>
            {' — '}
            {pullCaption}
          </p>
          {edgeCaption && (
            <p className="font-lora text-[12px] text-charcoal leading-[1.5]">
              <span className="text-sepia uppercase tracking-[0.14em] text-[10px]">Edge</span>
              {' — '}
              {edgeCaption}
            </p>
          )}
        </div>
      )}

      {/* No-signal calm line — same treatment as the radar, never a count. */}
      {!hasSignal && (
        <p className="font-lora text-[13px] text-charcoal leading-[1.6] text-center mt-1">
          Keep answering — your portrait takes its shape as you go.
        </p>
      )}
    </div>
  )
}
