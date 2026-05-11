# GREAT MINDS — Design System v4

> **Purpose:** Production-ready design specification for the Great Minds (Philosopher) reflective companion app. Source of truth for all visual, typographic, and interactive decisions.
>
> **Status:** Foundation locked. **43 screens specced** across Blocks 1–6 + Block 9.
>
> **Companion documents:**
> - `SCREENS_TRACKING_v4.md` — full screen inventory and per-screen specs
> - `USER_FLOW_v4.md` — how screens connect across user journeys
> - `IMPLEMENTATION_BACKLOG_v4.md` — non-UI implementation work
>
> **Version history:**
> - v1 (May 1, 2026) — initial design system, 19 screens
> - v2 (May 1, 2026) — Block 3 (Discovery), Block 4 (Auth), Block 5 (Reflection & Memory) added; 31 screens
> - v3 (May 1, 2026) — Block 6 (Account, Billing & Privacy) added; 39 screens
> - v4 (May 2, 2026) — Block 9 (App-wide empty/error states) added; 43 screens
>
> **Changelog v3 → v4:**
> - Block 9 (app-wide empty/error states): J1 Server error / 5xx, J2 App-wide offline (non-chat shell), J3 Empty saved reflections, J5 Empty conversation history. **All four reuse-only — zero new components, zero new ornaments.**
> - **J4 dropped from scope.** "Empty insights" had no surface to live in (F2 lite is in-chat, kept insights flow into F1). Subsumed by J3.
> - **K1/K2 deferred to v2** explicitly. Push permission and in-app notification banner not in v1 scope.
> - **§1.7 / Rust semantic clarified**: Rust never used for app-wide server-side errors. Reserved for actionable user-side errors and destructive actions only. Server-side errors use the calm-pause Sepia ornament family.
> - **§7.3 Bronze offline ornament scope expanded**: was "C6c only", now used in C6c (chat cold-start) and J2 (app-wide offline). Same ornament — no per-screen variants.
> - **§7.3 New entry: Sepia concentric circles ornament**: 50–52px, 1px Sepia stroke + center dot. Calm pause metaphor. Used in H4b (payment canceled) and J1 (server error). Was previously only specced inline in H4b.
> - **§4.3 Voice exemplars**: added Block 9 headlines (J1, J2, J3, J5).
> - **§4.10 Offline-family copy locked**: all offline states share "Waiting for a connection." headline + "Great Minds needs a connection to..." body. Drop "internet" — "connection" alone reads cleaner. **Applies retroactively: C6c headline updated from "Waiting on connection." to "Waiting for a connection."**
>
> **Changelog v2 → v3:**
> - Block 6: I1 Account hub, I2 Notifications, I3 Privacy & data, I4 Help & support, I5 About & legal, I6 Logout sheet, H5 Subscription management, H6 Cancel reason sheet
> - **Rust semantic extension** (§1.2): Rust may now be used for (1) error states, (2) destructive confirmation actions. Never for selection, upsell, warning decoration, or generic emphasis.
> - **New component 2.8 Destructive outlined button**: transparent bg, 0.5px Rust border, Rust text, 4px radius, Cormorant 17 weight 500. Used only for final destructive CTA after explicit user confirmation friction (e.g. type-DELETE input).
> - **New component 2.9 Tertiary text-link button**: low-emphasis action surface for non-primary paths in heavy decision contexts (e.g. Cancel Pro on H5).
> - **New component 3.31 Toggle**: preference toggle for binary settings. Track 46×26 / 4px radius (NOT iOS pill). Used in I2 Notifications and any future binary preference.
> - **New component 3.32 Settings row**: structured row for grouped lists (label + supporting + chevron/meta). Reused across all I-series screens.
> - **New component 3.33 Status card** (subscription summary): eyebrow + value + meta in single card; 5 state variants for H5.
> - **New component 3.34 Reason option** (single-select radio card): for H6 cancellation reasons; reusable for future surveys.
> - **Voice section** (§4.4): added utility-screen vs hub-screen title pattern (period vs no period).

---

## 1. Foundation

### 1.1 Aesthetic philosophy

Editorial premium. Antiquarian elegance, not nostalgic kitsch. Parchment + ink + restrained gold. Calm, literate, intimate, modern. Not clinical, not toy-like, not generic AI-startup. Flat surfaces, tonal hierarchy, no shadows except subtle elevation in modals/sheets.

Forbidden aesthetic territories:
- Wellness app vocabulary (rounded pills, pastel gradients, generic icons)
- Material Design shadows and elevations
- iOS-native button styling (except where mandated by Apple HIG, e.g. Apple Sign In button)
- Decorative ornaments beyond the locked Bronze divider
- Generic SaaS energy (countdowns, badges, "Most popular" labels)

### 1.2 Color palette

11 tokens. Hex values are exact and not subject to taste reinterpretation.

| Token | Hex | Use |
|---|---|---|
| Vellum | `#FAF4E6` | Page background, input bar, bottom sheet bg |
| Paper | `#FFFFFF` | Card surface, chat scroll area |
| Linen | `#E8DCC4` | Persona bubble, default avatar bg, weekly letter unread card, slow connection banner |
| Linen Deep | `#DDD0B5` | Selected chip fill, selected option fill |
| Edge | `#D4C8B0` | Borders (default 0.5px), dividers, hairlines |
| Ink | `#1F1B14` | Primary text, primary action fill, user bubble fill |
| Charcoal | `#5A5246` | Secondary text, body copy, avatar initials, disabled button text |
| Sepia | `#8A7E6A` | Muted text, captions, timestamps, eyebrow labels, chevrons |
| Bronze | `#A8884A` (or `#B89968` for stronger contexts) | Bookmarks, premium accents, dividers, app-voice avatar marker, suggested insight border, weekly letter unread dot |
| Bronze Dark | `#8A7340` | Bronze borders, hover state |
| Rust | `#A05A3C` | Error states ONLY (failed messages, payment failed indicator) |

**Rules:**
- Bronze is a structural token, not decorative. Use for: bookmarks, payment success ornament, app-voice safety bubble avatar, divider lozenges, suggested insight cards, weekly letter unread state, "sentence worth keeping" pull-quotes.
- **Rust semantic** (extended in v3, clarified in v4): Rust may be used for (1) **actionable user-side error states** (failed messages, payment failed indicator, payment issue text/dot in H5 past due), and (2) destructive confirmation actions (final CTA for irreversible operations like account deletion). Never for selection, upsell, warning decoration, generic emphasis, or **app-wide server-side errors** (which use the calm-pause Sepia ornament family — see §7.3 and J1 spec). Server 5xx is not user-actionable in the same way payment failure is — it is "our problem", which requires a calm tone, not a Rust alarm.
- Rust outlined buttons are reserved for confirmed destructive intent only — they require explicit user friction first (e.g. type-DELETE input). Never use Rust solid fill on buttons.
- No new colors. If a context "needs" a new color, the design is wrong.

### 1.3 Typography

Two typefaces. Locked.

- **Cormorant Garamond** (display): titles, persona names, headlines, button labels, large pricing numerals, italicized saved-line quotes
- **Lora** (body): body copy, chat bubbles, captions, eyebrows, microcopy
- **System fonts (-apple-system / Roboto)**: ONLY used inside Apple Sign In and Google Sign In buttons per their respective brand guidelines. Never elsewhere.

Six-step type scale:

