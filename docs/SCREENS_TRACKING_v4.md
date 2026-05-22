# GREAT MINDS — Screens Tracking v4

> **Purpose:** Full screen inventory of the Great Minds product. Each screen marked covered (✅) or pending (⚠️). Covered screens have full spec; pending screens have status notes.
>
> **Total: 56 screens** (A0 added 2026-05-18; D5 folded into D1, D4 deferred v2, F5 deferred v2, J4 dropped, A2/A3 merged, A6/A7 merged).
> **Effective specced count: 43** (Blocks 1–6 + Block 9 covered; A0 pending spec)
> **Pending: 13** (A0 pending spec + Block 7 Rituals 4 screens + Block 8 Multi-mind 5 screens + K1/K2 deferred v2 + D4 deferred v2 + F5 deferred v2)
>
> **Companion documents:**
> - `DESIGN_SYSTEM_v4.md` — visual and component spec
> - `USER_FLOW_v4.md` — how screens connect
> - `IMPLEMENTATION_BACKLOG_v4.md` — non-UI implementation work
>
> **Last updated:** May 2026 (v4).
>
> **Changelog v1 → v2:**
> - Block 3 added: D2 ✅, D3 ✅, D4 deferred v2
> - Block 4 added: A1 ✅, A2/A3 merged ✅, A4 ✅, A5 ✅, A6+A7 merged ✅
> - Block 5 added: F1 ✅, F2 lite ✅, F3 ✅, F4 ✅, F6 ✅, F5 deferred v2
> - Implementation backlog items captured (see Section "Backlog requirements")
>
> **Changelog v2 → v3:**
> - Block 6 added (Account, Billing & Privacy):
>   - I1 Account hub ✅
>   - I2 Notifications ✅
>   - I3 Privacy & data ✅
>   - I4 Help & support ✅
>   - I5 About & legal ✅
>   - I6 Logout sheet ✅ (sheet, not screen)
>   - H5 Subscription management ✅ (5 visual states + 2 spec-only states)
>   - H6 Cancel reason sheet ✅ (sheet, not screen)
> - Backlog additions: Stripe Portal return refresh, cancellation_reasons table, data_requests table, GDPR personal data boundaries
>
> **Changelog v3 → v4:**
> - Block 9 added (App-wide empty/error states):
>   - J1 App-wide server error / 5xx ✅
>   - J2 App-wide offline (non-chat shell) ✅ — was "covered partially via C6c"
>   - J3 Empty saved reflections ✅
>   - J5 Empty conversation history ✅
>   - **J4 Empty insights — DROPPED.** No surface to live in (F2 lite is in-chat, kept insights flow into F1 with insight tag, F3 has its own quiet-week state). Subsumed by J3.
> - **All four Block 9 screens reuse-only.** Zero new components, zero new ornaments.
> - K1 Push permission + K2 In-app notification banner — deferred v2 explicitly. Email-only notifications in v1.
> - C6c spec updated: headline "Waiting for a connection." (was "Waiting on connection."); body drops "internet" — "connection" alone reads cleaner.
> - Component reuse map: 3.26 empty state card extended to J3 + J5; Bronze offline ornament extended from C6c-only to C6c + J2; Sepia concentric circles ornament officially added to inventory (was inline-only in H4b).
> - Anti-patterns: Rust on app-wide server-side errors flagged.
>
> **Changelog v4 → v4.1 (2026-05-18):**
> - A0 Public Landing added as new pending screen (spec incomplete — design proposal pending from founder)
> - D1 build-status note added to full spec section (spec locked; build reprioritized to P0)
> - Screen count: 55 → 56; pending count: 12 → 13
>
> **Changelog v4.1 → v4.2 (2026-05-22):**
> - **A0 / A1 Splash**: Rebuilt in PR4h. Full-bleed dark `chesterfield-hero.jpg` background. Minimal Cormorant italic title overlay (top). Outlined CTA + sign-in link (bottom). Gradient overlays for legibility. Mode-aware routing: CTA passes `?mode=signup`, sign-in link passes `?mode=signin`. Status: ✅ rebuilt.
> - **A2/A3 Sign Up / Sign In**: Mode-aware copy added in PR4e. Auth entry page reads `?mode=` param: signup → "Create your account."; signin → "Welcome back." `AuthForm` wrapped in `<Suspense>` for Next.js `useSearchParams` compatibility. Status: ✅ updated.
> - **D1 Today**: `TodaysTopicCard` (editable textarea, 40×40 Bronze initials circle, day-deterministic placeholder, Reflect → `PersonaPickerSheet`) added in PR4b. `AppHeader` ('Great Minds · Day, Mon DD') added in PR4c. `RitualsCard` (Letter to future self functional Pro-gated, Emerging Patterns locked shell, Weekly Letter locked shell) added in PR3c/PR4c. Status: ✅ updated.
> - **All 4 tab screens (Today / Library / Reflections / Account)**: `AppHeader` component added to all in PR4c. Provides consistent 'Great Minds · Day, Mon DD' header across the tab bar shell.
> - **F1 Reflections**: `SwipeableRow` wrapping each `SavedLineCard` (framer-motion x-drag, Safety color reveal, undo toast, first-row wiggle hint) added in PR4f. ⚠️ To be revised in a future PR (per task brief: PR4l). Status: ✅ updated (revision pending).
> - **F6 Library — Past Conversations view**: `SwipeableRow` wrapping each `ConversationCard` (same swipe-to-delete pattern as F1) added in PR4f. Status: ✅ updated.
> - **New flow — Scheduled letters (PR3c)**: `RitualsCard` on D1 → "Letter to future self" → `RitualScheduleSheet` (BottomSheet, saved-line picker with thumbnails, datetime, note) → `POST /api/v1/scheduled-emails`. View at `/app/scheduled-letters`. No new screen spec needed — covered by existing Rituals + D1 specs.
> - **Companion documents updated**: `DESIGN_SYSTEM_v5_to_v6_ADDENDUM_2026_05_22.md` added. `IMPLEMENTATION_BACKLOG_v10.md`, `PROJECT_STATE_v10.md`, `HANDOFF_BRIEF_v10.md` replace v9 equivalents.

---

## Inventory

### A — Authentication & First-time user

| ID | Screen | Status |
|---|---|---|
| A0 | Public Landing (pre-auth marketing) | ⚠️ pending (spec incomplete) |
| A1 | Splash / loading screen | ✅ covered |
| A2 | Sign up | ✅ merged with A3 — single screen |
| A3 | Sign in | ✅ merged with A2 — single screen |
| A4 | Trouble accessing email (renamed from "Forgot password") | ✅ covered |
| A5 | OTP / Email verification | ✅ covered |
| A6 | Age gate | ✅ merged with A7 — single combined screen |
| A7 | Positioning disclaimer | ✅ merged with A6 — single combined screen |

### B — Onboarding

| ID | Screen | Status |
|---|---|---|
| B1 | Welcome | ✅ covered |
| B2 | What brings you here? | ✅ covered |
| B3 | What do you need most? | ✅ covered |
| B4 | Best matches | ✅ covered |
| B5 | Persona detail (default/unlocked) | ✅ covered |
| B6 | Persona detail (locked / Pro) | ✅ covered |

### C — Chat experience

| ID | Screen | Status |
|---|---|---|
| C1 | Chat — live conversation | ✅ covered |
| C2 | Chat — initial loading | ✅ covered |
| C3 | Chat — save line confirmation | ✅ covered |
| C4 | Chat — failed message + retry | ✅ covered |
| C5 | Chat — daily limit reached | ✅ covered |
| C6 | Chat — weak connection / offline (3 sub-states) | ✅ covered |
| C7 | Chat — safety mode activation | ✅ covered |
| C8 | Chat — first persona greeting | ✅ covered |
| C9 | Bring another mind flow | ✅ covered |

### D — Discovery & Library

| ID | Screen | Status |
|---|---|---|
| D1 | Home / Today (returning + empty) | ✅ covered |
| D2 | Explore Minds — Carousel/list view | ✅ covered |
| D3 | Explore Minds — Grid view | ✅ covered |
| D4 | Search / filter minds | ⏸ deferred v2 (when persona count >12) |
| ~~D5~~ | ~~Daily check-in prompt~~ | folded into D1 |

### E — Multi-mind features (post-MVP)

| ID | Screen | Status |
|---|---|---|
| E1 | Dual View setup | ⚠️ pending (Phase 5) |
| E2 | Dual View results | ⚠️ pending (Phase 5) |
| E3 | Council Mode setup | ⚠️ pending (Phase 5) |
| E4 | Council Mode results | ⚠️ pending (Phase 5) |
| E5 | Compare Modes | ⚠️ pending (Phase 5) |

### F — Reflection & Memory

| ID | Screen | Status |
|---|---|---|
| F1 | Saved reflections / lines archive | ✅ covered |
| F2 | Suggested insights (lite, in-chat) | ✅ covered (lite version v1) |
| F3 | Weekly letter inbox | ✅ covered |
| F4 | Weekly letter detail / read view | ✅ covered |
| F5 | Recurring themes dashboard | ⏸ deferred v2 (volume-dependent feature) |
| F6 | Reflection history (UI: "Past conversations") | ✅ covered |

### G — Rituals (Phase 3, post-MVP)

| ID | Screen | Status |
|---|---|---|
| G1 | Rituals library | ⚠️ pending |
| G2 | Ritual detail | ⚠️ pending |
| G3 | Ritual day-by-day flow | ⚠️ pending |
| G4 | Ritual completion | ⚠️ pending |

### H — Subscription & Billing

| ID | Screen | Status |
|---|---|---|
| H1 | Upgrade / pricing screen | ✅ covered |
| H2 | Checkout loading bridge | ✅ covered |
| H3 | Payment success | ✅ covered |
| H4 | Payment failed | ✅ covered |
| H4b | Payment canceled (gentle variant) | ✅ covered |
| H5 | Subscription management | ✅ covered |
| H6 | Cancel subscription flow | ✅ covered (bottom sheet) |

### I — Account & Settings

| ID | Screen | Status |
|---|---|---|
| I1 | Profile / account (renamed: Account hub) | ✅ covered |
| I2 | Notification preferences | ✅ covered |
| I3 | Privacy & data | ✅ covered |
| I4 | Help / support | ✅ covered |
| I5 | About / legal | ✅ covered |
| I6 | Logout confirmation | ✅ covered (bottom sheet) |

