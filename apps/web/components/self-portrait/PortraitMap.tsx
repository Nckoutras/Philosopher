// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait map (v4 — static hand-drawn territories). A SECOND view of the SAME
// theme_scores the radar uses. The base is now a HAND-DRAWN parchment map asset with 5
// fixed blank territories (1 large, 1 medium, 3 small). We rank the 8 themes by score and
// print the NAME + caption of each top-5 theme onto the territory matching its RANK
// (rank-1 → largest … rank-5 → the last small one). Ranks 6-8 do not appear.
//
// This preserves "stable world" by RANK: a theme's slot is its CURRENT rank, so when the
// ranking shifts the names move between the fixed territories — recognisable over time and
// trivial to diff then-vs-now. No procedural shapes; the map art IS the territory.
//
// • BASE: map-territories.webp at full opacity (it IS the map — no dimming; no baked
//   compass to fight). A FULL background sibling OUTSIDE the <svg> (like the radar's
//   frame/watermark), so it never enters the share-card canvas or taints it.
// • SLOTS: 5 fixed viewBox anchors (founder-confirmed centres), ordered by rank. Each
//   carries a wrap width (large/medium 18 ch/line; the three small corner slots 14 ch/line
//   so a caption never runs off the frame). Empty slots (fewer than 5 scored themes)
//   render nothing.
// • LABELS: stacked + centered on the slot anchor — name (Lora 13, ink, vellum halo;
//   rank-1 weight 600) then the sub-caption below, WRAPPED to ≤3 lines (Lora 9.5, sepia,
//   same halo) from selfPortraitMapCaptions.ts. The halo keeps small-slot captions legible
//   where they overrun the blank onto the faint contour lines.
// • NO connector paths between territories — we have NO theme-to-theme relationship data,
//   and no UI copy anywhere may imply one.
// • Compass rose + needle: the rose.webp overlay + needle stay in the data-share-omit group
//   (the share pipeline strips it — the <image> can't resolve there, avoiding an orphaned
//   needle). The needle points at SLOT_LARGE — the rank-1 (dominant) territory.
// • Empty / all-zero → the same calm "keep answering" line, never a degenerate blob.
// ─────────────────────────────────────────────────────────────────────────────
import Image from 'next/image'
import type { SelfPortraitThemeScore } from '@/lib/api'
import { MAP_CAPTIONS } from '@/lib/selfPortraitMapCaptions'

// Same-origin hand-drawn territory map (v4 asset). Full-bleed background, full opacity.
const MAP_SRC = '/self-portrait/map-territories.webp'

// ── FIXED territory slots (viewBox 360×264), in RANK order ─────────────────────
// Founder-confirmed centres of the 5 blank territories in the map art. rank-1 → LARGE,
// rank-2 → MEDIUM, rank-3/4/5 → the three small ones (top-left, bottom-left, bottom-
// center). `maxChars` is the per-slot caption wrap width: the three small CORNER slots use
// a tighter width so a wide caption never runs off the viewBox edge.
const SLOTS: Array<{ x: number; y: number; maxChars: number }> = [
  { x: 252.0, y: 79.2, maxChars: 18 }, // LARGE  — rank 1 (top-right)
  { x: 118.8, y: 134.6, maxChars: 18 }, // MEDIUM — rank 2 (center)
  { x: 57.6, y: 55.4, maxChars: 14 }, // SMALL  — rank 3 (top-left corner)
  { x: 52.2, y: 211.2, maxChars: 14 }, // SMALL  — rank 4 (bottom-left corner)
  { x: 171.0, y: 212.5, maxChars: 14 }, // SMALL  — rank 5 (bottom-center)
]

// Decorative compass rose overlay (same-origin asset shared with the radar) + a dynamic
// needle, lower-right. The rose+needle group is tagged data-share-omit so the share
// pipeline strips it (the <image> can't resolve there — avoids an orphaned needle).
const ROSE_SRC = '/self-portrait/rose.webp'
const ROSE_CX = 310.7 // 86.3% of the 360-wide viewBox
const ROSE_CY = 214.9 // 81.4% of the 264-tall viewBox
const ROSE_W = 44 // decorative scale (half-width 22)
const NEEDLE_LEN = 22 // reaches the rose's outer edge