| Step | Size / Line | Family | Weight | Use |
|---|---|---|---|---|
| Display | 44 / 48 (heroes 38–40) | Cormorant Garamond | 300 (light) | "Great Minds" wordmark, hero |
| Title | 30 / 36 | Cormorant Garamond | 400 (regular) | Onboarding screen titles, weekly letter headline |
| Subtitle | 22 / 28 | Cormorant Garamond | 400 / 500 | Section heads, persona names in cards, F1 saved line italics |
| Body | 15 / 22–25 | Lora | 400 | Chat bubbles, content paragraphs, weekly letter body |
| Caption | 13 / 19 | Lora | 400 | Card descriptions, supporting copy |
| Eyebrow | 11 / 14, letter-spacing 0.18em, uppercase | Lora | 400 / 500 | Section labels ("Today's question", "About", "Suggested for this moment") |

**Chat-specific:**
- Bubble body: Lora 14–15 / 22 line-height (tighter than reading body — denser conversational rhythm)
- Timestamps: Lora 10–11, Sepia
- Eyebrows in chat (e.g. "Great Minds", "Epictetus · brought in", "Great Minds · Insight"): Lora 9, Sepia, letter-spacing 0.18em, uppercase

**F1 saved-line specific:**
- Italicized quote: Cormorant Garamond 17, weight 400, italic
- Source meta line: Lora 11, Sepia ("Carl Jung · 2 days ago")

**F4 weekly letter specific:**
- Date eyebrow: Lora 11, Sepia, letter-spaced uppercase, centered
- Title: Cormorant 28, weight 400, centered
- Body paragraphs: Lora 14, Ink, line-height 1.75
- Pull-quote ("A sentence worth keeping"): Cormorant 18, weight 400, italic, with Bronze 1px left border + 14px 18px padding
- Suggested next mind row: Cormorant 16 weight 500 + Lora 11 Charcoal tagline

**Subtitle reservation:** Cormorant 20–22 weight 400 is reserved for hero/emotional copy ("Reflect with the world's greatest thinkers"). Not used for functional UI text.

### 1.4 Spacing scale

Locked: `4 / 8 / 12 / 16 / 24 / 32 / 48` (px). Use rem for vertical rhythm in long content; px for component-internal gaps.

### 1.5 Radius scale

Three steps. No more.

| Step | Value | Use |
|---|---|---|
| sm | 4px | Buttons, inputs, chips, theme tags, send button, number badges, OTP fields |
| md | 6px | Persona cards, content surfaces, chat bubbles, portrait frames, weekly letter cards, F1 saved cards, F6 history cards |
| lg | 8px | Modals, bottom sheets (top corners), hero blocks, chat bubbles (alt), suggested insight card |

Sharp-leaning intentionally. Wellness-app-territory begins at ~10px+. We do not go there.

**Forbidden:** mixed radii within the same component, fully rounded pill shapes (`border-radius: 999px`) except for circular avatars, the typing indicator dots, and the weekly letter unread Bronze dot indicator.

### 1.6 Border weights

- 0.5px Edge — default (cards, inputs, chips, dividers, hairlines)
- 1px Ink — selected chip state, focused input, selected disclaimer checkbox card
- 1px Bronze — suggested insight card border, weekly letter pull-quote left border
- Never used: 2px+ borders, double borders, dashed (except empty state ornament card and "quiet week" weekly letter card)

### 1.7 Forbidden visual patterns

These never ship:
- Drop shadows on cards (subtle elevation only on modals/sheets)
- Gradients (except portrait artwork, where they belong inside the image)
- Blur effects, neon glows
- Emoji in product UI (user-generated content fine; system UI never)
- Material Design ripple effects
- iOS bounce / overscroll affordances on web
- Frosted glass / glassmorphism
- Confetti, particle effects, achievement animations

---

## 2. Universal button patterns

### 2.1 Primary button (Ink solid)

```
background: #1F1B14
color: #FAF4E6
border: none
padding: 14–15px (mobile), 13–15px (chips/inline)
font: Cormorant Garamond 17–18px, weight 500
border-radius: 4px
```

Use: one per screen as the primary call to action ("Begin", "Continue", "Start conversation", "Continue with Pro", "Try again", "Continue with email", "Keep" on insight card).

### 2.2 Secondary button (Outlined)

```
background: transparent
color: #1F1B14
border: 0.5px solid #1F1B14
padding: 13.5–14.5px
font: Cormorant Garamond 17–18px, weight 500
border-radius: 4px
```

Use: paired alternative to primary ("Explore Minds" with "Begin"), "See all minds", "Go back" in error states, "Dismiss" on insight card.

### 2.3 Disabled button (Universal)

```
background: #E8DCC4 (Linen)
color: #5A5246 (Charcoal — readable, not faded)
border: none
cursor: not-allowed
```

Applied to send button, Continue button when no input, Continue button when disclaimer checkboxes incomplete, any other disabled state. **Charcoal text, not Sepia** — must remain legible.

### 2.4 Tertiary / text-link button

```
background: transparent
color: #5A5246 (Charcoal) or #1F1B14 (Ink for high-priority actions)
border: none
padding: 10px (smaller hit area acceptable for low-stakes dismissals)
font: Lora 13px, regular
```

Use: "Maybe later", "Try again" as secondary in canceled flow, "Go back" microcopy, "Resend" on OTP screen, "contact support" in payment failed.

### 2.5 Send button

Square, 40×40, 4px radius. Three states:
- **Disabled** (no input): Linen bg, Sepia arrow
- **Enabled** (text present): Ink bg, Vellum arrow
- **Sending**: Ink bg, Vellum spinner (border arc rotating, 1.4s duration)

Arrow: simple upward, 1.75px stroke, round linecaps. Not paper-airplane (cliché), not NW-arrow (ambiguous).

### 2.6 Apple Sign In button (compliance-locked)

```
background: #000000
color: #FFFFFF
border: none
padding: 13px (height: 50px total)
font: -apple-system, system-ui, sans-serif, 16px, weight 500
border-radius: 4px
icon: official Apple logo SVG, 16×20, white fill
label: "Continue with Apple"
icon-text gap: 10px
```

**Per Apple Sign In Human Interface Guidelines.** Do NOT customize. Required for App Store submission compliance.

### 2.7 Google Sign In button (compliance-locked)

```
background: #FFFFFF
color: #1F1F1F
border: 1px solid #DADCE0
padding: 13px (height: 50px total)
font: 'Roboto', system-ui, sans-serif, 14px, weight 500, letter-spacing 0.1px
border-radius: 4px
icon: official 4-color G logo SVG, 18×18 (blue/green/yellow/red brand colors)
label: "Continue with Google"
icon-text gap: 10px
```

**Per Google Identity branding guidelines.** Do NOT customize colors or logo. Custom font (Roboto) is required brand element.

### 2.8 Destructive outlined button (NEW v3)

Reserved for final destructive CTA after explicit user confirmation friction (e.g. type-DELETE input on I3 account deletion). Never used for any other purpose.

```
background: transparent
color: #A05A3C (Rust)
border: 0.5px solid #A05A3C (Rust)
padding: 13.5px
font: Cormorant Garamond, 17px, weight 500
border-radius: 4px
```

**Rules:**
- Never used for primary or default actions. Always paired with a Cancel button placed *before* it in the user's reading order (Cancel above, destructive below in vertical stacks).
- Never used as a Rust solid-fill button. Outlined treatment only.
- Disabled state: same border + Sepia text + cursor not-allowed (until friction step is satisfied, e.g. exact "DELETE" typed).
- Used in: I3 delete confirm sheet. Reusable for future irreversible actions (clear all data, log out from all devices, etc.).

### 2.9 Tertiary text-link button (NEW v3)

Lower-emphasis action surface for non-primary paths inside heavy decision contexts where a full secondary button would visually compete with the primary CTA.

