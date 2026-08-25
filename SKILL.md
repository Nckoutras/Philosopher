# SKILL.md — How implementation work is done in this repo

Complements CLAUDE.md (what to investigate before designing). This file
governs how a unit of work runs from brief to push. If it is ever unclear
which document governs a situation, that ambiguity is itself a STOP:
surface it and ask. Every rule here was paid for with a real failure; the
incidents live in CLAUDE.md's Failure Log — this file cites, it does not
duplicate.

## 1. The loop — no exceptions

INVESTIGATE → report → STOP → ruling → IMPLEMENT → full raw diff → STOP
→ "approved to push" → explicit git add → verify → commit → push
→ independent verification → founder squash-merges.

- One logical change per branch; one branch per PR. Branch from
  origin/main fetched in this session; state the base SHA in the report.
- "Approved to push" counts only from the founder, only in those words.
- A STOP is a full stop. A stated default ("I'll do X absent other
  instruction") is a recommendation inside a report — never permission
  to proceed. No ruling, no action.
- After approval, the working tree is FROZEN. If anything changes any
  file after the approved diff was shown — you, a hook, a formatter, a
  test artifact — the approval is void: show the new diff, STOP again.
- Before commit: git status must show staged == exactly the approved
  paths, nothing unstaged, nothing untracked-and-unexplained. Never
  git add -A. Never force-push. Push only the feature branch.
- After push: the planning assistant independently fetches the pushed
  branch and checks it against the approved diff before merge. Your
  report is a claim; this step is the evidence model.

## 2. Investigation discipline

- Read the live code of the branch you build on. Doc claims, session
  notes, backlog one-liners, and carried explanations for failing tests
  are all unverified text until checked against source (TD-45).
  Exception: schemas, migrations, contracts, and prompt specs ARE source.
- Enumerate mechanically (AST walk, string.Formatter, grep) and state
  the method next to every number. A method does not make a number true;
  it makes it checkable.
- When investigation contradicts the brief — a named helper doesn't
  exist, an assumed overlap isn't there, a "stub" is a full
  implementation — STOP and report. Do not follow the brief into what
  you now know is wrong, and do not redesign unilaterally.
- Partial overlaps: CLAUDE.md Rule 2 governs. STOP.

## 3. Rulings and copy

- Judgment calls the brief didn't settle: surface with a recommendation
  and default, then wait. Deliberate exclusions are stated; if you
  realize later that something was excluded by accident, report it then.
- Approved copy is locked: the founder-approved wording in the ruling is
  the canonical object. "Verbatim" is verified by a programmatic
  equality check on the exact strings, not by eye.
- Models follow examples over rules. A spec whose example contradicts
  its own rule is defective: never ship the pair. Fix unapproved
  examples; STOP for approved copy. Guard examples with tests.

## 4. Tests

- Prove-before-fix: a guard test must FAIL on the base branch first.
  Paste the raw output of both runs — run 1 failing, run 2 passing —
  plus the full-suite tail. Test counts and pass/fail lines are always
  raw pasted output, never narrated numbers.
- Coverage that cannot fail on main is fine — declared as coverage,
  never presented as proof.
- Pin live defaults by asserting the property that matters about the
  measured live value (e.g. "the default separator renders a glyph or
  blank in this font"), then prove the pin by a temporary revert run —
  restore, and show the final diff is the approved one.
- Hollow-test hazards (all shipped green here once): early-return paths
  that skip the assertion, bytes-valid output that renders broken,
  slices wide enough to pass on anything, auto-Mocks missing fields
  (C-06). Prefer delta assertions (with-X ≠ without-X), exact slices,
  field-complete mocks, real fonts/files.
- Ship gate: full suite 0 failed. There is no acceptable red.

## 5. Look at the output

Any rendered or user-visible surface: generate one sample through the
real code path with the real assets, view it, and report what you saw
with the artifact's path. The tofu bug passed the entire suite; one
render caught it.

## 6. Failure direction

On paths touching access, money, or user data: when a failure can land
two ways, choose the direction explicitly, state it in a comment at the
site, and make it loud — logger.error with the internal ids needed to
find the event. Silent-and-unrecoverable is never the accepted
direction. Logs, diffs, and reports carry internal ids only: never
tokens, keys, emails, or customer content.

## 7. Scope

- WHAT-YOU-WILL-NOT-TOUCH lists are binding. If correct implementation
  turns out to REQUIRE touching an excluded path, that is a STOP, not a
  choice between shipping broken and violating scope.
- Adjacent defects: logged as follow-ups, not fixed. If you believe a
  defect is not adjacent but caused-or-exposed by this change, say so
  and STOP for classification — do not classify alone.
- Standing pre-authorization: docstrings/comments your change makes
  false are in scope — fix and declare them. If they sit in an excluded
  file: flag, don't fix.

## 8. When things go wrong

- Context loss / restart / compaction: before any further action,
  re-read the brief, the last ruling, and git status; state which gate
  you believe you're at and wait for confirmation.
- A command fails: report it. Retrying until something passes and
  reporting only the success is misreporting.
- Merge conflict, or origin/main moved under you: STOP. Never resolve
  conflicts in business logic on your own authority.
- A previously-green unrelated test goes red after your change: STOP.
  Attribution (caused / flaky / pre-existing) is a ruling, not a guess.
- After any file write that matters, re-read the file (or the diff) —
  never reason from the pre-edit snapshot.

## 9. Reports

Every report states: what was verified and how, what is UNVERIFIED and
why, findings contradicting the brief, judgment calls awaiting rulings,
residuals and follow-ups. Critical evidence (test tails, prove runs,
git status before commit) is raw output. The founder reads outcomes and
decisions, not Python — anything that only a code-reader could catch
belongs in the diff for the planning assistant's verification pass,
stated, not buried.
