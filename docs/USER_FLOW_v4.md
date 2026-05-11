# GREAT MINDS — User Flow v4

> **Purpose:** Map of how screens connect across user journeys. Used to validate navigation logic, identify missing screens, and brief implementation.
>
> **Companion documents:**
> - `DESIGN_SYSTEM_v4.md`
> - `SCREENS_TRACKING_v4.md`
> - `IMPLEMENTATION_BACKLOG_v4.md`
>
> **Last updated:** May 2026 (v4).
>
> **Changelog v1 → v2:**
> - Auth flow expanded with passwordless OTP path
> - Account linking flow added
> - Discovery flow expanded with D2/D3 view toggle
> - Reflections journey added (F1, F2 lite, F3, F4, F6)
> - Pro/Free gating clarified across all journeys
>
> **Changelog v2 → v3:**
> - Settings / account journey (Section 7) fully specified — was pending in v2
> - H5 Subscription management flow detailed across 5 states + Stripe Portal handoff
> - H6 Cancel reason flow added with analytics + 24-hour reconciliation
> - I3 Privacy & data flow detailed including active-subscription deletion guard
> - I6 Logout sheet flow added
> - Cross-cutting rules: effective entitlement vs raw Stripe status, Stripe Portal return refresh, personal data boundaries
>
> **Changelog v3 → v4:**
> - Section 8 Edge / error states fully specified for Block 9: J1 (server error), J2 (offline non-chat), J3 (empty F1), J5 (empty F6).
> - C6c offline copy updated to match offline-family lock ("Waiting for a connection.").
> - **J4 dropped** from scope — no surface to live in.
> - **K1/K2 deferred v2** explicitly — email-only notifications in v1.
> - Section 10 Forbidden navigation: added Rust-on-server-error rule, per-tab offline variant prohibition, auto-retry prohibition on J1, "Available offline" without cache prohibition.

---

## 1. First-time user journey

```
[App launch]
    ↓
A1 Splash (briefly, while auth check)
    ↓
[No session detected]
    ↓
A2/A3 Sign up + sign in (single screen)
    ├── Tap Apple → OAuth flow → returns
    │       ├── Verified email → auto-link or create account → A6+A7
    │       └── Unverified email → OTP path (rare for Apple)
    │
    ├── Tap Google → OAuth flow → returns
    │       ├── Verified email → auto-link or create account → A6+A7
    │       └── Unverified email → OTP path (rare for Google)
    │
    └── Tap Continue with email → A5 OTP screen
            ↓
        [User enters 6-digit code]
            ├── Correct → A6+A7
            ├── Wrong → inline error, retry
            ├── Expired → modal "Send new code"
            ├── Too many attempts → A4 (trouble accessing)
            │
            └── [Trouble accessing email link tapped]
                    ↓
                A4 Recovery screen
                    ├── Try different sign-in method → back to A2/A3
                    └── Contact support → mailto with structured payload
    ↓
A6+A7 Combined disclaimer (one-time, both checkboxes required)
    ↓
B1 Welcome (Mind of the day shown)
    ↓
[User taps "Begin"]                    [User taps "Explore Minds"]
    ↓                                       ↓
B2 What brings you here?                D2 Explore Minds (carousel)
    ↓ (user selects themes)                 ↓
B3 What do you need most?               [User taps a persona card]
    ↓ (user selects need)                   ↓
B4 Best matches (3 ranked cards)        B5 Persona detail (or B6 if Pro-locked)
    ↓ (user taps a card)                    ↓
B5 Persona detail                       [Tap "Start conversation"]
    ↓ (user taps "Start conversation")      ↓
C2 Chat loading                         C2 Chat loading
    ↓ (1-2s)                                ↓
C8 First persona greeting               C8 First persona greeting
    ↓                                       ↓
[User writes first message]             [Same]
    ↓
C1 Chat live conversation
```

