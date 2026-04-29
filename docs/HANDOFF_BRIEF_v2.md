# HANDOFF BRIEF v2 — Philosopher / Great Minds

**For:** The next Claude Code (or developer) session
**From:** Nikos Koutras (founder) + mentor instance
**Date updated:** April 28, 2026 (v2 additions)
**Original date:** April 26, 2026
**Status:** Functional MVP. 6 personas registered (Section 5 update below). Section 5.7 framework now defined; migration plan in Section 16.

> **Update note for v2:** Sections 1-14 below remain authoritative as the original implementation snapshot. Sections 15-17 are new additions reflecting the Section 5.7 framework work and migration plan. Where v1 contradicts v2, v2 wins. The full v1 content is preserved verbatim in Sections 1-14.

---

## 1-14 — UNCHANGED FROM v1

[All original sections 1 through 14 preserved as-is from HANDOFF_BRIEF_FOR_CLAUDE_CODE.md v1. See repo `docs/HANDOFF_BRIEF_v1_archived.md` for the verbatim original.]

**One factual update applied to Section 5:** All 6 personas are present and registered in `apps/api/personas/__init__.py`. The "awaiting deploy verification" status from v1 has been resolved — code is in repo, deploy verified. Section 5.7-compliance remains pending for all 6.

---

## 15. SECTION 5.7 FRAMEWORK — PERSONA REGISTER ARCHITECTURE & CONVERSATIONAL DISCIPLINE

This section was added to the product spec after v1 of this brief. It is the most significant design refinement since the original 6-persona scope, and it directly impacts retention, conversion, and the premium feel of the product.

The full spec text lives in `PHILOSOPHER.docx` (or `PHILOSOPHER_v2.docx` once founder updates). The summary below is what Claude Code needs to know.

### 15.1 The core problem

Three documented failure modes of the current persona implementation:

1. **Abstraction drift** — persona speaks only at philosophical altitude, leaving modern users feeling unmet
2. **Verbosity** — persona over-explains, padding responses with elegant filler
3. **Identity flexing** — persona references its own biography, school, rivals, or works to "prove" authenticity

All three are partially addressed in current `system_fragment` prose (especially in Freud's anti-id/ego/superego clause and Jung's anti-archetype-labels clause). Section 5.7 makes this enforcement structural.

### 15.2 The framework — what changes

| Element | What it does | Status in current code |
|---|---|---|
| **Character anchors** | 3-5 non-negotiable behavioral rules per persona, enforced in post-processing | In `system_fragment` prose; **not structured** |
| **Register architecture** | Adaptive verbal altitude (scholarly/measured/grounded/bare) with per-persona allowed range | **Not implemented** |
| **Brevity discipline** | Numerical word bands per response mode, enforced post-generation | Numerical bands in prompt; **no post-check enforcement** |
| **Anti-flexing protocol** | `never_unprompted` lists per persona with conditional exemptions | In `system_fragment` prose; **not structured, no post-check** |
| **Modern phenomenology bridge** | Internal translation of modern terms (ghosting, burnout, toxic boss) to timeless essences | **Not implemented** |
| **Forbidden lexicon (universal + per-persona)** | Two-layer post-processing check | Per-persona only, ~7-13 phrases each, **no universal layer, no patterns, no categories** |
| **Eval suite (4 tests)** | Distinctiveness, Brevity, Anti-Flex, Listening orientation | **Not implemented** |

### 15.3 Why this matters for monetization

- **Anti-flexing** prevents the documented "Jung mentions Freud unprompted" failure mode. Direct credibility hit on Reflective Achiever segment (the highest-value tier).
- **Modern phenomenology bridge** is the unique selling proposition. Without it, Philosopher is "talk to historical figures wrapper #847". With it, it's the only product that engages with modern user contexts in timeless framework.
- **Brevity post-enforcement** addresses the #1 silent retention killer. Verbosity drift returns after every prompt edit if not enforced.
- **Register architecture** is the premium feel multiplier. Adaptive register ≈ "this product gets me" feedback.
- **Eval suite** prevents regression. Without it, every prompt change is gamble.

### 15.4 The brain — design source of truth

The Section 5.7 framework is fully designed in `philosopher_brain/` (in repo, also in claude.ai project files). It contains:

- 6 persona configs in YAML (design source — translates to extensions of `_base.py` PersonaConfig)
- `prompts/master_system_prompt.md` (extension to `system_base.jinja2`)
- `maps/modern_phenomenology.json` (30+ modern term mappings with persona-specific shading)
- `maps/universal_forbidden_lexicon.json` (10 categories with phrases + regex patterns)
- `maps/persona_specific_forbidden.json` (aggregator)
- `evals/eval_suite_spec.md` and `evals/ten_modern_problems.json`

**Critical:** The YAML configs in the brain are **NOT meant to replace** the existing `apps/api/personas/*.py` files. They are the **design source from which the existing Python configs are extended**. The migration plan in Section 16 details how.

---

## 16. MIGRATION PLAN — HYBRID INTEGRATION

