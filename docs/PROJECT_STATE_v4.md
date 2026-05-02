# PHILOSOPHER — Project State

> **What this file is:** Live snapshot of the project's current implementation status.
> Regenerated via `make state` (which calls Claude Code to read the repo and rewrite this file).
> Re-upload to Claude.ai Project Knowledge after each regeneration.
>
> **Sections marked "MANUAL — preserved across regenerations":** these are not auto-updated.
> Edit by hand for decisions, blockers, and qualitative notes.

---

**Last updated:** 2026-04-29
**Last `make state` run:** 2026-04-29
**Current phase:** Pre-Phase 1 (Section 5.7 framework defined, migration not started)
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
- Frontend: Vercel (project: thinkalike)
- Backend: Render (free tier — sleeps on inactivity, mitigated by external ping bot)
- Database: Supabase (eu-west-1, project_ref: plecolxlzshkfvybszgs)
- Redis: Not configured on Render (non-fatal warning at startup)

---

## 2. Production status

- Live URL: https://thinkalike.vercel.app
- Last production deploy: 2026-04-29 (commit `03242de`)
- Has paying users: **No**
- Has free trial users: **No**
- Stripe wired: **No** (P0 blocker — see PROJECT_STATE Section 8)
- User validation done: **No** (founder's plan: 5-person test with 3 working personas before Stripe wiring)

---

## 3. Personas registered (`apps/api/personas/__init__.py`)

| Slug | Tier | Python config | DB `is_active` | Tested by founder | Section 5.7-compliant |
|---|---|---|---|---|---|
| marcus_aurelius | free | ✅ | ✅ | ✅ excellent | ❌ pending |
| socrates | free | ✅ | ❌ awaiting deploy verification | ❌ untested | ❌ pending |
| carl_jung | pro | ✅ | ✅ | ✅ excellent | ❌ pending |
| simone_de_beauvoir | pro | ✅ | ✅ | ✅ excellent | ❌ pending |
| epictetus | pro | ✅ (verified Epictetus, not Jung) | ❌ awaiting deploy verification | ❌ untested | ❌ pending |
| sigmund_freud | pro | ✅ | ❌ awaiting deploy verification | ❌ untested | ❌ pending |

**Notes:**
- All 6 imported and registered in `__init__.py` as of commit `12a6e1d` (2026-04-27).
- 3 newer personas (socrates, epictetus, sigmund_freud) need DB activation:
  ```sql
  UPDATE public.personas
  SET is_active = true
  WHERE slug IN ('socrates', 'epictetus', 'sigmund_freud');
  ```

**Mid-2026-04-28 verification needed:** Confirm the 3 newer personas activate on production. Confirm voice differentiation against the same prompt across all 6.

---

## 4. PersonaConfig schema (`apps/api/personas/_base.py`)

Current dataclass fields (22 total):

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

    def to_dict(self) -> dict: ...
```

**Section 5.7 fields NOT yet in schema** (added in Phase 1):
- `character_anchors`
- `register_range`
- `anti_flexing`
- `response_length_words` (numerical band, distinct from `response_length` string)
- `persona_specific_forbidden`
- `modern_phenomenology_shading`
- `behavioral_parameters`
- `safety_overrides`

---

## 5. System prompt template (`apps/api/prompts/system_base.jinja2`)

Existing template structure (verified):
1. Application identity + non-clinical disclaimer
2. Current date + user_name (optional)
3. PERSONA section with persona.system_fragment + tone/structure/register/challenge/questioning + forbidden phrases
4. WHAT YOU KNOW ABOUT THIS PERSON (memories — conditional)
5. GROUNDING PASSAGES (RAG retrieval — conditional)
6. HARD RULES (7 numbered non-negotiables)

**Section 5.7 sections NOT yet in template** (added in Phase 3-5):
- Character anchors structured rendering
- Anti-flexing structured rendering
- Brevity directive (numerical)
- Register directive
- Modern phenomenology bridge

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
- `conversation_service.py` — conversation orchestration
- `embedding_client.py` — OpenAI embedding wrapper
- `llm_client.py` — Anthropic Claude client
- `memory_service.py` — long-term memory retrieval
- `prompt_builder.py` — system prompt assembly
- `retrieval_service.py` — pgvector similarity search
- `safety_service.py` — 3-tier safety classification

Systems:
- pgvector similarity search ✅
- Memory feature: implemented, untested end-to-end ⚠️
- Safety system: 3-tier (high/medium/low) per README, code path unverified ⚠️
- Rate limiting per plan: code merged commit `3ba572f`, NOT browser-tested ⚠️
- Streaming SSE ✅
- Persona registry pattern ✅

---

## 7. Section 5.7 brain (`philosopher_brain/`)

⚠️ **Directory does not exist in repo.** All expected files are missing.

Expected files and status:

| File | Status |
|---|---|
| `personas/socrates.yaml` | ❌ MISSING |
| `personas/nietzsche.yaml` | ❌ MISSING |
| `personas/freud.yaml` | ❌ MISSING |
| `personas/jung.yaml` | ❌ MISSING |
| `personas/epictetus.yaml` | ❌ MISSING |
| `personas/de_beauvoir.yaml` | ❌ MISSING |
| `prompts/master_system_prompt.md` | ❌ MISSING |
| `maps/modern_phenomenology.json` | ❌ MISSING |
| `maps/universal_forbidden_lexicon.json` | ❌ MISSING |
| `maps/persona_specific_forbidden.json` | ❌ MISSING |
| `evals/eval_suite_spec.md` | ❌ MISSING |
| `evals/ten_modern_problems.json` | ❌ MISSING |

The `philosopher_brain/` directory and all design-source YAML/JSON/MD files have not yet been committed to the repo. These files need to be created or imported before Phase 1 work can begin in a Claude Code session that reads them directly.

---

## 8. What's pending — priority order

(Updated by `make state` from `HANDOFF_BRIEF_v2.md` Section 17.)

### P0 — Revenue blockers
1. **Stripe wiring** — Cannot collect payment. ~1-2 days.
2. **Pricing finalization** — Currently $12/mo per README. Lock for launch, A/B later.

### P1 — Section 5.7 migration (Phases 1-6)
1. Phase 1: Schema extension (1 day) — `_base.py` extended with optional fields
2. Phase 2: Brevity + forbidden lexicon post-check (1 day)
3. Phase 3: Extract & structure anti-flexing from prose (1 day)
4. Phase 4: Modern phenomenology bridge (1-2 days)
5. Phase 5: Register architecture + UI chips (2 days)
6. Phase 6: Eval suite + CI (2-3 days)

### P2 — UX & monetization gaps (from v1 Section 7)
- "Bring another mind" → recast as Council/Dual mode (post-Phase 4)
- Onboarding flow for new users
- Pricing page
- `/app/billing` UI
- Mobile responsive testing
- Real persona avatar artwork (currently emoji)

### P3 — Technical debt (from v1 Section 7)
- `.env.production` committed with hardcoded URLs → move to Vercel env vars
- `requirements.txt` partial pinning → full pinning
- Two unzipped Philosopher folders on Desktop → delete
- Per-turn persona reminder injection (drift protection — only if drift observed)

---

## 9. MANUAL — Recent decisions (preserved across regenerations)

> Edit this section by hand. `make state` does not touch it.

- **2026-05-02** — **API deployment gap formally documented.** Investigation revealed `apps/web/.env.local` points at `localhost:8000` — Vercel frontend is deployed at `thinkalike.vercel.app`, but no production backend exists. All "verify in browser" tasks (rate limiting, memory, safety) blocked until API is deployed. Estimated effort 2-4 hours single session (Railway/Render + Postgres + Redis + env vars + frontend env update + smoke test). Identified as immediate revenue-blocking dependency, ahead of Stripe resumption. Documented in `HANDOFF_BRIEF_v3.md` §20.
- **2026-05-02** — **Repo migrated from OneDrive to non-OneDrive location.** Repo moved from `C:\\Users\\nkoutr\\OneDrive - OTE\\Desktop\\Philosopher` to `C:\\Projects\\Philosopher` after observing repeated OneDrive sync interference during PR #5 and #6 work (file-locking conflicts during `git checkout`, cloud-only reparse-point placeholders). OneDrive copy preserved as `Philosopher_OLD_DELETE_AFTER` for ~2-3 days as safety net before permanent delete.
- **2026-05-02** — **Stale top-level `philosopher_brain/` removed (commit `3eccc44`).** During investigation post-PR-#5, discovered the repo had two `philosopher_brain/` folders — top-level (stale, 4225 lines, missing the emoji regex fix) and `apps/api/philosopher_brain/` (canonical, with Phase 2 fixes). Top-level was strictly inferior (23/24 files byte-identical, 1 file diverged on the emoji regex). Removed via direct commit to main. Working tree clean post-cleanup.
- **2026-05-02** — **Phase 2 (Section 5.7 brevity + forbidden lexicon) COMPLETE + MERGED.** Branch `feat/section-5.7-phase-2`, squash-merged as `6e2daad` via PR #6. Buffer-then-stream architecture with feature flag (default `false`). 5 locked decisions: (A) full streaming rollback when disabled, (B) opt-in by default, (C) 3 attempts + deterministic strip, (D) safety override bypasses postprocessing (enforced via `if/elif` + tripwire test), (E) structured logging (persona_slug, attempt_count, final_action, duration_ms, hit_categories — no PII). 24 unit tests added. Bug fixed in transit: brain JSON emoji regex used JavaScript Unicode syntax, converted to Python-compatible. Wiring location corrected: spec said `routers/conversations.py`, actual correct location is inside `services/conversation_service.py` `stream_response()`. Cross-reviewed by ChatGPT in parallel — both verdicts APPROVE.
- **2026-05-02** — **Brain folder committed to repo (commit `3832ec4` via PR #5).** `philosopher_brain/` (12 files: 6 persona YAMLs + 3 maps JSONs + master_system_prompt.md + 2 evals files) committed at `apps/api/philosopher_brain/` (Option B: co-located with API service, not top-level). Doc path references in `HANDOFF_BRIEF_v2.md` and `scripts/generate_state.txt` updated to match. Brain becomes part of versioned source of truth (formerly local-only at `philosopher_brain_local`).
- **2026-05-02** — **Phase 1.5 housekeeping items 1 + 2 COMPLETE (commit `1581c76` via PR #4).** `forbidden_phrases` gap closed across 3 personas (`carl_jung`, `socrates`, `sigmund_freud`) — added `"That's valid"` phrase that was missing from these but present in others. `.gitignore` added with Python-standard ignore set (compiled artifacts, virtual environments, IDE configs). Test suite 10/10 PASS post-merge.
- **2026-05-02** — **Phase 1 schema extension COMPLETE + MERGED (commit `0ade549` via PR #2).** 8 optional fields added to `PersonaConfig` in `apps/api/personas/_base.py`, plus 7 supporting dataclasses in new `apps/api/personas/_models.py`. 4 schema corrections vs original v2 spec (discovered via cross-validation against socrates.yaml + jung.yaml + freud.yaml): `safety_overrides` flattened to `safety: Optional[dict]` (heterogeneous YAML), `behavioral_parameters_by_register` added as 8th field (sparse register overrides per persona, present in all 3 cross-validated YAMLs), `modern_phenomenology_shading` dropped (lives in shared map, not per-persona), `response_length_words` upgraded from tuple to 4-mode `ResponseLengthSpec` dataclass.
- **2026-04-28** — Verified Section 5.7 framework against existing codebase. Decision: hybrid migration (Option A) over clean rewrite. Existing `system_fragment` prose is high quality and preserves design intent; new structured fields extend rather than replace.
- **2026-04-28** — Confirmed all 6 personas Python files are correct in repo (Marcus, Socrates, De Beauvoir, Carl Jung, Epictetus, Sigmund Freud). Earlier confusion (Epictetus docx contained Jung) was an upload error, not a repo bug.
- **2026-04-28** — Stripe wiring elevated to P0 ahead of any Section 5.7 work. Rationale: revenue blocking gap is larger than quality gap.
- **2026-04-27** — Section 5.7 framework added to PHILOSOPHER spec. Persona register architecture, anti-flexing protocol, brevity discipline, modern phenomenology bridge, eval suite all defined.
- **2026-04-26** — `HANDOFF_BRIEF_v1` written. 3 personas working end-to-end. Methodology lessons documented for next Claude Code session.

---

## 10. MANUAL — Current blockers / open questions (preserved across regenerations)

> Edit this section by hand. `make state` does not touch it.

**Open questions:**
- [ ] User validation test: send 3 working persona screenshots to 5 humans, ask "would you pay $7/mo for this? Brutal honesty." (per v1 Section 8 Step 6). Decision tree: 3+ "yes" → Stripe wiring. 0-1 "yes" → repivot pitch or audience.
- [ ] Decide whether Nietzsche becomes a 7th persona, OR whether the brain YAML is pruned.
- [ ] Decide pricing for launch: $12/mo (per README) OR $15/€15 (per Section 5.7 spec target band of €15-29).
- [ ] Greek source text editions: which translations are legally clear for ingestion in RAG corpus? Founder must provide.

**Blockers:**
- None at the technical level. All blockers are decision-pending.

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

---

## 12. MANUAL — Live URLs (preserved across regenerations)

- Repo: https://github.com/Nckoutras/Philosopher
- Frontend live: https://thinkalike.vercel.app
- Backend live: https://philosopher-api-z9l9.onrender.com
- Backend health: https://philosopher-api-z9l9.onrender.com/health
- Vercel project: https://vercel.com/nckoutras-projects/thinkalike
- Render service: https://dashboard.render.com (philosopher-api)
- Supabase project: https://supabase.com/dashboard/project/plecolxlzshkfvybszgs
