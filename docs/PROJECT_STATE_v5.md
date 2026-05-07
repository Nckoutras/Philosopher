# PHILOSOPHER — Project State

> **What this file is:** Live snapshot of the project's current implementation status.
> Regenerated via `make state` (which calls Claude Code to read the repo and rewrite this file).
> Re-upload to Claude.ai Project Knowledge after each regeneration.
>
> **Sections marked "MANUAL — preserved across regenerations":** these are not auto-updated.
> Edit by hand for decisions, blockers, and qualitative notes.

---

**Last updated:** 2026-05-07 (Setup PR + Greenfield scaffold merged; Netlify hosting confirmed; thegreatminds.app domain registered)
**Last `make state` run:** 2026-04-29 (stale — `make state` infrastructure broken per §10 housekeeping #4)
**Current phase:** Phase 4 stabilization sequence CLOSED 2026-05-05 (8 ship items). 2026-05-06 founder decision: build all 43 specced screens before public launch. Phase 5 → P3 post-feedback. Phase 6 → P1 post-revenue. Web/PWA only for v1. Native app submission → v2. Next P0 work surface: 43-screen UI build per `SCREENS_TRACKING_v4.md` block sequence A→B→C→D→F→H→I→J. See `IMPLEMENTATION_BACKLOG_v5.md` §17 (authoritative) and `HANDOFF_BRIEF_v5.md` §17.
**Repo:** https://github.com/Nckoutras/Philosopher (public)
**Branch:** main
**Live deployment:** https://thinkalike.vercel.app

---

## 1. Stack (locked)

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router) · TypeScript · Tailwind |
| Backend | FastAPI · Python 3.12 |
| Database | PostgreSQL 16 + pgvector |
| Queue | Redis + ARQ |
| LLM | Anthropic Claude (streaming) |
| Embeddings | OpenAI text-embedding-3-small |
| Auth | Custom JWT (FastAPI-issued) — passlib + bcrypt 4.0.1 |
| Billing | Stripe (scaffolded, NOT wired) |
| Email | Resend (configured, unused) |
| Analytics | PostHog (configured, unused) |

**Hosting:**
- Frontend: Netlify (project: thinkalike)
- Backend: Render (free tier — sleeps on inactivity, mitigated by external ping bot)
- Database: Render PostgreSQL `philosopher-db` (per §12; Supabase configured but not in active use)
- Redis: Not configured on Render (non-fatal warning at startup)

---

## 2. Production status