### J — Empty states & Errors

| ID | Screen | Status |
|---|---|---|
| J1 | App-wide error (5xx server) | ✅ covered (v4) |
| J2 | App-wide offline (non-chat shell) | ✅ covered (v4) — replaces "covered partially via C6c" |
| J3 | Empty saved reflections | ✅ covered (v4) |
| ~~J4~~ | ~~Empty insights~~ | **DROPPED v4** — subsumed by J3 (no surface to live in) |
| J5 | Empty conversation history | ✅ covered (v4) |

### K — Notifications

| ID | Screen | Status |
|---|---|---|
| K1 | Push notification permission request | ⏸ deferred v2 (email-only in v1) |
| K2 | In-app notification banner | ⏸ deferred v2 (email-only in v1) |

---

## Covered screens — full specs

### A0 — Public Landing (pre-auth marketing)

**Status:** ⚠️ pending (spec incomplete)

Design proposal forthcoming from founder via separate Claude session. Will define hero direction, value prop copy, CTA structure, responsive behavior, and integration with the `/` route. Awaiting founder input before any implementation work begins.

---

### A1 — Splash / loading

Brief auth check screen.

**Structure:**
- Status bar
- Centered (flex column, justify center):
  - "Great Minds" wordmark (Cormorant Garamond 38px, weight 300, Ink, centered)
  - Bronze divider (1px line + 9×9 lozenge + 1px line, total ~80px wide)
  - 32×32 spinner (Edge ring 0.8px stroke + Ink rotating arc 1.2px, 1.4s rotation)

**Duration:** ~500ms. Routes to A2/A3 if no session, to D1 Home if session valid.

---

### A2 / A3 — Sign up + Sign in (merged single screen)

Provider auto-detects new vs returning user. No "Don't have account?" toggle needed in passwordless world.

**Structure:**
1. Status bar
2. Hero (centered, padding 32px 28px):
   - Title: "Begin your reflection." (Cormorant 28, weight 400)
   - Supporting: "Sign up or sign in to continue." (Lora 13, Charcoal)
3. Provider buttons stack (gap 10px):
   - **Apple Sign In** (compliance-locked styling, see DESIGN_SYSTEM 2.6)
   - **Google Sign In** (compliance-locked styling, see DESIGN_SYSTEM 2.7)
   - Divider with "or" label (Lora 11, Sepia, 0.18em uppercase)
   - Email input (single-line textfield, see DESIGN_SYSTEM 3.12)
   - "Continue with email" Ink primary button
4. Legal microcopy footer (centered, padding 22px 28px):
   - "By continuing, you agree to our [Terms] and [Privacy Policy]." (Lora 11, Sepia, line-height 1.6)
   - Links underlined, open external browser

**Provider order (platform-aware):**
- Web/PWA: Google first, Apple second, email third
- iOS native: Apple first, Google second, email third
- Android: Google first, Apple optional, email third

**Behavior:**
- Apple/Google → OAuth flow → returns with verified email → auto-link or new account → A6+A7 disclaimer (first time) or D1 Home (returning)
- Email + Continue → A5 OTP screen with email pre-filled

---

### A4 — Trouble accessing email (renamed from "Forgot password")

Recovery screen for users who can't access their account email. Reframed for passwordless context.

**Structure:**
1. Status bar + back chevron
2. Hero (centered, padding 24px 28px):
   - Title: "Trouble accessing your email?" (Cormorant 26, weight 400)
   - Supporting: "No password to reset — Great Minds uses passwordless sign-in. If you can't access the email tied to your account, here's what you can do." (Lora 13, Charcoal, 1.65 line-height)
3. Two option cards (Paper bg, Edge border, 6px radius):
   - **Option 1**: "Try a different sign-in method" / "If you also signed up with Apple or Google, use that."
   - **Option 2**: "Contact support" / "We'll help you regain access through identity verification."
4. Primary CTA: "Contact support" (Ink full-width)

**Reachable from:** Small "Trouble accessing email?" link on A5 OTP screen.

**Contact support behavior:** Opens email client via `mailto:` with structured pre-filled body:
```
Subject: Account access — [user_email_attempted]

Email used: [email]
Provider attempted: [Apple / Google / Email OTP]
Device: [User Agent string]
Browser: [Browser + version]
Timestamp: [ISO timestamp]
Error code: [if available]

[Cursor here for user message]
```

---

### A5 — OTP / Email verification

6-digit code entry screen.

**Structure:**
1. Status bar + back chevron
2. Hero (centered, padding 24px 28px):
   - Title: "Check your email." (Cormorant 26, weight 400)
   - Supporting: "We sent a 6-digit code to [email]" — email rendered in Ink weight 500
3. OTP fields row (6 cells, see DESIGN_SYSTEM 3.13):
   - Auto-advance, paste-friendly, iOS SMS autofill compatible
4. Expiry countdown (centered, Lora 12 Sepia): "The code expires in 9:42"
5. Resend link at bottom (centered, padding 28px): "Didn't get the code? Resend" — link in Ink, underlined

**State machine (implementation requirements):**
- Wrong code → Inline error below fields ("Code didn't match. Try again.")
- Expired code → Modal: "Code expired" + "Send new code" CTA
- Resend cooldown → Resend link disabled with countdown ("Resend in 24s")
- Too many attempts (5 wrong) → Lockout 15min + redirect to A4
- Use different email → Back button to A2/A3 with field pre-populated
- Backend rate limiting → 429 response → friendly copy ("Too many requests. Please try again in an hour.")

**Behavior:** Successful 6-digit entry → A6+A7 disclaimer (first time) or D1 Home (returning).

---

### A6 + A7 — Combined age + positioning disclaimer

Single screen, two required confirmations.

**Structure:**
1. Status bar
2. Top ornament: small Bronze divider (1px line + 9×9 lozenge + 1px line, 32px each side)
3. Hero (centered, padding 36px 28px):
   - Title: "Before we begin." (Cormorant 26, weight 400)
   - Supporting: "Two things to confirm." (Lora 13, Charcoal)
4. Two stacked checkbox cards (see DESIGN_SYSTEM 3.14):
   - **Confirmation 1**: "I am 18 years or older." (Lora 14, weight 500)
   - **Confirmation 2**: "I understand Great Minds is for reflection, not therapy, diagnosis, crisis support, or medical treatment. If I am in immediate danger or crisis, I should contact local emergency services or a qualified professional." (Lora 14, weight 400, multi-line)
5. CTA: "Continue" (disabled state until BOTH boxes checked)

**Disclaimer copy is versioned (v1.0).** Stored in DB as `disclaimer_version` per user. When copy changes, version bumps and existing users re-prompted on next session.

**Required DB schema:**
```
disclaimer_acceptances:
  - user_id, accepted_at, disclaimer_version, locale,
  - confirmed_age_18, confirmed_non_therapy,
  - ip_address, user_agent
```

**Behavior after both checked + Continue:** First-time flow → B1 Welcome → B2 onboarding. Returning users skip this entirely (only shown again if disclaimer_version bumped).

---

### B1 — Welcome

**Layout:** Variant B (full-bleed portrait) + Option 2 (Vellum tray below portrait with caption + buttons).

**Structure (top → bottom):**
1. Status bar
2. Portrait area (~65% of screen height): full-bleed illustrated persona portrait with hero text overlay
   - Title: "Great Minds" (Cormorant 36–40, weight 300, Vellum, centered)
   - Subtitle: "Reflect with the world's / greatest thinkers." (Cormorant 17, weight 400, Vellum, centered, 2 lines)
   - Bronze divider (1px line + 9×9 lozenge) below subtitle
3. Vellum tray section
   - Eyebrow: "Mind of the day" (Lora 11, Sepia, 0.18em, uppercase)
   - Persona name: "Simone de Beauvoir" (Cormorant 22–26, weight 500, Ink)
   - Persona tagline: "Freedom, ambiguity, and becoming." (Lora 13–14, Charcoal)
4. CTA stack
   - Primary: "Begin" (Ink full-width)
   - Secondary: "Explore Minds" (outlined full-width)

**Mind of the day logic:** Deterministic daily rotation, same for all users. Curated set of all 6 personas rotating in order.

**Behavior:** "Begin" → B2 onboarding flow. "Explore Minds" → D2 carousel view.

**Production constraint:** All 6 portraits must follow rules (subject upper/middle third, controllable bottom area, consistent crop).

---

### B2 — What brings you here?

**Two states:**
- **2a:** Empty (no chips selected, no Other text) — Continue disabled
- **2b:** Active (≥1 chip OR Other text) — Continue enabled

**Structure:**
1. Status bar
2. Back button row (left ‹ chevron only)
3. Title block (centered): "What brings you here?" (Cormorant 30, weight 400) + "Choose one or more themes that feel most relevant." (Lora 14, Charcoal)
4. 2-col theme grid, 8 themes:
   - Separation / Anxiety / Fear / Grief / Acceptance / Work / Relationships / Purpose
   - Each chip: theme chip selectable (left-aligned, no icons in v1)
5. "Other" field below grid:
   - Eyebrow: "Other" (Lora 12, Sepia)
   - Multiline textarea, 64–96px min-height
   - Placeholder: "What's on your mind lately…" (Sepia)
6. Continue button (Ink full-width, disabled state if no input)
7. Helper text below: "We'll suggest the minds best suited / to this conversation." (Lora 12, Sepia, centered, 2 lines)

**Selected chip pattern:** Linen Deep #DDD0B5 bg + 1px Ink border + Lora weight 500. Default: Paper bg + 0.5px Edge border + Lora weight 400.

**Multi-select:** user can select multiple chips. State persists until Back/Continue.

---

### B3 — What do you need most?

Single-select between 4 options after themes selected.

**Structure:**
1. Status bar
2. Back button
3. Title centered: "What do you need most?" (Cormorant 30, weight 400) + "Choose what feels closest right now." (Lora 14, Charcoal)
4. Vertical list of 4 options, single-select:
   - Comfort — to feel steadier and less alone
   - Challenge — to face what you may be avoiding
   - Interpretation — to understand the pattern beneath it
   - Practical steadiness — to regain control of the next step

Each option: full-width button, left-aligned, padding 16px 18px, 4px radius.
- Title: Cormorant 19, weight 500, Ink
- Description: Lora 13, Charcoal (default) → Lora 13, Ink (selected)

**Selected state:** Linen Deep #DDD0B5 bg + 1px Ink border + title weight stays 500.