// Wrap a caption to at most `maxLines` lines of ≤`maxChars` chars (greedy word-wrap) so it
// stays inside its slot and the viewBox. Deterministic — no layout measurement, so it
// renders identically on server and client. Small corner slots pass a tighter maxChars.
function wrapCaption(text: string, maxChars: number, maxLines = 3): string[] {
  const words = text.split(' ')
  const lines: string[] = []
  let cur = ''
  for (const w of words) {
    const cand = cur ? `${cur} ${w}` : w
    if (cur && cand.length > maxChars && lines.length < maxLines - 1) {
      lines.push(cur)
      cur = w
    } else {
      cur = cand
    }
  }
  if (cur) lines.push(cur)
  return lines
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

  // Rank the axes by score desc, tie-break by frozen (incoming) order via a stable index —
  // deterministic and stable on reopen. Keep only real signal; take the top-5.
  const ranked = axes
    .map((s, i) => ({ s, i }))
    .filter((e) => e.s.score > 0)
    .sort((a, b) => b.s.score - a.s.score || a.i - b.i)
    .map((e) => e.s)

  // Assign each top-5 theme to the slot matching its rank (rank-1 → SLOTS[0] = LARGE …).
  const assigned = ranked.slice(0, SLOTS.length).map((axis, i) => ({
    axis,
    slot: SLOTS[i],
    isDominant: i === 0,
  }))

  // Compass needle → SLOT_LARGE (the rank-1 / dominant territory). Decorative, so it only
  // shows when there's signal (a rank-1 exists). Same atan2 + triangle-tip math as before,
  // just a fixed target coordinate. Kept in the data-share-omit group.
  let needle: { bx: number; by: number; tip: string } | null = null
  if (hasSignal && assigned.length > 0) {
    const target = SLOTS[0]
    const theta = Math.atan2(target.y - ROSE_CY, target.x - ROSE_CX)
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
    <div className="relative w-full">
      {/* MAP container — hand-drawn territory art + watermark + the shareable <svg>. */}
      <div className="relative w-full max-w-[320px] mx-auto">
        {/* FULL hand-drawn map — the base layer at full opacity; a sibling OUTSIDE the
            <svg> so it never enters the share canvas. */}
        <div className="absolute inset-0 rounded-md overflow-hidden pointer-events-none">
          {/* eslint-disable-next-line @next/next/no-img-element -- decorative full-bleed map, no optimization needed */}
          <img src={MAP_SRC} alt="" className="w-full h-full object-cover" />
        </div>

        {/* Faint persona watermark — ready-state only, above the map, screen-only.
            Gated on a non-empty URL so an absent/blank portrait never shows a "?". */}
        {watermark && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="relative w-[52%] aspect-square rounded-full overflow-hidden opacity-[0.07]">
              <Image src={watermark} alt="" fill sizes="200px" className="object-cover" />
            </div>
          </div>
        )}

        <svg viewBox="0 0 360 264" className="relative w-full block" role="img" aria-label="Your theme map">
          {hasSignal && assigned.length > 0 && (
            <>
              {/* Rank-assigned labels — name (dominant=ink #1F1B14, others=bronze-dark
                  #8A7340) + wrapped sub-caption (sepia) centered on the slot anchor, each with
                  a vellum halo (paint-order stroke) so they read over the parchment and, on
                  small slots, the faint contour lines. The dominant also gets an X marker. */}
              {assigned.map(({ axis, slot, isDominant }) => {
                const capLines = MAP_CAPTIONS[axis.key]
                  ? wrapCaption(MAP_CAPTIONS[axis.key], slot.maxChars)
                  : []
                return (
                  <g key={axis.key}>
                    <text
                      x={slot.x}
                      y={slot.y}
                      textAnchor="middle"
                      className="font-lora"
                      fontSize={13}
                      fontWeight={isDominant ? 600 : 500}
                      fill={isDominant ? '#1F1B14' : '#5C4A2E'}
                      stroke="#EFE3CC"
                      strokeWidth={2.8}
                      strokeLinejoin="round"
                      paintOrder="stroke"
                    >
                      {axis.label}
                    </text>
                    {capLines.length > 0 && (
                      <text
                        x={slot.x}
                        y={slot.y}
                        textAnchor="middle"
                        className="font-lora"
                        fontSize={11}
                        fill="#8A7E6A"
                        stroke="#EFE3CC"
                        strokeWidth={2.0}
                        strokeLinejoin="round"
                        paintOrder="stroke"
                      >
                        {capLines.map((ln, j) => (
                          <tspan key={j} x={slot.x} dy={j === 0 ? 16 : 13}>
                            {ln}
                          </tspan>
                        ))}
                      </text>
                    )}

                    {/* X-marks-the-spot — a discreet hand-drawn cross above the DOMINANT
                        territory's name (clear of name + caption below). Vellum halo underlay
                        (stroke 3.2) then bronze-dark strokes (1.4) so it reads over parchment.
                        NOT in data-share-omit → it appears on the shared card too. */}
                    {isDominant &&
                      (() => {
                        const cx = slot.x
                        const cy = slot.y - 22
                        const h = 4
                        return (
                          <g strokeLinecap="round" fill="none">
                            {/* halo underlay */}
                            <line x1={cx - h} y1={cy - h} x2={cx + h} y2={cy + h} stroke="#EFE3CC" strokeWidth={3.2} />
                            <line x1={cx - h} y1={cy + h} x2={cx + h} y2={cy - h} stroke="#EFE3CC" strokeWidth={3.2} />
                            {/* cross */}
                            <line x1={cx - h} y1={cy - h} x2={cx + h} y2={cy + h} stroke="#8A7340" strokeWidth={1.4} />
                            <line x1={cx - h} y1={cy + h} x2={cx + h} y2={cy - h} stroke="#8A7340" strokeWidth={1.4} />
                          </g>
                        )
                      })()}
                  </g>
                )
              })}

              {/* Decorative compass rose + needle → SLOT_LARGE (rank-1). data-share-omit →
                  the share pipeline removes the whole group (rose <image> + needle) so the
                  shared map card shows neither, never an orphaned needle. */}
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
      </div>

      {/* No-signal calm line — same treatment as the radar, never a count. */}
      {!hasSignal && (
        <p className="font-lora text-[13px] text-charcoal leading-[1.6] text-center mt-1">
          Keep answering — your portrait takes its shape as you go.
        </p>
      )}
    </div>
  )
}
