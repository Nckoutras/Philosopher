// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait shareable card (Phase B, v2 — recomposed to the new radar aesthetic).
// CLIENT-SIDE, UNGATED, no server, no Pillow. Serializes the ACTIVE on-screen <svg>
// (radar OR map — whichever is showing, read via a ref by the caller), composites a
// 1080×1350 (4:5) card — vellum bg, a thin bronze plate border, a top brand eyebrow +
// "Your Self-Portrait" title, the (now larger) framed viz, the deterministic summary line,
// and a footer cluster (smaller/lower QR + "thewiseroom.app" + the render date) — and
// returns a PNG Blob fed to navigator.share (+ download fallback). Save and Share consume
// this one path. The summary line is passed IN (the on-screen <p> is outside the captured
// SVG); a null summary skips its band entirely.
//
// Two v2 fixes vs the on-screen restyle:
//  • UN-CLIPPED LABELS: the on-screen radar overflows its tight 360×270 viewBox
//    (overflow:visible), so for the RADAR we re-viewBox the serialized clone to the FULL
//    label extents (SER_*) — nothing clips, for any top-5 selection.
//  • ROSE: the on-screen <image href="/self-portrait/rose.webp"> can't resolve inside a
//    data-URL SVG, so the clone drops it and we composite rose.webp as a SEPARATE
//    same-origin drawImage layer UNDER the radar svg (its 0.3 pentagon fill shows it
//    through). The MAP path keeps its own viewBox, draws no rose, and is letterboxed
//    into the viz area undistorted.
//
// TAINT-SAFE: the on-screen <svg> is pure vector (its <image> is stripped from the
// clone); rose.webp + QR are same-origin /public assets drawn straight to the canvas.
// Nothing cross-origin enters the canvas → toBlob() works.
// ─────────────────────────────────────────────────────────────────────────────

const CARD_W = 1080
const CARD_H = 1350
const VELLUM = '#EFE3CC'
const INK = '#1F1B14'
const BRONZE = '#B89968'
const BRONZE_DARK = '#8A7340'

const QR_SRC = '/self-portrait/qr-wiseroom.png' // same-origin; supplied asset
const ROSE_SRC = '/self-portrait/rose.webp' // same-origin raster compass rose (under the svg)
const MAP_SRC = '/self-portrait/map-territories.webp' // same-origin map base art (under the MAP svg)
// Guarded: even when on, each optional asset is drawn ONLY if it actually loads
// (loadOptional swallows a 404), so a missing asset never draws a broken image.
const USE_SHARE_QR = true

// RADAR serialization bounds (the clone's viewBox). The on-screen radar's viewBox is a
// tight "0 0 360 270" that its fontSize-15 labels (LABEL_R 134) overflow via
// overflow:visible. Worst case over ANY top-5 (0.58 em/char; per-position worst label —
// right/top ≤7ch "Freedom" as frozen order keeps long labels off the right, left 10ch
// "Connection"): x∈[-34.4, 368.3], y∈[-7.8, 261.9]. This box adds ~L5.6 / R7.7 / T6.2 /
// B7.1 units of margin so no label ever clips. (The MAP path uses the svg's own viewBox
// instead — it has no overflow.)
const SER = { x: -40, y: -14, w: 416, h: 283 }
const RENDER_SCALE = 3 // rasterize the SVG at 3× for crisp text, drawn down

// Viz AREA on the card (C2 recomposition — larger than the previous 90/150/900/600). The
// active viz is fit into this box preserving aspect (so the radar's 420:272 and the map's
// 360:294 are each undistorted). The title sits above (y≈108–172); the summary line + QR +
// date sit below. Old box 900×600 → new 950×615 (radar +11% area, map wider & taller).
const VIZ_X = 65
const VIZ_Y = 205
const VIZ_W = 950
const VIZ_MAX_H = 615

// ── C2 footer/text layout constants (canvas px; see the approved STEP-1 y-map) ──────────
const EYEBROW_Y = 108 // "THE WISE ROOM" brand eyebrow baseline
const TITLE_Y = 172 // "Your Self-Portrait" title baseline
const SUMMARY_HEAD_Y = 852 // "The Wise Room says" header baseline (600 34px cormorant, ink)
const SUMMARY_HEAD_SIZE = 34 // Cormorant px for the header line
const SUMMARY_TOP = 872 // top of the lean-sentence band (first baseline = SUMMARY_TOP + size)
const SUMMARY_SIZE = 30 // Lora px for the summary line (worst-case wraps to ≤4 lines)
const SUMMARY_LH = 42 // summary line-height (~1.4). 4-line bottom ≈ 1035 clears QR_Y 1050.
const SUMMARY_MAXW = 900 // summary wrap width (centered → 90px margin each side)
const QR_SIZE = 150 // smaller than the old 240
const QR_Y = 1050 // lower than the old 875
const URL_Y = 1240 // "thewiseroom.app" baseline, beneath the QR
const DATE_Y = 1278 // render-date baseline, near the footer