```
background: transparent
color: #5A5246 (Charcoal)
border: none
padding: 14px (centered, full-width tap target)
font: Lora 13px, regular
text-decoration: underline
text-decoration-thickness: 0.5px
text-underline-offset: 3px
```

**Difference from 2.4:** 2.4 is a small dismiss action ("Maybe later"). 2.9 is a deliberate path that's intentionally subordinated visually (e.g. Cancel Pro under Manage Pro subscription on H5).

**Used in:** H5 Pro active state ("Cancel Pro").

---

## 3. Components

### 3.1 Persona card — list variant

Used in: Best matches (B4), Explore Minds list view (D2).

```
background: #FFFFFF (Paper)
border: 0.5px solid #D4C8B0 (Edge)
border-radius: 6px (md)
padding: 16px (or 16px 36px 16px 16px when chevron present)
position: relative

internal layout (vertical):
  - number badge (optional, ranked contexts only): 22×22, Ink bg, Vellum text, Cormorant 12 weight 500, radius 4
  - row: avatar 56×56 (Linen bg, Edge border, Cormorant initials Charcoal) + name (Cormorant 19 weight 500) + tagline (Cormorant 13 Charcoal)
  - eyebrow "Why he/she may help" (Lora 10 Sepia uppercase 0.18em)
  - copy (Lora 12 Ink, 1.55 line-height, 2 lines max)
  - tags row (max 2): Lora 11 chips, Vellum bg, Edge border, 4px radius
  - chevron right edge, vertically centered: SVG 10×16, 1px Sepia stroke
```

Tap target: entire card. Cards never have individual buttons (avoids visual noise).

### 3.2 Persona card — D2 list view (full portrait variant)

Used in: D2 Explore Minds vertical scroll.

```
background: #FFFFFF
border: 0.5px solid #D4C8B0
border-radius: 6px
overflow: hidden

structure:
  - portrait area: aspect-ratio 4/3, Linen bg with persona portrait
  - text block: padding 16px 18px
    - name: Cormorant 22 weight 500
    - tagline: Lora 12 Charcoal, single line
```

### 3.3 Persona card — D3 grid tile

Used in: D3 Explore Minds grid view (2-column).

```
background: #FFFFFF
border: 0.5px solid #D4C8B0
border-radius: 6px
overflow: hidden

structure:
  - portrait area: aspect-ratio 4/5, Linen bg with persona portrait
  - text block: padding 12px 12px 14px
    - name: Cormorant 17 weight 500 (smaller scale than D2 list)
    - NO tagline (grid is portrait-led; tap to detail for full info)
```

Long names (Simone de Beauvoir, Sigmund Freud) wrap to 2 lines naturally — no ellipsis.

### 3.4 Persona card — Pro-locked variant

Same as list/grid + small Pro pill chip on portrait.

```
Pro pill (D2 list scale):
  position: absolute, top: 12px, right: 12px
  background: rgba(31,27,20, 0.85)
  color: #FAF4E6
  padding: 4px 10px
  font: Lora 10px, letter-spacing 0.16em, uppercase
  border-radius: 4px
  icon: padlock outline 9×11, 0.9 stroke Bronze (#A8884A)

Pro pill (D3 grid scale, smaller):
  position: absolute, top: 8px, right: 8px
  padding: 3px 7px
  font: Lora 9px
  border-radius: 3px
  icon: padlock outline 7×9
```

CTA on locked persona detail (B6) screen changes from "Start conversation" to "Unlock with Pro" with padlock icon left of label.

### 3.5 Chat bubble

**User (right-aligned):**
```
background: #1F1B14 (Ink)
color: #FAF4E6 (Vellum)
padding: 10–12px / 14–16px
border-radius: 8px (lg)
max-width: 75% of container
font: Lora 14–15 / 22 line-height
```

**Persona (left-aligned, with avatar):**
```
background: #E8DCC4 (Linen)
color: #1F1B14 (Ink)
padding: 10–12px / 14–16px
border-radius: 8px
max-width: calc(75% - 32px) — accommodates avatar
font: Lora 14–15 / 22 line-height
avatar: 24×24 circle, Linen bg, Edge border 0.5px, Cormorant 11 weight 500 Charcoal initial
gap between avatar and bubble: 8px
```

Avatar appears only on first message of a continuous persona block, not repeated for stacked messages.

**Timestamp:**
- User: text-align right, 11px Sepia, margin-top 6px
- Persona: margin-left 32px (aligned with bubble), 10–11px Sepia

### 3.6 Typing indicator

Inside Linen bubble, 3 dots:
```
3× circle: 7×7px, #5A5246 (Charcoal), staggered opacity 0.35 / 0.6 / 0.35
animation: pulse 1.4s infinite, opacity oscillates
spacing: 6px gap
padding: 16px 18px (slightly tighter than message bubble)
```

### 3.7 Bookmark indicator

Position absolute, top-right corner inside saved persona bubble.
```
SVG: 12×14 bookmark shape, Bronze fill, Bronze Dark stroke 0.6
position: top: 8px, right: 8px
```

### 3.8 Toast (saved confirmation)

Bottom-centered above input bar, fades after 2s.
```
background: #1F1B14
color: #FAF4E6
padding: 9px 16px
border-radius: 4px
font: Lora 12px
icon left: bookmark Bronze 11×13
text: "Saved to your reflections"
position: absolute, bottom: ~76px (above input bar), left: 50%, transform: translateX(-50%)
```

### 3.9 Theme chip

Two contexts: selectable (onboarding multi-select) and descriptive (read-only tags).

**Selectable:**
```
default:
  background: #FFFFFF
  color: #1F1B14
  border: 0.5px solid #D4C8B0
  padding: 12px 14px
  font: Lora 14, weight 400
  border-radius: 4px
  text-align: left

selected:
  background: #DDD0B5 (Linen Deep)
  color: #1F1B14
  border: 1px solid #1F1B14
  padding: 11.5px 13.5px (compensates for thicker border)
  font-weight: 500

hover (desktop only):
  border becomes Ink
```

**Descriptive:**
```
background: #FAF4E6 (Vellum)
color: #1F1B14
border: 0.5px solid #D4C8B0
padding: 3px 9–10px
font: Lora 11–12px
border-radius: 4px
```

Smaller, non-interactive, used in persona detail "Best for" and best-match cards.

### 3.10 Filter pill (F1 reflections, D2/D3 future)

```
default:
  background: #FFFFFF
  color: #1F1B14
  border: 0.5px solid #D4C8B0
  padding: 6px 14px
  font: Lora 12px
  border-radius: 4px

active:
  background: #1F1B14
  color: #FAF4E6
  border: none
  padding: 6px 14px
```

Horizontal scrollable row when overflow. Single-active selection.

### 3.11 Input field — multiline (textarea)

```
background: #FFFFFF
border: 0.5px solid #D4C8B0
border-radius: 4px
padding: 12–14px
min-height: 64–96px (grows with content)
font: Lora 14–15 / 22

placeholder color: #8A7E6A (Sepia)
focus state: border becomes 1px Ink
character count (when typing): bottom-right, Lora 11px Sepia
```

### 3.12 Input field — email/single-line

```
background: #FFFFFF
border: 0.5px solid #D4C8B0
border-radius: 4px
padding: 14px
font: Lora 14, color #1F1B14
placeholder: Lora 14, color #8A7E6A
height: ~50px (matches Apple/Google buttons)
```

### 3.13 OTP input field (6-digit)