**Branching:**
- B1 → "Explore Minds" route bypasses onboarding flow. User gets generic experience.
- B6 (locked persona detail) shown if user explores Pro persona before subscribing. CTA "Unlock with Pro" → H1 Upgrade.
- A6+A7 only shown once. Subsequent sign-ins skip directly to D1 Home.
- If disclaimer version bumps in production, existing users re-prompted on next session.

---

## 2. Returning user journey

```
[App launch]
    ↓
A1 Splash (auth check)
    ↓
[Session valid]
    ↓
[Disclaimer version current?]
    ├── Yes → D1 Home / Today
    └── No → A6+A7 (re-acceptance for new version) → D1 Home
```

From D1, the user has 5 primary paths:

```
D1 Home
    ├── [Tap "Reflect" on Today's question]
    │       ↓
    │   C1 Chat with default/preferred persona
    │       (user message = answer to today's question)
    │
    ├── [Tap Continue card]
    │       ↓
    │   C1 Chat (resumes last conversation)
    │
    ├── [Tap recent insight quote]
    │       ↓
    │   F1 Saved reflections (with this insight focused)
    │
    ├── [Tap Weekly letter card] (Pro only)
    │       ↓
    │   F4 Weekly letter detail
    │
    ├── [Tap "Ask another mind"]
    │       ↓
    │   D2 Explore Minds
    │
    └── [Tap a tab in bottom bar]
            ├── Today (already here)
            ├── Library → D2 (or D3 if user's preference)
            ├── Reflections → F1 Saved (default sub-view) + F3 Letters
            └── Account → I1 Profile (Block 6, pending)
```

---

## 3. Chat journey (primary product loop)

```
[User in chat with persona]
    ↓
C1 Chat live
    ├── [User sends message — success path]
    │       ↓
    │   Persona streams response
    │       ↓
    │   Quick actions appear (Ask harder / Bring another mind / Save line)
    │       ↓
    │   ├── [User taps Save line]
    │   │       ↓
    │   │   ├── Free user, <3 saves → C3 Save confirmation
    │   │   ├── Free user, 3 saves used → upgrade prompt inline
    │   │   └── Pro user → C3 Save confirmation
    │   │
    │   └── [Conversation reaches ≥10 user messages]
    │           ↓
    │       Suggested insight card surfaces inline (F2 lite)
    │           ├── [Keep] → flows to F1 with insight tag
    │           ├── [Dismiss] → permanent dismiss
    │           ├── Free user: 1 preview lifetime
    │           └── Pro user: every qualifying conversation
    │
    ├── [User sends message — fails]
    │       ↓
    │   C4 Failed message + retry
    │       ↓ (tap retry)
    │   Returns to C1 success path
    │
    ├── [User sends message — daily limit reached, free tier]
    │       ↓
    │   C5 Daily limit (input bar replaced with upgrade CTA)
    │       ↓ (tap "Continue with Pro")
    │   H1 Upgrade
    │       ↓ (tap "Later")
    │   Returns to chat (input bar disabled until tomorrow)
    │
    ├── [Network drops mid-conversation]
    │       ↓
    │   C6a Slow → C6b Offline (banner appears)
    │       ↓ (user can write, messages queue)
    │   [Connection returns]
    │       ↓
    │   Queued messages auto-send, banner dismisses
    │
    ├── [User sends crisis-flagged message]
    │       ↓
    │   C7 Safety mode (persona suppressed, app voice + resources)
    │       ↓ (user writes again)
    │   [Re-classified]
    │   ├── Safe → persona resumes
    │   └── Still flagged → C7 again
    │
    └── [User taps "Bring another mind"]
            ↓
        ├── Free user → H1 Upgrade
        └── Pro user → C9a Bottom sheet picker
                ↓ (user selects another persona)
            C9b Inline second opinion appears
                ↓
            "Continuing with [original persona]" divider
                ↓
            Chat resumes with original persona on next user message
```

---

## 4. Subscription journey