**Continue:** Ink full-width primary, enabled only when one option selected.

---

### B4 — Best matches

**Structure:**
1. Status bar
2. Back button
3. Title centered: "Your best matches" (Cormorant 26, weight 400) + "Minds selected for your current moment." (Lora 13, Charcoal)
4. Vertical list of 3 ranked persona list cards (see DESIGN_SYSTEM 3.1):
   - Card 1: Epictetus (rank 1, Stoic wisdom on control)
   - Card 2: Carl Jung (rank 2, Depth, dreams, and meaning)
   - Card 3: Simone de Beauvoir (rank 3, Freedom and becoming)

Each card: ranked number badge (Ink, 22×22, 4px radius) + 56×56 avatar + name + tagline + "Why he/she may help" eyebrow + 2-line copy + 2 descriptive tags + middle-right chevron.

**Pronoun handling:** "Why he may help" / "Why she may help" — match persona gender.

**Tap target:** entire card, navigates to B5/B6 persona detail.

**Bottom CTA:** "See all minds" (outlined secondary button, full-width). Navigates to D2/D3 Explore Minds.

---

### B5 — Persona detail (unlocked / default)

**Structure:**
1. Status bar
2. Header row:
   - Back chevron (left)
   - Persona name (Cormorant 18, weight 500, centered)
   - Spacer (right, for visual balance)
3. Tagline below header (Lora 12, Charcoal, centered)
4. Portrait card: 4:3 aspect ratio, Linen bg, Edge border, 6px radius, contains illustrated portrait
5. Content blocks (padding 22px 24px):
   - Eyebrow "About" (Lora 10, Sepia, 0.18em uppercase)
   - About copy (Lora 13, Ink, 1.65 line-height, **2 sentences max — first = who, second = central idea**)
   - Eyebrow "Best for"
   - 4 descriptive tags (theme chip descriptive variant)
   - Eyebrow "Why this mind may help"
   - Body copy (Lora 13, Ink, 1.65 line-height, persona-specific value proposition)
6. CTA: "Start conversation" (Ink full-width)

**About copy rule:** Maximum 2 sentences. Biographical (app voice, not persona voice).

---

### B6 — Persona detail (Pro-locked variant)

Identical to B5 except:
- Pro pill chip on portrait top-right
- CTA changes to: "Unlock with Pro" (Ink full-width, with padlock icon left of label)
- Supporting microcopy below CTA: "Continue with this mind and the full library." (Lora 12, Sepia, centered)

**No blur. No modal overlay. No aggressive paywall.** Page remains fully readable so user understands what's locked.

**Behavior:** Tap "Unlock with Pro" → H1 Upgrade screen.

---

### C1 — Chat live conversation

**Structure:**
1. Status bar
2. Header (Vellum bg, 0.5px Edge bottom):
   - Back chevron
   - 36×36 persona avatar (Linen square, 4px radius, initials fallback)
   - Persona name (Cormorant 18, weight 500) + tagline (Lora 11, Charcoal)
   - More menu (⋯, Cormorant 22, Charcoal)
3. Chat scroll area (Paper bg, padding 20px 16px):
   - User bubbles right-aligned (Ink + Vellum text)
   - Persona bubbles left-aligned with 24×24 avatar (Linen + Ink text)
   - Timestamps Lora 10–11 Sepia
   - Quick actions row below persona reply (Ask harder / Bring another mind / Save line)
4. Input bar (Vellum bg, 0.5px Edge top): textarea + 40×40 send button

**Persona greetings (opening_invocation, locked):**
- Carl Jung: "Tell me what keeps returning in your life."
- Epictetus: "Tell me what feels outside your control."
- Socrates: "Let us begin with what you think you know."
- Marcus Aurelius: TBD
- Simone de Beauvoir: TBD
- Sigmund Freud: TBD

---

### C2 — Chat initial loading

Same chat shell as C1 with these states:
- Header fully visible (persona portrait, name, tagline)
- Chat scroll area shows ONLY: typing indicator (3 dots in Linen bubble) + 24×24 persona avatar at left, bottom-aligned
- Input bar visible but send button disabled

**Duration:** 1–2 seconds (LLM streaming initiation). May not visibly render if connection fast.

**Transition to C8:** Typing dots fade out, greeting text streams in character-by-character ~2 seconds.

---

### C3 — Save line confirmation

State of C1 after user taps "Save line" on a persona reply:
1. **Bookmark indicator** appears top-right corner of saved bubble (Bronze fill bookmark SVG, 12×14)
2. **Toast** appears bottom-centered above input bar for 2 seconds: "Saved to your reflections" (Ink bg, Vellum text, Lora 12, with Bronze bookmark icon left)
3. **Quick action chip** "Save line" → "Saved" (selected state: Linen Deep + 1px Ink border + weight 500)

All three layers concurrent. Bookmark persists, toast fades, chip stays in saved state.

---

### C4 — Failed message + retry

User bubble fails to send (network/API error):
- Bubble appearance: Ink bg, Vellum text, but **opacity 0.85 + bg color shifts to Charcoal** (NOT flat 0.55 — must remain readable)
- Below bubble, right-aligned: small error indicator
  - Rust circle with `!` icon (12×12, 0.8 stroke)
  - "Couldn't send" (Lora 11, Rust)
  - · separator (Sepia)
  - "Tap to retry" (Lora 11, Ink, underlined, clickable)

No modal. No banner. Inline only.

---

### C5 — Daily limit reached (free user)

Free user sends message that triggers daily limit:
- All previous messages remain visible
- Input bar **replaced** with upgrade card:
  - Heading: "You've reached today's free reflections." (Cormorant 16–17, weight 500)
  - Supporting copy: "Your free reflections renew tomorrow. Upgrade to Pro to continue now." (Lora 12, Charcoal)
  - CTA row: "Continue with Pro" (Ink, flex 1) + "Later" (outlined, fixed width)

No countdown. No "limited time" pressure.

---

### C6 — Weak connection / offline (3 sub-states)

**C6a — Slow connection (still working):**
- Slim banner: F2E5C8 bg, 0.5px Edge bottom, 9px 16px padding
- Wifi-with-dot icon (Sepia 1px stroke)
- Copy: "Slow connection. Responses may take longer." (Lora 12, Charcoal)
- Banner auto-dismisses when connection improves

**C6b — Fully offline (in active chat):**
- Stronger banner: F0E0D5 bg (Rust-tinted), 0.5px C9A593 bottom border
- Wifi-crossed icon (Rust stroke)
- Copy: "No connection. Your conversation will resume when you're back online." (Lora 12, Rust, weight 500)
- User can write; messages queue locally
- Queued message visual: Charcoal #5A5246 bg + Vellum text, opacity 0.85
- Below queued bubble: clock icon (Sepia) + "Waiting to send" (Lora 11, Sepia)
- Send button disabled

**C6c — Cold start offline:**
- Centered Bronze offline ornament (signal-blocked metaphor — circle + crossed line + arc, ~56×56, 1.2px Bronze stroke). Same ornament as J2.
- Headline: "Waiting for a connection." (Cormorant 26, weight 400) — **updated v4** from "Waiting on connection."
- Copy: "Great Minds needs a connection to start new conversations. Your saved reflections remain available below." (Lora 13, Charcoal, 1.6 line-height, centered) — **updated v4**: dropped "internet" qualifier per offline-family copy lock (DESIGN_SYSTEM §4.10).
- "Try again" (Ink button, centered, padding 12px 28px, **min-width 140px, white-space nowrap** — updated v4 to prevent label wrapping)
- Below: card "Available offline" with link to saved reflections (only if technically feasible in v1 — see DESIGN_SYSTEM §9 open production decisions)

---

### C7 — Safety mode activation

Triggered by safety classifier on user message.

**State:**
- Header REMAINS unchanged (persona still shown)
- User's triggering message appears normally
- Persona theatrics suppressed: persona does NOT respond
- Instead, **app-voice safety bubble** appears with attribution:
  - Eyebrow: "Great Minds" (Lora 9, Sepia, 0.18em, uppercase)
  - Avatar: 24×24 circle, Vellum bg, Edge border, Bronze diamond/lozenge centered
  - Bubble: Linen bg, Ink text, 14px 16px padding, 8px radius
  - Content (4 paragraphs):

```
Some of what you've shared sounds heavy. I want to make sure you're safe right now.

[BOLDED — weight 500] If you may be in immediate danger, please contact local emergency services or a crisis support line now.

If you can, reach out to a trusted person near you or a qualified mental health professional.

Great Minds can offer reflection, but it cannot provide crisis support, diagnosis, or medical treatment.
```

- Below safety bubble: re-entry card (Vellum bg, 1px Bronze left border, italic Charcoal: "You can continue when you're ready. Take your time.")
- Quick actions row: SUPPRESSED
- Input bar placeholder shifts to: "Write when you're ready…"

**Re-entry:** User writes next message → safety classifier re-evaluates.

**Backend:** Logs to `safety_events` table.

---

### C8 — First persona greeting

After C2 loading, persona's first message appears.

**Structure:**
- Day marker divider above first message: "Today · 9:41" (Lora 10 Sepia 0.18em uppercase, between two 0.5px Edge lines, 24px vertical margin)
- First persona message bubble with avatar
- Timestamp 9:41 below message
- NO quick actions row on first greeting
- Input bar fully active

**Greeting content:** persona-specific opening_invocation.

---

### C9 — Bring another mind flow (2 sub-states)

**C9a — Bottom sheet picker:**
- Chat behind dimmed to opacity 0.5
- Bottom sheet slides up from bottom
- Drag handle at top
- Title: "Bring another mind" (Cormorant 22, weight 400) + "Choose who should look at this from another angle." (Lora 13, Charcoal)
- "Suggested for this moment" eyebrow — top 2 personas
- "Other minds" eyebrow — remaining personas
- Each row: 40×40 avatar + name + tagline + middle-right chevron

**Pro gating:** Free user → tap "Bring another mind" → goes to H1 Upgrade screen, not picker.

**Suggested logic v1:** Static rules based on onboarding themes + current persona. v2 = context-aware.

**C9b — Inline second opinion:**
- Chat continues with header still showing original persona (Carl Jung)
- After user's message + Jung's response, the SECOND persona's response inserts inline:
  - Eyebrow above bubble: "Epictetus · brought in" (Lora 9, Sepia, 0.18em, uppercase)
  - Standard persona bubble with E avatar + Linen bg + Ink text
  - Timestamp below
