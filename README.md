# Philosopher

> A premium AI reflective companion grounded in historical philosophy.

---

## Stack

| Layer      | Tech                                                  |
|------------|-------------------------------------------------------|
| Frontend   | Next.js 14 (App Router) · TypeScript · Tailwind       |
| Backend    | FastAPI · Python 3.12                                 |
| Database   | PostgreSQL 16 + pgvector                             |
| Queue      | Redis + ARQ                                          |
| LLM        | Anthropic Claude (streaming)                          |
| Embeddings | OpenAI text-embedding-3-small                        |
| Billing    | Stripe (checkout + webhooks)                         |
| Email      | Resend                                               |
| Analytics  | PostHog                                              |

---

## Local setup (< 5 minutes)

### Prerequisites
- Docker + Docker Compose
- Python 3.12
- Node 22

### 1. Clone and configure

```bash
git clone <repo> && cd philosopher

cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
# Fill in your API keys in both .env files
```

### 2. Start infrastructure

```bash
make install          # install python + node deps
docker compose -f infra/docker-compose.yml up -d db redis
```

### 3. Migrate and seed

```bash
cd apps/api
alembic upgrade head
python db/seed.py
```

### 4. Run the apps

**Terminal 1 — Backend:**
```bash
cd apps/api
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Worker:**
```bash
cd apps/api
arq workers.arq_worker.WorkerSettings
```

**Terminal 3 — Frontend:**
```bash
cd apps/web
npm run dev
```

Open http://localhost:3000

---

## Or: full Docker Compose

```bash
make up
```

---

## Project structure

```
philosopher/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── main.py             # App entrypoint
│   │   ├── routers/            # One file per domain
│   │   ├── services/           # Business logic
│   │   ├── models/             # SQLAlchemy ORM
│   │   ├── schemas/            # Pydantic I/O
│   │   ├── personas/           # Persona configs (structured objects)
│   │   ├── prompts/            # Jinja2 prompt templates
│   │   ├── workers/            # ARQ background jobs
│   │   └── db/                 # Session, migrations, seed
│   └── web/                    # Next.js frontend
│       ├── app/                # App Router pages
│       ├── components/         # React components
│       └── lib/                # API client, store, hooks
└── infra/
    └── docker-compose.yml
```

---

## Adding a new persona

1. Create `apps/api/personas/epictetus.py` using the `PersonaConfig` dataclass
2. Add to registry in `apps/api/personas/__init__.py`
3. Run `python db/seed.py` to upsert into the database
4. Ingest source texts via `retrieval_service.ingest_chunk()`

No other files need to change.

---

## Stripe setup

1. Create products in Stripe dashboard
2. Copy price IDs into `.env`:
   - `STRIPE_PRICE_PRO_MONTHLY`
   - `STRIPE_PRICE_PRO_YEARLY`
3. Set webhook endpoint to `https://yourdomain.com/api/v1/billing/webhook`
4. Subscribe to events: `customer.subscription.*`, `invoice.payment_failed`

---

## Deployment (recommended: Railway or Render)

- **api**: Python service, `uvicorn main:app --host 0.0.0.0 --port 8000`
- **worker**: same image, `arq workers.arq_worker.WorkerSettings`
- **web**: Node service, `npm run build && npm start`
- **db**: Managed Postgres (Neon, Supabase, or Railway Postgres)
- **redis**: Upstash Redis (serverless, free tier works for MVP)

Set all env vars from `.env.example` in your deployment dashboard.

---

## Safety system

Pre-generation and post-generation checks on every message.

- **High/Critical risk** → persona suppressed, crisis resources shown, event logged
- **Medium risk** → redirect message + support signpost, persona continues
- **Low risk** → logged only, persona continues normally

Safety events are stored in `safety_events` table. Review them at `/admin`.

---

## Monetisation

| Plan    | Price        | Key gates                          |
|---------|--------------|------------------------------------|
| Free    | $0           | 2 personas, 3 rituals, no memory   |
| Pro     | $12/mo       | All personas, memory, insights      |
| Premium | (future)     | Premium persona packs (add-ons)    |

7-day trial on first Pro subscription.

---

## Key environment variables

| Variable                  | Purpose                         |
|---------------------------|---------------------------------|
| `ANTHROPIC_API_KEY`       | Claude API (required)           |
| `OPENAI_API_KEY`          | Embeddings (required)           |
| `STRIPE_SECRET_KEY`       | Payments (required for billing) |
| `STRIPE_WEBHOOK_SECRET`   | Webhook verification            |
| `DATABASE_URL`            | PostgreSQL connection           |
| `REDIS_URL`               | Redis connection                |
| `JWT_SECRET`              | Auth token signing              |
| `POSTHOG_API_KEY`         | Analytics (optional)            |
| `RESEND_API_KEY`          | Ritual reminder emails          |