```
[Free user encounters paywall — multiple entry points]
    ↓
H1 Upgrade screen
    ├── [Tap "Continue with Pro"]
    │       ↓
    │   H2 Loading bridge (1-2s)
    │       ↓
    │   [Redirect to Stripe Checkout — external]
    │       ↓
    │   [User completes payment]
    │       ↓
    │   ├── Success → H3 Payment success
    │   │       ↓ (tap "Begin where you left off")
    │   │       Returns to original context (Persona Detail / Limit Reached / Home / F1 / etc.)
    │   │
    │   ├── Failed → H4 Payment failed
    │   │       ↓ (tap "Try again")
    │   │       Returns to H2 → Stripe again
    │   │       ↓ (tap "Go back")
    │   │       Returns to H1 Upgrade
    │   │
    │   └── Canceled → H4b Payment canceled (gentle)
    │           ↓ (tap "Return to Great Minds")
    │           Returns to original context
    │           ↓ (tap "Try again")
    │           Returns to H1 → H2 → Stripe again
    │
    └── [Tap "Maybe later"]
            ↓
        Returns to original context
```

**Paywall entry points (v2 expanded):**
- B6 Persona detail (locked) → "Unlock with Pro" tap
- C5 Daily limit reached → "Continue with Pro" tap
- C9a "Bring another mind" picker (free user) → auto-redirected to H1
- F1 Saved reflections (4th save attempt for free user) → upgrade prompt
- F3 Weekly letters (free user opening Reflections > Letters) → upgrade prompt
- F2 lite (free user 2nd qualifying conversation) → no insight shown, soft Pro hint
- D1 Home (future: explicit "Upgrade" link in Account)
- I1 Profile / account (manage subscription state, Block 6)

**Post-payment:** User returns to context where they encountered the paywall. State preservation via Stripe redirect URL params.

---

## 5. Discovery journey (browsing minds outside onboarding)

```
[User wants to explore personas without conversation context]
    ↓
Entry points:
  - D1 Home → "Ask another mind" button
  - D1 Home → bottom tab "Library"
  - B1 Welcome → "Explore Minds" button
  - B4 Best matches → "See all minds" button
    ↓
D2 Explore Minds — list/carousel view (default for new users)
    OR
D3 Explore Minds — grid view (if user previously chose grid)
    ↓
[View toggle in sub-header — soft fade 200ms transition]
    ├── List icon → D2
    └── Grid icon → D3

    ↓ (user taps a persona card)
    ↓
    ├── Free persona → B5 Persona detail (unlocked)
    └── Pro persona → B6 Persona detail (locked)
            ↓
        ├── Free user taps "Unlock with Pro" → H1 Upgrade
        └── Pro user taps "Start conversation" → C2 → C8 → C1
```

**View preference persistence:**
- v1: localStorage
- v2: synced to user account in DB

---

## 6. Reflection / memory journey

### 6.1 Saved reflections (F1)

```
[User wants to revisit past insights]
    ↓
Entry points:
  - D1 Home → "Recent insight" card → F1 (with this insight focused)
  - D1 Home → bottom tab "Reflections" → F1 (default sub-view)
  - C3 Save line confirmation toast (no direct nav, but visible)
  - F4 Weekly letter detail → "Saved a sentence" link → F1
    ↓
F1 Saved reflections / lines archive
    ├── [Filter by All / By mind / By theme]
    │       ↓
    │   Filtered list with date groupers
    │
    └── [Tap a saved card]
            ↓
        Returns to source conversation in C1
        (saved message highlighted/focused)
            ↓
        ├── [User can continue conversation from there]
        ├── [User can save more lines from this conversation]
        └── [User can "Bring another mind" if Pro]
```

**Free/Pro states:**
- Free user with 0-3 saves: full F1 access, can save up to 3
- Free user attempting 4th save: inline "You've reached your free reflections (3 of 3). Upgrade to Pro to keep saving." + Continue with Pro CTA
- Free user F1 list bottom: "Upgrade to keep saving lines that matter" card
- Pro user: unlimited saves