- Quick actions row appears below brought-in response (apply to that response specifically)
- Below quick actions, divider: "Continuing with Carl Jung"
- Next user message resumes Jung's thread

**Soft cap (backlog, not v1):** After 3+ chained brought-in responses, soft notice.

---

### D1 — Home / Today (2 states)

**D1a — Returning user with content:**
1. Status bar
2. Header: date eyebrow + greeting "Good morning."
3. **Today's question card** (hero, Paper bg, Edge border, 6px radius)
4. **Continue last conversation card** (avatar + persona name + last message snippet)
5. **Recent insight card** (italicized quote + attribution)
6. **Themes this week** (3 theme chips + "View all" link)
7. **Weekly letter card** (conditional — only if unread)
8. **"Ask another mind"** outlined button (centered)
9. Bottom tab bar (Today active)

**D1b — First-day empty state:**
- Same status bar + header (greeting changes to "Welcome.")
- Same Today's question card
- **Empty state card** (dashed border + Bronze ornament + 3-item list)
- "Start your first conversation" (Ink button)
- Bottom tab bar

**Build status note (2026-05-18):** Spec locked since v4. Build was deferred under "Block D — Not yet planned"; reprioritized to P0 on 2026-05-18 after structural gap discovery (without D1, bottom tab bar surface is unreachable post-sign-in, making Reflections/Library/Account tabs invisible and C3 save-line feature effectively ROI-blind). See IMPLEMENTATION_BACKLOG_v9.md §"2026-05-18 launch priority shift".

---

### D2 — Explore Minds, Carousel/list view

**Structure:**
1. Status bar
2. Header: back chevron + "Explore minds" title (centered, Cormorant 19 weight 500)
3. Sub-header: "6 minds" eyebrow + view toggle (list active / grid dimmed)
4. Vertical scrollable list of persona cards (D2 list variant, see DESIGN_SYSTEM 3.2):
   - Free first: Marcus Aurelius, Socrates
   - Pro after: Carl Jung, Simone de Beauvoir, Epictetus, Sigmund Freud
   - Pro pill chip on Pro persona portraits
5. End-of-list: Bronze divider + "More minds will join the library." (Lora 11, Sepia, centered)

**No bottom tab bar** (immersive browse). Back chevron returns to previous context.

**Tap behavior:** Tap any card → B5 (free, unlocked) or B6 (Pro, locked).

**View toggle:** Tap grid icon → soft fade 200ms → D3 grid view. Preference stored localStorage.

---

### D3 — Explore Minds, Grid view

**Structure:**
1. Status bar
2. Header: identical to D2
3. Sub-header: "6 minds" + view toggle (grid active / list dimmed)
4. 2-column grid (12px gap, 18px outer padding):
   - Each cell: persona card grid variant (see DESIGN_SYSTEM 3.3)
   - Same ordering as D2 (free first, Pro after)
   - Pro pill chip smaller scale
5. End-of-list: Bronze divider + "More minds will join the library."

**No bottom tab bar.**

**Long names** (Simone de Beauvoir, Sigmund Freud) wrap to 2 lines naturally. No ellipsis.

**View toggle:** Tap list icon → soft fade 200ms → D2 list view.

---

### F1 — Saved reflections

Lives in Reflections tab (default sub-view).

**Structure:**
1. Status bar
2. Header: eyebrow "Reflections" + title "Your saved lines." (Cormorant 26, weight 400)
3. Filter pills (horizontal scroll):
   - "All" (active default)
   - "By mind" (filter by persona)
   - "By theme" (v1: shown but limited functionality without insight extraction; v2 fully functional)
4. Date-grouped chronological list:
   - Date grouper: "This week" / "Earlier" / "Last month"
   - Each saved card (Paper bg, Edge border, 6px radius, 16px 18px padding):
     - Italicized quote (Cormorant 17, weight 400, italic)
     - Source row: 18×18 persona avatar + name + relative date (Lora 11, Sepia)
5. Bottom tab bar (Reflections active)

**Tap on saved card:** Returns to source conversation in C1, with the saved message highlighted/focused.

**Free/Pro gating:**
- Free users: up to 3 saved reflections, then upgrade prompt on 4th save attempt
- Pro users: unlimited saves
- F1 list visible to free users (so they see what they saved + small "Upgrade to keep saving lines that matter" card at bottom)

---

### F2 — Suggested insights (lite, in-chat)

**Not a separate screen — inline component in chat (C1).**

**Trigger:** After conversation reaches ≥10 user messages, single suggested insight surfaces inline at end of chat.

**Component:** Suggested insight card (see DESIGN_SYSTEM 3.25)
- Vellum bg, 1px Bronze border, 6px radius
- Eyebrow: "Great Minds · Insight"
- Bronze diamond marker + insight text in Cormorant italic
- Two actions: "Keep" (Ink primary) / "Dismiss" (outlined)

**Quality guardrails (implementation requirement):** See DESIGN_SYSTEM 4.6.

**Behavior:**
- Keep → flows to F1 with insight tag indicator
- Dismiss → permanent dismiss, never resurfaces for that conversation

**Free/Pro gating:** Free users see 1 preview across product lifetime, then locked. Pro users see suggested insights on every qualifying conversation.

---

### F3 — Weekly letter inbox

Lives in Reflections tab (sub-view, accessible from F1).

**Structure:**
1. Status bar
2. Header: eyebrow "Reflections" + title "Weekly letters." (Cormorant 26, weight 400)
3. Chronological list of letter cards (3 visual states, see DESIGN_SYSTEM 3.29):
   - **Unread** (Linen bg + Bronze dot indicator)
   - **Read** (Paper bg + Edge border)
   - **Quiet week** (dashed border + italic "A quiet week.")
4. Bottom tab bar (Reflections active)

**Tap unread/read letter** → F4 detail view.

**Generation:** Async batch every Sunday. If insufficient material, render quiet week state — do NOT generate weak content.

**Pro-only feature.** Free users see upgrade prompt instead.

---

### F4 — Weekly letter detail

Long-form premium read view of a single weekly letter.

**Structure:**
1. Status bar
2. Header: back chevron + "Weekly letter" eyebrow (Lora 11, Sepia, 0.18em uppercase) + download/export icon (top-right, v1 placeholder, "Coming soon" toast)
3. Letter body (padding 32px 28px):
   - Date eyebrow centered
   - Title (Cormorant 28, weight 400, centered)
   - Bronze divider
   - Body paragraphs (Lora 14, line-height 1.75)
   - "A sentence worth keeping" pull-quote (see DESIGN_SYSTEM 3.30)
   - Forward gesture paragraph
4. Suggested next mind card (Vellum bg, Edge border, 6px radius):
   - Eyebrow: "Suggested next mind"
   - 32×32 avatar + persona name + tagline

**Letter copy structure** (see DESIGN_SYSTEM 4.7):
1. Opening observation (1-2 paragraphs)
2. Specific references (1 paragraph)
3. A sentence worth keeping (pull-quote)
4. Forward gesture (1-2 sentences)
5. Suggested next mind (optional)

Length: 150-250 words.

**PDF export:** v1 = placeholder icon with "coming soon" toast. v2 = actual PDF generation.

---

### F6 — Reflection history (UI: "Past conversations")

Lives in Library tab. Internal product strategy name: "Reflection history". UI label: "Past conversations" for clarity.

**Structure:**
1. Status bar
2. Header: eyebrow "Library" + title "Past conversations." (Cormorant 26, weight 400)
3. Date-grouped chronological list of conversation cards (Paper bg, Edge border, 6px radius):
   - Date grouper: "This week" / "Earlier" / etc.
   - Each card row:
     - 36×36 persona avatar
     - Persona name (Cormorant 16, weight 500)
     - Meta line: "Yesterday · 9:48 PM · 14 messages" (Lora 11, Sepia)
     - Last message snippet preview (Lora 12, Charcoal, italic, 1-line)
     - Right-side chevron
4. Bottom tab bar (Library active)

**Tap card:** Returns to that conversation in C1, scrolled to last message.

**Available to both Free + Pro users** (basic infrastructure, not Pro-gated).

**No search in v1** (defer until 20+ conversations average).

---

### H1 — Upgrade screen

**Structure:**
1. Status bar
2. Close X (top-right)
3. Hero (centered, padding 28px):
   - Eyebrow: "Great Minds Pro" (Lora 11, Sepia, 0.18em uppercase)
   - Headline: "The full conversation." (Cormorant 30, weight 400)
   - Supporting line: "All minds, all reflections, all the time you need." (Lora 13, Charcoal)
4. Bronze divider
5. Cultural quote (Socrates, italic Cormorant + attribution)
6. **Upgrade card** (Paper bg, Edge border, 8px radius):
   - Toggle: Monthly | Annual (Annual default with "−33%" Bronze badge)
   - Price: "€9.99/month" + "€119.99 billed annually" subline
   - Divider
   - 5 features list with Bronze checkmarks
7. CTAs: "Continue with Pro" (Ink primary) + "Maybe later" (text-link)
8. Guarantee microcopy: "14-day money-back guarantee" + shield icon

**Pricing model:** Monthly + Annual only. Annual selected by default.
**Currency:** € for v1.
**No trial.** 14-day money-back guarantee instead.

---

### H2 — Checkout loading bridge

Brief 1–2 second screen while creating Stripe Checkout session.

**Structure:**
- Centered: 56×56 spinner + "Preparing your checkout" + "You'll continue securely with Stripe."

---

### H3 — Payment success

**Structure:**
1. Centered hero block:
   - Bronze laurel ornament (50×50, concentric circles + checkmark)
   - Eyebrow: "Welcome to Pro"
   - Headline: "The full library is open." (Cormorant 30)
   - Supporting copy: "A confirmation has been sent to your email."
2. Bronze divider
3. Cultural quote (same Socrates as H1)
4. CTA: "Begin where you left off" (Ink full-width)

**Behavior:** CTA returns to original context.

---

### H4 — Payment failed

**Structure:**
1. Close X top-right
2. Centered: Rust circle with `!` indicator
3. Headline: "The payment didn't go through."
4. Critical line: "**No charge was made.** You can try again, or come back when you're ready."
5. Common reasons card (Paper bg)
6. CTAs: "Try again" (Ink) + "Go back" (text)
7. Support link: "If the issue persists, contact support."

---

### H4b — Payment canceled (gentle variant)

