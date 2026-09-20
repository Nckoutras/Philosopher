"""
Shared constants used across routers, services, and tests.
Keep this import-free from heavy dependencies so tests can import it standalone.
"""

# Plan tier hierarchy — higher = more access
TIER_ORDER: dict[str, int] = {
    "free":    0,
    "pro":     1,
    "premium": 2,
}

# Plan feature gates
PLAN_FEATURES: dict[str, dict] = {
    "free": {
        "personas": 2,
        "memory":   False,
        "rituals":  3,
        "insights": False,
    },
    "pro": {
        "personas": -1,   # unlimited
        "memory":   True,
        "rituals":  -1,
        "insights": True,
    },
    "premium": {
        "personas":      -1,
        "memory":        True,
        "rituals":       -1,
        "insights":      True,
        "premium_packs": True,
    },
}

# Analytics event names — single source of truth
ANALYTICS_EVENTS = {
    # THE BACKEND HALF OF THE TAXONOMY, AND ITS SOURCE OF TRUTH.
    #
    # This dict used to be inert: 21 names, 15 of which no code had ever fired,
    # one name that fired without being declared (user_signed_in), and nothing
    # anywhere that imported it. It documented an intention and drifted from the
    # code for months without anything noticing.
    #
    # It is now enforced, by tests rather than at runtime — see
    # tests/test_analytics_registry.py, which walks the AST of every module and
    # asserts BOTH directions: every analytics_service.track("...") literal
    # appears here, and every name here has at least one call site. A name with
    # no caller is deleted, not left as an aspiration.
    #
    # Enforcement is deliberately not a runtime check. An unknown event name
    # must never raise inside a request that was otherwise going to succeed;
    # analytics is an observer and may not change what the product does.
    #
    # The web half lives in apps/web/lib/analyticsEvents.ts under the same rule.
    # Names shared by both halves must carry the same property list.
    #
    # Property values are ids, enums, counts and buckets. Never conversation
    # text, memory text, letter text, an email, or the council `matter`.

    # ── Acquisition ──────────────────────────────────────────────────────────
    # Renamed from user_registered: one conversion, one name, matching the web
    # side's signup_started. No web twin — double-counting a signup is worse
    # than missing `source` on it.
    "signup_completed":       ["method", "plan"],
    "user_signed_in":         ["method"],

    # ── Engagement ───────────────────────────────────────────────────────────
    # Fired server-side at all THREE creation endpoints — /conversations,
    # /cross-persona and /reading-revisit — because an undercounted top of
    # funnel is the one number a funnel cannot afford to be wrong about. `via`
    # tells them apart without three event names. Server-side rather than at the
    # nine web createConversation call sites: one route cannot drift out of sync
    # with eight others. The cost is `source`, which is not knowable here.
    "conversation_started":   ["persona_slug", "ritual_id", "seeded_topic", "via"],
    # memory_count replaces the former memory_hit boolean. The Blueprint asked
    # for memory_reference_rendered; nothing renders a memory reference (the SSE
    # stream has no memory event and `brought in` is another persona), so the
    # count rides on the event that already knew the answer.
    # The open-thread loop's own closure metric (Γ-3). Fires INSTEAD of
    # conversation_started when a persona open hands back an existing thread —
    # never alongside it. A resumed thread did not start, and counting it as one
    # would inflate the top of the funnel with returns, making the
    # started -> completed ratio read worse exactly when the loop worked.
    #
    # gap_bucket is hours-since-last-message in five coarse buckets. The decision
    # it informs is "does the loop close, and over what gap" — a bucket answers
    # that; a raw hour count only looks more precise. `unknown` when the row
    # carries no last_message_at rather than a bucket that would be a guess.
    #
    # conversation_id (Γ-5) is what makes the loop's CLOSURE measurable at all.
    # Without it the only available reading was a person-level funnel to
    # message_sent, which scores "resumed thread A, then messaged thread B" as a
    # closure — a false positive that is invisible and flatters the loop.
    # message_sent has carried this same id since it shipped, so this adds no
    # privacy surface, only the join.
    "conversation_resumed":   ["persona_slug", "conversation_id", "gap_bucket"],
    "message_sent":           ["persona_slug", "conversation_id", "safety_level",
                               "retrieval_hit", "memory_count", "latency_ms"],
    # No `used_memory` on either: council_service passes memories=[]
    # unconditionally (council_service.py), so the property would be a hardcoded
    # False on every event. A constant is not a measurement — and a dashboard
    # reading "used_memory: false, 100%" invites the conclusion that memory does
    # not help the council, when the truth is the council never asks.
    "council_started":        ["source"],
    "council_completed":      ["member_count", "latency_bucket"],
    "council_saved":          [],
    # share_id (PR-1) is what turns two unrelated counts into a funnel. Before
    # the shares table there was nothing to join on: share_created and any later
    # view were separate populations, and "did this share bring anyone back" was
    # not a question the data could answer. It is an opaque row id, not a user id
    # and not derived from one.
    "share_created":          ["artifact_type", "share_id"],
    # The other half, and the reason share_id exists on both.
    #
    # FIRED SERVER-SIDE, AND THE distinct_id IS NOT THE SHARER. A landing view is
    # a stranger's act, so attributing it to the person who made the share would
    # put other people's browsing into that person's profile. The distinct_id is
    # derived from the share_id instead — stable enough to dedupe repeat opens of
    # the same link, tied to no account on either side.
    #
    # Server-side rather than from the page for the reason letter_open_to_app
    # gives above: a loop measurement that only counts consenting users is not a
    # measurement of the loop. The API has the key whatever the cookie banner
    # says, and this event carries nothing personal to begin with.
    "share_landing_view":     ["artifact_type", "share_id"],
    "letter_delivered":       ["week", "host", "reading_label"],
    # The other half of the letter loop (062). letter_delivered says an email
    # left the building; this says one brought a person back into the app, and
    # the pair is the Blueprint §16 gate. Fired from the API rather than the web
    # because a return that only counts for consenting users is not a delivery
    # measurement -- and the API has the key whatever the cookie banner says.
    # `week` and `host` match letter_delivered's so the two join on them; there
    # is no reading_label because the opened row carries no equivalent and a
    # property present on one side of a funnel and absent on the other is worse
    # than no property at all.
    "letter_open_to_app":     ["week", "host"],
    # The THIRD and last of the letter events, and the one the correspondence
    # loop is named for (Γ-5). delivered says an email left the building, opened
    # says one brought a person back, this says they answered it. `week` and
    # `host` are spelled identically across all three deliberately — that is what
    # lets them join into one funnel instead of three unrelated counts.
    #
    # FIRES ON THE FIRST WRITE-BACK ONLY, the letter_open_to_app precedent: a NULL
    # write_back_at is the idempotence, exactly as a NULL email_opened_at is
    # there. Re-submitting overwrites the stored text, but a revision is a person
    # changing their words rather than the loop closing twice, and counting it
    # would make this funnel's denominator mean two things at once.
    #
    # length_bucket is one of four fixed strings (routers/weekly_letters.py
    # write_back_length_bucket), measured over the stripped text. The text itself
    # is never a property — not truncated, not hashed. "Does the correspondence
    # get answered, and at what length" is answered completely by a bucket, and
    # an exact character count would be a weak fingerprint of the reply besides.
    "letter_write_back":      ["week", "host", "length_bucket"],

    # ── Monetisation ─────────────────────────────────────────────────────────
    # `source` is the paywall the checkout came from. It reaches the webhook
    # through Stripe metadata — session metadata for checkout.session.completed,
    # subscription_data.metadata for customer.subscription.*, because those two
    # webhook cases receive different objects and both fire
    # subscription_activated. None for a checkout that carried no source.
    "checkout_started":       ["plan", "interval", "source"],
    "subscription_activated": ["plan", "interval", "source"],
    # reason and cancel_feedback are Stripe enums read off
    # cancellation_details; its free-text sibling `comment` is never read.
    # last_14d_features is a sorted list drawn from a FIXED vocabulary in
    # routers/billing.py — user content can never enter it.
    "subscription_canceled":  ["plan", "tenure_days", "reason",
                               "cancel_feedback", "last_14d_features"],

    # ── Lifecycle ────────────────────────────────────────────────────────────
    # Fired from services/account_deletion_service.py AFTER the delete commits.
    #
    # Its distinct_id is the literal string "deleted_account", NOT the user id.
    # This is the one event in either registry that is deliberately not
    # attributable: the person it describes has just exercised Art. 17, and
    # attaching their id to a new analytics record would undo the erasure the
    # event is reporting. The churn count survives; the person profile stops
    # accumulating and no id links the two.
    #
    # tenure_days may be None — routers/billing.py::_tenure_days returns None
    # rather than 0 when a row never became paying, and this event reuses that
    # function rather than reimplementing it, so the property means the same
    # thing here as it does on subscription_canceled.
    "account_deleted":        ["plan", "tenure_days", "had_active_subscription"],
    # Fired from routers/auth.py after a successful export. Counts and a bucket,
    # never the contents — the one event whose subject is the user's entire
    # dataset must not carry any of it. size_bucket informs exactly one
    # decision, "is a synchronous download still viable", which a bucket answers
    # and a byte count would only pretend to answer more precisely.
    #
    # record_count, not message_count: test_no_property_name_suggests_free_text
    # bans "message" in a property name, and that guard is right to be blunt —
    # a privacy smoke alarm that carves out exceptions for the event that
    # happens to need one stops being a smoke alarm. record_count is the total
    # rows across every section, which answers the viability question better
    # than a message count anyway.
    "data_exported":          ["conversation_count", "record_count", "size_bucket"],

    # ── Limits ───────────────────────────────────────────────────────────────
    # Fired when a cap REFUSES a request, from SIX call sites across five paths.
    # Three closed enums and nothing else: tier is free|pro|premium, cap_kind
    # names which ceiling was hit, path names the door. The user's text is not
    # here and cannot be — a cap event describes the refusal, not the request.
    #
    # cap_kind exists so ceilings that mean different things stay separable in
    # the dashboard rather than averaging into one meaningless rate. Two values
    # today: "pro_fair_use" (five sites — a cost signal) and "council" (the
    # weekly 1-per-source council limit — a product shape, not a cost control,
    # and a conversion signal rather than a spend one).
    "usage_cap_hit":          ["tier", "cap_kind", "path"],

    # ── Recognition (Γ-2) ────────────────────────────────────────────────────
    # The epistemic loop's only event: the reader's verdict on a claim the product
    # made about them. Two closed enums and nothing else — insight_type is the
    # card's own type (None on rows written before the column, sent as None rather
    # than a stand-in, the letter_delivered precedent) and verdict is
    # yes|partly|no, bound by a Literal at the router's edge.
    #
    # The insight's CONTENT is the user's own material and is never a property —
    # not truncated, not hashed. What this event answers is "how often is the room
    # right", which two enums answer completely.
    #
    # Fired from the API after the explicit commit in routers/memory.py, not from
    # the web: a recognition metric that counts only readers who accepted the
    # analytics cookie would measure consent, not recognition.
    # `surface` (Γ-5) is insight | mirror | self_comparison. Ring-true is "one
    # speech act, one contract, three surfaces" (models.Insight), and until Γ-5
    # only the insight surface fired this event: mirror and you-vs-you verdicts
    # were stored in their own ring_true columns and counted NOWHERE, so the
    # recognition rate this event reports was drawn from a third of the verdicts
    # the product collects. One event with a surface property rather than three
    # event names — it is one question ("how often is the room right"), asked on
    # three doors, and three names would make the total require a union.
    #
    # insight_type is sent by the insight site only. The other two surfaces have
    # no such column, and the registry explicitly permits a site to omit a
    # property it cannot know; inventing a value to fill the column would put a
    # stand-in into a breakdown.
    "memory_feedback":        ["insight_type", "verdict", "surface"],

    # ── Safety (no PII) ──────────────────────────────────────────────────────
    "safety_event_pre":       ["risk_level", "category"],
}