### 6.2 Suggested insights (F2 lite, in-chat)

```
[User in conversation with persona]
    ↓
[Conversation reaches ≥10 user messages]
    ↓
[Backend evaluates: clear pattern across ≥3 user messages?]
    ├── No → no insight surfaces, conversation continues normally
    └── Yes → Suggested insight card appears inline at end of chat (F2 lite)
            ├── [User taps "Keep"]
            │       ↓
            │   Insight saved to F1 with insight tag
            │       ↓
            │   Chat continues
            │
            └── [User taps "Dismiss"]
                    ↓
                Insight permanent dismiss for that conversation
                    ↓
                Chat continues
```

**Free/Pro gating:**
- Free user: 1 insight preview shown lifetime, then no future insights surface
- Pro user: 1 insight max per qualifying conversation, every conversation eligible

### 6.3 Weekly letters (F3, F4)

```
[Sunday async batch generation runs for all Pro users]
    ↓
[For each user: evaluate weekly material]
    ├── Insufficient material → "Quiet week" letter card created
    └── Sufficient material → Full letter generated (150-250 words)
    ↓
[User opens Reflections tab, sub-view "Letters"]
    ↓
F3 Weekly letter inbox
    ├── Unread letter (Linen bg + Bronze dot)
    │       ↓ (tap)
    │   F4 Weekly letter detail
    │       ├── Reads full letter
    │       ├── [Tap suggested next mind card] → B5/B6 Persona detail
    │       ├── [Tap download icon] → "Coming soon" toast (v1)
    │       └── [Back] → returns to F3 (now marked read)
    │
    ├── Read letter (Paper bg + Edge border)
    │       ↓ (tap)
    │   F4 Weekly letter detail (re-read)
    │
    └── Quiet week letter (dashed border)
            ↓ (no tap action — informational only)
            "Not enough reflection this week. Your next one arrives Sunday."
```

**Free user**: F3 entry → upgrade prompt instead of inbox content. F4 inaccessible.

### 6.4 Reflection history (F6)

```
[User wants to revisit past conversations]
    ↓
Entry points:
  - D1 Home → "Continue" card → C1 (specific recent conversation)
  - D1 Home → bottom tab "Library" → F6 (or D2/D3 first depending on Library default)
    ↓
F6 Reflection history (UI label: "Past conversations")
    ↓
[Date-grouped chronological list]
    ↓
[User taps a conversation card]
    ↓
C1 Chat (returns to that conversation, scrolled to last message)
    ↓
[User can continue conversation from where it left off]
```

**Available to both Free + Pro users.** Basic infrastructure, not Pro-gated.

---

## 7. Settings / account journey (Block 6, locked)