```
container: display flex, gap 8px, justify-content center

each cell:
  width: 42px
  height: 52px
  background: #FFFFFF
  border: 0.5px solid #D4C8B0 (default)
  border: 1px solid #1F1B14 (focused or filled)
  border-radius: 4px
  text-align: center
  font: Cormorant Garamond 22px, weight 500, color #1F1B14
  caret: Ink
```

Behavior:
- Auto-advance to next field on input
- Backspace returns to previous field
- Paste of 6 digits auto-fills all cells
- iOS SMS autofill supported (when applicable)

States:
- Default empty: 0.5px Edge border
- Focused: 1px Ink border
- Filled: 1px Ink border (visual confirmation)
- Error: 1px Rust border + inline error message below
- Disabled (during verification): cells dimmed to opacity 0.6

### 3.14 Disclaimer checkbox card (A6+A7)

Used for the two combined required confirmations on the disclaimer screen.

```
unchecked:
  background: #FFFFFF
  border: 0.5px solid #D4C8B0
  border-radius: 4px
  padding: 14px
  display: flex
  gap: 12px
  align-items: flex-start

checked:
  background: #FFFFFF
  border: 1px solid #1F1B14
  padding: 13.5px (compensates for thicker border)

checkbox:
  width: 22px, height: 22px
  border-radius: 3px
  default: 1px solid Edge / 0.5px solid Edge unchecked
  checked: Ink fill, white checkmark inside

label text:
  Lora 14, color #1F1B14, line-height 1.55
  weight 500 for shorter labels (age confirmation)
  weight 400 for longer multi-line labels (positioning disclaimer)
```

Tap target: entire card (label + checkbox both clickable).

### 3.15 Chat input bar

Fixed bottom, Vellum bg, top border 0.5px Edge.
```
background: #FAF4E6 (Vellum, contrasting with Paper chat area above)
border-top: 0.5px solid #D4C8B0
padding: 12–14px / 16px
display: flex, align-items: center, gap: 10–12px
```

### 3.16 Quick actions row

Below persona reply, left-aligned (margin-left 32px to align with bubble):
```
display: flex, gap: 6px, flex-wrap: wrap
each button:
  background: #FAF4E6
  color: #1F1B14
  border: 0.5px solid #D4C8B0
  padding: 6px 10px
  font: Lora 11px
  border-radius: 4px
  inline-flex with 5px gap, icon left of label
```

Three actions: "Ask harder", "Bring another mind", "Save line".

Hybrid responsive: full labels at ≥360px wide, icon-only below. After "Save line" tapped, the chip becomes "Saved" with selected state styling (Linen Deep + Ink border).

### 3.17 Bronze divider (manuscript ornament)

Used at: Welcome (B1), Upgrade (H1), Payment success (H3), F4 weekly letter detail.
```
container: display flex, align-items center, gap 10px

structure:
  - left line: height 1px, background #B89968, flex 1
  - center lozenge: 9×9 square rotated 45°, fill #B89968
  - right line: height 1px, background #B89968, flex 1
```

Stronger than 0.5px Edge dividers — this carries premium weight.

### 3.18 Section divider (subtle)

Used inside chat for date markers, "Continuing with [persona]" indicators, F1 date groupers.
```
container: flex, gap 10px, align-items center
  - line: 0.5px #D4C8B0, flex 1
  - text: Lora 10 Sepia, letter-spacing 0.16–0.18em, uppercase
  - line: 0.5px #D4C8B0, flex 1
```

### 3.19 Bottom tab bar

Editorial-styled, not iOS native.
```
background: #FAF4E6
border-top: 0.5px solid #D4C8B0
padding: 10px 0 16px
display: flex, justify-content: space-around

each tab:
  display: flex, flex-direction: column, align-items: center, gap: 4px
  icon: 18–20×18–20 SVG, 1.2 stroke Ink (line-only, no fill)
  label: Lora 10px, Ink

active tab: weight 500, opacity 1
inactive: weight 400, opacity 0.55
```

Four tabs: Today / Library / Reflections / Account.

**Per-tab routing (locked v2):**
- **Today** → D1 Home
- **Library** → D2/D3 Explore Minds + F6 Reflection history (sub-section)
- **Reflections** → F1 Saved + F3 Weekly letters (sub-section)
- **Account** → I1 Profile (Block 6, pending)

Tab bar is **hidden** on D2/D3 (immersive browse) and on chat screens (C1+).

### 3.20 Bottom sheet

Used for: "Bring another mind" picker (C9a), future contextual pickers.
```
position: absolute, bottom: 0, left: 0, right: 0
background: #FAF4E6
border-radius: 12px 12px 0 0
padding: 16px 0 22px
box-shadow: 0 -2px 12px rgba(31,27,20, 0.12) — only modal/sheet shadow allowed

drag handle:
  margin: 0 auto 18px
  width: 40px, height: 4px
  background: #D4C8B0, border-radius: 2px

chat behind sheet: opacity 0.5, dimmed but visible
```

### 3.21 View toggle (D2 ↔ D3)

```
container: display flex, gap 12px

each toggle button:
  cursor: pointer
  display: flex, align-items: center
  icon: 14×14 SVG, Ink stroke 1.1 (active) or 1.2 (inactive)

active: opacity 1.0
inactive: opacity 0.4
```

Transition between D2 ↔ D3: **soft fade 200ms** (cards fade out/in, no layout animation).

Persistence: User's preferred view stored in localStorage (v1) or DB (v2 when accounts mature).

### 3.22 Pro pill chip

Used on locked persona portraits.

**D2 list / B6 detail scale:**
```
position: absolute, top: 12px, right: 12px (inside portrait)
background: rgba(31,27,20, 0.85) — semi-transparent Ink
color: #FAF4E6
padding: 4px 10px
font: Lora 10px, letter-spacing 0.16em, uppercase
border-radius: 4px
display: inline-flex, gap: 5px

icon: padlock outline 9×11, stroke Bronze (#A8884A) 0.9
text: "Pro"
```

**D3 grid scale:**
```
position: absolute, top: 8px, right: 8px
padding: 3px 7px
font: Lora 9px
border-radius: 3px
icon: padlock outline 7×9
```

### 3.23 Status banner (in-chat)

Slim banner directly under chat header. Two variants:

**Slow connection (info):**
```
background: #F2E5C8
border-bottom: 0.5px solid #D4C8B0
padding: 9px 16px
color: #5A5246
font: Lora 12, line-height 1.4
icon: wifi-with-dot, Sepia stroke 1px
```

**Offline (warning, muted Rust):**
```
background: #F0E0D5 (Rust-tinted, not flat Rust)
border-bottom: 0.5px solid #C9A593
padding: 10px 16px
color: #A05A3C
font: Lora 12, weight 500
icon: wifi-crossed, Rust stroke
```

### 3.24 Safety bubble (app-voice)

Distinct from persona bubbles. Used during safety mode.

```
avatar (24×24 circle):
  background: #FAF4E6 (Vellum, NOT Linen — distinguishes from persona)
  border: 0.5px solid #D4C8B0
  center: Bronze diamond (lozenge SVG 9×9, rotated 45°, #B89968 fill)

eyebrow above bubble:
  margin-left: 32px
  text: "Great Minds"
  font: Lora 9, Sepia, letter-spacing 0.18em, uppercase

bubble: same Linen bg as persona bubbles
content has critical lines bolded (weight 500), e.g. immediate-danger sentence
soft re-entry prompt below: italic, Charcoal, Bronze left border 1px
```

### 3.25 Suggested insight card (F2 lite, in-chat)

Inline app-voice insight that surfaces after qualifying conversations.