### 16.1 Principle

The existing `apps/api/personas/` implementation is **architecturally sound and emotionally well-written**. The `system_fragment` prose for each persona contains design intent that took real effort and is well-calibrated. We do not throw it away.

The migration **extends** the existing `PersonaConfig` dataclass with new optional fields, **extracts** structured anti-flexing and character anchors from the existing prose, and **adds** the new layers (register, modern phenomenology, post-processing, evals) that don't exist yet.

### 16.2 Six-phase plan

**Phase 1 — Schema extension (1 day)**
- Extend `apps/api/personas/_base.py` with new optional fields (all default None for backward compatibility):
  - `character_anchors: list[CharacterAnchor] | None`
  - `register_range: RegisterRange | None`
  - `anti_flexing: AntiFlexingRules | None`
  - `response_length_words: tuple[int, int] | None`
  - `persona_specific_forbidden: ForbiddenLexicon | None`
  - `modern_phenomenology_shading: dict | None`
  - `behavioral_parameters: BehavioralParameters | None`
  - `safety_overrides: SafetyOverrides | None`
- Add corresponding new dataclasses in same file or new `_models.py`
- Run existing tests; all 6 personas should still load with new fields = None
- **Done criterion:** repo deploys, no runtime change visible to users

**Phase 2 — Brevity post-check + universal forbidden lexicon (1 day)** — *highest immediate retention impact*
- Add `apps/api/services/postprocessing.py` with:
  - `check_brevity(reply: str, persona: PersonaConfig) -> CheckResult`
  - `check_universal_forbidden(reply: str) -> CheckResult` (loads `maps/universal_forbidden_lexicon.json` from brain)
  - `check_persona_forbidden(reply: str, persona: PersonaConfig) -> CheckResult`
  - `regenerate_or_trim(reply, checks, max_attempts=3) -> str`
- Wire into `apps/api/routers/conversations.py` after generation, before streaming end
- Feature flag: `POSTPROCESSING_ENABLED` env var (default true in dev, opt-in for prod rollout)
- **Done criterion:** average reply length per persona within ±15% of target band; zero forbidden lexicon hits in 50-message sample

**Phase 3 — Extract & structure anti-flexing from prose (1 day)**
- For each of the 6 personas, read existing `system_fragment` and extract:
  - Character anchors → populate `character_anchors` field
  - Anti-flexing rules → populate `anti_flexing` field
  - Response length → populate `response_length_words` field
- Update `system_base.jinja2` to render the new structured fields **in addition to** existing prose (initially redundant)
- A/B test: half traffic with structured + prose, half with prose only
- After validation, can deprecate redundant prose sections in `system_fragment`
- **Done criterion:** evals show no quality regression; structured fields produce equivalent or better outputs

**Phase 4 — Modern phenomenology bridge (1-2 days)**
- Add `apps/api/services/phenomenology.py`:
  - Load `maps/modern_phenomenology.json` from brain
  - `detect_modern_context(user_message: str) -> PhenomenologyMatch | None` (start with substring match, can upgrade to embedding similarity later)
  - Inject `phenomenological_essence` into prompt context when matched
- Update `system_base.jinja2` with conditional `MODERN PHENOMENOLOGY BRIDGE` section
- **Done criterion:** for inputs containing "ghosting", "burnout", "toxic boss" etc., persona reply does NOT echo modern term verbatim; engages with underlying experience

**Phase 5 — Register architecture (2 days)**
- Add register classifier (heuristic-based first):
  - Sentence length, vocabulary density, distress signals
  - Returns one of `scholarly` | `measured` | `grounded` | `bare`
- Update `system_base.jinja2` with register-conditional sections
- Frontend: two chips below each reply: "speak more plainly" / "go deeper"
- Persistent register lock per conversation (Redis key)
- **Done criterion:** distress test inputs ("I can't") get grounded/bare; long literate inputs get measured/scholarly; chips work end-to-end

**Phase 6 — Eval suite + CI (2-3 days)**
- Implement `apps/api/evals/` with 4 tests per `eval_suite_spec.md`:
  - `anti_flex.py` (auto-graded, hard fail on any hit)
  - `brevity.py` (auto-graded, ±15% tolerance)
  - `distinctiveness.py` (auto-grade subset for CI; full version requires human blind review)
  - `listening.py` (LLM-as-judge with separate model)
- CLI runner: `make eval` or `philosopher eval run --persona X --test Y`
- GitHub Actions: anti-flex on every PR, brevity subset, full suite weekly
- **Done criterion:** all 4 tests run via CLI; CI gates merges on anti-flex; weekly drift report runs

### 16.3 Sequence rationale

The order is **monetization-first**, not architectural-purity-first:

