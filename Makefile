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


.PHONY: state state-help

state:
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  Generating PROJECT_STATE_v4.md..."
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@if [ ! -f scripts/generate_state.txt ]; then \
		echo "ERROR: scripts/generate_state.txt not found"; \
		echo "Run 'make state-help' for setup instructions"; \
		exit 1; \
	fi
	@if ! command -v claude >/dev/null 2>&1; then \
		echo "ERROR: 'claude' CLI not found in PATH"; \
		echo "Install Claude Code: https://docs.claude.com/claude-code"; \
		exit 1; \
	fi
	@claude < scripts/generate_state.txt
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  ✓ PROJECT_STATE_v4.md updated"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  Next steps:"
	@echo "  1. Review changes:   git diff docs/PROJECT_STATE_v4.md"
	@echo "  2. Commit:           git add docs/PROJECT_STATE_v4.md && git commit -m 'chore: update state'"
	@echo "  3. Push:             git push"
	@echo "  4. Re-upload to Claude.ai Project Knowledge:"
	@echo "     - Settings → Projects → Philosopher → Project Knowledge"
	@echo "     - Delete old PROJECT_STATE_v4.md"
	@echo "     - Upload docs/PROJECT_STATE_v4.md"
	@echo ""

state-help:
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  make state — Setup & Usage"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "WHAT IT DOES:"
	@echo "  Calls Claude Code to read the repo and rewrite docs/PROJECT_STATE_v4.md"
	@echo "  with a fresh snapshot of personas, schema, routers, and pending work."
	@echo ""
	@echo "ONE-TIME SETUP:"
	@echo "  1. Install Claude Code:"
	@echo "       npm install -g @anthropic-ai/claude-code"
	@echo "       (or follow https://docs.claude.com/claude-code)"
	@echo ""
	@echo "  2. Authenticate Claude Code:"
	@echo "       claude login"
	@echo ""
	@echo "  3. Verify scripts/generate_state.txt exists in repo"
	@echo "     (provided in initial setup; do not edit unless updating logic)"
	@echo ""
	@echo "  4. Verify docs/PROJECT_STATE_v4.md exists in repo"
	@echo "     (initial seed file is committed; subsequent runs update in place)"
	@echo ""
	@echo "USAGE:"
	@echo "  make state            Regenerate PROJECT_STATE.md"
	@echo "  make state-help       Show this help"
	@echo ""
	@echo "FREQUENCY:"
	@echo "  Run before opening a new technical thread on Claude.ai."
	@echo "  Typical cadence: 2-3 times per week."
	@echo ""
	@echo "WHAT IS PRESERVED:"
	@echo "  Sections marked 'MANUAL — preserved across regenerations' in"
	@echo "  PROJECT_STATE.md are NOT auto-updated. Edit them by hand for"
	@echo "  decisions, blockers, and qualitative notes."
	@echo ""