```
container:
  margin-left: 32px (aligns with persona bubbles)
  background: #FAF4E6 (Vellum, NOT Linen — distinguishes from persona/safety)
  border: 0.5px solid #B89968 (Bronze — premium signal)
  border-radius: 6px
  padding: 18px 18px 14px

eyebrow above card:
  text: "Great Minds · Insight"
  font: Lora 9, Sepia, 0.18em uppercase

content row:
  display: flex, gap: 10px, align-items: flex-start
  - Bronze diamond marker 9×9 (left)
  - Insight text: Cormorant 17, weight 400, italic, line-height 1.4

action row (top border 0.5px Edge):
  display: flex, gap: 8px, padding-top: 12px

  Keep button (primary):
    background: #1F1B14
    color: #FAF4E6
    padding: 9px
    flex: 1
    icon: bookmark outline Vellum + label "Keep"

  Dismiss button (secondary):
    background: transparent
    color: #5A5246
    border: 0.5px solid #D4C8B0
    padding: 9px
    flex: 1
    label: "Dismiss"
```

**Behavior:**
- Surfaces inline at the end of chat after qualifying conversation (≥10 user messages)
- Max 1 per conversation
- Keep → flows to F1 with insight tag indicator
- Dismiss → permanent dismiss, never resurfaces for that conversation
- For free users: 1 preview shown across product lifetime, then locked

### 3.26 Empty state card

Used at first-day Home, empty Library, empty Reflections.
```
background: #FFFFFF
border: 0.5px DASHED #C9BC9F (only place dashed border is permitted, plus quiet-week letter card)
border-radius: 6px
padding: 24px 20px

structure:
  - top ornament: thin Edge line + Bronze star/lozenge SVG centered + thin Edge line
  - centered headline (Cormorant 19, weight 400)
  - centered description (Lora 13, Charcoal, 1.6 line-height)
  - 3-item list (mini-icons in 24×24 Edge-bordered squares + label + description)
```

### 3.27 Day marker (chat divider)

Inside chat, marks new sessions or first messages.
```
display: flex, gap: 10px, align-items: center, margin: 24px 0
  - line: 0.5px #D4C8B0, flex 1
  - text: "Today · 9:41" or "Yesterday" — Lora 10, Sepia, 0.18em uppercase
  - line: 0.5px #D4C8B0, flex 1
```

### 3.28 Date grouper (F1, F6 lists)

Section heading inside chronological lists:
```
font: Lora 10, Sepia, 0.18em uppercase
margin: 8px 0 (or 16px before next group)
text: "This week" / "Earlier" / "Last month" (relative, adapts to data range)
```

### 3.29 Weekly letter card states (F3)

Three visual states in the weekly letter inbox.

**Unread:**
```
background: #E8DCC4 (Linen)
border: none
padding: 18px 20px
position: relative

unread dot indicator:
  position: absolute, top: 18px, right: 18px
  width: 8px, height: 8px, border-radius: 999px
  background: #B89968 (Bronze)

content:
  - eyebrow: "Sunday, May 4 · Unread" (Lora 10, Sepia, 0.18em uppercase)
  - title: Cormorant 19, weight 500, color Ink
  - preview: Lora 13, Charcoal, 1.55 line-height, 2-line truncation
```

**Read:**
```
background: #FFFFFF (Paper)
border: 0.5px solid #D4C8B0
padding: 18px 20px

content:
  - eyebrow: date only (no "· Unread")
  - title: Cormorant 18, weight 500
  - preview: Lora 13, Charcoal
```

**Quiet week (no letter generated):**
```
background: #FFFFFF
border: 0.5px DASHED #C9BC9F
padding: 18px 20px

content:
  - eyebrow: date
  - headline: "A quiet week." (Cormorant 17, weight 400, italic, Charcoal)
  - explanation: "Not enough reflection this week to draw a letter from. Your next one arrives Sunday." (Lora 12, Sepia)
```

### 3.30 Pull-quote (F4 weekly letter)

"A sentence worth keeping" callout inside long-form letter content.

```
background: #FFFFFF
border-left: 1px solid #B89968 (Bronze)
padding: 14px 18px
margin: 24px 0

eyebrow: "A sentence worth keeping" (Lora 10, Sepia, 0.18em uppercase)
quote: Cormorant 18, weight 400, italic, line-height 1.45
```

### 3.31 Toggle (NEW v3)

Preference toggle for binary settings. Used in I2 Notifications. Distinct from 3.14 Disclaimer checkbox card (which is for one-time agreement contexts only).

```
track:
  width: 46px
  height: 26px
  border-radius: 4px (NOT iOS pill — locked at 4px)

knob:
  width: 20px
  height: 20px
  border-radius: 2px (square knob, not circle — non-iOS aesthetic)

OFF state:
  track: #FAF4E6 (Paper) bg
  border: 0.5px solid #D4C8B0 (Edge)
  knob: #DDD0B5 (Linen Deep) positioned left, 2.5px inset

ON state:
  track: #1F1B14 (Ink) bg
  border: none
  knob: #FAF4E6 (Vellum) positioned right, 3px inset

DISABLED state:
  track: #E8DCC4 (Linen) bg
  border: 0.5px solid #D4C8B0 (Edge)
  knob: #8A7E6A (Sepia)
  opacity: 0.55

DISABLED + Pro state (used when feature is Pro-locked for Free users):
  Toggle is hidden entirely; replaced by inline Pro pill (3.22) at right of row.
  Tap on entire row routes to H1 Upgrade.
```

**Forbidden:** iOS pill capsule shape, fully-rounded track, green/red color states, generic Material switches.

### 3.32 Settings row (NEW v3)

Structured row for grouped lists in I-series screens (account hub, sub-screens). Reusable across all settings/preferences contexts.

```
container: card (3.x card pattern, single or grouped)
padding: 14–16px / 16px
display: flex, justify-content: space-between, align-items: center (or flex-start for multiline supporting text)
gap: 12–14px

label: Lora 14, Ink (#1F1B14)
supporting (optional): Lora 12, Charcoal (#5A5246), 1.45 line-height, margin-top 3–4px
right-element (one of):
  - chevron 6×10 Sepia (1px stroke) — for in-app navigation
  - outbound icon 11×11 Sepia (1px stroke) — for external browser links
  - meta text Lora 12 Charcoal — for inline status (e.g. "Pro · Renews June 14")
  - 3.31 Toggle — for binary settings
  - 3.22 Pro pill — for Pro-locked rows
```

