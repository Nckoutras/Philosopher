# Deploy Notes

Operational requirements that are **not** enforced by code or migrations and will
cause **silent degradation** if missed on deploy. Add an entry here whenever a
feature depends on an environment variable, an external dashboard setting, or a
manual step that a fresh deploy would otherwise skip.

This file lists *requirements and consequences*, never secret values. Secret
values live only in the Render / Netlify dashboards.

---

## Required environment variables

### API service (Render)

| Variable | Required for | Consequence if missing / wrong |
| --- | --- | --- |
| `API_BASE_URL` | Weekly-letter email (unsubscribe link) | Defaults to `http://localhost:8000`. The worker **refuses to send** the weekly email when this is localhost (so no real user gets a broken unsubscribe link) and logs `Weekly email skipped (API_BASE_URL not configured for prod)`. Set to the public backend URL, e.g. `https://philosopher-api-z9l9.onrender.com`. |
| `JWT_SECRET` | Auth **and** weekly-letter unsubscribe token (HMAC) | Must be a stable secret. Rotating it invalidates all previously emailed unsubscribe links (and all sessions). |
| `FRONTEND_URL` | Email links ("Read it in the app"), OAuth redirects, Stripe return URLs | Defaults to `http://localhost:3000`; links point at localhost if unset. |
| `RESEND_API_KEY` / `FROM_EMAIL` | All transactional email (OTP, ritual reminders, weekly letter) | No email is delivered if unset. |
| `DATABASE_URL`, `REDIS_URL` | App + ARQ worker/cron | App/worker won't start. |

> The list above is the operationally fragile subset. The full set of secrets
> (Anthropic, OpenAI, Stripe, PostHog, Google OAuth, …) is configured in the
> Render dashboard.

---

## Per-feature deploy requirements

### Weekly-letter email (PR #325, Slice 3a)

After deploying:

1. **Set `API_BASE_URL`** on the Render API service to the public backend URL
   (see table). Without it, every weekly email is suppressed by design.
2. **Verify the migration applied:** `SELECT version_num FROM alembic_version;`
   should be `028_user_weekly_email_opt_out`, and the `users.weekly_email_opt_out`
   column should exist.
3. **Smoke test** via the admin weekly-letter trigger: a `generated` letter is
   written *and* an email arrives with the sharp subject, the letter body, a
   "Read it in the app" link, and a working unsubscribe link. Clicking
   unsubscribe sets the flag and shows the confirmation; `empty`/`suppressed`
   weeks send no email; re-running a sent letter does not double-send
   (`email_sent_at` gate).

Unsubscribe endpoint (public, no auth):
`GET /api/v1/unsubscribe/weekly?u=<user_id>&t=<hmac>` — token is
`HMAC-SHA256(user_id)` keyed by `JWT_SECRET`.
