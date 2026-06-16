# GREAT MINDS — Screens Tracking v6

> **Purpose:** Full screen inventory of the Great Minds product. Each screen marked covered (✅) or pending (⚠️). Covered screens have full spec; pending screens have status notes.
>
> **Total: 68 screens** (v6 adds D6 guide + G13–G16 Sunday Letter reader; A0 added 2026-05-18; D5 folded into D1, D4 deferred v2, F5 deferred v2, J4 dropped, A2/A3 merged, A6/A7 merged; G5–G11 added 2026-05-28).
> **Effective specced count: 48** (Blocks 1–6 + Block 9 covered; D6 + G13–G16 shipped & logged; A0 pending spec)
> **Pending: 15** (A0 pending spec + Block 7 Rituals fuller-flow specs + Block 8 Multi-mind 5 screens + K1/K2 deferred v2 + D4 deferred v2 + F5 deferred v2)
>
> **Companion documents:**
> - `DESIGN_SYSTEM_v4.md` — visual and component spec
> - `USER_FLOW_v4.md` — how screens connect
> - `IMPLEMENTATION_BACKLOG_v18.md` — non-UI implementation work
>
> **Last updated:** 2026-06-15 (v6).
>
> **Changelog v5 → v6 (2026-06-15):**
> - **Sunday Letter / Weekly Reading reader SHIPPED** — G11 placeholder superseded; added **G13** reading library (search + hard-delete), **G14** reading detail (Revisit + Share), **G15** Revisit persona picker, **G16** letter share preview (`SharePreviewModal kind='letter'`; asset `sundayletter.png`). F3/F4 now point at concrete `app/app/letters/*` implementations.
> - **F1 Reflections** — unified feed (`GET /reflections/feed`) of saved lines + Mirror/Council verdicts + Mirror saves (`mirror_saves` 025); client-side search; `formatItemDate`; share-from-verdict cards; gravity-gated conclusions savable.
> - **D6** — "Living in the Wise Room" guide (`app/app/guide/page.tsx`, PR #275) logged; v6 imagery refresh (#304).
> - **D1** — Sunday-letter card next-Sunday date + returning-user archive link (#309).
> - **G12 You vs You** — forming preview as bullets (#300); admin bypass (#296).
> - Screen count: 63 → 68; pending: 20 → 15.
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
>   - **J4 Empty insights — DROPPED.** Subsumed by J3.
> - K1 Push permission + K2 In-app notification banner — deferred v2 explicitly.
> - C6c spec updated: headline "Waiting for a connection."
> - Component reuse map extended (J3, J5, J2 ornament sharing).
>
> **Changelog v4 → v4.1 (2026-05-18):**
> - A0 Public Landing added as new pending screen.
> - Screen count: 55 → 56; pending count: 12 → 13.
>
> **Changelog v4.1 → v4.2 (2026-05-28):**
> - D1 spec note updated: greeting personalization live (PR-D #129); NamePromptCard conditional render (PR-D2 #130)
> - G5–G11 added: 7 new pending ritual sub-screens (Mirror 3, Counterview 3, Weekly Reading placeholder 1)
> - Screen count: 56 → 63; pending count: 13 → 20
>
> **Changelog v4.2 → v4.3 (2026-06-03):**
> - D1 bug note added: PR3a cold-beta bugs pending (Continuing/Mind-of-the-Day 404s; item A chat stuck)
> - F6 bug note added: PR3a item #2 — ConversationCard.tsx:49 demotes title to snippet fallback (root cause identified; fix in PR3a sweep)
> - G deferred triage: items #3, #4, #7 deferred post-cold-beta; item #8 (Letter tap-to-card) in PR3a sweep
>
> **Changelog v4.3 → v5 (2026-06-03):**
> - D1: first-day "Reflect" picker bug fixed (PR #210 — opens PersonaPickerSheet, no longer hardcodes Marcus Aurelius). Item A (Ask another mind chat stuck) fixed (PR #210 — PersonaPickerSheet.tsx `onClose()` before async create). "Continuing" 404s still pending.
> - F6: PR3a item #2 ConversationCard title bug fixed (PR #210 — `title ?? last_message_snippet`). ⚠️ note removed.
> - Rituals hub (G-section note): micro-polish shipped 2026-06-03 — You-vs-You card: half-sphere inline SVG replaces `<Contrast>`; Letter-to-Future-Self card: whole-card `<button>` replaces `<div>` + inner Begin button.
> - App icon: photo icon (`appbutton.png`) tried as `apps/web/app/icon.png`/`apple-icon.png`, accidentally landed on main, removed via hotfix. **App-icon mark DEFERRED (TD-29).** No custom app icon on main. Purpose-built icon mark required before next attempt.
> - daily_questions: 50 modern-phenomenology themes active (display_order 1000–1049); old 30 deactivated. Item #6 closed.

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
| D1 | Home / Today (returning + empty) | ✅ covered — greeting personalized PR-D #129; NamePromptCard for nameless OTP users PR-D2 #130; first-day Reflect fixed (PR #210): opens PersonaPickerSheet, no longer hardcodes Marcus Aurelius; Ask another mind chat stuck fixed (PR #210); ⚠️ still pending: "Continuing" card 404s; item #6 "What's on your mind?" now rotates 50 phenomenology themes (daily_questions updated 2026-06-03). v17: consolidated "What brings you here?" card (#274); "Living in the Wise Room" button → D6. v6: Sunday-letter card shows next-Sunday date + returning-user archive link (#309). |
| D6 | "Living in the Wise Room" guide / explainer | ✅ shipped (v6 logging; PR #275, 2026-06-12) — `apps/web/app/app/guide/page.tsx`. Explainer reached from Today's bottom button. v6: "Explore The Wise Room" minds + rituals imagery (#304). |
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
| F1 | Saved reflections / lines archive | ✅ covered. **v6: unified Reflections feed** (`GET /reflections/feed`, #279–#281) — saved lines + Mirror/Council verdicts + Mirror saves (`mirror_saves` 025) in one feed; **client-side search** (#307); `formatItemDate` on cards (#306); share-from-verdict cards. Gravity-gated conclusions savable (`source_type='conclusion'`). |
| F2 | Suggested insights (lite, in-chat) | ✅ covered (lite version v1) |
| F3 | Weekly letter inbox | ✅ covered. **v6: concrete impl** `apps/web/app/app/letters/page.tsx` (search + hard-delete) — see G13. |
| F4 | Weekly letter detail / read view | ✅ covered. **v6: concrete impl** `apps/web/app/app/letters/[id]/page.tsx` (Revisit + Share) — see G14–G16. |
| F5 | Recurring themes dashboard | ⏸ deferred v2 (volume-dependent feature) |
| F6 | Reflection history (UI: "Past conversations") | ✅ covered; ConversationCard title bug (PR3a item #2) fixed 2026-06-03 (PR #210): `title ?? last_message_snippet` |

### G — Rituals (Phase 3, post-MVP)

> **Rituals hub micro-polish (2026-06-03):** The live rituals hub page (`apps/web/app/app/(tabs)/rituals/page.tsx`) received micro-polish — You-vs-You card icon: inline half-sphere SVG (`currentColor`) replacing `<Contrast>`; Letter-to-Future-Self card: whole-card `<button onClick={handleBeginLetter}>` replacing `<div>` + inner Begin button. These are implementation changes to the live hub; the G1–G11 pending specs remain for the fuller ritual-flow experience.

| ID | Screen | Status |
|---|---|---|
| G1 | Rituals library | ⚠️ pending |
| G2 | Ritual detail | ⚠️ pending |
| G3 | Ritual day-by-day flow | ⚠️ pending |
| G4 | Ritual completion | ⚠️ pending |
| G5 | The Mirror — Setup | ⚠️ pending (ref Brief #4; BLOCKED on `mirror_ritual_prompt.md` for Jung + Marcus) |
| G6 | The Mirror — Reflection rounds | ⚠️ pending (ref Brief #4; ≤3 rounds, editorial passages) |
| G7 | The Mirror — Closing | ⚠️ pending (ref Brief #4; "A line worth keeping" pull-quote + CTAs) |
| G8 | The Counterview — Setup | ⚠️ pending (ref Brief #5; BLOCKED on Mirror done + `counterview_ritual_prompt.md` for Machiavelli) |
| G9 | The Counterview — Rounds | ⚠️ pending (ref Brief #5; 2 rounds, ≤4 sentences, steelman-the-opposite) |
| G10 | The Counterview — Closing | ⚠️ pending (ref Brief #5; 2-line "What shifted, what didn't") |
| G11 | Weekly Reading — placeholder card (Rituals tile) | ✅ **SUPERSEDED by reader surface (v6, 2026-06-15).** No longer "Coming this season" — see G13–G16. |
| G12 | You vs You | ✅ shipped (2026-06-02, PRs #193–#202) — forming/locked guard → input (textarea + saved-lines) → dual-self reveal THEN/NOW → closing card (WiseMark + evidence quotes + ring-true + humility line) + usage meter + premium nudge. Pro-gated. Bg: youvsyou.webp. Hub card icon: half-sphere SVG (v5, 2026-06-03). v6: forming preview as 2–3 bullets (#300); admin bypass for forming gate (#296). |
| **G13** | **Sunday Letter — reading library** | ✅ **shipped (v6, 2026-06-15, #308/#309)** — `apps/web/app/app/letters/page.tsx`. List of weekly letters + **client-side search** + **hard-delete** (`DELETE /weekly-letters/{id}`). Today Sunday-card shows next-Sunday date; returning users get an archive link here. |
| **G14** | **Sunday Letter — reading detail** | ✅ **shipped (v6, 2026-06-15, #311/#313)** — `apps/web/app/app/letters/[id]/page.tsx`. Reads the letter (title/opening/references/pull_quote/forward_gesture). **Revisit** button + **Share** button (wax-seal card). |
| **G15** | **Sunday Letter — Revisit persona picker** | ✅ **shipped (v6, 2026-06-15, #310/#311)** — revisit-mode `PersonaPickerSheet` → `POST /conversations/reading-revisit` → a persona's candid read of the letter (non-stream; post-gen safety gate; no brevity band). |
| **G16** | **Sunday Letter — share preview** | ✅ **shipped (v6, 2026-06-15, #312/#313)** — `SharePreviewModal kind='letter'` wax-seal card from the letter's pull_quote. Asset: `apps/api/static/rituals/sundayletter.png`. Free = 3/90-day on shared share counter. |

### App icon — deferred

> **App icon (TD-29, deferred 2026-06-03):** `apps/web/app/icon.png` and `apps/web/app/apple-icon.png` do not exist on main. Photo asset `appbutton.png` (1122×1402 px) was tried and removed via hotfix — wrong shape and size for favicon/PWA/apple-touch. A purpose-built square icon mark must be designed before wiring. The Chesterfield armchair photo remains as brand/hero/OG image only.

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
| J2 | App-wide offline (non-chat shell) | ✅ covered (v4) |
| J3 | Empty saved reflections | ✅ covered (v4) |
| ~~J4~~ | ~~Empty insights~~ | **DROPPED v4** — subsumed by J3 |
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
- **OTP request rate-limit (v5 note):** Upstash Redis `otp_request:{email}` enforces 5 requests/hour in `auth.py`. Separate from the 5-attempt DB lockout. Testing workaround: `+alias` email = fresh bucket.

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
- Copy: "Great Minds needs a connection to start new conversations. Your saved reflections remain available below." (Lora 13, Charcoal, 1.6 line-height, centered) — **updated v4**: dropped "internet" qualifier.
- "Try again" (Ink button, centered, padding 12px 28px, **min-width 140px, white-space nowrap**)
- Below: card "Available offline" with link to saved reflections (only if technically feasible in v1)

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

**Build status note (2026-05-18):** Spec locked since v4. Build was deferred under "Block D — Not yet planned"; reprioritized to P0 on 2026-05-18 after structural gap discovery. See IMPLEMENTATION_BACKLOG_v9.md §"2026-05-18 launch priority shift".

**v4.2 additions (2026-05-28):**
- **Greeting personalization (PR-D #129):** Header greeting now personalizes — "Good morning, Nikos." for users with `full_name` set.
- **NamePromptCard (PR-D2 #130):** Conditional card shown to OTP users with no `full_name` set.

**v4.2 additions (2026-06-03):**
- **PR3a cold-beta bugs pending:** "Continuing" card 404s. Item #6: "What's on your mind?" prompts (pending in sweep).

**v5 updates (2026-06-03):**
- **First-day Reflect picker fixed (PR #210):** First-day "Reflect" now opens `PersonaPickerSheet` instead of hardcoding Marcus Aurelius. Opening message skipped only when a topic already exists.
- **Ask another mind chat stuck fixed (PR #210):** `PersonaPickerSheet.tsx` — `onClose()` called before async create. `history.back()` no longer reverts `router.push`. PR3a item A closed.
- **"What's on your mind?" prompts updated:** `daily_questions` table now has 50 modern-phenomenology themes active (display_order 1000–1049). PR3a item #6 closed.
- **Still pending:** "Continuing" card 404s (memory bugs; PR3a sweep still open for this item).

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
     - Conversation title (Lora 12, Charcoal, italic, 1-line) — **v5 (PR #210): `title ?? last_message_snippet`; title renders first, snippet is fallback. PR3a item #2 / BUG-013 closed.**
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
- Past-due users keep Pro access until Stripe/entitlement marks access inactive.

**State 4 — Canceling at period end:**
- Status card: eyebrow "Your plan", value "Pro", meta "Active until June 14, 2026."
- CTA: "Manage Pro subscription" — outlined Ink → Stripe Portal
- Microcopy: "Billing is managed securely through Stripe."
- No countdown. No in-app reactivate button.

**State 5 — Canceled / no access:**
- Status card: eyebrow "Your plan", value "Free", meta "Your Pro subscription has ended."
- CTA: "Upgrade to Pro" — Ink solid → H1
- No microcopy

**State 6 — Loading (spec only, no mock):**
- Render shell; status card content replaced with skeleton; all CTAs hidden.

**State 7 — Error (spec only, no mock):**
- Render shell; status card replaced with single line: "We couldn't load your subscription."
- Primary CTA: "Try again" (Ink solid)

**State mapping (Stripe → app):**
| Stripe condition | App state |
|---|---|
| No customer record | Free |
| Subscription active | Pro active |
| Subscription past_due | Past due |
| cancel_at_period_end = true AND current_period_end in future | Canceling at period end |
| Subscription canceled OR current_period_end in past for canceled sub | Canceled / no access |
| Subscription state cannot be resolved | Loading or Error |

**Critical rule:** State resolution always reads effective entitlement. After return from Stripe Portal, H5 must refetch subscription state before re-rendering.

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

**Conditional reveal — `other` selected:**
Inline textarea below option:
- Placeholder: "What made you cancel? (optional)" (italic Lora 13, Sepia)
- Max 300 characters
- Character count appears after first keystroke

**Behavior + analytics:**
| Action | Event logged | State change |
|---|---|---|
| "Keep Pro" tap | `retention.kept_pro` `{reason_code, free_text?}` | Close sheet, return to H5 unchanged |
| Backdrop tap | `retention.dismissed_without_cancel` | Close sheet |
| Drag down | `retention.dismissed_without_cancel` | Close sheet |
| "Continue to Stripe to cancel" tap | Save `cancel_intent` row, then open Stripe Portal | CTA enters loading state immediately |

**Save failure rule:** If saving the reason fails, do NOT block cancellation. Open Stripe Portal anyway and log a retry job.

**Critical rule:** On return from Stripe Portal, H5 refetches subscription state before render. H5 NEVER renders billing state from H6 intent alone.

---

### I1 — Account hub

Authenticated user's account control surface.

**Pattern:**
- Bottom tab bar visible (Account tab active)
- No back chevron (primary tab destination)
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
4. Grouped lists (4 sections):
   - **Subscription section:** Row: "Plan" + meta + chevron → H5
   - **Preferences section:** Row: "Notifications" + chevron → I2
   - **Data & support section (3 rows):** Privacy & data → I3; Help & support → I4; About & legal → I5
   - **Sign out card:** Single row, "Sign out" → I6 sheet

---

### I2 — Notifications

Email notification preferences. Push notifications NOT supported in v1.

**Structure:**
1. Status bar + back chevron
2. Title: "Notifications"
3. Single card with 3 toggle rows:

   | Row | Supporting text | Free default | Pro default |
   |---|---|---|---|
   | Weekly letters | "Sent Sundays · a summary of your week" | Pro pill (no toggle); tap row → H1 | ON |
   | Reflection reminders | "A short daily reminder" | OFF | OFF |
   | Product updates | "Only major changes" | OFF | OFF |

4. Footer: "Great Minds sends notifications by email." (Lora 12, Sepia, 1.5)

---

### I3 — Privacy & data

Actionable data rights only.

**Structure:**
1. Status bar + back chevron
2. Title: "Privacy & data"
3. Single card, 2 rows with divider:
   - Row 1: "Request my data" + supporting "Receive a copy of your account data by email." + chevron
   - Row 2: "Delete my account" + supporting "Permanently delete your account, conversations, saved reflections, and weekly letters." + chevron

**Delete flow (sheet sequence):**
- **Sheet A — Active subscription guard:** "Cancel Pro before deleting" → routes to H5/Stripe Portal
- **Sheet B — Delete confirm:** TYPE "DELETE" to confirm; "Delete account" destructive outlined Rust button

---

### I4 — Help & support

Operational support routing. Two rows opening prefilled mailto.

**Structure:**
1. Status bar + back chevron
2. Title: "Help & support"
3. Single card, 2 rows: "Contact support" + "Report a problem"
4. Footer: "We aim to respond within 2 business days." (Lora 12, Sepia)

---

### I5 — About & legal

Brand context + legal documents.

**Structure:**
1. Status bar + back chevron
2. Title: "About & legal"
3. About section → in-app bottom sheet
4. Legal section: Terms → external; Privacy policy → external; Disclaimer → in-app sheet
5. Footer: "Great Minds · Version 1.0.0 (build 47)" + "Made in Athens."

---

### I6 — Logout (bottom sheet)

Compact bottom sheet (~28% viewport) over I1.

**Structure:**
1. Drag handle
2. Title: "Sign out?" (Cormorant 24, weight 400)
3. Body: "You can sign back in anytime with your account." (Lora 14, Charcoal, 1.55)
4. Buttons (horizontal 50/50): "Cancel" (outlined Ink) | "Sign out" (Ink solid)

**Behavior:** Sign out → clear auth session and all user-specific cached data → route to A2/A3.

---

### J1 — App-wide server error / 5xx (NEW v4)

Shared full-screen error state for any backend 5xx. Reuse-only.

**Pattern:**
- Full-screen replacement; status bar full opacity; tab bar visible.

**Structure:**
1. Status bar
2. Centered content area:
   - **Sepia concentric circles ornament** (DESIGN_SYSTEM §7.3): 50–52px, 1px Sepia stroke. Calm pause metaphor. NOT Rust.
   - Headline: "Something on our end." (Cormorant 26, weight 400, Ink, centered)
   - Body: "Something didn't load. Try again in a moment." (Lora 13, Charcoal, 1.65 line-height, centered, max-width 280px)
   - CTA "Try again" (Ink primary, centered, **min-width 140px, white-space nowrap**)
   - Support fallback: "If this persists, [contact support]."
3. Tab bar (current tab active)

**Why Sepia (not Rust):** Server 5xx is not user-actionable. Rust is reserved for actionable user-side errors. See DESIGN_SYSTEM §1.2.

---

### J2 — App-wide offline (non-chat shell) (NEW v4)

Shared full-screen offline state for non-chat tabs. Sibling to C6c. Reuse-only.

**Pattern:**
- Full-screen replacement; status bar with signal/wifi icons dimmed to 0.35 opacity; tab bar visible.

**Structure:**
1. Status bar (dimmed signal/wifi)
2. Centered content area:
   - **Bronze offline ornament** (DESIGN_SYSTEM §7.3): 56×56, 1.2px Bronze stroke. **Same ornament as C6c** — no per-screen variants.
   - Headline: "Waiting for a connection." (Cormorant 26, weight 400, Ink, centered)
   - Body: "Great Minds needs a connection to load this. Try again when you're back online." (Lora 13, Charcoal, 1.65 line-height, centered, max-width 280px)
   - CTA "Try again" (Ink primary, centered, **min-width 140px, white-space nowrap**)
3. Tab bar (current tab active)

---

### J3 — Empty saved reflections (NEW v4)

Empty state for F1 when user has zero saved reflections. Reuse-only.

**Structure:**
1. Status bar
2. Header: eyebrow "Reflections" + title "Your saved lines."
3. **No filter pills** while `saved_lines_count = 0`
4. Empty state card (component 3.26):
   - Top ornament row: 0.5px Edge line + Bronze star/sparkle SVG (14×14) + 0.5px Edge line
   - Headline: "A space for the lines that stay with you." (Cormorant 19, weight 400, centered)
   - Body: "When a sentence settles, save it. Saved lines live here, ready when you return." (Lora 13, Charcoal, 1.6 line-height, centered)
   - 3-item instruction list: Save what resonates / Group by mind or theme / Return when you need them
5. CTA "Start a conversation" (Ink primary, full-width) — routes to D1
6. Bottom tab bar (Reflections active)

---

### J5 — Empty conversation history (NEW v4)

Empty state for F6 when user has zero past conversations. Reuse-only.

**Structure:**
1. Status bar
2. Header: eyebrow "Library" + title "Past conversations."
3. Empty state card (component 3.26):
   - Top ornament row: 0.5px Edge line + Bronze star/sparkle (14×14) + 0.5px Edge line
   - Headline: "Past conversations gather here." (Cormorant 19, weight 400, centered)
   - Body: "Every conversation you start is saved here. Return to any of them when you need to." (Lora 13, Charcoal, 1.6 line-height, centered)
   - 3-item instruction list: Saved automatically / Resume where you left off / Organized by recency
4. CTA "Explore minds" (Ink primary, full-width) — routes to D2
5. Bottom tab bar (Library active)

---

## Backlog requirements (implementation, not UI design)

### Authentication (Block 4)
- **Platform-aware provider order**: Web=Google first, iOS=Apple first, Android=Google first
- **OTP state machine**: wrong code, expired, cooldown, too many attempts (5 lockout 15min), use different email, rate limiting (5/hour)
- **OTP request rate-limit (v5):** Upstash Redis `otp_request:{email}` 5/hour enforced in `auth.py`. Separate from the 5-attempt lockout. Workaround: `+alias` = fresh bucket.
- **Disclaimer versioning**: DB schema with version field, re-prompt on copy change
- **A4 structured support payload**: pre-filled mailto with device/browser/timestamp
- **Account linking security**: only auto-link when both providers report `email_verified: true`

### Reflection & Memory (Block 5)
- **F2 lite quality guardrails**: prompt-level enforcement (see DESIGN_SYSTEM 4.6)
- **F2 lite trigger threshold**: ≥10 user messages, max 1 per conversation
- **F3/F4 weekly letter generation**: async batch Sunday job, minimum material rule, "quiet week" graceful handling
- **F1 free-tier limit**: 3 saves max, 4th attempt triggers upgrade prompt
- **F2 free-tier limit**: 1 preview lifetime, then locked

### Discovery (Block 3)
- **D2/D3 view preference**: localStorage v1, DB v2
- **daily_questions rotation (v5):** 50 phenomenology themes (display_order 1000–1049) rotate by day-of-year. Old 30 deactivated (reversible). `GET /api/v1/today/question` selects `WHERE active=true ORDER BY display_order`.

### Account, Billing & Privacy (Block 6)

See v4 spec for full Stripe integration, cancellation analytics, GDPR data rights, account deletion guard, and notification system backlog requirements. Unchanged from v4.

### General
- **Insight extraction timing**: F2 surfaces inline only after persona's last message renders (250ms fade-in)
- **Library offline read-only**: v1 feasibility check
- **Soft cap notice**: "Bring another mind" 3+ chain → backlog v2 message

---

## Implementation notes

### Sequencing for Claude Code

Unchanged from v4. See `SCREENS_TRACKING_v4.md` §Implementation notes for full ordering.

### Component reuse map

Unchanged from v4 except:
- **Rituals hub You-vs-You icon:** inline half-sphere SVG (v5) — `currentColor`, `circle` + `path` (right-semicircle). NOT a Lucide component. Reusable via inline SVG or extracted component.
- All other reuse rules unchanged from v4.

### Anti-patterns to flag in code review

All v4 anti-patterns apply. Addition for v5:
- **Using a photo PNG as app icon** — `icon.png` / `apple-icon.png` require square icon marks at appropriate dimensions. Do not copy a full-bleed photo PNG. Photo icon was tried and hotfixed in 2026-06-03 session (TD-29).

Addition for v6:
- **Hand-assembling a persona system prompt that drops the safety preamble** — append mode prompts (e.g. `REVISIT_OPENING`) AFTER `build_system(persona)`; never replace it (HANDOFF v18 §13.26).
- **Skipping the post-gen safety gate on a new generation surface** — any persona-voice generation (incl. non-stream like Reading Revisit) must run `safety_service.check_output` before persist/display (HANDOFF v18 §13.25).

---

**End of SCREENS_TRACKING v6.** Authoritative as of 2026-06-15 (Sunday Letter reader + unified Reflections feed). Supersedes `SCREENS_TRACKING_v5.md` (preserved as historical reference).