**Structure:**
1. Close X
2. Centered: Sepia concentric circles ornament (pause metaphor, NOT alarm)
3. Headline: "No rush."
4. Supporting copy: "You can come back to Pro anytime. No charge was made."
5. CTAs: "Return to Great Minds" (Ink primary) + "Try again" (text secondary)

**No quote, no common reasons card, no support link.** Reverse CTA priority vs H4.

**Routing logic:**
- `?payment_status=succeeded` → H3
- `?payment_status=failed` → H4
- `?payment_status=canceled` → H4b

---

### H5 — Subscription management

Subscription control screen. Stripe is billing source of truth; H5 displays effective app entitlement, not raw Stripe status.

**Pattern:**
- Sub-screen, back chevron top-left
- No bottom tab bar
- Functional title: "Subscription" (no period)
- 5 visual states + 2 spec-only states (Loading, Error)

**Structure (common shell, all states):**
1. Status bar
2. Back chevron (top-left, 11×18, 1.5px Ink stroke)
3. Title: "Subscription" (Cormorant 28, weight 400, padding 22px 24px 32px)
4. Status card (3.33) — content varies per state
5. Primary CTA — varies per state
6. Optional secondary action (Pro active only)
7. Optional microcopy ("Billing is managed securely through Stripe.") — paid states only

**State 1 — Free:**
- Status card: eyebrow "Your plan", value "Free", meta "You're on the Free plan."
- CTA: "Upgrade to Pro" — Ink solid primary → routes to H1
- No microcopy

**State 2 — Pro active:**
- Status card: eyebrow "Your plan", value "Pro", meta "Renews on June 14, 2026."
- Primary CTA: "Manage Pro subscription" — outlined Ink (2.2 secondary) → opens Stripe Customer Portal
- Secondary action: "Cancel Pro" — text-link tertiary (2.9), centered below microcopy → opens H6 cancel reason sheet
- Microcopy: "Billing is managed securely through Stripe." (Lora 12, Sepia, centered, 18px top padding)

**Cancel Pro production gate:** Visible only when H6 is implemented and routable AND state is Pro active. Hidden in canceling, past due, free, canceled states.

