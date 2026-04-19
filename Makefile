.PHONY: dev up down migrate seed api worker web logs

# ── Start full stack ──────────────────────────────────────────────
up:
	docker compose -f infra/docker-compose.yml up -d db redis
	@echo "Waiting for postgres..." && sleep 3
	cd apps/api && alembic upgrade head
	cd apps/api && python db/seed.py
	docker compose -f infra/docker-compose.yml up -d api worker web

# ── Dev (local, no docker for app) ───────────────────────────────
dev:
	docker compose -f infra/docker-compose.yml up -d db redis
	@echo "Postgres and Redis running. Start api and web manually:"
	@echo "  cd apps/api  && uvicorn main:app --reload --port 8000"
	@echo "  cd apps/web  && npm run dev"
	@echo "  cd apps/api  && arq workers.arq_worker.WorkerSettings"

# ── DB ────────────────────────────────────────────────────────────
migrate:
	cd apps/api && alembic upgrade head

migrate-new:
	cd apps/api && alembic revision --autogenerate -m "$(name)"

seed:
	cd apps/api && python db/seed.py

# ── Logs ─────────────────────────────────────────────────────────
logs:
	docker compose -f infra/docker-compose.yml logs -f api worker

# ── Stop ─────────────────────────────────────────────────────────
down:
	docker compose -f infra/docker-compose.yml down

# ── Install deps ─────────────────────────────────────────────────
install:
	cd apps/api && pip install -r requirements.txt
	cd apps/web && npm install