```
D1 Home → bottom tab "Account"
    ↓
I1 Account hub
    ├── [Profile area] avatar + name + email (display only, no edit in v1)
    │
    ├── Subscription section
    │       ↓ tap "Plan" row
    │   H5 Subscription management
    │       │
    │       ├── Free state
    │       │       └── tap "Upgrade to Pro"
    │       │               ↓
    │       │           H1 Upgrade screen → H2/H3/H4/H4b checkout flow
    │       │
    │       ├── Pro active state
    │       │       ├── tap "Manage Pro subscription"
    │       │       │       ↓
    │       │       │   Stripe Customer Portal (external)
    │       │       │       ↓ on return
    │       │       │   H5 refetches subscription state, re-renders
    │       │       │
    │       │       └── tap "Cancel Pro" (text link, only when H6 implemented)
    │       │               ↓
    │       │           H6 Cancel reason sheet (bottom sheet over H5)
    │       │               ├── Select reason (single-select)
    │       │               │       ├── "I had a technical issue" → reveals helper
    │       │               │       │       ├── "Contact support" → I4 Report a problem mailto
    │       │               │       │       └── "Continue to Stripe to cancel" → continues normally
    │       │               │       ├── "Other" → reveals optional textarea (max 300 chars)
    │       │               │       └── Other reasons: no inline reveal
    │       │               │
    │       │               ├── "Keep Pro" → log retention.kept_pro, close sheet
    │       │               │
    │       │               ├── Backdrop tap / Drag down / Esc / Android back
    │       │               │       → log retention.dismissed_without_cancel, close sheet
    │       │               │
    │       │               └── "Continue to Stripe to cancel"
    │       │                       ├── CTA enters loading state, prevents duplicate
    │       │                       ├── Save cancel_intent (status sent_to_stripe, expires_at +24h)
    │       │                       │       │ (if save fails, do NOT block; queue retry)
    │       │                       └── Open Stripe Customer Portal (external)
    │       │                               ↓ on return
    │       │                           H5 refetches subscription state
    │       │                               ↓
    │       │                           Renders Canceling state if cancel_at_period_end=true
    │       │                           Renders Pro active if no change
    │       │                               ↓ (24h reconciliation)
    │       │                           Outcome: canceled_confirmed | not_canceled_after_24h |
    │       │                                    superseded | unknown
    │       │
    │       ├── Past due state
    │       │       └── tap "Update payment method" → Stripe Portal
    │       │
    │       ├── Canceling state
    │       │       └── tap "Manage Pro subscription" → Stripe Portal (resume happens there)
    │       │
    │       └── Canceled / no-access state
    │               └── tap "Upgrade to Pro" → H1
    │
    ├── Preferences section
    │       ↓ tap "Notifications"
    │   I2 Notifications
    │       ├── Free user: Weekly letters row shows Pro pill (no toggle)
    │       │       └── tap row → H1 Upgrade
    │       └── Pro user: 3 toggles (Weekly letters / Reflection reminders / Product updates)
    │
    ├── Data & support section
    │       │
    │       ├── tap "Privacy & data"
    │       │       ↓
    │       │   I3 Privacy & data
    │       │       ├── tap "Request my data"
    │       │       │       ↓ (if no pending request)
    │       │       │   Confirmation sheet: "Send within 30 days"
    │       │       │       ↓ confirm
    │       │       │   Create data_requests row (type=export, status=requested)
    │       │       │       ↓ (if pending request exists)
    │       │       │   "Request already in progress" sheet — no duplicate created
    │       │       │
    │       │       └── tap "Delete my account"
    │       │               ├── (active Pro subscription exists)
    │       │               │       ↓
    │       │               │   Sheet A: "Cancel Pro before deleting"
    │       │               │       ├── "Manage Pro subscription" → H5 / Stripe Portal
    │       │               │       └── "Close" → dismiss
    │       │               │
    │       │               └── (no active subscription)
    │       │                       ↓
    │       │                   Sheet B: "Delete your account?"
    │       │                       ├── Type "DELETE" (case-sensitive, trim spaces)
    │       │                       ├── "Cancel" (top button) → dismiss
    │       │                       └── "Delete account" (bottom, Rust outlined, disabled until valid)
    │       │                               ↓
    │       │                           Cascade deletion → route to A2/A3
    │       │
    │       ├── tap "Help & support"
    │       │       ↓
    │       │   I4 Help & support
    │       │       ├── tap "Contact support" → mailto with diagnostic block
    │       │       │       (subject: "Great Minds support · General inquiry")
    │       │       └── tap "Report a problem" → mailto with diagnostic block
    │       │               (subject: "Great Minds support · Bug report")
    │       │
    │       └── tap "About & legal"
    │               ↓
    │           I5 About & legal
    │               ├── tap "About Great Minds" → in-app bottom sheet (brand copy)
    │               ├── tap "Terms of use" → external browser
    │               ├── tap "Privacy policy" → external browser
    │               └── tap "Disclaimer" → in-app sheet/modal (read-only)
    │
    └── Sign out card
            ↓ tap "Sign out"
        I6 Logout sheet (bottom sheet over I1)
            ├── "Cancel" / Backdrop / Drag-down / Esc / Android back
            │       → dismiss sheet, no state change
            └── "Sign out"
                    ↓
                Clear auth session, clear user-specific cached data,
                keep device-level preferences only
                    ↓
                A2/A3 sign-in screen
```

