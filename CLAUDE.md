# Pre-Work Investigation Protocol

This document defines the mandatory investigation discipline that both the 
planning Claude (in claude.ai conversations) and the Claude Code agent must 
follow before any new code is written for this project.

This exists because on 2026-05-16 we discovered that ~3 hours of work 
building a new message endpoint had duplicated existing infrastructure 
(streaming send-message, llm_client, safety pipeline, memory extraction, 
RAG retrieval) from prior engine work. This protocol prevents that pattern 
from recurring.

## Rule 1: Feature Domain Enumeration

Before writing any brief or any code that adds, modifies, or extends a 
feature, the agent MUST enumerate what already exists in the same feature 
domain. "Look at existing patterns" is NOT sufficient — explicit 
enumeration is required.

### For HTTP endpoint work
- Fetch the live openapi.json from production OR read every router file
- List ALL endpoints in the same logical domain (e.g., "messages", 
  "conversations", "personas")
- For each existing endpoint, note: what it does, what schema it uses, 
  who calls it, whether it overlaps with the proposed new work

### For service / business logic work
- Grep the codebase for files with similar names 
  (e.g., `*_service.py`, `*_client.py`, `*_handler.py`)
- Read every file whose name suggests overlap
- Note overlaps in function names, responsibilities, dependencies

### For database work
- Query information_schema for relevant tables and columns
- Read the latest alembic migration to confirm current state
- Compare proposed schema against existing schema BEFORE designing new

### For frontend / UI work
- Grep for existing components with similar names or purposes  
- Check routing structure for related pages
- List existing screens that touch the same user flow

## Rule 2: Report Findings Before Designing

When investigation surfaces existing functionality:

**If overlap is total** (feature already exists): STOP. Surface to founder. 
Do NOT design a replacement without explicit decision.

**If overlap is partial** (some pieces exist, others missing): surface 
with concrete code references. Do NOT design until founder decides 
(extend existing, build parallel, replace, etc.).

**If no overlap**: confirm absence by listing what was checked, then proceed.

## Rule 3: Source of Truth Verification

Before trusting any second-hand description of existing code ("thin 
streaming wrapper", "scaffold", "stub", "minimal implementation"), the 
agent MUST read the actual code and verify the characterization. 
One-line summaries from prior sessions are NOT sufficient evidence of 
what exists or doesn't exist.

## Rule 4: Cross-System Dependency Check

Every new endpoint, service, or schema change must check for:
- Existing ARQ tasks that might depend on the surface area
- Existing webhook handlers (Stripe, etc.) that might depend on it  
- Existing admin endpoints that might call into it
- Existing tests that exercise it
- Existing frontend code that calls the existing surface

## Rule 5: Reconciliation Default

When parallel implementations of the same feature are discovered, the 
default is NOT "delete the duplicate". The default is:
1. Investigation-only PR producing a comparison report
2. Founder approves a reconciliation strategy based on the report
3. Reconciliation PRs follow, ordered by risk (close security or 
   billing holes first)
4. Each step independently reviewed and merged

## Enforcement

Every brief written by the planning Claude MUST include "Investigation 
step" as Step 2 of the brief structure, with explicit requirements per 
Rules 1-4 above. The brief must require the executing agent to:
1. Read the relevant files first
2. Report findings before implementing  
3. Stop and escalate if overlaps are found

Both Claude assistants (planning and execution) consult this protocol 
at the start of every new work item.

## Failure Log

Lessons that updated this protocol:

- **2026-05-16**: C4 message endpoint built in parallel with existing 
  SSE streaming send-message endpoint. Discovered via openapi.json 
  inspection. Cost: ~3 hours of duplicate work + a rate limit security 
  hole. Lesson: enumerate existing endpoints in same domain BEFORE 
  designing new ones.

## Future-proof first, shortcuts second

Every proposal — code, schema, architecture — must be evaluated against
production behavior with real subscribers, not just current cold-beta state.
Cold-beta shortcuts are allowed ONLY when:

1. The shortcut is explicitly named as such (not silently shipped as a "fix")
2. The production-grade alternative is articulated with concrete cost
3. A specific milestone is set for the proper implementation (e.g. "before public launch", "after first 10 paying subscribers")
4. Mentor confirms the shortcut doesn't create user-visible regressions or
   data integrity risks in the cold-beta window

When proposing solutions, default order:
- Production-grade approach (long-term sustainable)
- Hybrid / phased approach if time-to-ship matters
- Shortcut only if the above are infeasible AND the cost is named

When auditing CC's proposals, flag any solution that ships technical debt
without naming it. Tech debt that's named is manageable; tech debt that's
buried compounds silently.

Apply this principle to: schema design (FK constraints, soft vs hard delete,
retention policies), security (auth flows, dead-end navigation post-signout),
state management (caching, race conditions), and any "quick fix" that
touches data integrity.

## Known tech debt

### Dual tier resolution (added PR4j-paywall-audit, 2026-05-23)

`apps/api/auth.py:get_current_user_plan` and `apps/api/services/tier_service.py:get_user_tier`
are two parallel tier-resolution functions with different semantics:

- `get_current_user_plan` returns `"free" | "pro" | "premium"` from `Subscription.plan` directly
- `get_user_tier` returns `"free" | "pro"` with expiry/status validation and BETA_GRANT_PRO_TO_ALL bypass

PR4j added BETA bypass to both, but the duplication remains. Eight endpoints across
`personas.py`, `rituals.py`, `conversations.py`, and `share.py` use `get_current_user_plan`;
five use `get_user_tier`. Frontend `isPro` logic depends on whichever these endpoints return.

**Refactor before paid launch:** consolidate to a single tier-resolution function used by all
enforcement points. Decision needed at that time: keep `"premium"` tier semantics or collapse
to `free | pro`. Affects all paywall gates and the frontend Subscription type.
