// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait shareable card (Phase B, v2 — recomposed to the new radar aesthetic).
// CLIENT-SIDE, UNGATED, no server, no Pillow. Serializes the ACTIVE on-screen <svg>
// (radar OR map — whichever is showing, read via a ref by the caller), composites a
// 1080×1350 (4:5) card — vellum bg, a thin bronze plate border, the framed viz, and a
// brand strip (wordmark + optional QR + URL) — and returns a PNG Blob fed to
// navigator.share (+ download fallback). Save and Share consume this one path.
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
// Guarded: even when on, each optional asset is drawn ONLY if it actually loads
// (loadOptional swallows a 404), so a missing asset never draws a broken image.
const USE_SHARE_QR = true

// RADAR serialization bounds (the clone's viewBox). The on-screen radar's viewBox is a
// tight "0 0 360 270" that its fontSize-17 labels overflow via overflow:visible. Worst
// case over ANY top-5 (0.58 em/char): x∈[-38.4, 368.8], y∈[-1.64, 257.2]. This box adds
// L5.6 / R7.2 / T6.4 / B6.8 units of margin so no label ever clips. (The MAP path uses
// the svg's own viewBox instead — it has no overflow.)
const SER = { x: -44, y: -8, w: 420, h: 272 }
const RENDER_SCALE = 3 // rasterize the SVG at 3× for crisp text, drawn down

// Viz AREA on the card — the active viz is fit into this box preserving aspect (so the
// radar's 420:272 and the map's 360:264 are each undistorted), then the brand sits below.
const VIZ_X = 90
const VIZ_Y = 150
const VIZ_W = 900
const VIZ_MAX_H = 600

// Radar center + rose size in viewBox units (mirror PortraitRadar: R=116, ROSE=R·0.55).
const RADAR_CX = 180
const RADAR_CY = 140
const ROSE_VB = 116 * 0.55 // 63.8

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

/**
 * Composite the 1080×1350 share card from the active radar/map <svg>. Returns a PNG
 * Blob. Throws on a missing canvas context or a null toBlob (caller surfaces an error).
 */
export async function renderPortraitCardBlob(svg: SVGSVGElement): Promise<Blob> {
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

  // 4. The active viz — radar labels UN-CLIPPED via the expanded viewBox; map undistorted.
  ctx.drawImage(vizImg, dest.x, dest.y, dest.w, dest.h)

  // 5. Brand strip — real fonts via the next/font CSS vars (read off <body>, where the
  //    .variable class resolves them to the actual loaded family names).
  const css = getComputedStyle(document.body)
  const cormorant = css.getPropertyValue('--font-cormorant').trim() || 'Georgia, serif'
  const lora = css.getPropertyValue('--font-lora').trim() || 'Georgia, serif'

  ctx.textAlign = 'center'
  ctx.textBaseline = 'alphabetic'

  // Wordmark (italic 500 — matches the app's synthetic-italic Cormorant brandmark).
  ctx.fillStyle = INK
  ctx.font = `italic 500 46px ${cormorant}`
  ctx.fillText('The Wise Room', CARD_W / 2, 825)

  // QR (optional) + URL, balanced in the space below the viz area.
  ctx.fillStyle = BRONZE_DARK
  ctx.font = `400 30px ${lora}`
  if (qrImg) {
    const QR = 240
    ctx.drawImage(qrImg, (CARD_W - QR) / 2, 875, QR, QR)
    ctx.fillText('thewiseroom.app', CARD_W / 2, 1180)
  } else {
    ctx.fillText('thewiseroom.app', CARD_W / 2, 895)
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
export async function sharePortraitCardBlob(blob: Blob): Promise<'shared' | 'downloaded'> {
  const filename = 'my-self-portrait.png'
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