Dividers between rows in same card: 0.5px Edge (#D4C8B0) horizontal line. No divider on last row.

**Eyebrow group label** (when card belongs to a labeled section):
```
font: Lora 11, Sepia, letter-spacing 0.18em, uppercase
padding: 0 24px 8px (8px from card top, indented to match section header pattern)
```

### 3.33 Status card — subscription summary (NEW v3)

Single card showing plan + meta. Used exclusively in H5 across 5 states. State variations are content-only; layout/structure constant.

```
container: card (Paper bg, 0.5px Edge border, 6px radius, margin 0 16px)
padding: 18px

structure:
  - eyebrow: "Your plan" (Lora 11, Sepia, 0.12em uppercase)
  - value: plan name (Cormorant 22, weight 400, Ink, margin-top 4px)
  - meta: status copy (Lora 13, Charcoal, 1.55 line-height, margin-top 14px)

Past due value variant:
  value displays plan name + inline status indicator:
    "Pro" (Cormorant 22 Ink) +
    "● Payment issue" (Lora 13, Rust #A05A3C, weight 500, 7px Rust dot, gap 10px)
```

**Rule:** Status card never contains CTA buttons. CTAs appear below the card with 24px gap.

### 3.34 Reason option (single-select radio card) (NEW v3)

Used in H6 cancel reason sheet. Reusable for future single-select surveys.

```
container:
  background: #FFFFFF (Paper)
  border: 0.5px solid #D4C8B0 (Edge)
  border-radius: 6px
  padding: 13px 14px
  margin-bottom: 8px
  display: flex, align-items: center, gap: 12px
  cursor: pointer

selected state:
  border: 1px solid #1F1B14 (Ink, upgraded from 0.5px)

radio control (custom, not native iOS):
  width: 18px, height: 18px
  border-radius: 50%
  border: 0.5px solid #8A7E6A (Sepia) when unselected
  border: 1px solid #1F1B14 (Ink) when selected
  inner fill (selected only): 12×12 Ink circle, centered (3px inset from outer ring)
  background: Vellum (matches sheet bg)

label: Lora 14, Ink, flex: 1
```

**Conditional reveal pattern** (e.g. Other → text field, Technical issue → helper):
The revealed element appears inline directly below the selected option, using:
- For text field: 3.11 Input field (multiline) with margin-top 4px, max-height inline
- For helper card: Paper bg, 2px Ink left border, 6px right radius (no left), padding 14px 16px, 4px top margin, 12px bottom margin

**Rule:** Reveals collapse when another option is selected. Only the currently selected option's reveal (if any) is visible.

---

## 4. Voice principles

### 4.1 App voice vs persona voice

The app speaks in three voices:
1. **App-narrative** (eyebrows, captions, safety messages, system feedback, suggested insights, weekly letters): warm, restrained, never patronizing. "Today's question", "Mind of the day", "We'll suggest the minds best suited to this conversation."
2. **Persona** (chat bubbles, opening invocations): persona-specific, bound by Section 5.7 character anchors. Never references modern phenomena verbatim.
3. **Brand** (Welcome screen, Upgrade screen, marketing copy): Cormorant-led, premium, philosophical. "The full conversation.", "The full library is open."

### 4.2 Forbidden microcopy

- "Loading…" (use specific verbs: "Preparing your checkout")
- "Oops!" / "Something went wrong"
- "You've got this!" / motivational SaaS energy
- "Try Pro free for 7 days!" (we use 14-day money-back guarantee instead)
- "Limited time offer" / countdown timers
- "Most popular" badges
- Therapy jargon presented as our voice ("trigger", "boundary" as noun, "trauma response")
- Generic AI mysticism ("The universe is showing you...", "Your higher self...", "Soul's journey...")
- Diagnostic language ("You suffer from...", "This is anxiety/depression/...")

### 4.3 Voice exemplars (locked)

- Welcome: "Great Minds" / "Reflect with the world's greatest thinkers."
- Onboarding intro: "What brings you here?" / "Choose one or more themes that feel most relevant."
- Need question: "What do you need most?" / "Choose what feels closest right now."
- Match results: "Your best matches" / "Minds selected for your current moment."
- Today's question (sample): "What are you pretending not to know?"
- Empty state: "Your space, beginning to take shape."
- Safety opener: "Some of what you've shared sounds heavy. I want to make sure you're safe right now."
- Limit reached: "You've reached today's free reflections."
- Upgrade hero: "The full conversation." / "All minds, all reflections, all the time you need."
- Payment success: "The full library is open."
- Payment canceled: "No rush." / "You can come back to Pro anytime."
- Cancel CTA: "Maybe later" (never "Skip" or "No thanks")
- Conversation continuity: "Continuing with Carl Jung" (divider after second-mind contribution)
- Auth hero: "Begin your reflection." / "Sign up or sign in to continue."
- OTP screen: "Check your email." / "We sent a 6-digit code to [email]"
- A4 trouble accessing: "Trouble accessing your email?" / "No password to reset — Great Minds uses passwordless sign-in."
- Disclaimer: "Before we begin." / "Two things to confirm."
- Reflections section header: "Your saved lines."
- Weekly letters section header: "Weekly letters."
- Weekly letter title example: "A pattern emerged this week."
- Weekly letter pull-quote header: "A sentence worth keeping"
- Weekly letter quiet state: "A quiet week." / "Not enough reflection this week to draw a letter from."
- F6 history section header: "Past conversations." (renders within "Library" tab) — note: F6 conceptually called "Reflection history" in product strategy, but UI label remains "Past conversations" for clarity.
- Reflection history section: "Past conversations" (UI), "Reflection history" (internal/strategy terminology)
- Suggested insight eyebrow: "Great Minds · Insight"
- Suggested insight actions: "Keep" / "Dismiss"
- J3 empty saved reflections headline: "A space for the lines that stay with you."
- J3 empty saved reflections body: "When a sentence settles, save it. Saved lines live here, ready when you return."
- J5 empty conversation history headline: "Past conversations gather here."
- J5 empty conversation history body: "Every conversation you start is saved here. Return to any of them when you need to."
- J2 / C6c offline headline (locked v4): "Waiting for a connection."
- J2 offline body: "Great Minds needs a connection to load this. Try again when you're back online."
- C6c offline body (locked v4): "Great Minds needs a connection to start new conversations. Your saved reflections remain available below."
- J1 server error headline: "Something on our end."
- J1 server error body: "Something didn't load. Try again in a moment."
- J1 support fallback link (Lora 12, Sepia, link in Ink underlined): "If this persists, contact support."
- Universal retry CTA across J1 / J2 / C6c: "Try again"

### 4.4 Disclaimer copy v1 (locked, versioned)

```
Confirmation 1:
"I am 18 or older."

Confirmation 2:
"I understand Great Minds is for reflection, not therapy, diagnosis, 
crisis support, or medical treatment. If I am in immediate danger or 
crisis, I should contact local emergency services or a qualified 
professional."
```

This text is **versioned in the database** (`disclaimer_version: "v1.0"`). When copy changes, version bumps and existing users prompted for re-acceptance.

### 4.5 Cultural quotes

Used in Welcome, Upgrade, Payment success. Static for v1, rotating set in v2.

Approved for v1:
- Socrates: "The unexamined life is not worth living." (used in Upgrade and Success)

Quote attribution: em-dash + name, Lora 10–11 letter-spaced, Sepia color. No quote in error/cancel states unless intentionally philosophical (Seneca was rejected on canceled payment as it read as snark).

### 4.6 Suggested insight copy guardrails (F2 lite)

**Critical product requirement.** The insight generator (LLM-driven) must enforce:

**REQUIRED:**
- Reference actual words/themes the user used
- One sentence, ≤25 words
- Specific to user's actual conversation content
- Reframe without diagnosing
- Generate ONLY when clear pattern emerges across ≥3 user messages

**FORBIDDEN PATTERNS:**
- "You seem to..." / "You appear to..." (psychological labeling)
- "This is the shadow/inner child/trauma response..." (clinical jargon)
- "The universe is showing you..." / "Your soul..." (mystical phrasing)
- "Many people feel..." / "It's common to..." (generic)
- Second-person directives ("You should...", "You need to...")
- Diagnostic statements

**Example acceptable:**
- "A pattern emerged here: you describe loyalty and self-erasure as if they were the same thing."

**Example rejected:**
- "You seem to have abandonment issues stemming from..." (diagnostic)
- "Your inner shadow is calling to be acknowledged." (mystical)
- "Many people struggle with this." (generic)

This guardrail spec is part of the implementation backlog and must be enforced at the prompt-engineering level. UI design alone cannot prevent low-quality output.

### 4.7 Weekly letter copy structure (F4)

Each weekly letter follows a consistent narrative structure:

1. **Opening observation** (1-2 paragraphs): What pattern emerged this week, grounded in actual user content
2. **Specific references** (1 paragraph): Mention which personas user spoke with and what they said — concrete, not vague
3. **A sentence worth keeping** (pull-quote): Single line that captures the insight of the week
4. **Forward gesture** (1-2 sentences): A question or invitation for the week ahead, not advice
5. **Suggested next mind** (optional): 1 persona to consider for next conversation

Length: 150-250 words total. NOT a recap. NOT a summary. A reflection composed FROM the week's material.

If insufficient material: graceful "A quiet week" state. Do not generate weak content.

### 4.8 Screen title patterns (utility vs hub) (NEW v3)

Hub screens and emotional/brand screens use periods at the end of titles, signalling editorial DNA. Utility/settings screens use no period, signalling functional clarity.

**With period (hub / emotional / brand):**
- "Your account." (I1 hub)
- "Today's question."
- "The full conversation."
- "The full library is open."

**Without period (utility / settings / functional):**
- "Notifications" (I2)
- "Privacy & data" (I3)
- "Help & support" (I4)
- "About & legal" (I5)
- "Subscription" (H5)

**Rule:** Period-bearing titles are exceptions reserved for moments where editorial flair adds product feeling. Settings/utility surfaces stay functional. Apply consistently — do not give every utility screen poetic punctuation.

### 4.9 Stripe / billing copy patterns (NEW v3)

**Microcopy used in paid subscription contexts:**
- Trust line below CTAs: "Billing is managed securely through Stripe." (Lora 12, Sepia, centered)
- Cancel CTA wording: "Continue to Stripe to cancel" (NOT "Cancel subscription" — the app does not execute cancellation; Stripe does. Wording must match technical reality.)
- Past-due explanation: "We couldn't process your latest payment. Update your payment method to keep Pro active." (active voice, no finger-pointing at user, no panic)
- Canceling state copy: "Active until [date]." (factual, calm, no countdown, no anxiety language)
- Canceled/no-access copy: "Your Pro subscription has ended." (past tense, closure, no guilt)

**Forbidden in billing surfaces:**
- Countdown timers ("X days remaining")
- Aggressive urgency ("act now")
- Guilt copy ("we'll miss you", "are you sure?")
- Marketing-ish persuasion ("save 33%")
- Vague status ("subscription updated") — always specific

### 4.10 Offline-family + server-error copy patterns (NEW v4)

All offline and server-side error states share a calm, non-alarming register. Three distinct contexts, two distinct ornament families, one shared retry CTA.

**Offline family (Bronze offline ornament):**
- Headline (locked global): "Waiting for a connection."
- Body baseline: "Great Minds needs a connection to [load this | start new conversations]." + context-specific second sentence
- C6c (chat cold-start offline): "Great Minds needs a connection to start new conversations. Your saved reflections remain available below."
- J2 (app-wide offline, non-chat tabs): "Great Minds needs a connection to load this. Try again when you're back online."

**Server-error family (Sepia concentric circles ornament):**
- Headline: "Something on our end."
- Body: "Something didn't load. Try again in a moment."
- Support fallback (small Lora 12, link Ink underlined): "If this persists, contact support." → routes to I4 mailto with diagnostic block.

**Universal retry CTA (all three contexts):**
- Label: "Try again"
- Style: Ink primary (2.1), centered, content-sized — NOT full-width
- Required CSS: `min-width: 140px; white-space: nowrap;` so the label never wraps to two lines
- Padding: 12px 28px

**Forbidden in offline / server-error surfaces:**
- "Loading…" — use specific verbs or the locked headlines above
- "Oops!" / "Something went wrong" — generic SaaS, no ownership
- "Internet connection" — say "connection" alone (the qualifier is implied and reads cleaner)
- "Please" / "We apologize for the inconvenience" — over-formal, breaks editorial register
- Countdown timers ("Reconnecting in 3…")
- Auto-retry without user action on server errors (J1 retry must be explicit; auto-retry hides systemic problems)
- Rust on server-side errors — see §1.2 Rust semantic clarification

**Why two distinct ornaments:**
J2 (Bronze offline) and J1 (Sepia server error) must be visually distinguishable at a glance. A user retrying J2 who lands on J1 needs to see immediately that the cause has shifted (network → our infra). Same ornament with different headline is not enough — most users do not read headlines on second exposure.

---

## 5. Animation principles

Minimal, functional, never decorative.

- **Streaming**: Persona text streams character-by-character (or word-by-word) over ~1–2 seconds. Typing indicator fades out as streaming begins.
- **Toast**: fade in 200ms, hold 2s, fade out 200ms.
- **Bottom sheet**: slide up from bottom 250ms ease-out. Slide down on dismiss 200ms.
- **Loading spinner**: 1.4s rotation, calm pace.
- **Selected state transitions**: 150ms color/border change, no bounce.
- **D2 ↔ D3 view toggle**: soft fade 200ms (no layout animation).
- **Suggested insight card appearance**: fade in 250ms after persona's last message renders.
- **OTP field auto-advance**: instant, no animation.
- **Forbidden**: confetti, parallax, scroll-jacking, hover-only animations on mobile, particle effects, achievement unlocks.

---

## 6. Responsive notes

Designed mobile-first at 380px width target. PWA-deployable, no native app required for v1.

- Type scale stays constant down to 360px
- 2-column theme grid stays 2-col down to 320px
- 2-column persona grid (D3) stays 2-col down to 320px
- Quick actions row: full labels ≥360px, icon-only below
- Bottom tab bar: 4 tabs spaced equally; sub-360 acceptable, sub-320 risk of label clipping
- OTP fields: 6 fields × 42px + 5 gaps × 8px = 292px total — fits comfortably ≥320px

Desktop: same 380–420px max content width, centered. We do not "expand" the layout — Great Minds is intentionally column-bounded for reading rhythm.

---

## 7. Asset requirements

### 7.1 Portraits

Each persona requires production portrait assets. Specifications:
- **Aspect ratio**: 4:3 for persona detail screen B5/B6 (locked)
- **D2 list aspect**: 4:3 (matches B5/B6)
- **D3 grid aspect**: 4:5 (taller, magazine-cover feel for 2-col layout)
- **Composition**: subject upper/middle third, dark/controllable bottom area for CTA readability if used full-bleed
- **Style**: painted/etched/illustrated, NOT photographic, NOT photo-realistic AI portrait
- **Consistency**: all 6 personas must share treatment (palette range, brush style, lighting direction)
- **Format**: SVG preferred (scalable), high-res PNG fallback
- **Fallback**: if image fails to load, persona initial(s) in Cormorant Garamond, Charcoal on Linen square (list/tile) or Linen circle (chat avatar)

V1 placeholder: ChatGPT-generated images with consistency caveat. V2: commissioned illustrator OR curated public-domain portraits with unified treatment.

### 7.2 Icons

All icons custom SVG, line-only (no fills except in semantic exceptions like bookmark fill, padlock in Pro pill, Bronze diamond in safety/insight markers).
- Stroke weight: 0.8–1.2px standard, 1.5–1.75 for emphasized actions (send arrow)
- Stroke linecap: round
- Color: Ink (#1F1B14) primary, Sepia (#8A7E6A) muted, Bronze (#A8884A) premium accents only

Reference set for production: **Lucide thin** or **Phosphor thin**. Generic wellness-app icon sets (Feather default, Material) are forbidden.

**Exceptions to custom icon rule:**
- Apple Sign In logo: official Apple SVG, mandated
- Google Sign In logo: official 4-color G logo, mandated

### 7.3 Decorative elements

- **Bronze lozenge** (rotated square): 9×9 standard, 6×6 inline. Used in dividers, eyebrows, ornaments, safety bubble avatar, suggested insight markers.
- **Bronze star/sparkle**: 14×14, used in empty states (J3, J5, D1b first-day). 0.7 stroke.
- **Bronze laurel circle**: 40–50px, used in payment success only. Concentric circles + checkmark.
- **Bronze offline ornament**: circle + crossed line + arc, ~56×56 wifi-with-slash metaphor, 1.2px Bronze stroke. **Used in C6c (chat cold-start offline) and J2 (app-wide offline on non-chat tabs)** — same ornament, no per-screen variants.
- **Sepia concentric circles ornament** (NEW v4): 50–52px diameter, 1px Sepia (#8A7E6A) stroke, two concentric circles (outer ~21px radius, inner ~14px radius) + Sepia center dot 2.5px. Calm pause metaphor (NOT alarm). **Used in H4b (payment canceled) and J1 (app-wide server error / 5xx)**. Reusable for any "we paused, no user action required, stand by" state. Sepia (not Bronze) is intentional — Bronze signals premium/active, Sepia signals neutral/muted. The two ornaments must look distinct so users can tell offline (J2, your network) apart from server error (J1, our infra) without reading the headline.

---

## 8. Accessibility

- Minimum text contrast: WCAG AA (4.5:1 for body, 3:1 for large text)
- All locked colors verified against AA. Rust on Vellum = 4.8:1, Charcoal on Linen = 5.1:1, Sepia on Vellum = 4.6:1
- Touch targets: minimum 44×44px (achieved via padding even when visual element is smaller)
- Focus rings on all interactive elements (desktop): 0 0 0 2px rgba(31,27,20, 0.4) — Ink with 40% alpha
- Screen reader: every avatar has aria-label with persona name; every chevron has aria-hidden (decorative)
- Reduced motion: typing indicator pulse, streaming animations, view toggle fade respect `prefers-reduced-motion`
- OTP fields: properly labeled with aria-label "Digit 1 of 6", etc., screen reader announces filled state
- Apple/Google buttons: native screen reader support via official patterns
- Disclaimer checkboxes: standard HTML labels, fully accessible

---

## 9. Open production decisions

Resolved during v2:
- ✅ Auth method: Apple + Google + email OTP fallback
- ✅ Provider order: platform-aware (Web=Google first, iOS=Apple first, Android=Google first)
- ✅ Age gate placement: combined with positioning disclaimer
- ✅ Free/Pro gating in F1: 3 free saves, then upgrade prompt
- ✅ F2 trigger threshold: ≥10 user messages in conversation
- ✅ F4 export: download icon present, "coming soon" toast for v1
- ✅ F6 naming: "Reflection history" internally, "Past conversations" UI label

Still open for v1 launch:
1. **Region-aware pricing** for international users (currently € only)
2. **Library offline read-only** — feasibility check in v1 dev cycle, otherwise post-MVP
3. **Smart suggestion algorithm** for "Bring another mind" (v1 = static rules, v2 = context-aware)
4. **Rotating cultural quotes** in Welcome / Upgrade / Success (v1 = Socrates static)
5. **Onboarding theme icons** — pending decision on icon set; v1 ships without icons
6. **Production portraits** — commissioned vs curated public-domain decision
7. **Soft cap notice** for stacked "Bring another mind" calls (3+ in chain): backlog item
8. **Rotating "Today's question" pool**: 30–60 curated entries needed before launch
9. **Persona-specific opening invocations** for Marcus Aurelius, Beauvoir, Freud (Jung, Epictetus, Socrates done)
10. **Locale support**: app currently English-only; Greek translation pending
11. **Block 6 design**: Settings + billing management (I1-I6, H5-H6) — pending
12. **Rituals (G1-G4)**: Phase 3 retention layer — pending
13. **Multi-mind premium (E1-E5)**: Phase 5 premium differentiation — pending
14. ~~**Empty states + errors batch (J1-J5, K1-K2)**: pending~~ → Resolved v4: J1, J2, J3, J5 specced; J4 dropped (no surface to live in); K1/K2 deferred to v2 explicitly (push permission + in-app notification banner not in v1 scope).
15. **Free-tier ordering test**: D3 ordering perception monitoring — track whether 4/6 locked feels too restrictive

---

## 10. Backlog notes (deferred to v2 or post-launch)

Captured during v1/v2 spec sessions:
- Multi-mind features (Council Mode, Compare View) — Phase 5 per PHILOSOPHER.docx
- Rituals library (G1–G4) — Phase 3 retention layer
- Personalized Mind-of-the-day rotation
- Per-persona greeting variants based on user's selected need (comfort/challenge/etc.)
- Context-aware safety message variants (self-harm / harm-to-others / eating disorder)
- Embedded Stripe Payment Element (vs hosted Checkout) for tighter UX
- A/B test on Upgrade headline copy ("The full conversation." vs "Go deeper with every mind.")
- D2 search (D4): defer until persona count >12
- D3 grid card 1-word category microcopy: add when persona count >12
- F2 full insight engine (F2 lite is v1; full cross-conversation pattern detection v2)
- F5 themes dashboard
- F4 PDF export (placeholder icon in v1)
- F1 "By theme" filter activation (currently shown but limited data in v1)
- F6 search functionality (defer until users have 20+ conversations)
- Account linking edge cases beyond verified email match
- Re-acceptance flow when disclaimer version bumps

---

## 11. Auth provider compliance (NEW v2)

### 11.1 Apple Sign In requirements

Per Apple Sign In Human Interface Guidelines (App Store Guideline 4.8):
- **Mandatory** if app offers Google Sign In (or any third-party social login)
- Button styling **must** match official spec (black bg, white text, white logo, 4px radius minimum, 50px tap target)
- Cannot be hidden behind "more options" or de-prioritized
- Must handle "Hide My Email" relay correctly (user gives Apple-generated alias)
- Must respect "Sign in with Apple" branding rules in marketing

### 11.2 Google Sign In requirements

Per Google Identity branding guidelines:
- Official 4-color G logo SVG required (no monochrome variants)
- Roboto font for label (system fallback acceptable)
- White or light background recommended
- Cannot say "Sign in with Google" — official label is "Continue with Google" or "Sign in with Google" (we use the former)

### 11.3 Email OTP compliance

- 6-digit numeric code (not 4 — 4 is too easily brute-forced)
- 10-minute expiry (industry standard)
- Resend cooldown: 30 seconds after first send
- Lockout after 5 wrong attempts: 15-minute cooldown
- Server-side rate limiting: max 5 OTP requests per email per hour

### 11.4 Account linking security

When user signs in with provider B and email matches existing account from provider A:
- **Auto-link** ONLY if both providers report `email_verified: true`
- If incoming provider reports `email_verified: false`, require OTP verification before linking
- Never link based on email string match without verified claim
- Log linking events with provider, timestamp, IP for audit trail

### 11.5 Disclaimer storage requirements

```
disclaimer_acceptances table schema:
  - user_id (foreign key)
  - accepted_at (timestamp, ISO 8601)
  - disclaimer_version (e.g. "v1.0")
  - locale (e.g. "en", "el")
  - confirmed_age_18 (boolean)
  - confirmed_non_therapy (boolean)
  - ip_address (audit)
  - user_agent (audit)
```

When disclaimer copy changes (legal review, safety updates), bump version and prompt existing users for re-acceptance on next session.

---

**End of DESIGN_SYSTEM_v4.**

If a decision in production contradicts this document, update this document first (bump to v5) — never let the implementation drift silently from spec.
