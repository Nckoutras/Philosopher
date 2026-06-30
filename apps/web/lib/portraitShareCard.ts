// ─────────────────────────────────────────────────────────────────────────────
// Self-Portrait shareable card (Phase B3). CLIENT-SIDE, UNGATED, no server, no
// Pillow. Serializes the ACTIVE on-screen <svg> (radar OR map — whichever is showing,
// read via a ref by the caller), composites a 1080×1350 (4:5) card — vellum bg, the
// framed viz, and a brand strip (wordmark + optional QR + URL) — and returns a PNG
// Blob fed to navigator.share (+ download fallback).
//
// TAINT-SAFE: the on-screen <svg> is pure vector (no <image>/<foreignObject>); the
// persona watermark + frame are HTML sibling layers OUTSIDE the <svg>, so serializing
// only the <svg> excludes the persona for free. The frame + QR we draw ourselves are
// same-origin /public assets. Nothing cross-origin enters the canvas → toBlob() works.
// ─────────────────────────────────────────────────────────────────────────────

const CARD_W = 1080
const CARD_H = 1350
const VELLUM = '#EFE3CC'
const INK = '#1F1B14'
const BRONZE = '#B89968'
const BRONZE_DARK = '#8A7340'

const FRAME_SRC = '/self-portrait/radar-frame.webp' // same-origin κάδρο (B1.5 asset)
const QR_SRC = '/self-portrait/qr-wiseroom.png' // same-origin; supplied asset (incoming)
// Guarded: even when on, the QR is drawn ONLY if the file actually loads (loadOptional
// swallows a 404), so a missing asset never draws a broken image.
const USE_SHARE_QR = true

// Viz box on the card — matches the 360:264 viewBox aspect so the viz isn't distorted.
const VIZ_W = 900
const VIZ_H = 660 // 900 * 264 / 360
const VIZ_X = (CARD_W - VIZ_W) / 2 // 90
const VIZ_Y = 130
const RENDER_SCALE = 2 // rasterize the SVG at 2× for crisp text/strokes, drawn down to VIZ_W×VIZ_H

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

// Serialize the active svg to a data-URL <img>. Two fixes baked in:
//  • explicit pixel width/height on the CLONE — without it Firefox rasterizes a
//    serialized SVG at 0×0 (blank draw).
//  • explicit font-family on every <text> — a standalone serialized SVG can't see the
//    page's Tailwind/next-font, so labels would fall back to the browser default
//    serif. Georgia,serif matches the app's declared fallback (the brand text is drawn
//    separately via canvas fillText in the real fonts).
function svgToDataUrl(svg: SVGSVGElement): string {
  const clone = svg.cloneNode(true) as SVGSVGElement
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clone.setAttribute('width', String(VIZ_W * RENDER_SCALE))
  clone.setAttribute('height', String(VIZ_H * RENDER_SCALE))
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

  const vizImg = await loadImage(svgToDataUrl(svg)) // pure vector → never taints
  const frameImg = await loadOptional(FRAME_SRC) // same-origin κάδρο
  const qrImg = USE_SHARE_QR ? await loadOptional(QR_SRC) : null

  const canvas = document.createElement('canvas')
  canvas.width = CARD_W
  canvas.height = CARD_H
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('canvas 2d context unavailable')

  // 1. Background
  ctx.fillStyle = VELLUM
  ctx.fillRect(0, 0, CARD_W, CARD_H)

  // 2. Framed viz — frame behind (85% to match on-screen), the svg on top. If the
  //    frame asset is missing, fall back to a clean bronze hairline border.
  if (frameImg) {
    ctx.globalAlpha = 0.85
    ctx.drawImage(frameImg, VIZ_X, VIZ_Y, VIZ_W, VIZ_H)
    ctx.globalAlpha = 1
  } else {
    ctx.strokeStyle = BRONZE
    ctx.lineWidth = 1.5
    ctx.strokeRect(VIZ_X + 6, VIZ_Y + 6, VIZ_W - 12, VIZ_H - 12)
  }
  ctx.drawImage(vizImg, VIZ_X, VIZ_Y, VIZ_W, VIZ_H)

  // 3. Brand strip — real fonts via the next/font CSS vars (read off <body>, where the
  //    .variable class resolves them to the actual loaded family names).
  const css = getComputedStyle(document.body)
  const cormorant = css.getPropertyValue('--font-cormorant').trim() || 'Georgia, serif'
  const lora = css.getPropertyValue('--font-lora').trim() || 'Georgia, serif'

  ctx.textAlign = 'center'
  ctx.textBaseline = 'alphabetic'

  // Wordmark (italic 500 — matches the app's synthetic-italic Cormorant brandmark).
  ctx.fillStyle = INK
  ctx.font = `italic 500 46px ${cormorant}`
  ctx.fillText('The Wise Room', CARD_W / 2, 900)

  // QR (optional) + URL.
  ctx.fillStyle = BRONZE_DARK
  ctx.font = `400 30px ${lora}`
  if (qrImg) {
    const QR = 240
    ctx.drawImage(qrImg, (CARD_W - QR) / 2, 950, QR, QR)
    ctx.fillText('thewiseroom.app', CARD_W / 2, 1252)
  } else {
    ctx.fillText('thewiseroom.app', CARD_W / 2, 980)
  }

  // 4. Encode
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
