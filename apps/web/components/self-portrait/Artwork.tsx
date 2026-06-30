// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait artwork — ORIGINAL abstract placeholders (Phase A).
//
// Every shape here is generated from our own palette tokens (vellum / linen / bronze
// / sepia / charcoal) and a deterministic per-category seed. Nothing is traced,
// sampled, or derived from any external/AI/copyrighted image — they are plain
// geometric SVG, original to this file.
//
// SWAP SEAM for Nikos's real watercolor assets:
//   1. Drop the WebP/SVG files at the spec'd paths below (keyed on the category slug).
//   2. Flip USE_REAL_ARTWORK to true.
// No other code change — the components below already point at these exact paths when
// the flag is on. Until then, the deterministic placeholders render.
//
// Asset spec (also documented in the Phase A/B reports):
//   • per-theme tile     — 1:1  256×256  WebP q82  → /self-portrait/themes/<category>.webp
//   • question-card band — 16:9 768×432  WebP q82  → /self-portrait/card/<category>.webp
//   • "pattern" comp     — 16:9 1024×576 WebP q82  → /self-portrait/pattern.webp
//   • "room notices" eye — 1:1  64×64    SVG       → /self-portrait/eye.svg
//   • radar frame texture— 1:1 1024×1024 WebP q82  → /self-portrait/radar-frame.webp  (B1, OPTIONAL)
// (<category> = the 12 bank category slugs, exact machine values.)
// ─────────────────────────────────────────────────────────────────────────────
import Image from 'next/image'

// Flip to true once the real assets are dropped at the paths above. Typed as a
// plain boolean (not the `false` literal) so it reads as a toggle, not a constant.
export const USE_REAL_ARTWORK: boolean = true

export const themeArtworkSrc = (category: string) => `/self-portrait/themes/${category}.webp`
export const cardArtworkSrc = (category: string) => `/self-portrait/card/${category}.webp`
export const patternArtworkSrc = () => `/self-portrait/pattern.webp`
// OPTIONAL radar κάδρο/frame texture (B1). The radar renders fully without it; this
// only overlays a watercolor canvas-grain when the real asset is present.
export const radarFrameSrc = () => `/self-portrait/radar-frame.webp`
// Independent of USE_REAL_ARTWORK: radar-frame.webp is the ONE artwork asset not yet
// supplied, so this stays false even though the rest of the real art is live —
// otherwise the frame <img> would 404 to a broken-image icon. Flip to true ONLY after
// dropping radar-frame.webp into /public/self-portrait/.
export const USE_RADAR_FRAME: boolean = false

// Palette tokens (hex, DESIGN_SYSTEM_v4 §1.2) — used directly in SVG fills.
const PALETTE = ['#B89968', '#8A7340', '#8A7E6A', '#DDD0B5', '#C7B284', '#A98C5C']

// FNV-1a 32-bit, local (kept independent of lib/selfPortraitObservations).
function seedOf(s: string): number {
  let h = 0x811c9dc5
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 0x01000193)
  }
  return h >>> 0
}

// Tiny deterministic PRNG (mulberry32) seeded by the category — so each theme's
// placeholder is stable and distinct, but all share the palette + soft feel.
function prng(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// A handful of soft overlapping shapes inside a 0..100 viewBox, deterministic per
// category. Shared by the tile and the wider band (different aspect, same seed).
function AbstractField({ category, w, h }: { category: string; w: number; h: number }) {
  const rand = prng(seedOf(category))
  const blobs = Array.from({ length: 4 }, () => ({
    cx: 12 + rand() * (w - 24),
    cy: 12 + rand() * (h - 24),
    r: 10 + rand() * Math.min(w, h) * 0.28,
    fill: PALETTE[Math.floor(rand() * PALETTE.length)],
    o: 0.18 + rand() * 0.34,
  }))
  const rot = Math.floor(rand() * 360)
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="xMidYMid slice"
      className="w-full h-full block"
      role="presentation"
      aria-hidden="true"
    >
      <rect x="0" y="0" width={w} height={h} fill="#E8DCC4" />
      <g transform={`rotate(${rot} ${w / 2} ${h / 2})`}>
        {blobs.map((b, i) => (
          <circle key={i} cx={b.cx} cy={b.cy} r={b.r} fill={b.fill} opacity={b.o} />
        ))}
      </g>
      {/* a single bronze hairline arc for a hand-drawn feel */}
      <path
        d={`M0 ${h * 0.7} Q ${w * 0.5} ${h * 0.4} ${w} ${h * 0.72}`}
        fill="none"
        stroke="#8A7340"
        strokeWidth={0.6}
        opacity={0.5}
      />
    </svg>
  )
}