**Critical flow rules (Block 6):**

1. **H5 displays effective app entitlement, never raw Stripe status.** State resolution always reads authoritative source.

2. **After return from Stripe Portal, H5 must refetch subscription state before render.** Never derive billing state from H6 intent or local UI events.

3. **`cancel_at_period_end = true` renders Canceling, not Canceled.** User retains full Pro entitlement until period end.

4. **Account deletion blocked while active Pro subscription exists.** Backend enforces; UI shows Sheet A (active subscription guard) routing user to Stripe Portal first.

5. **Cancel Pro visible only on Pro active state.** Hidden on canceling, past due, free, canceled states.

6. **Cancellation analytics: Great Minds captures reason; Stripe executes cancellation.** App never claims to have canceled; copy reflects technical reality ("Continue to Stripe to cancel").

7. **Personal data boundaries:** `cancellation_reasons.free_text` and all I3-related data flagged personal; included in export, deleted on account deletion, never raw in analytics dashboards.

---

## 8. Edge / error states

### Network completely down on cold start (chat)
```
[User opens app, no connection]
    ↓
A1 Splash → fallback
    ↓
C6c Cold start offline (Bronze offline ornament)
    Headline: "Waiting for a connection." (locked v4 offline-family)
    Body: "Great Minds needs a connection to start new conversations.
           Your saved reflections remain available below."
    ↓ (tap "Try again")
    ↓
[Retry connection]
    ├── Success → D1 Home
    └── Fail → stays at C6c
        ↓ (user can browse saved reflections via tab if technically feasible v1)
        F1 Saved reflections (read-only mode)
```

### Network down on a non-chat tab (J2, NEW v4)
```
[User on D1 / D2-D3 / F1 / F3 / F6 / I1 — connection drops mid-session OR fails on tab load]
    ↓
J2 App-wide offline (full-screen replacement, Bronze offline ornament)
    Status bar: signal/wifi icons dimmed (0.35 opacity)
    Tab bar: visible with current tab still active
    Headline: "Waiting for a connection." (same as C6c — offline-family locked)
    Body: "Great Minds needs a connection to load this. Try again when you're back online."
    ↓
    ├── [Tap "Try again"]
    │       ↓
    │   ├── Success → renders normal tab content
    │   └── Fail → re-renders J2 (no escalation)
    │
    └── [Tap a different tab in tab bar]
            ↓
        Re-renders J2 with newly selected tab active
        (every tab hits network → all fail until connection restored)
```

**No "contact support" link on J2** — offline is the user's network, not our infra. Support cannot help.

**No per-tab copy variants in v1.** Single unified offline state across all non-chat tabs.

**No "Available offline" / cached-content card** unless cache is actually implemented.

### App-wide 5xx server errors (J1, NEW v4)
```
[Backend down or 5xx response on tab load]
    ↓
J1 App-wide server error (full-screen replacement, Sepia concentric circles ornament)
    Status bar: signal/wifi icons FULL opacity (distinguishes from J2)
    Tab bar: visible with current tab still active
    Headline: "Something on our end."
    Body: "Something didn't load. Try again in a moment."
    ↓
    ├── [Tap "Try again"]
    │       ↓
    │   ├── Success → renders normal tab content
    │   └── Fail → re-renders J1 (no auto-retry, no escalation)
    │
    ├── [Tap a different tab in tab bar]
    │       ↓
    │   Re-renders J1 with newly selected tab active
    │   (5xx is shell-wide → every tab fails until backend recovers)
    │
    └── [Tap "contact support" tertiary link]
            ↓
        I4 mailto flow with diagnostic block
        Subject auto-set: "Great Minds support · App couldn't load"
```

