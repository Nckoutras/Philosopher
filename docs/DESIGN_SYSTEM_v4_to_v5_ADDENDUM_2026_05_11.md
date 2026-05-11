# DESIGN_SYSTEM v4 → v5 ADDENDUM (2026-05-11)

> **What this file is:** Targeted delta applying the v5 palette migration to the `DESIGN_SYSTEM_v4.md` baseline.
>
> **How to read this:** `DESIGN_SYSTEM_v4.md` remains the structural reference for components (§2 through §10). This addendum **supersedes** the listed sections of v4 with locked v5 values. Where a section is not mentioned here, v4 still applies.
>
> **Authoritative status:** Locked 2026-05-11. Token values are not subject to taste reinterpretation. Code-side migration shipped in commit `d018bcf` (Block A backfilled).
>
> **Consolidation note:** This addendum should be folded into a future `DESIGN_SYSTEM_v5.md` consolidated doc when the next major design system iteration is needed. Until then, the pairing `DESIGN_SYSTEM_v4.md` + this addendum is the authoritative source of truth.

---

## Why this migration happened

Silent palette drift was identified 2026-05-11. The original 1-May design vision used a **warmer parchment-toned palette** (Vellum #EFE3CC, Paper #FAF4E6). Between 1-May and 10-May the spec doc evolved toward a cooler editorial palette (Vellum #FAF4E6, Paper #FFFFFF) through unintentional drift across multiple Claude conversations.

Block A shipped to production 2026-05-10 with the drifted v4 values. The founder reviewed both palettes side-by-side, confirmed preference for the original warmer vision, and authorized restoration. Code-side migration shipped 2026-05-11. This addendum locks the spec.

---

## §1.2 Color palette — SUPERSEDES v4 §1.2

12 tokens (one added vs v4's 11). Hex values are exact and not subject to taste reinterpretation.

| Token | Hex | Use |
|---|---|---|
| Vellum | `#EFE3CC` | Page background, input bar, bottom sheet bg |
| Paper | `#FAF4E6` | Card surface, chat scroll area outer container |
| **White (NEW)** | `#FFFFFF` | True-white surfaces requiring max contrast against warmer Paper: chat content area inside cards, input field backgrounds, OTP cell backgrounds, quote-card backgrounds |
| Linen | `#E8DCC4` | Persona bubble, default avatar bg, weekly letter unread card, slow connection banner |
| Linen Deep | `#DDD0B5` | Selected chip fill, selected option fill |
| Edge | `#D4C8B0` | Borders (default 0.5px), dividers, hairlines |
| Ink | `#1F1B14` | Primary text, primary action fill, user bubble fill |
| Charcoal | `#5A5246` | Secondary text, body copy, avatar initials, disabled button text |
| Sepia | `#8A7E6A` | Muted text, captions, timestamps, eyebrow labels, chevrons |
| Bronze | `#B89968` | Bookmarks, premium accents, dividers, app-voice avatar marker, suggested insight border, weekly letter unread dot |
| Bronze Dark | `#8A7340` | Bronze borders, hover state |
| **Safety** *(renamed from Rust)* | `#7A4030` | Error states ONLY (failed messages, payment failed indicator). Renamed from Rust; semantic role unchanged. |

**Rules (unchanged from v4 except for Rust→Safety rename):**
- Bronze is a structural token, not decorative. Use for: bookmarks, payment success ornament, app-voice safety bubble avatar, divider lozenges, suggested insight cards, weekly letter unread state, "sentence worth keeping" pull-quotes.
- **Safety semantic** (formerly Rust): used for (1) actionable user-side error states (failed messages, payment failed indicator, payment issue text/dot in H5 past due), and (2) destructive confirmation actions (final CTA for irreversible operations like account deletion). Never for selection, upsell, warning decoration, generic emphasis, or app-wide server-side errors (which use the calm-pause Sepia ornament family — see §7.3 and J1 spec).
- Safety outlined buttons are reserved for confirmed destructive intent only — they require explicit user friction first (e.g. type-DELETE input). Never use Safety solid fill on buttons.
- **No new colors.** If a context "needs" a new color beyond these 12 tokens, the design is wrong.

---

## §1.7 Forbidden visual patterns — SUPERSEDES v4 §1.7

These never ship:
- Drop shadows beyond the locked subtle elevation tokens (see §1.8). Material Design elevations forbidden. Heavy shadows forbidden.
- Gradients (except portrait artwork, where they belong inside the image)
- Blur effects, neon glows
- Emoji in product UI (user-generated content fine; system UI never)
- Material Design ripple effects
- iOS bounce / overscroll affordances on web
- Frosted glass / glassmorphism
- Confetti, particle effects, achievement animations

**Permitted subtle elevation** (new in v5): `shadow-card` and `shadow-card-hover` tokens may be applied to persona cards, quote cards, and primary buttons in hover state only. All other surfaces remain flat — chips, inputs, buttons at rest, generic containers. See §1.8 for exact values.

---

## §1.8 Shadow tokens — NEW in v5

Two tokens. Both subtle, single-shadow (no compound shadows). Defined in both `apps/web/app/globals.css` (`--shadow-card`, `--shadow-card-hover`) and `apps/web/tailwind.config.js` (`shadow-card`, `shadow-card-hover` utility classes).

| Token | Value | Use |
|---|---|---|
| `shadow-card` | `0 2px 8px rgba(31, 27, 20, 0.06)` | Persona cards, quote cards (resting state). Primary button is flat at rest. |
| `shadow-card-hover` | `0 4px 16px rgba(31, 27, 20, 0.10)` | Hover state for elevated surfaces above. Primary button hover. |

**Rules:**
- No shadow on chips, inputs, buttons at rest, or generic containers
- Modals and bottom sheets keep their existing elevation specs from v4 §6 (unchanged by v5)
- Hover shadow application via Tailwind: `hover:shadow-card-hover`
- Resting shadow application via Tailwind: `shadow-card`
- Block A screens currently have NO applied shadow (no persona/quote cards in Block A). Application begins in Block C/D when persona cards appear.

---

## §3.9 Theme chip — NO CHANGE FROM v4

The selected-chip pattern (Linen Deep `#DDD0B5` fill + 1px Ink border + weight 500) is unchanged in v5. Default chip background uses Paper (`#FAF4E6` in v5, was `#FFFFFF` in v4 — cascades automatically via token reference).

---

## Inline hex references in v4 §2 through §10

**Caveat:** v4 sections §2 through §10 contain inline hex values like `#FFFFFF (Paper)` and `#FAF4E6 (Vellum)` as documentation annotations. **These reflect v4 token VALUES, not v5.** The token NAMES (Paper, Vellum, Bronze, etc.) are semantically unchanged in v5 — only their underlying hex values have shifted.

**For implementation:** code uses semantic token references (`var(--paper)`, `bg-paper`, `text-vellum`), so values cascade automatically from §1.2. The inline hex annotations in v4 component specs are illustrative, not authoritative. **§1.2 of this addendum is the authoritative source for actual hex values.**

**For future doc maintenance:** When a component is next worked on, its inline hex annotations should be updated to v5 values as a cleanup pass. Until then, do not assume v4 inline hex is current.

---

## §10 Mappings — Rust → Safety throughout

Every reference to "Rust" as a token name in v4 should be read as "Safety" in v5. Specifically affects:
- §1.2 palette (handled above)
- §1.7 forbidden patterns rule about Rust solid fills (now Safety)
- §2.8 Destructive outlined button: uses Safety `#7A4030` (was Rust `#A05A3C`)
- Any future component spec mentioning Rust by token name

**Code-side already updated:** the `rust` token has been renamed to `safety` in both `tailwind.config.js` and `globals.css` as of commit `d018bcf`. Zero usage existed in shipped code at the time of rename, so no consumer breakage occurred.

---

## What this addendum does NOT change

- Any component spec in v4 §2 through §10 (structure, layout, padding, typography, behavior) — all unchanged
- Type scale (§1.3) — unchanged
- Spacing scale (§1.4) — unchanged
- Radius scale (§1.5) — unchanged
- Border weights (§1.6) — unchanged
- Voice exemplars (§4.x) — unchanged
- Copy rules — unchanged
- Component documentation for Block B onboarding (B1, B2, etc. in v4 §5) — unchanged, ready to use for Block B build

---

**End of DESIGN_SYSTEM v4 → v5 ADDENDUM.** Pair with `DESIGN_SYSTEM_v4.md` for complete spec coverage.
