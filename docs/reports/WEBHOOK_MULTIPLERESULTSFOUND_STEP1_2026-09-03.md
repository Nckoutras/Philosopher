# Stripe webhook `MultipleResultsFound` — Step-1 investigation report

**Baseline SHA:** `b0148f73ccda330d811a21d404e79426d0ce3c49` (`git ls-remote origin refs/heads/main`)
**Date:** 2026-09-03
**Status:** Step 1 complete; ruling given; fix implemented on `fix/billing-invoice-subscription-basil`.

---

## 1. Mechanism

`subscriptions.stripe_subscription_id` is `String(255) UNIQUE`, **nullable**
([models/__init__.py:56](../../apps/api/models/__init__.py#L56); DDL confirmed at
[001_initial.py:42](../../apps/api/db/migrations/versions/001_initial.py#L42)).
Postgres UNIQUE permits unlimited NULLs, and every signup creates a row with that
column unset ([auth.py:289-294](../../apps/api/routers/auth.py#L289-L294),
[auth_oauth.py:141](../../apps/api/routers/auth_oauth.py#L141)) — so in cold beta
nearly the whole table is NULL there.

SQLAlchemy renders `col == None` as `IS NULL`, confirmed in-process against the real
model:

```
key=None       -> WHERE subscriptions.stripe_subscription_id IS NULL
key='sub_123'  -> WHERE subscriptions.stripe_subscription_id = :stripe_subscription_id_1
```

A `None` key therefore does not match zero rows — it matches **every never-subscribed
user**, and `scalar_one_or_none()` raises `MultipleResultsFound` at ≥2. That exception
reaches the handler's catch-all
([billing.py:277-289](../../apps/api/routers/billing.py#L277-L289)), which deletes the
`StripeEvent` row and re-raises for a 500; Stripe retries, and every retry fails
identically. The event never processes.

## 2. Enumeration — every `scalar_one*` site with a payload-derived key

All five are in `_process_webhook_event`. Nothing outside `routers/billing.py` queries
`stripe_subscription_id`.

| # | Line (pre-fix) | Event | Key expression | Column (constraints) | Key can be `None`? | Exposure |
|---|---|---|---|---|---|---|
| 1 | :519-521 | `checkout.session.completed` | `obj["customer"]` | `stripe_customer_id` — NOT NULL, UNIQUE | No — sessions created `mode="subscription"` with explicit `customer=` (:195-197) | **None.** Even if None, `IS NULL` on a NOT NULL column matches 0 rows → silent no-op |
| 2 | :578-580 | `invoice.payment_succeeded` | `obj.get("subscription")` | `stripe_subscription_id` — **nullable**, UNIQUE | **Yes** | **`MultipleResultsFound`** |
| 3 | :605-607 | `customer.subscription.created\|updated` | `obj["customer"]` | `stripe_customer_id` — NOT NULL, UNIQUE | No | None |
| 4 | :677-679 | `customer.subscription.deleted` | `obj["id"]` | `stripe_subscription_id` — nullable, UNIQUE | No — the object's own id | None |
| 5 | :723-725 | `invoice.payment_failed` | `obj.get("subscription")` | `stripe_subscription_id` — **nullable**, UNIQUE | **Yes** | **`MultipleResultsFound`** |

Two sites exposed, both keyed on `invoice.subscription`. The three safe sites are safe
because of column nullability and payload guarantees, not because of any guard in code.

Non-payload sites in the same file, all keyed on the authenticated `user.id` or an
internal id: :153, :166, :219, :394.

## 3. Stripe docs citation — the `invoice.subscription` relocation

**API version `2025-03-31.basil`, documented as a breaking change.** Per
[Invoicing resources now specify how they were generated](https://docs.stripe.com/changelog/basil/2025-03-31/adds-new-parent-field-to-invoicing-objects):

> On the Invoice object, we deprecated the `quote`, `subscription`,
> `subscription_details`, and `subscription_proration_date` fields.
> Use `invoice.parent.subscription_details.subscription` (verify `invoice.parent.type`
> is `subscription_details`) instead of `invoice.subscription`.

The REST change table lists `subscription` as **Removed** from Invoice. The
corresponding Python SDK is **v12.0.0**; `requirements.txt:19` pins **`stripe==10.11.0`**
(SDK upgrade is out of scope — its own chore).

**Why this is live now — inference, needs Dashboard confirmation.** No
`stripe.api_version` is set anywhere in the codebase (only `stripe.api_key`, at four
sites). Webhook payload shape is set by the endpoint's API version **in the Stripe
Dashboard**, not by the library — so the code cannot tell which shape arrives. But the
comment at [billing.py:645-647](../../apps/api/routers/billing.py#L645-L647) says Stripe
"already moved this field once (top-level -> items)", and `_period_end_from_stripe`
absorbs it. That period-end move is
[the sibling change from the same 2025-03-31.basil release](https://docs.stripe.com/changelog/basil/2025-03-31/deprecate-subscription-current-period-start-and-end).
If the account were pre-Basil, that move would not have been observed — so the endpoint
is very likely already on Basil, one relocation was absorbed and the other was not.
Confirm at [webhook versioning](https://docs.stripe.com/webhooks/versioning); it is the
one load-bearing fact not readable from the repo.

## 4. Verification limits (TD-57)

Both exposed sites sit in the untestable half of the domain. The defect *is* a
`WHERE`-clause result over multi-row NULL state; a mocked `db.execute` returns whatever
the test author configured, so no test in this repository can reproduce the
`MultipleResultsFound`. The tests shipped with the fix pin the **guard** — id resolution
across both payload shapes, and the short-circuit that prevents the query being built —
plus the emitted SQL form (`= :param`, never `IS NULL`), which is as close to the defect
as a mock can get. Revert-verified: all 10 new tests fail against pre-fix code.

---

## 5. Out of scope for the fix PR — carry to the next docs rotation

Both were found during the Step-1 enumeration. Neither is the reported defect; both are
the same *class* of gap — an invariant enforced by application logic rather than by the
schema. Recorded verbatim as required by the Step-1 ruling, item 5.

### GAP-1 — `subscriptions.user_id` has no UNIQUE constraint

> **`subscriptions.user_id` has no UNIQUE constraint** —
> [015](../../apps/api/db/migrations/versions/015_add_fk_indexes.py#L20) adds a plain
> index, not a unique one. The three `user_id`-keyed `scalar_one_or_none()` sites above
> would raise the same exception on a duplicate row. Duplicates are prevented only by
> both creation sites being gated on `user is None` behind the UNIQUE on `users.email` —
> application logic, not schema.

Affected sites: [billing.py:153](../../apps/api/routers/billing.py#L153),
[:166](../../apps/api/routers/billing.py#L166),
[:219](../../apps/api/routers/billing.py#L219).

### GAP-2 — `users.oauth_provider_id` is nullable and non-unique

> **`users.oauth_provider_id` is nullable and non-unique**
> ([models/__init__.py:30](../../apps/api/models/__init__.py#L30)), queried with
> `scalar_one_or_none()` at
> [auth_oauth.py:119](../../apps/api/routers/auth_oauth.py#L119). Safe today because
> `google_sub` defaults to `""` and an explicit `if not email or not google_sub: return`
> guard precedes the query
> ([:110-114](../../apps/api/routers/auth_oauth.py#L110-L114)) — again a guard, not a
> constraint.

Note the shape of GAP-2: were that guard ever removed or reordered, the failure would be
identical to the one this PR fixes — `IS NULL` across every OTP-only user.