// Radar center + rose size in viewBox units (mirror PortraitRadar: R=124, ROSE=R·0.55).
const RADAR_CX = 180
const RADAR_CY = 140
const ROSE_VB = 124 * 0.55 // 68.2

type ViewBox = { x: number; y: number; w: number; h: number }

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error(`image load failed: ${src}`))
    img.src = src
  })
}

async function loadOptional(src: string): Promise<HTMLImageElement | null> {
  try {
    return await loadImage(src)
  } catch {
    return null
  }
}

// The svg's own viewBox (fallback to the legacy 360×264 if somehow absent).
function ownViewBox(svg: SVGSVGElement): ViewBox {
  const p = (svg.getAttribute('viewBox') || '0 0 360 264').split(/[\s,]+/).map(Number)
  const [x, y, w, h] = p
  return Number.isFinite(w) && Number.isFinite(h) && w > 0 && h > 0
    ? { x, y, w, h }
    : { x: 0, y: 0, w: 360, h: 264 }
}

// Fit a viewBox aspect into the viz AREA, centered, preserving aspect (no distortion).
function fitViz(vb: ViewBox): { x: number; y: number; w: number; h: number } {
  const aspect = vb.w / vb.h
  let w = VIZ_W
  let h = w / aspect
  if (h > VIZ_MAX_H) {
    h = VIZ_MAX_H
    w = h * aspect
  }
  return { x: VIZ_X + (VIZ_W - w) / 2, y: VIZ_Y + (VIZ_MAX_H - h) / 2, w, h }
}

// Rounded-rect path (ctx.roundRect isn't universal on older Safari share targets).
function roundRectPath(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
): void {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

// Greedy word-wrap using the REAL canvas metrics (ctx.measureText) so line-breaks are exact
// on the actual device — no headless estimate. `ctx.font` must already be set to the target
// face/size. Returns one string per line, never breaking mid-word.
function wrapCanvasText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const words = text.split(' ')
  const lines: string[] = []
  let cur = ''
  for (const w of words) {
    const cand = cur ? `${cur} ${w}` : w
    if (cur && ctx.measureText(cand).width > maxWidth) {
      lines.push(cur)
      cur = w
    } else {
      cur = cand
    }
  }
  if (cur) lines.push(cur)
  return lines
}

// Render-time date, formatted "5 July 2026" (en-GB long). Dates the snapshot being shared;
// no backend field exists, so this is the render date by design.
function renderDateLabel(): string {
  try {
    return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }).format(
      new Date(),
    )
  } catch {
    return ''
  }
}

