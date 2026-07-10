# Counterview share-title — the last wire (share fix)

**Branch:** `feat/counterview-share-title` (same branch as the title build) · **Date:** 2026-07-10

## Diagnosis first (P-06): where the shared text actually comes from

Traced `shareCounterview` end to end before changing anything.

- **The actual shared artifact is a SERVER-composed PNG.** `api.shareCounterview(id)`
  ([api.ts:1005](../../apps/web/lib/api.ts)) → `POST /share/counterview`
  ([share.py:68](../../apps/api/routers/share.py)) → `generate_counterview_share_image`
  → `_render_counterview_card` ([image_service.py:1042](../../apps/api/services/image_service.py)).
  This is the blob that Send shares (`navigator.share({ files: [file] })`) for **both**
  pro (pre-generated) and free (generate-on-send). The prior commit already switched this
  renderer to draw `cv.title` (title-or-nothing, never `anchor_text`). **So the shared
  IMAGE was already correct.**

- **The real gap was the DATA WIRE + the client preview, not the PNG.** Two findings:
  1. **The feed never returned `title`.** `_counterview_verdicts`
     ([reflections_feed_service.py:110](../../apps/api/services/reflections_feed_service.py))
     selected `anchor_text` but not `title`, and the `ReflectionFeedCounterview` schema
     ([schemas:784](../../apps/api/schemas/__init__.py)) had no `title` field — so
     `response_model` validation would strip it even if added to the dict. The client
     literally could not know the title. Same for the live counterview detail
     (`CounterviewOut` / `_serialize_counterview`).
  2. **The client preview + caption still drew `anchor_text`.** Both share entry points
     passed `quote={anchor_text}` into `SharePreviewModal`, which rendered `{quote}` as the
     big card text in the HTML fallback ([SharePreviewModal.tsx:390]) and put it in the
     download-path clipboard caption (`fullShareText`). The HTML fallback is what **free
     users see in the modal** until Send (they don't pre-gen). That is the confession
     showing in a share surface — the thing item 7 exists to prevent.

## Fix — title-or-nothing everywhere shared text is drawn

### Backend — expose `title` on both read paths
- `ReflectionFeedCounterview` schema + `_counterview_verdicts` service: select
  `Counterview.title`, add `"title": r.title` to the payload.
- `CounterviewOut` schema + `_serialize_counterview`: add `title=cv.title` (covers the live
  counterview page + insight/deeper/respond responses).

### Frontend types
- `ReflectionFeedCounterview` and `Counterview` (`lib/api.ts`) gain `title: string | null`.

### SharePreviewModal contract (per the approved spec)
- New prop `heading?: string | null` — the counterview terrain title.
- `const cardText = isCounterview ? (heading ?? '') : quote` — the counterview card/caption
  uses the title, **never** `quote`; every other variant is unchanged.
- HTML fallback renders `{heading}` (Cormorant, ink, non-italic to mirror the server title).
  `heading` null → the flex-1 spacer stays but **no text renders** — never falls back to
  `anchor_text`.
- Caption: `fullShareText` uses `cardText`; when it is empty (null title) it degrades to
  `shortShareText` (wordmark only) — no confession in the clipboard/download caption.
  (`navigator.share` already used `shortShareText`, so the native sheet never leaked.)

### Both callers pass the title, not the anchor
- `CounterviewVerdictCard.tsx` (reflections feed): `heading={item.title}`,
  `quote={item.title ?? ''}` (quote is no longer `anchor_text`).
- `counterview/page.tsx` (live screen): `heading={counterview.title}`,
  `quote={counterview.title ?? ''}`.

The **in-app** anchor_text display is untouched on purpose — it stays as "your words"
(CounterviewVerdictCard at higher contrast from the prior commit; the counterview page body
already uses `text-charcoal`). Only the **shared** surfaces switched to title-or-nothing.

## Verification
- `py_compile` clean on all changed backend files.
- `pytest -k "counterview or reflection or feed"`: **16 passed**, 2 failed — the same two
  pre-existing `test_counterview_rebuttal.py` MagicMock/`still_stands` failures confirmed on
  clean origin/main (unrelated, out of scope). No new failures.
- TypeScript: `tsc` could not run (no Node in this environment). Changes verified by
  inspection — `heading`/`title` are `string | null` (assignable to the optional prop);
  `quote` remains a required `string` at every call site; `{heading}` renders nothing when
  null. **Please confirm a clean `tsc`/preview build on your side before merge.**

## The crux, restated for your re-audit
Wherever counterview share text is drawn it is now **title-or-nothing**:
- Server PNG (the real artifact): `cv.title` or omitted line — prior commit.
- Client HTML preview: `heading` or nothing — this commit.
- Share caption (clipboard/download): title or wordmark-only — this commit.
- Native share sheet text: already wordmark-only.

`anchor_text` no longer reaches any shared surface. It survives ONLY in the in-app cards as
"your words". **Do not merge until you confirm the shared artifact shows the title (or
nothing), never the confession.**