/** Small square theme tile — revisit cards + the question-card eyebrow. */
export function ThemeGlyph({ category, size = 40 }: { category: string; size?: number }) {
  return (
    <div
      className="rounded-md overflow-hidden flex-shrink-0 border-[0.5px] border-bronze/30"
      style={{ width: size, height: size }}
    >
      {USE_REAL_ARTWORK ? (
        <Image src={themeArtworkSrc(category)} alt="" width={size} height={size} className="object-cover w-full h-full" />
      ) : (
        <AbstractField category={category} w={100} h={100} />
      )}
    </div>
  )
}

/** Wide 16:9 band across the top of the question card. */
export function CardArtwork({ category }: { category: string }) {
  return (
    <div className="w-full rounded-md overflow-hidden border-[0.5px] border-bronze/20 aspect-[16/9]">
      {USE_REAL_ARTWORK ? (
        <Image src={cardArtworkSrc(category)} alt="" width={768} height={432} className="object-cover w-full h-full" />
      ) : (
        <AbstractField category={category} w={160} h={90} />
      )}
    </div>
  )
}

/** The abstract composition shown on the "A pattern is emerging" forming moment. */
export function PatternArtwork() {
  // A small constellation of nodes + connecting lines — original, geometric, calm.
  const rand = prng(seedOf('pattern'))
  const nodes = Array.from({ length: 7 }, () => ({
    x: 14 + rand() * 132,
    y: 12 + rand() * 66,
    r: 1.6 + rand() * 2.6,
  }))
  return (
    <div className="w-full rounded-md overflow-hidden border-[0.5px] border-bronze/20 aspect-[16/9]">
      {USE_REAL_ARTWORK ? (
        <Image src={patternArtworkSrc()} alt="" width={1024} height={576} className="object-cover w-full h-full" />
      ) : (
        <svg viewBox="0 0 160 90" preserveAspectRatio="xMidYMid slice" className="w-full h-full block" role="presentation" aria-hidden="true">
          <rect x="0" y="0" width="160" height="90" fill="#EFE3CC" />
          {nodes.map((n, i) =>
            nodes.slice(i + 1).map((m, j) => (
              <line key={`${i}-${j}`} x1={n.x} y1={n.y} x2={m.x} y2={m.y} stroke="#B89968" strokeWidth={0.3} opacity={0.35} />
            )),
          )}
          {nodes.map((n, i) => (
            <circle key={i} cx={n.x} cy={n.y} r={n.r} fill="#8A7340" opacity={0.7} />
          ))}
        </svg>
      )}
    </div>
  )
}

/** The "The Room notices" eye glyph — small, original line-art mark. */
export function EyeGlyph({ size = 18 }: { size?: number }) {
  if (USE_REAL_ARTWORK) {
    // eslint-disable-next-line @next/next/no-img-element -- tiny static svg, no optimization needed
    return <img src="/self-portrait/eye.svg" alt="" width={size} height={size} aria-hidden="true" />
  }
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" role="presentation" aria-hidden="true" className="inline-block align-middle">
      <path d="M2 12 Q 12 4 22 12 Q 12 20 2 12 Z" stroke="#8A7340" strokeWidth={1.2} fill="none" />
      <circle cx="12" cy="12" r="3.2" stroke="#8A7340" strokeWidth={1.2} fill="none" />
      <circle cx="12" cy="12" r="1.1" fill="#8A7340" />
    </svg>
  )
}
