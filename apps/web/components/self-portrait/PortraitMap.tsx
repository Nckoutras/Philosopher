// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait map (v5 — hand-drawn territories, re-art). A SECOND view of the SAME
// theme_scores the radar uses. The base is a HAND-DRAWN parchment map asset with 5 baked-in
// anchor markers — a central compass bullseye plus four location dots (top-left, top-right,
// bottom-right, and one over the lake, bottom-left). We rank the 8 themes by score and print
// the NAME + caption of each top-5 theme onto the anchor matching its RANK (rank-1 → the
// central bullseye … rank-5 → the lake). Ranks 6-8 do not appear.
//
// This preserves "stable world" by RANK: a theme's slot is its CURRENT rank, so when the
// ranking shifts the names move between the fixed anchors — recognisable over time and
// trivial to diff then-vs-now. No procedural shapes; the map art IS the territory.
//
// • BASE: map-territories.webp at full opacity (it IS the map). A FULL background sibling
//   OUTSIDE the <svg> (like the radar's frame/watermark), so it never enters the share-card
//   canvas or taints it. The art carries its OWN central compass, so we draw no rose overlay.
// • SLOTS: 5 fixed viewBox anchors (detected centres of the map's markers), ordered by rank.
//   Each carries a wrap width (centre + top-right 18 ch/line; the three corner slots
//   14 ch/line so a caption never runs off the frame). Empty slots (fewer than 5 scored
//   themes) render nothing.
// • LABELS: stacked + centered on the slot anchor — name (Lora 13, ink, vellum halo;
//   rank-1 weight 600) then the sub-caption below, WRAPPED to ≤3 lines (Lora 11, sepia,
//   same halo) from selfPortraitMapCaptions.ts. The halo keeps corner-slot captions legible
//   where they overrun onto the faint contour lines.
// • X-MARKS-THE-SPOT: a discreet cross above the rank-1 (dominant) name, on the central
//   bullseye. NO connector paths between territories — we have NO theme-to-theme relationship
//   data, and no UI copy anywhere may imply one.
// • Empty / all-zero → the same calm "keep answering" line, never a degenerate blob.
// ─────────────────────────────────────────────────────────────────────────────
import Image from 'next/image'
import type { SelfPortraitThemeScore } from '@/lib/api'
import { MAP_CAPTIONS } from '@/lib/selfPortraitMapCaptions'

// Same-origin hand-drawn territory map (v5 re-art asset). Full-bleed background, full opacity.
const MAP_SRC = '/self-portrait/map-territories.webp'

// ── FIXED territory slots (viewBox 360×294), in RANK order ─────────────────────
// Detected centres of the 5 baked-in anchor markers on the map art (frac→viewBox from the
// 1388×1133 asset). rank-1 → the CENTRAL bullseye (also gets the X-mark), rank-2 → top-right
// territory, rank-3 → top-left, rank-4 → bottom-right, rank-5 → the lake (bottom-left).
// `maxChars` is the per-slot caption wrap width: the three corner slots use a tighter width
// so a wide caption never runs off the viewBox edge.
const SLOTS: Array<{ x: number; y: number; maxChars: number }> = [
  { x: 172.7, y: 173.3, maxChars: 18 }, // CENTRE    — rank 1 (bullseye)
  { x: 267.7, y: 83.8, maxChars: 18 }, // TOP-RIGHT — rank 2
  { x: 83.8, y: 77.3, maxChars: 14 }, // TOP-LEFT  — rank 3
  { x: 292.6, y: 243.9, maxChars: 14 }, // BOT-RIGHT — rank 4
  { x: 76.8, y: 247.0, maxChars: 14 }, // LAKE (BL) — rank 5
]

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

        <svg viewBox="0 0 360 294" className="relative w-full block" role="img" aria-label="Your theme map">
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
