# Liquid-glass active tab — item 8

**Branch:** `feat/tabbar-liquid-glass` (fresh off `origin/main` @ `65b05490`)
**Commit:** `feat(tabbar): liquid-glass active-tab lens with icon magnify`
**File touched:** `apps/web/components/layout/BottomTabBar.tsx` **only.** No backend, no new deps.

## What shipped

A glass "lens" that slides (spring) to the active tab, magnifies its icon, and carries a
specular highlight — the approved *Liquid + magnify* look. It is **additive**: the existing
color active state (`text-ink` vs `text-sepia`, `aria-current="page"`, `font-medium` label)
is untouched and remains the a11y signal and the no-`backdrop-filter` fallback.

### Implementation notes

- **Lens element** — an `aria-hidden` `<span class="tabbar-lens">` inserted as the first child
  of the tabs row, before the `<Link>`s. `top:6px; height:52px; width:calc(25% - 3px);
  border-radius:999px; z-index:1`.
- **Movement** — GPU-composited `transform: translateX(...)`, not `left`. Position is driven by
  a `--active` CSS var (the active tab index) set inline:
  `translateX(calc(var(--active) * (100% + 3px)))`. The math: the lens is `25% − 3px` wide, so
  100% of *its own* width + 3px equals exactly 25% of the bar (one tab step); the `left:1.5px`
  seed centers it under tab 0, and each index step centers it under the next tab. Spring:
  `cubic-bezier(.34,1.56,.64,1)` at `.42s`, `will-change:transform`.
- **Active index** — `TABS.findIndex(tab => tab.activePattern.test(pathname))`, reusing the exact
  existing `isActive` predicate; exactly one matches on `(tabs)` routes. On `-1` (no match) the
  lens is set to `opacity:0` and clamped to index 0 — it simply doesn't show, and the per-tab
  color state is unaffected.
- **Glass styling** — verbatim approved values: the radial-gradient fill,
  `backdrop-filter: blur(1px) brightness(1.18) saturate(1.15)` **with** the `-webkit-` prefix
  (iOS Safari is the primary target), the white hairline border, the triple box-shadow (two inset
  + one drop), and a `::after` specular strip (`top:4px; left:14%; right:30%; height:9px;` white→
  transparent gradient, `blur(1px)`).
- **Icons above the glass** — each `<Link>` is `relative z-[2]`, so glyphs and labels render above
  the lens (`z-index:1`). Active `<Link>` gets `-translate-y-px` (the 1px lift).
- **Magnify** — the icon glyph is wrapped in `<span class="tabbar-glyph">`; the active variant is
  `transform: scale(1.34)` + `drop-shadow(0 1px 1px rgba(255,255,255,.7))`, transitioned on the
  same spring. Because CSS `scale` is visual-only (doesn't change the layout box), the wrapper's
  box stays 20px.
- **Home Sparkle protection** — the magnify is on `.tabbar-glyph`, which for Home wraps **only**
  the `<Icon>` and sits *inside* the existing `relative` span next to the `<Sparkle>` badge. The
  Sparkle remains a sibling anchored to the unchanged 20px box corner, so it keeps its size and
  `-top-[3px] -right-[5px]` position when Home is active + has-new. Its `motion-safe:animate-soft-pulse`
  is left exactly as-is.

### Robustness

- **`prefers-reduced-motion: reduce`** — `.tabbar-lens` and `.tabbar-glyph` transitions are set to
  `none`, so the lens appears instantly under the active tab (no travel) and the icon magnifies
  with no spring overshoot. The Sparkle pulse is already `motion-safe:` and is untouched.
- **`-webkit-backdrop-filter`** set alongside `backdrop-filter`.
- **No `backdrop-filter` support** — the lens degrades to a soft white highlight; the active tab is
  still fully conveyed by the color state. Active state never depends on the lens.

### Styling mechanism

Uses a scoped `<style jsx>` block (styled-jsx) to keep everything in the one permitted file while
supporting the `::after` pseudo-element and the reduced-motion media query. Verified styled-jsx is
first-class here: `next/index.d.ts` references the bundled `styled-jsx` global type augmentation
(`jsx?: boolean` on `StyleHTMLAttributes`), which reaches this file via `next-env.d.ts`, and the SWC
`styledJsx` transform is on by default in Next 14. The `--active` CSS var is passed via a typed
inline style (`import { type CSSProperties }`).

## Verification status — READ THIS

**Node.js is not installed in this session's environment** (not on PATH, no `node.exe` on disk).
As a result I could **not** run `tsc`, `next lint`, `next dev`, or capture the requested
screenshots / screen-record here. The change was verified by:

- Full manual review of the diff (geometry math, stacking order, Sparkle-unscaled behavior).
- Static confirmation that the two type-sensitive points compile: `type CSSProperties` import and
  the styled-jsx `jsx` prop augmentation (traced through `next/index.d.ts` → `styled-jsx` global).

**Outstanding — founder / next environment must do the visual gate:**

```bash
cd apps/web
npm run dev      # or: npm run lint && npm run build   to confirm the typecheck
```

Then eyeball on a mobile viewport:
1. **Home active with the Sparkle "new" badge** — confirm the lens sits under Home, the Home icon
   is magnified, and the Sparkle stays its normal size at the corner (NOT scaled/distorted).
2. **Explore active** — confirm the lens has sprung over to Explore and its icon is magnified.
3. Toggle OS "reduce motion" and confirm the lens jumps (no slide) with no bounce.

I was unable to produce the screenshots in-session; flagging rather than skipping silently.

## Gate

Branch pushed. **No PR.** Report committed alongside the change.