- Phase 1 unlocks everything (mechanical, low-risk)
- Phase 2 = immediate retention impact (brevity is #1 silent killer)
- Phase 3 = structural cleanup of what already works (low new value, high enabler value)
- Phase 4 = the unique selling proposition (justifies €15-29/mo)
- Phase 5 = premium feel (adaptive register = "this gets me")
- Phase 6 = drift protection (gates everything else)

### 16.4 Backward compatibility guarantee

At every phase boundary, the system must remain deployable. No "big bang" rewrite. No feature flag dependency chains. Each phase is independently reversible by feature flag.

### 16.5 What does NOT change

- Existing `PersonaConfig` core fields (slug, name, era, tradition, tier, tagline, avatar_emoji, worldview, tone, sentence_structure, vocabulary_register, forbidden_phrases, questioning_pattern, challenge_level, challenge_style, response_length, uses_personal_anecdote, cites_own_works, retrieval_sources, retrieval_top_k, opening_invocation, system_fragment) — all preserved
- Existing `system_base.jinja2` core structure — extended, not replaced
- Existing routers, services, models, db schema for non-persona concerns
- Existing auth, billing, memory, rituals, admin
- The 6 personas' essential voice as captured in their current `system_fragment` prose

---

## 17. UPDATED PHASE QUEUE

This section supersedes Section 9 of v1. The original 5-task queue (rate limiting, persona configs, "Bring another mind", Stripe wiring, drift protection) is reorganized below into the new structure.

### 17.1 Status of original v1 tasks

| Task (from v1 Section 9) | Status | Now part of |
|---|---|---|
| 1. Rate limiting per plan | ✅ Code merged | Standalone — verify in browser |
| 2. Add Socrates / Epictetus / Freud Python configs | ✅ Code merged + verified | Section 5 update |
| 3. "Bring another mind" feature | ⏸️ Deferred | Post-Phase 4; see 17.3 |
| 4. Stripe checkout wiring | ❌ Not started | **Now P0 — see 17.2** |
| 5. Persona drift protection | ❌ Not started | Subsumed by Phase 6 (eval suite) |

### 17.2 Revenue-blocking work — must precede or parallel Phase 1

**Stripe wiring is now P0.**

Rationale: Section 5.7 work increases product quality, but **without Stripe wired, no quality improvement converts to revenue**. The product cannot accept payment. This is the single largest revenue-blocking gap.

Concrete sub-tasks:
- Stripe products + price IDs in dashboard
- Webhook endpoint with signature verification
- Customer portal embed
- Subscription state sync to user table
- Frontend `/app/billing` UI

This work runs in **parallel** with Phase 1 of Section 5.7 work, not after. It is independent infrastructure.

### 17.3 "Bring another mind" — clarified scope

This was the originally-positioned "killer differentiator" in v1. Re-evaluation in light of Section 5.7:

The Section 5.7 framework (Council Mode, Dual View per spec section 6.1) **already covers this concept** more rigorously. "Bring another mind" was a v1 sketch. The spec's Council Mode (3 personas + synthesis) and Dual View (2 personas, no synthesis) are the productized versions.

Recommendation: defer "Bring another mind" implementation until **after Phase 4 (modern phenomenology)**. Reason: a multi-persona feature where personas all sound similar is a regression. Modern phenomenology + structured anti-flexing make multi-persona meaningfully distinct. Building the feature before those is putting the cart before the horse.

### 17.4 Updated immediate next steps for Claude Code

**Recommended order for next session:**

1. **Verify rate limiting in browser** (5 minutes) — completes original Task 1
2. **Begin Stripe wiring** (1-2 days) — P0 revenue blocker
3. **Phase 1 of Section 5.7 — Schema extension** (1 day) — unlocks everything else
4. **Phase 2 — Brevity + universal forbidden lexicon** (1 day) — immediate retention impact
5. Continue Phases 3-6 in order

Stripe and Phase 1 can run in parallel if Claude Code has bandwidth. Otherwise Stripe first (revenue), Phase 1 second (foundation).

### 17.5 Pricing decision

Per v1 Section 7: pricing not finalized. Recommendation: ship initial Stripe products at:

- Free: $0 (current 2-persona limit per README)
- Pro: $12/month, $120/year (per README)
- 7-day trial on first Pro subscription

These can change later. Lock for launch; A/B test after first 50 paying users.

---

## 18. WHAT THE CLAUDE.AI PROJECT KNOWLEDGE NOW CONTAINS

For continuity between Claude Code (local) and Claude.ai (browser) sessions:

**Files uploaded to Claude.ai Project Knowledge (stable foundation):**
- `PHILOSOPHER.docx` — product spec (founder to update with Section 5.7)
- `HANDOFF_BRIEF_v2.md` — this document
- `philosopher_brain/` zip — design source of truth for Section 5.7

**Files updated regularly:**
- `PROJECT_STATE.md` — live state snapshot, regenerated via `make state` (see repo `docs/`)

**Project Instructions in Claude.ai Project setup:**
- Reference to repo location
- Distinction from KIEN project
- Mentor mode preferences
- Section 5.7 design source pointer

---

## END OF v2 ADDITIONS

If v2 conflicts with v1 anywhere, v2 wins. If a future v3 refines this document, mark it explicitly. Never silently overwrite — preserve version history.