**Sepia ornament (not Rust)**: Server 5xx is "our problem", not user-actionable. Calm tone, not alarm. Rust is reserved for actionable user-side errors (failed messages, payment failures) per DESIGN_SYSTEM §1.2.

**Visual distinction from J2**: J2 uses Bronze offline ornament + dimmed status icons. J1 uses Sepia concentric circles + full-opacity status icons. A user retrying J2 who lands on J1 must see immediately that the cause shifted.

**No auto-retry.** Retry must be user-initiated. Auto-retry hides systemic problems and burns server resources during incidents.

### Empty saved reflections (J3, NEW v4)
```
[User taps Reflections tab → F1]
    ↓
[saved_lines_count = 0]
    ↓
J3 Empty saved reflections (in-tab body replacement, NOT full-screen)
    Header preserved: REFLECTIONS / Your saved lines.
    Filter pills hidden (no filterable content)
    No upgrade card / no Pro pill (premature monetization friction)
    Empty state card (3.26): Bronze star + headline + body + 3-item list
    CTA "Start a conversation" → D1 Today / Home
    ↓
[User has first save event from any conversation]
    ↓
saved_lines_count = 1 → J3 disappears, F1 renders populated state with filter pills shown
```

### Empty conversation history (J5, NEW v4)
```
[User taps Library tab → navigates to F6 sub-section]
    ↓
[conversation_count = 0]
    ↓
J5 Empty conversation history (in-tab body replacement, NOT full-screen)
    Header preserved: LIBRARY / Past conversations.
    No filter pills exist on F6 in v1
    Empty state card (3.26): Bronze star + headline + body + 3-item list
    CTA "Explore minds" → D2 Explore Minds (tab-aware: stays in Library)
    ↓
[User completes any conversation]
    ↓
conversation_count = 1 → J5 disappears, F6 renders populated state
```

### Auth expired during session
```
[User active, session expires]
    ↓
[Next action triggers 401]
    ↓
Modal banner: "Please sign in again"
    ↓
A2/A3 Sign in (existing email pre-populated if known)
    ↓
Returns to where user was (state preservation)
```

### OTP edge cases (within A5)
```
A5 OTP entry
    ├── Wrong code (1-4 attempts) → inline error, retry
    ├── Wrong code (5 attempts) → lockout 15min → A4
    ├── Expired code (>10min) → modal "Send new code"
    ├── Resend cooldown active → resend link disabled with countdown
    ├── Backend rate limit (>5 OTP req/hour) → "Too many requests, try again in an hour"
    └── User wants different email → back chevron → A2/A3 with field cleared
```

---

## 9. Critical state preservation requirements

These must be tracked across the user journey to avoid breaking flow:

1. **Original paywall context** — when user enters H1 from Limit Reached or F1 4th-save attempt, completing payment must return to that context, not to Home
2. **Conversation persona** — when user returns from another section to a conversation, header and persona thread must restore exactly
3. **Onboarding selections** — themes (B2) and need (B3) must persist into matching algorithm
4. **Bottom tab active state** — must reflect actual user location, not always "Today"
5. **Bring another mind chain** — original persona context preserved even when other personas contribute
6. **Safety mode flag** — once triggered, classifier sensitivity may be elevated for remainder of session
7. **D2/D3 view preference** — localStorage v1, DB v2
8. **Disclaimer version acceptance** — re-prompt on version bump
9. **Saved insight tag** — F1 entries from F2 lite Keep action must show "insight" tag
10. **Free-tier save count** — track count, surface upgrade prompt on 4th attempt
11. **Free-tier insight preview used** — lifetime flag, only 1 preview shown ever for free users
12. **Last conversation per persona** — C9b "Continuing with [persona]" requires knowing which persona owns the conversation thread
13. **OTP attempt count** — server-side, 5 wrong = lockout 15min
14. **Auth provider linked accounts** — DB record of all providers verified for a user
15. **Subscription state cache** — H5 must refetch on return from Stripe Portal; never trust cached state across portal navigation
16. **Active cancel_intent** — duplicate prevention requires tracking active intent within 24h window (status `sent_to_stripe`)
17. **Pending data_request status** — I3 row state derived from DB; no duplicate requests created while one is in-flight
18. **Notification toggle preferences** — per-user DB persistence; defaults applied on first sign-in (Pro: weekly letters ON; all others OFF)