- Live URL: https://thinkalike.vercel.app
- Last production deploy: 2026-05-05 (engine-first stabilization sequence — 8 ship items including `718a7dd`, `2bf9244`, `54a8be4`, `ae58479`)
- Has paying users: **No**
- Has free trial users: **No**
- Stripe wired: **No** (calendar-gated until 2026-05-11; see `IMPLEMENTATION_BACKLOG_v5.md` §5)
- User validation done: **No** (founder's plan: UAT mixed-group with ≥2/5 spontaneous "I'd pay" criterion before public launch, after 43-screen UI build)
- Phase 4 feature flag (`PHENOMENOLOGY_BRIDGE_ENABLED`): **verified active during 14-test session 2026-05-04/05** (modern terms confirmed not leaking, voice differentiation visible). Current state should be confirmed in Render env vars before public launch.
- Render API web service `philosopher-api`: **free tier** as of 2026-05-06. Upgrade decision pending. Free-tier limits: `WEB_CONCURRENCY=1`, 15-min idle cold-start. Mentor recommendation: upgrade now (~$7/month) to avoid friction during 43-screen UI dev cycle.
- Render PostgreSQL `philosopher-db`: **paid tier** as of 2026-05-06 (avoids 30-day free-tier auto-expiry).

---

## 3. Personas registered (`apps/api/personas/__init__.py`)

| Slug | Tier | Python config | DB `is_active` | Tested by founder | Section 5.7-compliant |
|---|---|---|---|---|---|
| marcus_aurelius | free | ✅ | ✅ | ✅ excellent | ✅ Phases 1-3; Phase 4 essence-only (shading PR Β pending) |
| socrates | free | ✅ | ✅ (fixed via direct SQL 2026-05-03) | ✅ smoke-tested 2026-05-03 | ✅ Phases 1-4 |
| carl_jung | pro | ✅ | ✅ | ✅ excellent | ✅ Phases 1-4 |
| simone_de_beauvoir | pro | ✅ | ✅ | ✅ excellent | ✅ Phases 1-4 |
| epictetus | pro | ✅ (verified Epictetus, not Jung) | ✅ (fixed via direct SQL 2026-05-03) | ⚠️ untested by founder | ✅ Phases 1-4 |
| sigmund_freud | pro | ✅ | ✅ (fixed via direct SQL 2026-05-03) | ⚠️ untested by founder | ✅ Phases 1-4 |

**Notes:**
- All 6 imported and registered in `__init__.py` as of commit `12a6e1d` (2026-04-27).
- All 6 active in production DB as of 2026-05-03 (direct SQL fix from Render Shell — `seed.py` UPDATE branch bug deferred to backlog #21).
- Phase 4 PR Α covers all 6 personas via shared `modern_phenomenology.json` map. 5/6 personas (socrates, jung, de_beauvoir, freud, epictetus) have populated shading data. Marcus has none (33 strings to be authored in PR Β); falls back to generic essence rendering.

---

## 4. PersonaConfig schema (`apps/api/personas/_base.py`)

Current dataclass fields (22 base + 8 Phase 1 optional = 30 total):

```python
@dataclass
class PersonaConfig:
    # Identity (5)
    slug: str
    name: str
    era: str
    tradition: str
    tier: str  # free | pro | premium

    # Avatar & display (2)
    tagline: str
    avatar_emoji: str

    # Voice (5)
    worldview: str
    tone: str
    sentence_structure: str
    vocabulary_register: str
    forbidden_phrases: list[str] = field(default_factory=list)

    # Behaviour (6)
    questioning_pattern: str = ""
    challenge_level: int = 3          # 1=gentle 5=relentless
    challenge_style: str = ""
    response_length: str = "medium"   # short | medium | long
    uses_personal_anecdote: bool = True
    cites_own_works: bool = True

    # Retrieval (2)
    retrieval_sources: list[str] = field(default_factory=list)
    retrieval_top_k: int = 4

    # UX (1)
    opening_invocation: str = ""

    # System prompt fragment (1)
    system_fragment: str = ""

    # Section 5.7 — Phase 1 schema extension (8 optional fields, all None by default)
    character_anchors: Optional[list[CharacterAnchor]] = None
    register_range: Optional[RegisterRange] = None
    anti_flexing: Optional[AntiFlexingRules] = None
    response_length_words: Optional[ResponseLengthSpec] = None
    forbidden_lexicon_persona_specific: Optional[ForbiddenLexicon] = None
    behavioral_parameters: Optional[BehavioralParameters] = None
    behavioral_parameters_by_register: Optional[dict[str, RegisterOverride]] = None
    safety: Optional[dict] = None

    def to_dict(self) -> dict: ...
```

**Section 5.7 fields populated for all 6 personas as of 2026-05-04** (Phase 3 closure):
- All 8 Phase 1 optional fields above

**Section 5.7 fields lifecycle (Phase 4 update):**
- `modern_phenomenology_shading` was DROPPED from `PersonaConfig` schema in Phase 1 (commit `0ade549`) — lives in shared map `apps/api/philosopher_brain/maps/modern_phenomenology.json`, not per-persona.
- New runtime per-request dataclass `PhenomenologyBridge` added to `apps/api/personas/_models.py` 2026-05-04 (Phase 4 PR Α). Not part of `PersonaConfig`; produced by `phenomenology_bridge_service.lookup()` per request.

---

## 5. System prompt template (`apps/api/prompts/system_base.jinja2`)

Existing template structure (verified, post-Phase-4):
1. Application identity + non-clinical disclaimer
2. Current date + user_name (optional)
3. PERSONA section with persona.system_fragment + tone/structure/register/challenge/questioning + forbidden phrases
4. **MODERN PHENOMENOLOGY BRIDGE** (Phase 4 PR Α — conditional on `phenomenology_bridge` argument; inner conditional for `persona_shading` to handle Marcus case)
5. WHAT YOU KNOW ABOUT THIS PERSON (memories — conditional)
6. GROUNDING PASSAGES (RAG retrieval — conditional)
7. HARD RULES (7 numbered non-negotiables)

**Section 5.7 sections still NOT in template** (Phase 5+ work):
- Character anchors structured rendering
- Anti-flexing structured rendering
- Brevity directive (numerical) — currently enforced via runtime postprocessing only
- Register directive

**Phase 4 follow-up issue tracked:** Runtime template doesn't render Phase 1-3 structured fields. Phase 3 enforcement happens via postprocessing (regenerate-or-trim) only, not via prompt-level instructions. Future Phase (3.5 or 5+) to add. Tracked in IMPLEMENTATION_BACKLOG_v4 §8.2 #26.

---

## 6. What's been built (production-verified)

Routers (`apps/api/routers/`):
- `auth.py` — register/login via custom JWT ✅
- `personas.py` — list/get with tier filtering ✅
- `conversations.py` — chat endpoint with Anthropic streaming ✅
- `memory.py` — long-term recall (UNTESTED end-to-end) ⚠️
- `billing.py` — Stripe scaffolding only, NOT wired ❌
- `rituals.py` — endpoint exists, "Begin" button broken in UI ❌
- `admin.py` — review safety events ✅

Services (`apps/api/services/`):
- `analytics_service.py` — usage/event analytics
- `conversation_service.py` — conversation orchestration (extended 2026-05-04 with Step 3.5 phenomenology bridge lookup + `PHENOMENOLOGY_BRIDGE_ENABLED` feature flag)
- `embedding_client.py` — OpenAI embedding wrapper
- `llm_client.py` — Anthropic Claude client
- `memory_service.py` — long-term memory retrieval
- `phenomenology_bridge_service.py` — **NEW 2026-05-04, Phase 4 PR Α.** Loads shared phenomenology map at startup, performs substring-match classifier with specificity resolution + slug normalization + fail-open exception handling
- `postprocessing_service.py` — Phase 2 brevity + forbidden lexicon enforcement
- `prompt_builder.py` — system prompt assembly (extended 2026-05-04 with `phenomenology_bridge` argument)
- `retrieval_service.py` — pgvector similarity search
- `safety_service.py` — 3-tier safety classification

Systems:
- pgvector similarity search ✅
- Memory feature: implemented, untested end-to-end ⚠️
- Safety system: 3-tier (high/medium/low) per README, code path unverified ⚠️
- Rate limiting per plan: code merged commit `3ba572f`, NOT browser-tested ⚠️
- Streaming SSE ✅
- Persona registry pattern ✅
- **Postprocessing pipeline (Phase 2):** active in production, smoke-tested 2026-05-03 ✅
- **Modern phenomenology bridge (Phase 4 PR Α):** infrastructure deployed 2026-05-04 evening; map expanded 33→78 entries 2026-05-05 (`54a8be4`); +88 verb-form/gerund triggers 2026-05-05 (`ae58479`); flag verified active during 14-test session 2026-05-04/05 ✅

---

## 7. Section 5.7 brain (`apps/api/philosopher_brain/`)

✅ **Directory exists in repo as of 2026-05-02 commit `3832ec4` (PR #5).**

Files and status:

| File | Status |
|---|---|
| `personas/socrates.yaml` | ✅ Present, used as Phase 3 source for PR #7 |
| `personas/nietzsche.yaml` | ✅ Present (NOT in production registry — see open questions §10) |
| `personas/freud.yaml` | ✅ Present, used as Phase 3 source for PR #9 |
| `personas/jung.yaml` | ✅ Present, used as Phase 3 source for PR #10 |
| `personas/epictetus.yaml` | ✅ Present, used as Phase 3 source for PR #8 |
| `personas/de_beauvoir.yaml` | ✅ Present, used as Phase 3 source for PR #11 |
| `personas/marcus_aurelius.yaml` | ✅ Present, authored from scratch 2026-05-03 by mentor + ChatGPT adversarial review, committed standalone as `1c67d22` then used as Phase 3 source for PR #12 |
| `prompts/master_system_prompt.md` | ✅ Present (design source — runtime uses `apps/api/prompts/system_base.jinja2`) |
| `maps/modern_phenomenology.json` | ✅ Present + extended 2026-05-04 with `triggers` schema (33 entries × 181 triggers); used by Phase 4 PR Α `phenomenology_bridge_service` |
| `maps/universal_forbidden_lexicon.json` | ✅ Present, used by Phase 2 postprocessing |
| `maps/persona_specific_forbidden.json` | ✅ Present, used as Phase 3 source for `forbidden_lexicon_persona_specific` field |
| `evals/eval_suite_spec.md` | ✅ Present (design source for Phase 6) |
| `evals/ten_modern_problems.json` | ✅ Present |

---

## 8. What's pending — priority order

> **AUTHORITATIVE source for current priorities:** `IMPLEMENTATION_BACKLOG_v5.md` §17. The summary below is a snapshot; if conflicts emerge with the backlog, backlog wins.

### P0 — 43-screen UI build (per founder decision 2026-05-06)

Order follows `SCREENS_TRACKING_v4.md` block sequence:

1. **Block A — Authentication** (5 items: A1, A2/A3, A4, A5, A6+A7)
2. **Block B — Onboarding** (6 items: B1–B6)
3. **Block C — Chat experience** (9 items: C1–C9; some partially live, verify against spec)
4. **Block D — Discovery** (3 items: D1, D2, D3)
5. **Block F — Reflection** (5 items: F1, F2, F3, F4, F6)
6. **Block H — Subscription & Billing** (7 items: H1, H2, H3, H4, H4b, H5, H6)
7. **Block I — Account & Settings** (6 items: I1, I2, I3, I4, I5, I6)
8. **Block J — Empty/error states** (4 items: J1, J2, J3, J5)

Total: 43 effective specced screens (45 line items because A2/A3 and A6/A7 are merged screens).

### P0 — Parallel & post-UI work

9. **Stripe wiring** — calendar-gated until 2026-05-11; can start in parallel once Block H exists in placeholder form
10. **Legal copy** — Terms, Privacy Policy, disclaimer (parallelizable with UI)
11. **Email infrastructure** — provider, templates, SPF/DKIM/DMARC (parallelizable)
12. **Founder runbooks** — refund, account recovery, GDPR fulfillment, cancellation override, safety escalation
13. **Production smoke test** — after UI complete, verify 8 closed Phase 4 stabilization items + 43 screens + flag state
14. **UAT mixed-group** — 3-5 testers (close + acquaintances + strangers); ≥2/5 spontaneous "I'd pay" criterion
15. **Public launch** — web/PWA only

### Reclassified post-launch (per 2026-05-06 founder decision)

- **Phase 5** (Register architecture + UI chips + classifier) → **P3 post-feedback** (data populated; runtime activation deferred until user demand signal)
- **Phase 6** (Eval suite + CI) → **P1 post-revenue** (combined with adversarial classifier coverage as safety/quality audit)
- **Phase 4 PR Β** (Marcus shading content, 33 strings) → **P3 post-launch**
- **Native app submission** (iOS App Store, Google Play) → **v2**

### P1+ — Continuity, refinements, post-launch UX, technical debt

See `IMPLEMENTATION_BACKLOG_v5.md` §13 (P1–P4 backlog).

---

## 9. MANUAL — Recent decisions (preserved across regenerations)

> Edit this section by hand. `make state` does not touch it.

- **2026-05-06** — **Documentation v5 cycle delivered.** `IMPLEMENTATION_BACKLOG_v5.md` and `HANDOFF_BRIEF_v5.md` produced as full rewrites (not patches). The v5 backlog reorganizes the v4 backlog around the 2026-05-06 reality: Phase 4 stabilization closed (8 ship items), 43-screen UI build as next P0, Phase 5 → P3 post-feedback, Phase 6 → P1 post-revenue, web/PWA only for v1. The v5 HANDOFF corrects 4 stale entries that survived in v4 (Phase 3 listed as "pending" while it was shipped via PRs #7-12; database listed as "Supabase" while production DB is Render PostgreSQL; §17 framing of "next phase: launch readiness, not engineering" was made false by 6/5 decision; missing 2026-05-06 decision log). Also adds §16.A operating discipline (8 codified principles from prior sessions) and §21 Decision History. Files to delete from project knowledge: `IMPLEMENTATION_BACKLOG_v4(1).md`, `IMPLEMENTATION_BACKLOG_v4(as in 040526).md`, `IMPLEMENTATION_BACKLOGadditional_v4.md`, optionally `HANDOFF_BRIEF_v4.md` (or keep as historical reference). New v5 backlog §13.4 P4 #10 captures Render WEB_CONCURRENCY=1 bottleneck.

- **2026-05-06** — **Render PostgreSQL upgraded to paid tier.** `philosopher-db` (Service ID `dpg-d7l5n09f9bms739s9ab0-a`) moved from free tier to paid tier. Resolves the 30-day free-tier auto-expiry risk that would have destroyed the database around mid-to-late May 2026. The Render API web service `philosopher-api` (`srv-d7ijct6gvqtc739a0pdg`) remains on free tier as of 2026-05-06; upgrade decision pending. Mentor recommendation: upgrade now (~$7/month) to avoid cold-start friction (`WEB_CONCURRENCY=1`, 15-min idle wake-up of 30-60 seconds) during 43-screen UI development cycle and to prevent first-impression damage with UAT testers.

- **2026-05-06** — **UI scope decision REVERSED. Founder elected to build all 43 specced screens before public launch.** This reverses the 2026-05-04 "critical UX subset only" compromise. All 43 screens per `SCREENS_TRACKING_v4.md` will ship before launch, in block order A→B→C→D→F→H→I→J. Phase 5 (Register architecture + UI chips + classifier) reclassified to P3 post-feedback — data is populated in YAML; runtime activation deferred until user feedback indicates demand. Phase 6 (Eval suite + CI) reclassified to P1 post-revenue safety/quality audit — combined with adversarial classifier coverage as a single post-launch audit cycle. Native app submission (iOS App Store, Google Play) deferred to v2; **v1 launch is web/PWA only**. Estimated timeline: ~12-16 weeks to first paying user (vs ~6-7 weeks under prior compromise). Mentor pushed back on time cost; founder confirmed Plan A. Trade-off alternatives (Plan B critical subset + revenue first, Plan C parallel UAT during build) preserved in `IMPLEMENTATION_BACKLOG_v5.md` §17.4 for future reconsideration if circumstances change.

- **2026-05-07** — **Setup PR (#13) + Greenfield scaffold (#14) MERGED.** Setup PR (commit `ad24d15`): 11 spec colors + Cormorant Garamond/Lora fonts wired into Tailwind + dark mode dropped (forced light) + BronzeDivider/Spinner primitives + `.glass` utility removed per spec §1.7. Greenfield scaffold (commit `474f081`): 19 legacy frontend files deleted (auth/, admin/, billing/, app/app/, components/billing|chat|persona, AppSidebar) — 2183 deletions. Replaced `apps/web/app/page.tsx` with minimal spec-aware placeholder ("Great Minds" Cormorant + BronzeDivider + Lora subtitle, Vellum bg). Backend integration glue (`apps/web/lib/`: api.ts, apiExt.ts, store.ts, useStream.tsx) and `middleware.ts` kept untouched. Hosting clarified as Netlify (`thinkalike.netlify.app`) — earlier PROJECT_STATE drafts incorrectly stated Vercel. Custom domain `thegreatminds.app` registered by founder same session; DNS + SSL setup deferred to pre-launch. Next P0: A1 splash per SCREENS_TRACKING_v4 §17.1, fresh thread.

- **2026-05-05 evening** — **Engine-first launch sequence COMPLETE: 7/7 P0 closed in single ~7h session.** 8 ship items closed (the v4 additional file phrased it as "7/7" because Bug #33 + Bug #34 shipped together on the same `fix/safety-crisis-pathway` branch). Closed items:
  - **Bug #33 + Bug #34** (safety pathway) — refactored to deterministic classifier-only path with country-neutral copy; LLM-side crisis directives removed; medium risk now suppresses persona (spec divergence noted as defensible launch fix).
  - **1.7** (`user_name` removal + hotfix `0256f97`) — missed call site at `conversation_service.py:159` produced 10-minute production crash. Lesson: grep summaries don't replace full diff trail. Discipline rule established.
  - **1.6** (Nietzsche frontend removal `c49c3cd`, Option A) — backend YAML kept for v2.
  - **1.4** (phenomenology trigger audit `ae58479`) — +88 verb-form and gerund triggers across 32 entries.
  - **2.1** (phenomenology map content expansion `54a8be4`) — 33→78 entries from mentor-reviewed adversarial submission.
  - **1.3** (truncation 3-layer fix `2bf9244`) — generation budget tweak attempt-2 multiplier 1.0→1.15, strip-time sentence-boundary trim with `hard_cut_no_sentence_boundary` fallback logging, Layer 3 observability hook `brevity_passed_but_mid_sentence`. 125→129 tests.
  - **1.5** (empty-conversation dedup + in-flight flag `718a7dd`) — backend `POST /conversations` returns existing empty conversation for `(user, persona, ritual)` tuple if `message_count == 0`; frontend `useState` in-flight flag with disabled HTML attribute and `animate-pulse` visual; defense in depth — backend dedup catches frontend race window. 129→134 tests.

  Production verified working post-each-deploy. Burnout test #4 echo no longer reproduces. Engine-first launch ready: backend stable, frontend type-safe (Vercel build verified), all critical safety paths exercised, empty-row growth bounded. New discipline rule established: full diffs required for all parameter/schema changes, no grep summaries trusted as caller audit (origin: 1.7 hotfix incident).

- **2026-05-04 evening** — **Section 5.7 Phase 4 PR Α (Modern phenomenology bridge infrastructure) SHIPPED to main.** 5 commits across 6 files: `96761fb` (new `phenomenology_bridge_service.py`, 199 lines), `ea41d2e` (`prompt_builder.py` signature extended with `phenomenology_bridge` param), `a0b54b7` (`conversation_service.py` Step 3.5 + `PHENOMENOLOGY_BRIDGE_ENABLED` feature flag default false + fail-open exception handling), `5f14ddf` (`modern_phenomenology.json` 33 entries × 181 triggers + `_models.py` `PhenomenologyBridge` frozen dataclass + `system_base.jinja2` slot inserted between PERSONA and MEMORIES), `fe23a10` (16 unit tests in `test_phenomenology_bridge.py`, all passing locally). Mid-flight pivot caught at Step 1: original 6-PR-per-persona plan was wrong because shading data already lives in shared map (not per-persona). Re-planned to 4-PR functional shape (infrastructure / classifier / Marcus shading / flag flip). Adversarial cross-model review of triggers (ChatGPT) flagged 81 distinctiveness issues; mentor accepted 71 (88%), rejected 10 with rationale. Time-box honored within ~3 days end-to-end. Feature flag default false → production untouched until smoke test + flag flip. **NOTE 2026-05-05:** flag verified active during 14-test session that surfaced bugs #30-34 leading to the engine-first stabilization sequence. Marcus shading (PR Β) deferred to P3 post-launch per 2026-05-06 v5 backlog.

- **2026-05-04 evening** — **Phase 4 follow-up issues captured in IMPLEMENTATION_BACKLOG_v4 §8.2.** Four new items added: #26 Runtime template doesn't render Phase 1-3 structured fields (P3 — discovered during INVESTIGATE; not a launch blocker since postprocessing layer catches violations); #27 Explicit priority hints for overlapping phenomenology mappings (P3 — edge case where user mentions both `burnout` and `caregiving_burden` in same message); #28 Modern-term-leak post-check (P2/P3 — defer to Phase 6 eval suite, founder approved trust-the-prompt for now); #29 Local Python env missing API dependencies (P4 — `jinja2` missing locally, blocks integration test runs; pre-existing, overlaps with #20 housekeeping). New decision principle codified in §8.5 #8: distinctiveness test for substring-matching content (triggers, classifiers, forbidden patterns) — better to miss a match than fire in wrong context.

- **2026-05-04 evening** — **Phase 4 PR Α distribution method note.** All 5 commits made via GitHub web editor (browser, not local). Local working copy required `git pull origin main` to sync afterward. Brief blocker: a 0-byte placeholder file from a failed local paste attempt blocked the pull until removed (`rm apps/api/services/phenomenology_bridge_service.py`). Lesson codified in HANDOFF_BRIEF_v4 §19.10: web editor commits are real but require explicit local sync before resuming local work.

- **2026-05-04** — **Engine-first strategy decision.** Founder pushed back on mentor's distribution-first proposal. Engine-first execution chosen: Phase 4 → 5 → 6 → critical UX subset (Block 6 H5/H6/I1 + Pricing H1) → Stripe → UAT → public launch. Founder self-identified motivation: 80% quality pride / brand standards, 20% comfort working in familiar territory. Mentor concession: legitimate when engine is differentiator, founder has demonstrated 2-3 day per phase pace, and Stripe is calendar-blocked anyway. Time-boxes set on each engine phase to prevent perfectionism creep (3-day soft cap per phase). Compromise: NOT all 43 v4 UX screens — only Block 6 billing critical screens + pricing page. UAT public launch criterion: ≥2/5 testers spontaneously say "I'd pay for this". Distribution planning workshop deferred to ~1 week before launch (~2026-06-10). Total realistic timeline: ~6-7 weeks from 2026-05-04 to first paying user. Documented in HANDOFF_BRIEF_v4 §17 + IMPLEMENTATION_BACKLOG_v4 §8.

- **2026-05-04** — **HANDOFF_BRIEF_v4 + IMPLEMENTATION_BACKLOG_v4 (engine-first revisions) delivered.** HANDOFF_BRIEF_v4 §17 substantially rewritten from distribution-first to engine-first execution. §22 starter prompt for next thread now points to Phase 4 work. IMPLEMENTATION_BACKLOG_v4 gained new §8 (Backlog & housekeeping — engine-first authoritative priority section) inserted between original §7 (Auth) and what is now §9 (GDPR). Section numbering shifted: original §8-§13 became §9-§14. §8.0 reconciliation note flags 4 outdated items in earlier sections (§6.1, §6.3, §12.5, §12.9) where current priorities have superseded original priority calls. Where §8 conflicts with prior sections, §8 wins. Original content preserved verbatim throughout — only the priority calls were superseded.

- **2026-05-04** — **Phase 3 of Section 5.7 framework SHIPPED in full.** Sub-session 3.3 (Marcus Aurelius) merged via PR #12 (commit `a7a233b`). All 6 production personas now have populated 8 Section 5.7 structured fields: character_anchors, register_range, anti_flexing, response_length_words, forbidden_lexicon_persona_specific, behavioral_parameters, behavioral_parameters_by_register, safety. Postprocessing service runtime checks active across the entire roster. The framework is content-complete enough for first paying user. Phases 4 (modern phenomenology bridge), 5 (register UI chips), 6 (eval suite) deferred per monetization-first principle in HANDOFF_BRIEF_v4 §17.

- **2026-05-04** — **Site state verified by founder.** Loads, all 6 personas visible on dashboard (post-is_active fix), navigation works with reasonable inter-screen latency, no catastrophic delays observed. Streaming chat functional. Auth flow works. Free/Pro tier filtering works. Site is "working enough" to push to first paying user once Stripe un-pauses.

- **2026-05-03** — **Marcus Aurelius brain YAML authored from scratch.** No pre-existing brain YAML for Marcus. Mentor instance authored v1.0, ChatGPT performed adversarial review, mentor accepted ~85% of feedback (rejected ~15% with rationale, e.g., schema field additions out of scope), produced v1.1, founder approved. Committed standalone to main as commit `1c67d22` before the Phase 3 PR. Pattern documented for future persona additions if needed (e.g., if Νίτσε is later added). Adversarial cross-model review codified as a future practice in HANDOFF_BRIEF_v4 §19.7.

- **2026-05-03** — **Critical hallucination event caught mid-PR-12.** First Step 2 mapping proposal from Claude Code returned values *completely unrelated* to the Marcus YAML (forbidden phrases like "you've got this" instead of "amor fati"; regex patterns for "resilience"/"mindset" instead of imperative-opening detection; rewritten anchor enforcement strings). Cause: long-session context drift; Claude Code generated plausible-sounding Marcus values from pattern memory of prior 5 PRs instead of reading the actual file. Caught by mentor cross-check. Resolution: founder cleared Claude Code conversation, started fresh session with explicit "extract verbatim, do not generate plausible alternatives" instruction. Second attempt was clean. Lessons codified in HANDOFF_BRIEF_v4 §19.6.

- **2026-05-03** — **Phase 3 Sub-session 3.2 fully shipped.** PR #8 Επίκτητος (`6c55086`), PR #9 Σιγμ. Φρόυντ (`491e06f`), PR #10 Καρλ Γιουνγκ (`d46d37b`), PR #11 Σιμόν ντε Μποβουάρ (`b213838`). Combined with PR #7 Σωκράτη (`5507b74`) from Sub-session 3.1, this brought 5 of 6 personas into the framework. Each PR followed the locked pattern: mechanical extraction from brain YAML → 8 structured fields populated → `PHASE_3_MIGRATED_PERSONAS` test set updated. Test suite remained 36/36 PASS post each merge.

- **2026-05-03** — **Three personas were inactive in production DB.** Σωκράτης, Επίκτητος, Σιγμ. Φρόυντ existed in the personas table but had `is_active=False`, hiding them from the Vercel dashboard. Root cause: the `seed.py` UPDATE branch only sets `config`/`name`/`era`/`tradition`/`tier`, NOT `is_active`. Fixed in production via direct SQL `UPDATE personas SET is_active=TRUE` run via Render Shell. Bug fix in `seed.py` deferred until post-first-payment per monetization-first principle. Tracked in IMPLEMENTATION_BACKLOG_v4 §8.2 #21.

- **2026-05-03** — **HANDOFF_BRIEF_v3 §20 deployment-gap statement was INCORRECT.** Backend has been deployed to Render at `philosopher-api-z9l9.onrender.com` for ~10 days (Service ID `srv-d7ijct6gvqtc739a0pdg`). `apps/web/.env.production` correctly points at the deployed API URL. Live database is Render PostgreSQL `philosopher-db` (Service ID `dpg-d7l5n09f9bms739s9ab0-a`), free tier — **NOT Supabase** as v3 assumed. Section §20 in HANDOFF_BRIEF_v4 has been replaced with corrected information.

- **2026-05-03** — **`POSTPROCESSING_ENABLED=true` added explicitly to Render Environment** (philosopher-api Web Service). Previously the service relied on the implicit Python default (`os.getenv("POSTPROCESSING_ENABLED", "true")`). Explicit setting prevents silent regression if the default changes in a refactor.

- **2026-05-03** — **Production smoke test of Phase 2/3 pipeline PASSED.** Verified live for socrates after PR #7 merge: normal user prompts → 1 Anthropic call, ~32-word reply, log entry `INFO postprocessing_outcome` (clean pass). Adversarial prompts → up to 4 Anthropic calls, log entry `WARNING postprocessing_exhausted`, deterministic strip applied per Decision C. **Edge case observed:** strip behavior truncates response mid-sentence visible to user (e.g., reply ending at "That is a man" without continuation). Strip is correct fallback per Decision C, but UX could be smoothed in future Phase 7+ refinement (trim to last full sentence, append graceful pivot). Tracked in IMPLEMENTATION_BACKLOG_v4 §8.2 #12.

- **2026-05-03** — **Brain YAML "supplement vs replace" decision REAFFIRMED.** Original Phase 3 plan considered brain YAML's `forbidden_lexicon_persona_specific` REPLACING the legacy Python `forbidden_phrases` field. Cross-validation showed: legacy field is enforced at PROMPT level (soft, AI instruction via Jinja template `system_base.jinja2`); new structured field is enforced at RUNTIME level (hard, regenerate-or-strip via Phase 2 service). They are layered defense, not duplicates. Decision applied uniformly across all 6 migrated personas: legacy `forbidden_phrases` stays as-is; brain YAML data goes into new `forbidden_lexicon_persona_specific` structured field. Future Phase 7+ housekeeping may consolidate generic sycophancy phrases into a new universal lexicon category, leaving persona-specific lexicons for actual persona-specific phrases.

- **2026-05-02** — **API deployment gap formally documented.** Investigation revealed `apps/web/.env.local` points at `localhost:8000` — Vercel frontend is deployed at `thinkalike.vercel.app`, but no production backend exists. All "verify in browser" tasks (rate limiting, memory, safety) blocked until API is deployed. Estimated effort 2-4 hours single session (Railway/Render + Postgres + Redis + env vars + frontend env update + smoke test). Identified as immediate revenue-blocking dependency, ahead of Stripe resumption. Documented in `HANDOFF_BRIEF_v3.md` §20. **NOTE 2026-05-03:** This statement was later proven INCORRECT — backend was already deployed to Render. See 2026-05-03 entry above.

- **2026-05-02** — **Repo migrated from OneDrive to non-OneDrive location.** Repo moved from `C:\\Users\\nkoutr\\OneDrive - OTE\\Desktop\\Philosopher` to `C:\\Projects\\Philosopher` after observing repeated OneDrive sync interference during PR #5 and #6 work (file-locking conflicts during `git checkout`, cloud-only reparse-point placeholders). OneDrive copy preserved as `Philosopher_OLD_DELETE_AFTER` for ~2-3 days as safety net before permanent delete.

- **2026-05-02** — **Stale top-level `philosopher_brain/` removed (commit `3eccc44`).** During investigation post-PR-#5, discovered the repo had two `philosopher_brain/` folders — top-level (stale, 4225 lines, missing the emoji regex fix) and `apps/api/philosopher_brain/` (canonical, with Phase 2 fixes). Top-level was strictly inferior (23/24 files byte-identical, 1 file diverged on the emoji regex). Removed via direct commit to main. Working tree clean post-cleanup.

- **2026-05-02** — **Phase 2 (Section 5.7 brevity + forbidden lexicon) COMPLETE + MERGED.** Branch `feat/section-5.7-phase-2`, squash-merged as `6e2daad` via PR #6. Buffer-then-stream architecture with feature flag (default `false`). 5 locked decisions: (A) full streaming rollback when disabled, (B) opt-in by default, (C) 3 attempts + deterministic strip, (D) safety override bypasses postprocessing (enforced via `if/elif` + tripwire test), (E) structured logging (persona_slug, attempt_count, final_action, duration_ms, hit_categories — no PII). 24 unit tests added. Bug fixed in transit: brain JSON emoji regex used JavaScript Unicode syntax, converted to Python-compatible. Wiring location corrected: spec said `routers/conversations.py`, actual correct location is inside `services/conversation_service.py` `stream_response()`. Cross-reviewed by ChatGPT in parallel — both verdicts APPROVE.

- **2026-05-02** — **Brain folder committed to repo (commit `3832ec4` via PR #5).** `philosopher_brain/` (12 files: 6 persona YAMLs + 3 maps JSONs + master_system_prompt.md + 2 evals files) committed at `apps/api/philosopher_brain/` (Option B: co-located with API service, not top-level). Doc path references in `HANDOFF_BRIEF_v2.md` and `scripts/generate_state.txt` updated to match. Brain becomes part of versioned source of truth (formerly local-only at `philosopher_brain_local`).

- **2026-05-02** — **Phase 1.5 housekeeping items 1 + 2 COMPLETE (commit `1581c76` via PR #4).** `forbidden_phrases` gap closed across 3 personas (`carl_jung`, `socrates`, `sigmund_freud`) — added `"That's valid"` phrase that was missing from these but present in others. `.gitignore` added with Python-standard ignore set (compiled artifacts, virtual environments, IDE configs). Test suite 10/10 PASS post-merge.

- **2026-05-02** — **Phase 1 schema extension COMPLETE + MERGED (commit `0ade549` via PR #2).** 8 optional fields added to `PersonaConfig` in `apps/api/personas/_base.py`, plus 7 supporting dataclasses in new `apps/api/personas/_models.py`. 4 schema corrections vs original v2 spec (discovered via cross-validation against socrates.yaml + jung.yaml + freud.yaml): `safety_overrides` flattened to `safety: Optional[dict]` (heterogeneous YAML), `behavioral_parameters_by_register` added as 8th field (sparse register overrides per persona, present in all 3 cross-validated YAMLs), `modern_phenomenology_shading` dropped (lives in shared map, not per-persona — **validated again in Phase 4 PR Α 2026-05-04**), `response_length_words` upgraded from tuple to 4-mode `ResponseLengthSpec` dataclass.

- **2026-04-28** — Verified Section 5.7 framework against existing codebase. Decision: hybrid migration (Option A) over clean rewrite. Existing `system_fragment` prose is high quality and preserves design intent; new structured fields extend rather than replace.

- **2026-04-28** — Confirmed all 6 personas Python files are correct in repo (Marcus, Socrates, De Beauvoir, Carl Jung, Epictetus, Sigmund Freud). Earlier confusion (Epictetus docx contained Jung) was an upload error, not a repo bug.

- **2026-04-28** — Stripe wiring elevated to P0 ahead of any Section 5.7 work. Rationale: revenue blocking gap is larger than quality gap. **NOTE 2026-05-04:** Engine-first strategy decision later supplanted this — see 2026-05-04 entry above.

- **2026-04-27** — Section 5.7 framework added to PHILOSOPHER spec. Persona register architecture, anti-flexing protocol, brevity discipline, modern phenomenology bridge, eval suite all defined.

- **2026-04-26** — `HANDOFF_BRIEF_v1` written. 3 personas working end-to-end. Methodology lessons documented for next Claude Code session.

---

## 10. MANUAL — Current blockers / open questions (preserved across regenerations)

> Edit this section by hand. `make state` does not touch it.

**Open questions:**
- [ ] **API web service plan upgrade** (NEW 2026-05-06) — paid (~$7/month) for production-ready performance, or stay on free tier until launch and accept cold-start friction during dev cycle? Mentor recommendation: upgrade now. DB already upgraded to paid 2026-05-06.
- [ ] User validation test: send working persona experience to 5 humans (UAT mixed-group: close + acquaintances + strangers), ≥2/5 spontaneous "I'd pay" criterion before public launch. Per `IMPLEMENTATION_BACKLOG_v5.md` §17.2 and `HANDOFF_BRIEF_v5.md` §17.4.
- [ ] Decide whether Nietzsche becomes a 7th persona, OR whether the brain YAML is permanently retired. Frontend landing display already removed via `c49c3cd` (Option A). Backend YAML retained for v2. Decision is overdue but no longer blocks launch.
- [ ] Decide pricing for launch: €9.99/mo + €119.99/yr per `IMPLEMENTATION_BACKLOG_v5.md` §5.6 baseline, or different number? **NEEDED before H1 pricing page implementation in Block H of UI build.**
- [ ] Greek source text editions: which translations are legally clear for ingestion in RAG corpus? Founder must provide. Not a launch blocker; relevant only for post-launch content depth.
- [x] **CLOSED 2026-05-07** — Frontend hosting clarified: Netlify (`thinkalike.netlify.app`), not Vercel as earlier drafts implied. Vercel project at `vercel.com/nckoutras-projects/thinkalike` is dormant/unused.
- [x] **CLOSED 2026-05-07** — Greenfield rewrite vs in-place refactor: greenfield chosen per HANDOFF_BRIEF §21 2026-05-07. Setup PR + scaffold merged.
- [ ] **DNS setup for `thegreatminds.app`** (NEW 2026-05-07) — domain registered by founder; needs DNS records pointing to Netlify + SSL activation. Founder action, ~10 min in Netlify dashboard + DNS provider. Not launch blocker; do before public launch.
- [x] **CLOSED 2026-05-06** — Phase 4 PR Β (Marcus shading) timing: deferred to **P3 post-launch** per `IMPLEMENTATION_BACKLOG_v5.md` §13.3 #4. Marcus currently fallback-renders to generic essence; user-invisible.
- [x] **CLOSED 2026-05-05** — Phase 4 production smoke test timing: 14-test session 2026-05-04/05 verified bridge active and modern terms not leaking. Bugs surfaced were addressed in engine-first stabilization sequence (8 ship items). Formal post-engine-first smoke test deferred to post-43-screen-UI-build per `IMPLEMENTATION_BACKLOG_v5.md` §2.1.A.

**Blockers:**
- **Stripe account paused** (cooldown ~10 days as of 2026-05-01). Resolves itself ~2026-05-11. Not a code blocker; calendar blocker.
- All other blockers are decision-pending, not technical.

**Phase 1.5 housekeeping list — STATUS:**

✅ **Item 1: DONE 2026-05-02** — `forbidden_phrases` gap fixed across 3 personas (carl_jung, socrates, sigmund_freud). Audit revealed broader scope than initially assumed.

✅ **Item 2: DONE 2026-05-02** — `.gitignore` created with `__pycache__/`, `*.pyc`, `.pytest_cache/`.

⏳ **Item 3: pending — needs decision.** Local test environment broken: `test_billing.py`, `test_prompts.py`, `test_safety.py` un-runnable due to missing packages (`stripe`, `jinja2`, `pydantic_settings`). Two options:
   - (A) Add `requirements-dev.txt` with these packages, document local install workflow
   - (B) Document Docker-only test workflow, accept that local PowerShell cannot run full suite
   Sub-decision: which packages should live in `requirements-dev.txt` vs main `requirements.txt`?
   **REINFORCED 2026-05-04 evening** — Phase 4 verification by Claude Code re-confirmed `jinja2` missing locally, blocking 3 integration tests for `prompt_builder.py`. Tracked in IMPLEMENTATION_BACKLOG_v4 §8.2 #29.

⏳ **Item 4: pending — needs decision.** `make state` infrastructure mismatch. Makefile's `state:` target invokes `claude` CLI (`@claude < scripts/generate_state.txt`), but founder uses VS Code extension (Claude Code for VS Code), not the standalone CLI. **Workaround in use 2026-05-04:** manual §9 entries written by mentor instance per session. **Tracked in IMPLEMENTATION_BACKLOG_v4 §8.2 #19 — defer until post-first-payment.**

⏳ **Item 5: pending.** Two unzipped `Philosopher` folders on Desktop (legacy from earlier setup). Not breaking anything, just cleanup. Delete when convenient.

**Phase 4 follow-up items (NEW 2026-05-04 evening) — tracked in IMPLEMENTATION_BACKLOG_v4 §8.2:**

⏳ **#26 Runtime template doesn't render Phase 1-3 structured fields** (P3) — discovered during INVESTIGATE; not a launch blocker.

⏳ **#27 Explicit priority hints for overlapping phenomenology mappings** (P3) — edge case in classifier; future Phase 7+.

⏳ **#28 Modern-term-leak post-check** (P2/P3) — defer to Phase 6 eval suite.

⏳ **#29 Local Python env missing API dependencies** (P4) — overlaps with housekeeping #3 above.

---

## 11. MANUAL — How to refresh this file (preserved across regenerations)

> Edit this section by hand. `make state` does not touch it.

1. From repo root: `make state`
2. Claude Code reads the repo and rewrites this file
3. Manual sections (9, 10, 11) are preserved — only auto-sections are updated
4. Review the diff: `git diff docs/PROJECT_STATE.md`
5. Commit: `git add docs/PROJECT_STATE.md && git commit -m "chore: update state"`
6. Push: `git push`
7. Re-upload to Claude.ai Project Knowledge:
   - Open Claude.ai → Philosopher Project → Project Knowledge
   - Delete old `PROJECT_STATE.md`
   - Upload `docs/PROJECT_STATE.md` (the just-regenerated one)

**Frequency:** Before opening a new technical thread on Claude.ai. 2-3 times per week is typical.

**When NOT to run `make state`:** Right before a commit (it'll create extra noise in git log). Run after the commit, then commit the state update separately.

**STATUS NOTE 2026-05-04:** `make state` infrastructure currently broken (uses `claude` CLI; founder uses VS Code extension). Manual §9 entries written by mentor instance per session as workaround. See §10 housekeeping item #4. Fix deferred until post-first-payment.

---

## 12. MANUAL — Live URLs (preserved across regenerations)

- Repo: https://github.com/Nckoutras/Philosopher
- Frontend live: https://thinkalike.netlify.app
- Frontend planned domain: https://thegreatminds.app (DNS + SSL setup pending — registered 2026-05-07)
- Backend live: https://philosopher-api-z9l9.onrender.com
- Backend health: https://philosopher-api-z9l9.onrender.com/health
- Vercel project: https://vercel.com/nckoutras-projects/thinkalike
- Render service: https://dashboard.render.com (philosopher-api, Service ID `srv-d7ijct6gvqtc739a0pdg`)
- Render PostgreSQL: `philosopher-db` (Service ID `dpg-d7l5n09f9bms739s9ab0-a`) — **production database, paid tier as of 2026-05-06**
- Supabase project: https://supabase.com/dashboard/project/plecolxlzshkfvybszgs — **NOT in active use** (configured but dormant; production DB is Render PostgreSQL above)