**State 3 — Past due:**
- Status card: eyebrow "Your plan", value layout = "Pro" + inline Rust dot + "Payment issue" (Lora 13, Rust #A05A3C, weight 500)
- Meta: "We couldn't process your latest payment. Update your payment method to keep Pro active."
- CTA: "Update payment method" — Ink solid primary → opens Stripe Portal
- Microcopy: "Billing is managed securely through Stripe."
- Past-due users keep Pro access until Stripe/entitlement marks access inactive. H5 shows the issue but does not unilaterally degrade access.

**State 4 — Canceling at period end:**
- Status card: eyebrow "Your plan", value "Pro", meta "Active until June 14, 2026."
- CTA: "Manage Pro subscription" — outlined Ink → Stripe Portal
- Microcopy: "Billing is managed securely through Stripe."
- No countdown. No in-app reactivate button. Resume happens via Stripe Portal.

**State 5 — Canceled / no access:**
- Status card: eyebrow "Your plan", value "Free", meta "Your Pro subscription has ended."
- CTA: "Upgrade to Pro" — Ink solid → H1
- No microcopy

**State 6 — Loading (spec only, no mock):**
- Render shell (back chevron, title)
- Status card content replaced with subtle skeleton (Linen rects on Paper bg, gentle 1.5s shimmer)
- All CTAs and microcopy hidden until state resolves
- No flicker between loading and resolved state

**State 7 — Error (spec only, no mock):**
- Render shell
- Status card replaced with single line: "We couldn't load your subscription."
- Primary CTA: "Try again" (Ink solid)
- No secondary action in v1, no microcopy

**State mapping (Stripe → app):**
| Stripe condition | App state |
|---|---|
| No customer record | Free |
| Subscription active | Pro active |
| Subscription past_due | Past due |
| cancel_at_period_end = true AND current_period_end in future | Canceling at period end |
| Subscription canceled OR current_period_end in past for canceled sub | Canceled / no access |
| Subscription state cannot be resolved | Loading or Error |

**Critical rule:** State resolution always reads effective entitlement, never derives state from H6 intent or local UI events. After return from Stripe Portal, H5 must refetch subscription state before re-rendering.

---

### H6 — Cancel subscription flow (bottom sheet)

Tall bottom sheet over H5. Captures cancellation reason for analytics; Stripe Portal executes the cancellation.

**Pattern:**
- Tall bottom sheet (~85% viewport)
- Renders over H5 (Pro active state)
- Dim backdrop rgba(31,27,20, 0.32)
- Drag handle top-center (40×4 Edge, 2px radius)
- Dismissable: Cancel button / Backdrop tap / Drag-down / Esc / Android back

**Structure:**
1. Drag handle
2. Header (padding 0 24px 10px):
   - Title: "Before you cancel" (Cormorant 24, weight 400)
   - Body: "What is the main reason you're leaving Pro?" (Lora 14, Charcoal, 6px top margin)
3. Scrollable reason list (padding 8px 16px 0):
   - 7 single-select reason options (component 3.34)
   - Conditional reveals inline below selected option
4. Fixed bottom action area (12px 16px 24px, Vellum bg, 0.5px Linen top border):
   - Vertical button stack, 8px gap
   - Primary: "Keep Pro" — Ink solid (2.1)
   - Secondary: "Continue to Stripe to cancel" — outlined Ink (2.2), disabled until reason selected

**Reasons (single-select, stable codes):**
| Label | Code |
|---|---|
| I do not use it enough | `not_using_enough` |
| Too expensive | `too_expensive` |
| The answers were not useful enough | `not_useful_enough` |
| I expected more from the personas | `expected_more_from_personas` |
| I only needed it temporarily | `temporary_need` |
| I had a technical issue | `technical_issue` |
| Other | `other` |

**Conditional reveal — `technical_issue` selected:**
Inline helper card below option:
- Title: "Want help fixing this first?" (Lora 14, weight 500, Ink)
- Body: "If something broke, we can look into it before you cancel." (Lora 13, Charcoal, 1.5)
- CTA: "Contact support" (text link, Lora 13, Ink, underlined 0.5px, 3px offset) — opens I4 Report a problem flow
- Continue to Stripe to cancel remains visible and enabled
- Helper styled: Paper bg, 2px Ink left border, 6px right radius, padding 14px 16px

**Conditional reveal — `other` selected:**
Inline textarea below option:
- Placeholder: "What made you cancel? (optional)" (italic Lora 13, Sepia)
- Max 300 characters
- Character count appears after first keystroke (Lora 11, Sepia, right-aligned, 6px top padding)
- Empty submission valid (no required field)
- Single Paper bg, 0.5px Edge border, 6px radius
- 78px height, no resize handle

**Behavior + analytics:**
| Action | Event logged | State change |
|---|---|---|
| "Keep Pro" tap | `retention.kept_pro` `{reason_code, free_text?}` | Close sheet, return to H5 unchanged |
| Backdrop tap | `retention.dismissed_without_cancel` | Close sheet |
| Drag down | `retention.dismissed_without_cancel` | Close sheet |
| Esc / Android back | `retention.dismissed_without_cancel` | Close sheet |
| "Continue to Stripe to cancel" tap | Save `cancel_intent` row, then open Stripe Portal | CTA enters loading state immediately, prevents duplicate submissions |

**Save failure rule:** If saving the reason fails (network/server error), do NOT block cancellation. Open Stripe Portal anyway and log a retry job for intent creation.

**Outcome reconciliation (24-hour window):**
On "Continue to Stripe to cancel" tap, create `cancel_intent` with:
- `status = sent_to_stripe`
- `expires_at = now + 24 hours`

Possible outcomes:
| Outcome | Trigger |
|---|---|
| `canceled_confirmed` | Stripe webhook `customer.subscription.updated` with `cancel_at_period_end = true` OR `customer.subscription.deleted` received within 24h |
| `not_canceled_after_24h` | 24h elapsed without cancellation event |
| `superseded` | New `cancel_intent` created before previous expired |
| `unknown` | Webhook/sync failed before resolution |

**Critical rule:** On return from Stripe Portal, H5 refetches subscription state before render. H5 NEVER renders billing state from H6 intent alone. `cancel_at_period_end = true` renders Canceling, not Canceled. Canceled / no-access renders only when Stripe confirms subscription ended OR effective entitlement is inactive.

**Duplicate prevention:**
- After "Continue to Stripe to cancel" tap, CTA enters loading state immediately and is disabled
- Stripe Portal opens exactly once
- If active `sent_to_stripe` intent exists for this user within 24h, reuse `intent_id`; supersede only when new `reason_code` differs

**Privacy boundary (other_text):**
- Treated as user-generated personal data
- Included in I3 data export
- Deleted on I3 account deletion
- Never exposed raw in analytics dashboards (aggregation/redaction required)
- DB column flagged `personal_data = true`

---

### I1 — Account hub

Authenticated user's account control surface. Single home screen for all settings, billing, privacy, and support.

**Pattern:**
- Bottom tab bar visible (Account tab active)
- No back chevron (this is a primary tab destination)
- Mixed-tone title (period): "Your account."

**Structure:**
1. Status bar
2. Header (padding 24px 24px 14px):
   - Eyebrow: "Account" (Lora 11, Sepia, 0.18em uppercase)
   - Title: "Your account." (Cormorant 28, weight 400, 8px top margin)
3. Profile card (padding 8px 24px 24px):
   - 48×48 circle avatar (Linen bg, 0.5px Edge border, Cormorant 18 weight 500 Charcoal initials)
   - Name (Cormorant 20, weight 500, Ink) + Email (Lora 12, Charcoal, 2px top)
   - **v1: initials only.** Custom avatar upload deferred post-MVP.
4. Grouped lists (4 sections, each with eyebrow + card):

   **Subscription section:**
   - Row: "Plan" + meta (varies by state) + chevron → routes to H5
   - Meta variants:
     - Free: "Free"
     - Pro active: "Pro · Renews June 14"
     - Past due: Rust dot 7×7 + "Pro · Payment issue" (Lora 12 Rust, weight 500)
     - Canceling: "Pro · Active until June 14"
     - Canceled: "Free"

   **Preferences section:**
   - Row: "Notifications" + chevron → I2

   **Data & support section (single card, 3 rows with dividers):**
   - "Privacy & data" + chevron → I3
   - "Help & support" + chevron → I4
   - "About & legal" + chevron → I5

   **Sign out card (standalone):**
   - Single row, left-aligned, no chevron, no eyebrow, no Rust
   - Label: "Sign out" (Lora 14, Charcoal #5A5246)
   - Tap → I6 logout sheet

**Profile rules:**
- Plan info appears only inside Subscription row, never as a badge next to user name (avoids redundancy)
- Past-due treatment relies on text + dot, never icon-only (accessibility: color is not the sole signal)

---

### I2 — Notifications

Email notification preferences. Push notifications NOT supported in v1.

**Pattern:**
- Sub-screen
- Back chevron top-left
- Tab bar hidden
- Functional title: "Notifications" (no period)

**Structure:**
1. Status bar + back chevron
2. Title: "Notifications"
3. Single card with 3 toggle rows (each row uses 3.32 settings row + 3.31 toggle):

   | Row | Supporting text | Free default | Pro default |
   |---|---|---|---|
   | Weekly letters | "Sent Sundays · a summary of your week" | Pro pill (no toggle); tap row → H1 | ON |
   | Reflection reminders | "A short daily reminder" | OFF | OFF |
   | Product updates | "Only major changes" | OFF | OFF |

4. Footer (centered, padding 32px 32px 24px): "Great Minds sends notifications by email." (Lora 12, Sepia, 1.5)

**Rules:**
- For Free users on Weekly letters row: toggle is replaced entirely by Pro pill (3.22). No fake disabled-toggle interaction. Tap on entire row routes to H1 Upgrade.
- Pro users: all toggles use 3.31 component states (off/on/disabled).
- No push toggle. No "coming soon" copy. Honest UI > impressive UI.

---

### I3 — Privacy & data

Actionable data rights only. Legal documents (Privacy Policy, Terms, Disclaimer) live in I5, not here.

**Pattern:**
- Sub-screen
- Back chevron top-left
- Tab bar hidden
- Functional title: "Privacy & data" (no period)

**Structure (main screen):**
1. Status bar + back chevron
2. Title: "Privacy & data"
3. Single card, 2 rows with divider:
   - Row 1: "Request my data" + supporting "Receive a copy of your account data by email." + chevron
   - Row 2: "Delete my account" + supporting "Permanently delete your account, conversations, saved reflections, and weekly letters." + chevron

No footer. No "Privacy Policy / Terms / Correct details / Contact support" rows. Editorial sparseness, not "Danger Zone" SaaS aesthetic.

**Pending export request state:**
When `data_requests` row exists with status `requested` or `processing`:
- "Request my data" row subtitle replaces with: "Requested · April 30 · Expected by May 30"
- Tap opens informational sheet "Request already in progress" with body "We're preparing your data and will send it to your account email by May 30." and single "Close" button
- No duplicate `data_requests` row created
- Re-enabled when status transitions to `completed`, `rejected`, or `expired`

**Delete flow (sheet sequence):**

**Sheet A — Active subscription guard (when active Pro subscription exists):**
- Title: "Cancel Pro before deleting"
- Body: "An active Pro subscription is linked to this account. Cancel your subscription first, then return to delete."
- Primary CTA: "Manage Pro subscription" (Ink solid) → routes to H5/Stripe Portal
- Tertiary: "Close" (text link, Charcoal)

**Sheet B — Delete confirm (when no active subscription):**
- Title: "Delete your account?"
- Body: "This will permanently delete your account, conversations, saved reflections, and weekly letters. This action cannot be undone."
- Eyebrow label: "TYPE DELETE TO CONFIRM" (Lora 11, Sepia, 0.18em uppercase, 18px top padding)
- Input field: 50px height, Paper bg, 0.5px Edge border (1px Ink when focused/filled), Lora 14
- Validation: case-sensitive "DELETE", trim leading/trailing whitespace
  - Valid: "DELETE", "DELETE " (trimmed), " DELETE" (trimmed)
  - Invalid: "delete", " delete ", "Delete"
- Buttons (vertical stack, Cancel-first):
  - "Cancel" — secondary outlined Ink (2.2), placed above
  - "Delete account" — destructive outlined Rust (2.8), disabled until exact "DELETE" entered, placed below

**Request my data flow:**
- Confirmation sheet: "We'll prepare a copy of your data and send it to your account email within 30 days."
- CTA: "Request export" → creates `data_requests` row
- Confirmation toast or state update on row

---

### I4 — Help & support

Operational support routing. Two rows, both opening prefilled mailto with diagnostic context.

**Pattern:**
- Sub-screen
- Back chevron top-left
- Tab bar hidden
- Functional title: "Help & support" (no period)

**Structure:**
1. Status bar + back chevron
2. Title: "Help & support"
3. Single card, 2 rows with divider:
   - Row 1: "Contact support" + supporting "Questions, billing, or account help." + chevron
   - Row 2: "Report a problem" + supporting "Tell us what broke. Diagnostic details are included." + chevron
4. Footer (centered, padding 32px): "We aim to respond within 2 business days." (Lora 12, Sepia)

**Mailto behavior:**

Row 1 (Contact support):
- to: `SUPPORT_EMAIL` from config/env (NOT hardcoded)
- subject: "Great Minds support · General inquiry"
- body opens with: "How can we help?" then 2 blank lines, then diagnostic block

Row 2 (Report a problem):
- to: `SUPPORT_EMAIL`
- subject: "Great Minds support · Bug report"
- body opens with: "What happened?" + blank + "What did you expect to happen?" + blank + "Can you reproduce it?" + 2 blank lines, then diagnostic block

**Diagnostic block format (visible in email body):**
```
---
Sent from Great Minds — diagnostic details below
User ID: usr_a8f3…
Email: [user-email]
Plan: [Free / Pro / Pro · Past due / Pro · Canceling]
Device: [iPhone 15 Pro · iOS 18.2]
App version: [1.0.0]
Locale: [browser/system locale, e.g. en-GR]
Timestamp: [YYYY-MM-DD HH:MM UTC]
Issue type: [General inquiry / Bug report]
```

**Rules:**
- Cursor lands at top of email body (where user types)
- Diagnostic block is visible to user, with em-dash separator above
- User ID truncated in email body (privacy hygiene); full ID stays in backend logs
- Email subject remains English regardless of user locale (internal routing primarily)

---

### I5 — About & legal

Brand context + legal documents. Mixed external/in-app routing.

**Pattern:**
- Sub-screen
- Back chevron top-left
- Tab bar hidden
- Functional title: "About & legal" (no period)

**Structure:**
1. Status bar + back chevron
2. Title: "About & legal"
3. **About section:**
   - Eyebrow: "About"
   - Card with single row: "About Great Minds" + chevron → opens in-app bottom sheet (1-2 paragraphs of brand copy)
4. **Legal section:**
   - Eyebrow: "Legal"
   - Card with 3 rows (dividers between):
     - "Terms of use" + outbound icon (11×11 corner-up-right arrow) → external browser
     - "Privacy policy" + outbound icon → external browser
     - "Disclaimer" + chevron (in-app, NOT outbound) → opens in-app read-only sheet/modal
5. Footer (centered, padding 24px 32px):
   - "Great Minds · Version 1.0.0 (build 47)" (Lora 11, Sepia)
   - "Made in Athens." (Lora 11, Sepia, 6px top)

**Routing rationale:**
- Terms / Privacy → external because they're website-published, frequently updated, single source of truth, app-store-required URL exists anyway
- Disclaimer → in-app because it's app-specific (tied to A6+A7 onboarding acceptance and disclaimer versioning)
- About → in-app sheet because it's brand storytelling, not legal

**Pre-launch blocker:** Terms of use, Privacy policy URLs must be live on website before app store submission.

---

### I6 — Logout (bottom sheet, NOT screen)

Compact bottom sheet over I1 confirming sign-out intent.

**Pattern:**
- Bottom sheet over I1 (NOT a separate screen)
- Dim backdrop rgba(31,27,20, 0.32)
- Compact height (~28% viewport)
- Drag handle top-center
- Dismissable: Cancel button / Backdrop tap / Drag-down / Esc / Android back

**Structure:**
1. Drag handle (40×4 Edge)
2. Title (centered, padding 0 22px): "Sign out?" (Cormorant 24, weight 400)
3. Body (centered, padding 12px 22px 0): "You can sign back in anytime with your account." (Lora 14, Charcoal, 1.55)
4. Buttons (horizontal 50/50, padding 24px 22px 28px, gap 10px):
   - Left: "Cancel" — secondary outlined Ink (2.2)
   - Right: "Sign out" — Ink solid primary (2.1)

**Behavior:**
- Cancel button: dismiss sheet, no state change
- Backdrop tap: dismiss sheet, no state change
- Drag down: dismiss sheet, no state change
- Esc / Android back: dismiss sheet, no state change
- Sign out: clear auth session (access token, refresh token, session cookie); clear all user-specific cached data (cached conversations, saved reflections, profile, subscription state, last active session context); keep only device-level preferences that do not reveal user identity, account status, conversations, personas, or reflection behavior; route to A2/A3 sign-in screen

**No Rust on Sign out button** — logout is reversible, not destructive.

---

### J1 — App-wide server error / 5xx (NEW v4)

Shared full-screen error state for any backend 5xx that prevents tab content from loading. Reuse-only — no new component, no new ornament.

**Pattern:**
- Full-screen replacement (replaces tab body and tab-specific header alike — the entire content area between status bar and tab bar)
- Status bar visible at **full opacity** (signal/wifi/battery icons normal — distinguishes from J2 where these are dimmed)
- No back chevron (this is the route, not a sub-screen)
- Tab bar visible with currently active tab preserved

**Structure:**
1. Status bar
2. Centered content area (vertical flex, justify-center, padding 32px 36px 60px):
   - **Sepia concentric circles ornament** (DESIGN_SYSTEM §7.3): 50–52px, 1px Sepia (#8A7E6A) stroke, two concentric circles + Sepia center dot. Calm pause metaphor. Same ornament family as H4b — NOT Rust, NOT exclamation, NOT alarm.
   - Gap 26px
   - Headline: "Something on our end." (Cormorant 26, weight 400, Ink, centered)
   - Gap 12px
   - Body: "Something didn't load. Try again in a moment." (Lora 13, Charcoal, 1.65 line-height, centered, max-width 280px)
   - Gap 30px
   - CTA "Try again" (Ink primary, centered, content-sized, padding 12px 28px, **min-width 140px, white-space nowrap**)
   - Gap 20px
   - Support fallback: "If this persists, [contact support]." (Lora 12, Sepia; "contact support" link in Ink, underlined 0.5px, 3px offset)
3. Tab bar (current tab active)

**Behavior:**
- CTA "Try again" retries the failed data load for the current tab/context. On success → renders normal tab content. On failure → re-renders J1 (no error escalation; same calm state).
- Tap on a different tab in the tab bar → re-renders J1 with the newly selected tab active (since 5xx is shell-wide, every tab will fail until the backend recovers).
- "contact support" routes to I4 mailto flow with the diagnostic block (see I4 spec). Subject auto-set to: "Great Minds support · App couldn't load".
- No auto-retry. Retry must be user-initiated. Auto-retry hides systemic problems and burns server resources during incidents.

**Why Sepia (not Rust):**
Per DESIGN_SYSTEM §1.2, Rust is reserved for actionable user-side errors (failed messages, payment failures) and destructive actions. Server 5xx is not user-actionable in the same way — the user did not cause it and cannot fix it directly. The correct register is calm, apologetic, "we got it". Sepia concentric circles (H4b family) carry exactly that emotional register.

**Why distinct from J2:**
J2 (offline) and J1 (server error) must look different at a glance. A user retrying J2 who lands on J1 needs to see immediately that the cause shifted (network → our infra). Bronze offline ornament for J2, Sepia concentric circles for J1. Same headline pattern would be wrong — cause-blind.

---

### J2 — App-wide offline (non-chat shell) (NEW v4)

Shared full-screen offline state for any non-chat tab when the device cannot reach the backend due to lost connectivity. Sibling to C6c (which handles chat-specific cold-start offline). Reuse-only.

**Pattern:**
- Full-screen replacement (status bar + centered content + tab bar; no tab-specific header)
- Status bar visible with **signal/wifi icons dimmed to 0.35 opacity** — visual signal that the device has lost connectivity (distinguishes from J1 where icons are full opacity)
- Tab bar visible with currently active tab preserved

**Structure:**
1. Status bar (with dimmed signal/wifi icons)
2. Centered content area:
   - **Bronze offline ornament** (DESIGN_SYSTEM §7.3): 56×56, 1.2px Bronze (#A8884A) stroke. Wifi-with-slash metaphor: two concentric arcs + Bronze center dot + diagonal slash through. **Same ornament as C6c** — no per-screen variants.
   - Gap 26px
   - Headline: "Waiting for a connection." (Cormorant 26, weight 400, Ink, centered) — **locked offline-family v4** (DESIGN_SYSTEM §4.10)
   - Gap 12px
   - Body: "Great Minds needs a connection to load this. Try again when you're back online." (Lora 13, Charcoal, 1.65 line-height, centered, max-width 280px)
   - Gap 32px
   - CTA "Try again" (Ink primary, centered, content-sized, padding 12px 28px, **min-width 140px, white-space nowrap**)
3. Tab bar (current tab active)

**Behavior:**
- CTA "Try again" retries the failed data load for the current tab/context. On success → renders normal tab content. On failure → re-renders J2.
- Tap on a different tab → re-renders J2 with the newly selected tab active (every tab hits network).
- No "Available offline" / cached-content card promise. The offline-cache feasibility is open per DESIGN_SYSTEM §9. Do not promise what is not implemented.
- No "contact support" link — offline is the user's network, not our infra. Support cannot help.
- No per-tab copy variants in v1. Single unified offline state across Today / Library / Reflections / Account.

**Difference vs C6c:**
| Aspect | C6c | J2 |
|---|---|---|
| Context | Chat cold-start offline | Non-chat tab offline |
| Tab bar | Hidden (chat does not have tab bar) | Visible |
| Body copy | "...to start new conversations. Your saved reflections remain available below." | "...to load this. Try again when you're back online." |
| Available-offline card | Yes (if feasible) | No |
| Ornament | Bronze offline (same) | Bronze offline (same) |
| Headline | "Waiting for a connection." (same) | "Waiting for a connection." (same) |

---

### J3 — Empty saved reflections (NEW v4)

Empty state for F1 when user has zero saved reflections. Reuse-only — uses 3.26 empty state card pattern unchanged.

**Pattern:**
- Replaces the date-grouped saved-card list area inside F1 (not full-screen)
- F1 header preserved: eyebrow "Reflections" + title "Your saved lines."
- Filter pills hidden while empty (no filterable content)
- Bottom tab bar visible, Reflections tab active

**Structure:**
1. Status bar
2. Header (padding 22px 24px 16px):
   - Eyebrow "Reflections" (Lora 11, Sepia, 0.18em uppercase)
   - Title "Your saved lines." (Cormorant 26, weight 400)
3. **No filter pills** while `saved_lines_count = 0`
4. Empty state card (component 3.26, margin 12px 16px 0):
   - Top ornament row: 0.5px Edge line + Bronze star/sparkle SVG (14×14, 0.7 stroke) + 0.5px Edge line
   - Headline: "A space for the lines that stay with you." (Cormorant 19, weight 400, centered)
   - Body: "When a sentence settles, save it. Saved lines live here, ready when you return." (Lora 13, Charcoal, 1.6 line-height, centered)
   - Top divider (0.5px Linen)
   - 3-item instruction list (left-aligned, 13px gap between items):
     1. **Save what resonates** / "Tap Save line below any response that lands."
     2. **Group by mind or theme** / "Filter by who said it or what it touched."
     3. **Return when you need them** / "Saved lines remain until you remove them."
     - Each row: 24×24 Edge-bordered square containing mini-icon (bookmark / filter-bars / archive-box) + label (Lora 13, weight 500, Ink) + description (Lora 12, Charcoal, 1.45 line-height)
5. CTA "Start a conversation" (Ink primary, full-width, padding 14px, Cormorant 17 weight 500, 4px radius) — routes to D1 Today / Home
6. Bottom tab bar (Reflections active)

**Behavior:**
- Filter pills hidden while `saved_lines_count = 0`. Show automatically once `saved_lines_count >= 1` — no flag, no animation.
- No upgrade messaging in this empty state. Upgrade prompt appears only on 4th save attempt (Free user limit) or in populated F1 limit context. Surfacing upgrade on empty state is premature monetization friction.
- F1 hub title retains period ("Your saved lines.") — empty state does not flip the screen from hub to utility.
- Single Free/Pro variant. Free user with zero saves looks identical to Pro user with zero saves (the difference only matters once they have saves).

**Reuse rule:**
- 3.26 empty state card pattern unchanged.
- Bronze star/sparkle ornament (DESIGN_SYSTEM §7.3) unchanged.
- No new component, no new ornament.

---

### J5 — Empty conversation history (NEW v4)

Empty state for F6 when user has zero past conversations. Reuse-only — same 3.26 pattern as J3 with different content.

**Pattern:**
- Replaces the date-grouped conversation-card list area inside F6 (not full-screen)
- F6 header preserved: eyebrow "Library" + title "Past conversations."
- No filter pills exist on F6 in v1 (search deferred until 20+ conversations average)
- Bottom tab bar visible, Library tab active

**Structure:**
1. Status bar
2. Header (padding 22px 24px 16px):
   - Eyebrow "Library" (Lora 11, Sepia, 0.18em uppercase)
   - Title "Past conversations." (Cormorant 26, weight 400)
3. Empty state card (component 3.26, margin 12px 16px 0):
   - Top ornament row: 0.5px Edge line + Bronze star/sparkle (14×14, 0.7 stroke) + 0.5px Edge line
   - Headline: "Past conversations gather here." (Cormorant 19, weight 400, centered)
   - Body: "Every conversation you start is saved here. Return to any of them when you need to." (Lora 13, Charcoal, 1.6 line-height, centered)
   - Top divider (0.5px Linen)
   - 3-item instruction list:
     1. **Saved automatically** / "No need to save conversations manually."
     2. **Resume where you left off** / "Tap any card to return to the exact place."
     3. **Organized by recency** / "Grouped by week, with the most recent at the top."
4. CTA "Explore minds" (Ink primary, full-width) — routes to D2 Explore Minds (NOT D1; tab-aware CTA — Library is the user's current tab and D2 is its primary destination)
5. Bottom tab bar (Library active)

**Behavior:**
- No save-count gating, no Pro/Free differentiation (F6 is universal Free + Pro per F6 spec).
- F6 hub title retains period ("Past conversations.") — empty state does not flip the screen from hub to utility.
- CTA destination is D2, not D1. Reasoning: tab-aware CTAs. The user is already in the Library tab; D2 is the Library tab's primary destination. Routing to D1 (Today) would unnecessarily switch tabs. This deliberately differs from J3 (where CTA routes to D1 because Reflections has no inline browse equivalent).

**Reuse rule:**
- 3.26 empty state card pattern unchanged.
- Bronze star/sparkle ornament unchanged.
- No new component, no new ornament.

**Difference vs J3:**
| Aspect | J3 (empty F1) | J5 (empty F6) |
|---|---|---|
| Tab active | Reflections | Library |
| Filter pills | Hidden while empty | None exist (deferred v2) |
| CTA label | "Start a conversation" | "Explore minds" |
| CTA destination | D1 Today | D2 Explore Minds |
| Save-count gating | Yes (3-save limit visible only when populated) | None (universal Free + Pro) |

---

## Backlog requirements (implementation, not UI design)

These are product requirements captured during spec sessions that must be implemented but don't have UI screens of their own.

### Authentication (Block 4)
- **Platform-aware provider order**: Web=Google first, iOS=Apple first, Android=Google first
- **OTP state machine**: wrong code, expired, cooldown, too many attempts (5 lockout 15min), use different email, rate limiting (5/hour)
- **Disclaimer versioning**: DB schema with version field, re-prompt on copy change
- **A4 structured support payload**: pre-filled mailto with device/browser/timestamp
- **Account linking security**: only auto-link when both providers report `email_verified: true`; require OTP if unverified; never link on email string match alone

### Reflection & Memory (Block 5)
- **F2 lite quality guardrails**: prompt-level enforcement of insight specificity rules (see DESIGN_SYSTEM 4.6)
- **F2 lite trigger threshold**: ≥10 user messages, max 1 per conversation
- **F2 lite cost monitoring**: ~$0.01-0.05 per qualifying conversation
- **F3/F4 weekly letter generation**: async batch Sunday job, minimum material rule, "quiet week" graceful handling
- **F1 free-tier limit**: 3 saves max, 4th attempt triggers upgrade prompt
- **F2 free-tier limit**: 1 preview lifetime, then locked

### Discovery (Block 3)
- **D2/D3 view preference**: localStorage v1, DB v2
- **D3 ordering perception test**: monitor first 50-100 free users for 4/6 locked feeling restrictive

### Account, Billing & Privacy (Block 6) — NEW v3

**Stripe integration:**
- `SUPPORT_EMAIL` from config/env. Never hardcode support mailbox in UI logic.
- Stripe Customer Portal handles: card updates, invoices, billing history, plan changes, cancellation execution.
- H5 displays effective app entitlement, NOT raw Stripe status.
- After return from Stripe Portal, H5 must refetch subscription state before render. Never derive billing state from H6 intent.
- App listens to Stripe webhooks: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`, `invoice.payment_succeeded`.
- State mapping: `cancel_at_period_end = true` AND `current_period_end` in future → renders Canceling (NOT Canceled). Canceled / no-access renders only when Stripe confirms subscription ended OR effective entitlement is inactive.

**Cancellation analytics:**
- Table `cancellation_reasons`:
  ```
  id (uuid)
  user_id (fk)
  reason_code (enum: not_using_enough, too_expensive, not_useful_enough,
                expected_more_from_personas, temporary_need,
                technical_issue, other)
  free_text (nullable, varchar 300, personal_data = true)
  created_at (timestamp)
  outcome (enum: canceled_confirmed, not_canceled_after_24h,
            superseded, unknown)
  expires_at (timestamp, default now + 24h)
  ```
- 24-hour reconciliation window for outcome inference.
- Save failure must NOT block cancellation; open Stripe Portal anyway and queue retry.
- Duplicate prevention: CTA enters loading state immediately; reuse `intent_id` if active intent exists within 24h window.

**GDPR data rights:**
- Table `data_requests`:
  ```
  id (uuid)
  user_id (fk)
  request_type (enum: export, deletion, correction)
  status (enum: requested, processing, completed, rejected, expired)
  requested_at (timestamp)
  completed_at (timestamp, nullable)
  user_email (varchar)
  notes (text, nullable, internal only)
  ```
- Pending state in I3 derived from `status IN (requested, processing)`.
- Status auto-transitions to `expired` after 30 days if not actioned.
- Export fulfillment: founder/admin runs SQL query, sends JSON/CSV via email. v1 manual; v2 automated pipeline.

**Account deletion guard:**
- Backend check before deletion: query Stripe for active subscription tied to user.
- If active subscription exists, return error "active_subscription_exists"; UI shows blocked sheet (Sheet A in I3 spec).
- If no active subscription, proceed with deletion: cascade-delete user record, conversations, saved reflections, weekly letters, cancellation_reasons free_text, data_requests rows.
- Soft-delete vs hard-delete policy: hard-delete after 30-day grace period (configurable). Within grace period, account is recoverable via support.

**Personal data classification:**
- `cancellation_reasons.free_text` flagged `personal_data = true`. Included in data export. Deleted on account deletion. Never exposed raw in analytics dashboards (aggregation/redaction required).
- I4 mailto diagnostic block: User ID truncated; full ID stays in backend logs only.

**Notification system (v1):**
- Email-only. Push notification permission (K1) NOT implemented in v1.
- Toggles control email sends only.
- Defaults: Weekly letters ON for Pro / disabled+Pro pill for Free; Reflection reminders OFF; Product updates OFF.
- Honest UI: no fake push toggle.

**Legal documents:**
- Pre-launch blocker: Terms of use, Privacy policy URLs must be live and routable.
- Disclaimer is in-app (tied to A6+A7 acceptance and disclaimer versioning).
- About Great Minds copy must be written before launch (in-app sheet content).

### General
- **Insight extraction timing**: F2 surfaces inline only after persona's last message renders (250ms fade-in)
- **Library offline read-only**: v1 feasibility check; if not feasible, do not promise in C6c UI
- **Soft cap notice**: "Bring another mind" 3+ chain → backlog v2 message

---

## Implementation notes

### Sequencing for Claude Code

When implementing v2 screens, follow this order:
1. Foundation tokens (palette, typography, type scale, radius, spacing) → CSS variables
2. Universal buttons (incl. Apple/Google compliance variants) → reusable components
3. Theme chip + filter pill → reusable components
4. OTP field component → reusable
5. Disclaimer checkbox card → reusable
6. Persona card variants (3 variants) → component family
7. Chat bubble variants → core chat shell
8. Auth screens (A1, A2/A3 merged, A4, A5, A6+A7 merged) → linear flow with passwordless backend integration
9. Onboarding screens (B1–B6) → linear flow
10. Chat states (C1–C9) → expanded chat shell
11. Home (D1) → integration of multiple components
12. Discovery (D2 list, D3 grid, view toggle) → 2-view system
13. Reflection (F1 saved, F3 letters inbox, F4 letter detail) → tab structure
14. Suggested insight card (F2 lite) → in-chat component
15. Reflection history (F6) → list component
16. Upgrade flow (H1–H4b) → modal-like screens
17. Account hub + utility screens (I1, I2, I3, I4, I5) → grouped-list pattern, sub-screen navigation
18. Subscription management (H5) — 5 visual states + loading/error → state-driven render based on effective entitlement
19. Cancellation flow (H6 sheet, I6 sheet) → bottom sheet patterns

### Component reuse map

- Persona card list variant: B4 Best matches, F6 Reflection history, C9a bottom sheet rows (compact version)
- Persona card grid variant: D3 only
- Persona card D2 portrait list variant: D2 only
- Theme chip selectable: B2 What brings you here?, future onboarding/preference contexts
- Theme chip descriptive: B5 Persona detail, D1 themes section
- Filter pill: F1 saved reflections, future filtering contexts
- OTP field: A5 only (specialized)
- Disclaimer checkbox card: A6+A7 only (specialized)
- Chat bubble (persona): C1, C2, C7 (with safety variant), C8, C9b
- Chat bubble (user): C1, C4 (failed variant), C6b (queued variant)
- Suggested insight card: F2 lite (in-chat C1)
- Bronze divider: B1, H1, H3, F4 weekly letter
- Pull-quote: F4 weekly letter only
- Bottom tab bar: D1, F1, F3, F6, I1 — hidden on D2/D3, chat screens, auth screens, I2/I3/I4/I5/H5
- Apple Sign In button: A2/A3 only (compliance-locked)
- Google Sign In button: A2/A3 only (compliance-locked)
- **Toggle (3.31)**: I2 only in v1; reusable for any future binary preference
- **Settings row (3.32)**: I1, I2, I3, I4, I5 — universal grouped-list row component
- **Status card (3.33)**: H5 only (5 state variants)
- **Reason option (3.34)**: H6 only in v1; reusable for future single-select surveys
- **Destructive outlined button (2.8)**: I3 delete confirm sheet only in v1
- **Tertiary text-link button (2.9)**: H5 Cancel Pro only in v1
- **Bottom sheet pattern (3.20)**: H6 (tall ~85%), I6 (compact ~28%), I3 delete sheets, F2 lite preview, A4 various — sheet height varies by content/risk
- **Empty state card (3.26)**: D1b first-day, **J3 empty saved reflections (v4), J5 empty conversation history (v4)** — same dashed-border + Bronze star + 3-item list pattern across all instances; content varies by surface
- **Bronze star/sparkle ornament (§7.3)**: D1b first-day, J3, J5 — empty-state ornament family
- **Bronze offline ornament (§7.3)**: C6c chat cold-start offline, **J2 app-wide offline (v4)** — same wifi-with-slash metaphor across both
- **Sepia concentric circles ornament (§7.3, NEW v4)**: H4b payment canceled, **J1 server error (v4)** — calm-pause family, distinct from Bronze ornaments
- **Universal retry CTA**: "Try again" with `min-width: 140px; white-space: nowrap;` — used across J1, J2, C6c. Content-sized, NOT full-width, padding 12px 28px

### Anti-patterns to flag in code review

- Hardcoded hex values not from the locked palette (all colors must be CSS variables)
- Mixed border radii within a component
- Box-shadows on cards (only modals/sheets)
- Multiple primary buttons on one screen
- Generic icon imports from default Material/Feather sets (use Lucide thin or custom)
- Persona-specific styling forks (all personas share the same component, only data differs)
- Apple/Google button styling deviation (compliance violation)
- Suggested insight using forbidden patterns (mystical, diagnostic, generic)
- Weekly letter generation when material < threshold (must show quiet state)
- **iOS-pill-shaped toggles** anywhere (3.31 locked at 4px radius; circular knobs forbidden)
- **Rust solid-fill buttons** (Rust is reserved for outlined destructive only)
- **Countdown timers in billing** (H5 Canceling state shows static date, never "X days remaining")
- **Hardcoded support email** (must use `SUPPORT_EMAIL` from config/env)
- **Account deletion without subscription guard** (must block when active Pro exists)
- **Type-DELETE validation that's case-insensitive** or doesn't trim whitespace
- **Rendering billing state from H6 intent** (always read effective entitlement from authoritative source)
- **Showing Cancel Pro on non-Pro-active states** (canceling, past due, free, canceled all hide it)
- **Storing free-text cancellation reasons without `personal_data = true` flag**
- **Rust on app-wide server-side errors** (J1 — must use Sepia concentric circles family, not Rust circle with `!`. Rust is for actionable user-side errors only.)
- **Auto-retry on server errors** (J1 retry must be user-initiated; auto-retry hides systemic problems and burns server resources during incidents)
- **Per-tab offline copy variants** (J2 must be unified across Today / Library / Reflections / Account in v1)
- **"Available offline" promise without offline cache implemented** (do not show this card unless cache is actually working)
- **Wrapping "Try again" CTA label to two lines** (button must have `min-width: 140px; white-space: nowrap;`)
- **Showing filter pills on empty F1** (J3 must hide filter pills while `saved_lines_count = 0`)
- **Showing upgrade messaging on empty F1** (J3 must not surface upgrade prompt until 4th save attempt or populated F1 limit context)
- **Different ornament for J2 vs C6c** (must reuse the same Bronze offline ornament — no per-screen variants)
- **Different ornament for J1 vs H4b** (must reuse the same Sepia concentric circles — calm-pause family is shared)

---

**End of SCREENS_TRACKING_v4.**