---

## 10. Forbidden navigation patterns

- **Modal stacking** (modal opens another modal). All flows are inline or full-screen replacement.
- **Back button ambiguity.** Every screen with a back chevron must have one canonical "back" destination. No history-based "where did I come from?" guessing.
- **Forced linear onboarding skips.** User must always have escape hatch (Skip / "Explore Minds" alternative) — onboarding is preferred but not required.
- **Hidden Pro features.** Free user must SEE the locked persona's value (B6) before being asked to pay. We never hide Pro content; we make Pro the only path to engage with it.
- **Auto-charge after trial.** No trial mechanic. Money-back guarantee instead.
- **Notification permission prompt on first launch.** K1 push permission asked only after user demonstrates engagement (e.g., after 3 conversations OR after first saved insight).
- **Account creation without disclaimer.** A6+A7 is gating step before B1 Welcome.
- **OTP without rate limiting.** Server must enforce 5/hour limit and lockout on wrong attempts.
- **Account linking without verified email.** Never link based on string match alone — provider must report `email_verified: true` OR user must verify via OTP.
- **Suggested insight without quality guardrails.** F2 lite must enforce specificity, no diagnosis, no mysticism.
- **Weekly letter from thin material.** F3/F4 must show "quiet week" graceful state instead of generating weak content.
- **Account deletion without subscription guard.** Backend must block deletion when active Pro subscription exists; UI route user to Stripe Portal first.
- **Rendering billing state from H6 intent.** H5 must always read effective entitlement; intent is analytics, not state.
- **Cancel Pro on non-Pro-active states.** Hidden on canceling, past due, free, canceled.
- **Hardcoded support email.** Use `SUPPORT_EMAIL` from config/env; never hardcode in UI logic.
- **Push notification toggles when push not implemented.** Email-only in v1; no fake toggles.
- **Logout that doesn't clear sensitive cached data.** I6 must clear all user-specific cached data, keeping only device-level non-identifying preferences.
- **Custom in-app cancellation execution.** Stripe Portal executes cancellation. App captures intent + reason only.
- **Type-DELETE validation that's case-insensitive** or doesn't trim whitespace.
- **Rust on app-wide server-side errors (J1).** Server 5xx uses Sepia concentric circles family (calm pause), not Rust. Rust is reserved for actionable user-side errors and destructive actions per DESIGN_SYSTEM §1.2.
- **Auto-retry on J1.** Retry must be user-initiated. Auto-retry hides systemic problems and burns server resources during incidents.
- **Per-tab offline copy variants (J2).** Single unified offline state across Today / Library / Reflections / Account in v1. No tab-specific copy.
- **"Available offline" promise on J2 without offline cache implemented.** Do not show this card unless cache is actually working.
- **Showing filter pills on empty F1 (J3).** Filter pills hidden while `saved_lines_count = 0`. Render automatically when count >= 1.
- **Showing upgrade messaging on empty F1 (J3).** Upgrade prompt appears only on 4th save attempt or populated F1 limit context. Never on empty state.
- **Different ornaments for offline-family screens (C6c vs J2).** Same Bronze offline ornament across both — no per-screen variants.
- **Different ornaments for calm-pause-family screens (H4b vs J1).** Same Sepia concentric circles across both.
- **"Try again" CTA wrapping to two lines.** Button must have `min-width: 140px; white-space: nowrap;` across J1, J2, C6c.
- **Adding J4 / push notification surfaces (K1, K2) in v1.** J4 dropped (no surface). K1/K2 deferred v2 (email-only in v1).

---

**End of USER_FLOW_v4.**