// Serialize the active svg to a data-URL <img> under the given serialization viewBox.
// Three things baked in:
//  • re-viewBox to `ser` (expanded for the radar so overflow labels rasterize, own box
//    for the map), with explicit pixel width/height on the CLONE (Firefox rasterizes a
//    0×0 SVG otherwise).
//  • strip <image> (the radar rose): its href can't resolve in a data-URL SVG — it's
//    drawn as a same-origin canvas layer instead.
//  • pin font-family on every <text>: a standalone serialized SVG can't see the page's
//    next-font Lora, so we use the app's declared serif fallback (Georgia). The brand
//    text is drawn separately via canvas fillText in the real loaded fonts.
function svgToDataUrl(svg: SVGSVGElement, ser: ViewBox): string {
  const clone = svg.cloneNode(true) as SVGSVGElement
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clone.setAttribute('viewBox', `${ser.x} ${ser.y} ${ser.w} ${ser.h}`)
  clone.setAttribute('width', String(ser.w * RENDER_SCALE))
  clone.setAttribute('height', String(ser.h * RENDER_SCALE))
  clone.querySelectorAll('image').forEach((el) => el.remove())
  clone.querySelectorAll('[data-share-omit]').forEach((el) => el.remove())
  clone.querySelectorAll('text').forEach((t) => {
    t.setAttribute('font-family', 'Georgia, serif')
  })
  const xml = new XMLSerializer().serializeToString(clone)
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(xml)}`
}

// Personalized card title. `first` is the user's first name (may arrive as a full
// name — defensively take the first token). Empty → the generic title. A name
// ending in s/S or the Greek final sigma ς takes a bare apostrophe
// ("Nikos' Self-Portrait", "Νίκος' Self-Portrait"), else 's.
function portraitTitle(userFirstName?: string): string {
  const first = (userFirstName ?? '').trim().split(/\s+/)[0] ?? ''
  if (!first) return 'Your Self-Portrait'
  const possessive = /[sSς]$/.test(first) ? `${first}'` : `${first}'s`
  return `${possessive} Self-Portrait`
}

/** Slugified share filename from the first name; falls back when there's no name
 *  (or it slugs to empty, e.g. a non-Latin script). Single source for both the
 *  Share and Save paths. */
export function portraitCardFilename(userFirstName?: string): string {
  const slug = (userFirstName ?? '')
    .trim()
    .split(/\s+/)[0]
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return slug ? `${slug}-self-portrait.png` : 'my-self-portrait.png'
}

/**
 * Composite the 1080×1350 share card from the active radar/map <svg>. Returns a PNG
 * Blob. Throws on a missing canvas context or a null toBlob (caller surfaces an error).
 */
export async function renderPortraitCardBlob(
  svg: SVGSVGElement,
  summaryLine: string | null,
  userFirstName?: string,
): Promise<Blob> {
  // Ensure the real webfonts are loaded before any canvas fillText (canvas text DOES
  // use page-loaded faces, unlike a sandboxed serialized-SVG <img>).
  if (typeof document !== 'undefined' && document.fonts?.ready) {
    try {
      await document.fonts.ready
    } catch {
      /* non-fatal — fall back to system fonts */
    }
  }

  // Radar gets the expanded serialization box + the rose layer; the map keeps its own
  // viewBox and draws no rose (it has none on screen).
  const isRadar = svg.getAttribute('aria-label') === 'Your theme radar'
  const ser: ViewBox = isRadar ? SER : ownViewBox(svg)

  const vizImg = await loadImage(svgToDataUrl(svg, ser)) // pure vector → never taints
  const roseImg = isRadar ? await loadOptional(ROSE_SRC) : null // same-origin, under the svg
  const mapImg = !isRadar ? await loadOptional(MAP_SRC) : null // same-origin map base, under the MAP svg
  const qrImg = USE_SHARE_QR ? await loadOptional(QR_SRC) : null

  const canvas = document.createElement('canvas')
  canvas.width = CARD_W
  canvas.height = CARD_H
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('canvas 2d context unavailable')

  // 1. Vellum background.
  ctx.fillStyle = VELLUM
  ctx.fillRect(0, 0, CARD_W, CARD_H)

  // 2. Thin bronze plate border — rounded, ~bronze/50, matching the on-screen plate.
  const PLATE_INSET = 48
  const PLATE_RADIUS = 40
  ctx.save()
  ctx.globalAlpha = 0.5
  ctx.strokeStyle = BRONZE
  ctx.lineWidth = 3
  roundRectPath(ctx, PLATE_INSET, PLATE_INSET, CARD_W - 2 * PLATE_INSET, CARD_H - 2 * PLATE_INSET, PLATE_RADIUS)
  ctx.stroke()
  ctx.restore()

  // Fit the active viz into the viz area (undistorted); rose + svg share this dest rect.
  const dest = fitViz(ser)

  // 3. Compass rose (radar only) — same-origin raster, centered on the radar center,
  //    UNDER the svg so the svg's transparent bg + 0.3 pentagon fill let it show through.
  if (roseImg) {
    const scale = dest.w / ser.w // canvas px per viewBox unit (uniform — aspect preserved)
    const roseCX = dest.x + (RADAR_CX - ser.x) * scale
    const roseCY = dest.y + (RADAR_CY - ser.y) * scale
    const roseW = ROSE_VB * scale
    ctx.save()
    ctx.globalAlpha = 0.9
    ctx.drawImage(roseImg, roseCX - roseW / 2, roseCY - roseW / 2, roseW, roseW)
    ctx.restore()
  }

  // 3b. Map base art (map only) — same-origin parchment territories, drawn straight into
  //     the dest rect UNDER the label svg. On screen it's an <img> sibling outside the svg
  //     (so it's stripped from the clone); the container shares the svg's 360×294 aspect, so
  //     a plain fill of dest is correct. Radar path is unaffected (mapImg is null there).
  if (mapImg) {
    ctx.drawImage(mapImg, dest.x, dest.y, dest.w, dest.h)
  }

  // 4. The active viz — radar labels UN-CLIPPED via the expanded viewBox; map undistorted.
  ctx.drawImage(vizImg, dest.x, dest.y, dest.w, dest.h)

  // 5. Text + footer — real fonts via the next/font CSS vars (read off <body>, where the
  //    .variable class resolves them to the actual loaded family names).
  const css = getComputedStyle(document.body)
  const cormorant = css.getPropertyValue('--font-cormorant').trim() || 'Georgia, serif'
  const lora = css.getPropertyValue('--font-lora').trim() || 'Georgia, serif'

  ctx.textAlign = 'center'
  ctx.textBaseline = 'alphabetic'

  // 5a. Brand eyebrow (tracked caps) + title, above the viz. letterSpacing isn't in every
  //     lib.dom typings / engine, so set it through a guarded cast (no-op where absent).
  const spaced = ctx as CanvasRenderingContext2D & { letterSpacing?: string }
  ctx.fillStyle = BRONZE_DARK
  ctx.font = `500 22px ${cormorant}`
  spaced.letterSpacing = '4px'
  ctx.fillText('THE WISE ROOM', CARD_W / 2, EYEBROW_Y)
  spaced.letterSpacing = '0px'

  ctx.fillStyle = INK
  ctx.font = `500 54px ${cormorant}`
  // Personalize with the first name; if the name makes the (single, centred) line
  // too wide, fall back to the generic title rather than shrink it.
  let title = portraitTitle(userFirstName)
  if (title !== 'Your Self-Portrait') {
    const TITLE_MAXW = CARD_W - 2 * PLATE_INSET - 40 // plate insets + breathing room
    if (ctx.measureText(title).width > TITLE_MAXW) title = 'Your Self-Portrait'
  }
  ctx.fillText(title, CARD_W / 2, TITLE_Y)

  // 5b. Summary band — a bold "The Wise Room says" header (drawn here, NOT part of the
  //     summaryLine value) above the deterministic lean sentence passed in (the on-screen
  //     <p> is outside the captured SVG). Sentence wrapped with the REAL canvas metrics.
  //     Null → skip the whole band (no crash, no "null"; the space simply stays empty).
  if (summaryLine) {
    ctx.fillStyle = INK
    ctx.font = `600 ${SUMMARY_HEAD_SIZE}px ${cormorant}`
    ctx.fillText('The Wise Room says', CARD_W / 2, SUMMARY_HEAD_Y)

    ctx.fillStyle = INK
    ctx.font = `400 ${SUMMARY_SIZE}px ${lora}`
    const lines = wrapCanvasText(ctx, summaryLine, SUMMARY_MAXW)
    lines.forEach((ln, i) => {
      ctx.fillText(ln, CARD_W / 2, SUMMARY_TOP + SUMMARY_SIZE + i * SUMMARY_LH)
    })
  }

  // 5c. Footer cluster — smaller/lower QR (optional; drawn only if it loaded), the URL
  //     beneath it, and the render date near the plate's bottom edge.
  if (qrImg) {
    ctx.drawImage(qrImg, (CARD_W - QR_SIZE) / 2, QR_Y, QR_SIZE, QR_SIZE)
  }
  ctx.fillStyle = BRONZE_DARK
  ctx.font = `400 28px ${lora}`
  ctx.fillText('thewiseroom.app', CARD_W / 2, URL_Y)

  const dateLabel = renderDateLabel()
  if (dateLabel) {
    ctx.fillStyle = INK
    ctx.font = `500 28px ${lora}`
    ctx.fillText(dateLabel, CARD_W / 2, DATE_Y)
  }

  // 6. Encode.
  return await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob)
      else reject(new Error('canvas toBlob returned null'))
    }, 'image/png')
  })
}

/**
 * Share the card Blob: Web Share API with the file when available, else a download
 * fallback (+ clipboard text). Returns how it was delivered. Re-throws ONLY an
 * AbortError (user dismissed the native sheet) so the caller can keep the preview open;
 * any other share failure falls through to the download path.
 */
export async function sharePortraitCardBlob(blob: Blob, userFirstName?: string): Promise<'shared' | 'downloaded'> {
  const filename = portraitCardFilename(userFirstName)
  const text = 'My Self-Portrait\nthewiseroom.app'
  const file = new File([blob], filename, { type: 'image/png' })

  if (typeof navigator !== 'undefined' && navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], text })
      return 'shared'
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') throw err
      // else fall through to download
    }
  }

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
  void navigator.clipboard?.writeText(text).catch(() => {})
  return 'downloaded'
}