# Safety risk levels in ascending severity
RISK_LEVELS = ["none", "low", "medium", "high", "critical"]


# ── Scheduled-run expectations (worker-absence alerting) ──────────────────────
#
# WHAT THIS CLOSES. Mon 14 -> Wed 16 September 2026 the ARQ worker ran with a
# wrong DATABASE_URL password. Every job in it failed or never ran -- Sunday
# letters, the trajectory snapshot, the OTP purge -- and NOTHING ALERTED. Job
# FAILURE was already reported: an exception reaches Sentry. Job ABSENCE was not,
# because a process that never starts raises nothing to report. The outage
# surfaced three days later, by accident, through otp_codes rows the founder
# happened to look at.
#
# THE CHECKER RUNS IN THE API PROCESS, which is the whole design and not an
# implementation detail: it watches the OTHER process. September's wrong URL was
# the WORKER's; the API's was fine. A liveness signal hosted by the process that
# may be dead cannot report its own death.
#
# PLAIN DATA, NO CRON PARSER. Each entry carries a cadence the checker evaluates
# with arithmetic. 'weekly' fires at a fixed ISO weekday + hour UTC and is keyed
# by ISO week; 'interval' fires every N minutes and is keyed by an N-minute
# bucket. A dependency that parses five-field cron strings would buy nothing
# these two shapes do not already cover.
#
# `job_name` IS THE LOOKUP KEY and must equal job_run.job_name EXACTLY. The
# literals are retyped here rather than imported because this module is
# import-free from heavy dependencies by contract (see the file docstring) and
# the worker modules are not. tests/test_job_expectations.py asserts the two
# agree, and that test is the only reason this duplication is allowed to exist.
#
# The cost of getting a name wrong, stated because it nearly happened: this
# feature's brief said "weekly_trajectory". The live literal is
# "weekly_trajectory_snapshot" (workers/trajectory_snapshot.py:50). An
# expectation naming a job_name that appears in zero rows does not fail loudly --
# it reports that job missing on every tick, forever, starting the hour it
# deploys, filling the channel this exists to create with one false positive.
#
# v1 IS THESE THREE AND NOTHING ELSE.
#   - monthly_letter is deliberately out: month-end edge cases, and it already
#     has a catch-up pass. Revisit after the 2026-09-30 monthly run.
#   - preview_mirror is out because it writes no job_run row to check. It runs in
#     the API process under APScheduler and leaves only log lines (TD logged).
#   - purge_expired_otp_codes is out by its own design: a purge is
#     self-evidencing -- if it stops, the surviving rows ARE the evidence. See
#     its docstring in workers/arq_worker.py.
#
# `grace_minutes` is how long after a run was due the checker waits before
# calling it missed. It absorbs a slow dispatch, a worker restarting into its
# schedule, and clock skew -- not a genuine outage, which outlives any of these.
JOB_EXPECTATIONS: tuple[dict, ...] = (
    # Sunday 18:00 UTC, keyed by the ISO week that is ending.
    # workers/letter_dispatch.py JOB_WEEKLY + arq_worker.py cron_jobs.
    {
        "job_name":      "weekly_letter",
        "cadence":       "weekly",
        "isoweekday":    7,      # Sunday, ISO numbering (Monday = 1)
        "hour":          18,     # UTC, pinned by WorkerSettings.timezone
        "grace_minutes": 60,
    },
    # Sunday 17:00 UTC -- one hour BEFORE the letter, so its per-user fan-out
    # drains before step D would read it. Same ISO-week key.
    # workers/trajectory_snapshot.py JOB_WEEKLY_TRAJECTORY.
    {
        "job_name":      "weekly_trajectory_snapshot",
        "cadence":       "weekly",
        "isoweekday":    7,
        "hour":          17,
        "grace_minutes": 60,
    },
    # The heartbeat, and the reason the other two are checkable at all. Every
    # other job_run writer is WEEKLY, so without a signal at this cadence the
    # mean time to detect a dead worker is about three and a half days and the
    # worst case is seven. workers/heartbeat.py.
    {
        "job_name":      "worker_heartbeat",
        "cadence":       "interval",
        "every_minutes": 10,
        "grace_minutes": 20,
    },
)


def is_plan_sufficient(user_plan: str, required_plan: str) -> bool:
    """Return True if user_plan meets or exceeds required_plan."""
    return TIER_ORDER.get(user_plan, 0) >= TIER_ORDER.get(required_plan, 99)
