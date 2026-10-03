"""GET /health/deep: the verdict rule, the payload contract, and the one number
it shares with the workflow (OBS-001).

The checks are patched at their SOURCE functions rather than through a mocked
session: a MagicMock session answers every scalar with a Mock, and "is the
revision at head?" would then be neither True nor False but truthy (C-06).
"""
import os
import re
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import health
from routers.health import deep_health, router
from workers.heartbeat import HEARTBEAT_EVERY_MINUTES, HEARTBEAT_STALE_AFTER_MINUTES

HEAD = "071_memory_provenance_backfill"

# The payload is PUBLIC. This is the whole allowed key set — booleans, ages and
# the two alembic ids — and a new key must be added here on purpose, having
# answered "could this be read by someone it was not meant for?".
ALLOWED_KEYS = {
    "status", "checked_at",
    "db", "migrations_at_head", "worker_alive", "queue_reachable", "scheduler_running",
    "heartbeat_age_minutes", "heartbeat_stale_after_minutes",
    "db_revision", "code_head",
}


def _healthy(**overrides):
    """Every check green unless overridden. Returns the patch context managers."""
    values = {
        "_db_select_one": True,
        "_db_revision": HEAD,
        "_heartbeat_age_minutes": 4,
        "_queue_ping": True,
    }
    values.update({k: v for k, v in overrides.items() if k in values})
    patches = [
        patch.object(health, name, new=AsyncMock(return_value=value))
        for name, value in values.items()
    ]
    patches.append(patch.object(health, "_code_head", return_value=overrides.get("_code_head", HEAD)))
    patches.append(patch.object(health, "_scheduler_running", return_value=overrides.get("_scheduler_running", True)))
    return patches


async def _run(**overrides):
    patches = _healthy(**overrides)
    for p in patches:
        p.start()
    try:
        return await deep_health(SimpleNamespace(arq_queue=object()))
    finally:
        for p in patches:
            p.stop()


# ── the verdict ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_green_is_200_ok():
    status, payload = await _run()
    assert status == 200
    assert payload["status"] == "ok"
    assert all(payload[k] is True for k in (
        "db", "migrations_at_head", "worker_alive", "queue_reachable", "scheduler_running",
    ))


@pytest.mark.asyncio
@pytest.mark.parametrize("override, key", [
    ({"_db_select_one": False}, "db"),
    ({"_db_revision": "070_memory_epistemic_core"}, "migrations_at_head"),
    ({"_db_revision": None}, "migrations_at_head"),
    ({"_code_head": None}, "migrations_at_head"),
    ({"_heartbeat_age_minutes": HEARTBEAT_STALE_AFTER_MINUTES + 1}, "worker_alive"),
    ({"_heartbeat_age_minutes": None}, "worker_alive"),
    ({"_queue_ping": False}, "queue_reachable"),
    ({"_scheduler_running": False}, "scheduler_running"),
])
async def test_any_single_failure_is_503_and_names_the_check(override, key):
    status, payload = await _run(**override)
    assert status == 503
    assert payload["status"] == "degraded"
    assert payload[key] is False
    others = {"db", "migrations_at_head", "worker_alive", "queue_reachable", "scheduler_running"} - {key}
    assert all(payload[k] is True for k in others), "one failure must not mask the others"


@pytest.mark.asyncio
async def test_a_heartbeat_exactly_at_the_threshold_is_still_alive():
    status, payload = await _run(_heartbeat_age_minutes=HEARTBEAT_STALE_AFTER_MINUTES)
    assert status == 200 and payload["worker_alive"] is True


@pytest.mark.asyncio
async def test_a_check_that_raises_is_a_false_not_a_500():
    """The route must answer. A pool that raises becomes db=False and a 503;
    the exception is logged at WARNING, never re-raised."""
    with patch.object(health, "_db_select_one", new=AsyncMock(side_effect=RuntimeError("pool gone"))), \
         patch.object(health, "_db_revision", new=AsyncMock(return_value=HEAD)), \
         patch.object(health, "_heartbeat_age_minutes", new=AsyncMock(return_value=1)), \
         patch.object(health, "_queue_ping", new=AsyncMock(return_value=True)), \
         patch.object(health, "_code_head", return_value=HEAD), \
         patch.object(health, "_scheduler_running", return_value=True):
        status, payload = await deep_health(SimpleNamespace(arq_queue=object()))
    assert status == 503
    assert payload["db"] is False


@pytest.mark.asyncio
async def test_a_check_that_hangs_is_cut_at_the_ceiling():
    import asyncio

    async def never():
        await asyncio.sleep(60)

    with patch.object(health, "CHECK_TIMEOUT_S", 0.05), \
         patch.object(health, "_db_select_one", new=never), \
         patch.object(health, "_db_revision", new=AsyncMock(return_value=HEAD)), \
         patch.object(health, "_heartbeat_age_minutes", new=AsyncMock(return_value=1)), \
         patch.object(health, "_queue_ping", new=AsyncMock(return_value=True)), \
         patch.object(health, "_code_head", return_value=HEAD), \
         patch.object(health, "_scheduler_running", return_value=True):
        status, payload = await deep_health(SimpleNamespace(arq_queue=object()))
    assert status == 503 and payload["db"] is False


@pytest.mark.asyncio
async def test_no_queue_on_app_state_is_queue_unreachable():
    """The lifespan-failed-silently shape: app.state has no arq_queue at all."""
    assert await health._queue_ping(None) is False


# ── the payload contract (ruling 2: public, so nothing worth reading) ──────────

@pytest.mark.asyncio
async def test_the_payload_carries_exactly_the_allowed_keys():
    _, payload = await _run()
    assert set(payload) == ALLOWED_KEYS


@pytest.mark.asyncio
async def test_the_payload_holds_only_booleans_ints_revision_ids_and_a_timestamp():
    _, payload = await _run(_db_select_one=False)
    for key, value in payload.items():
        if key in ("status",):
            assert value in ("ok", "degraded")
        elif key == "checked_at":
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", value)
        elif key in ("db_revision", "code_head"):
            assert value is None or re.fullmatch(r"[0-9a-z_]{1,32}", value)
        elif key in ("heartbeat_age_minutes", "heartbeat_stale_after_minutes"):
            assert value is None or isinstance(value, int)
        else:
            assert isinstance(value, bool), key


# ── the route ─────────────────────────────────────────────────────────────────

def test_the_route_is_public_and_returns_the_verdict_as_its_status_code():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    patches = _healthy(_queue_ping=False)
    for p in patches:
        p.start()
    try:
        resp = client.get("/health/deep")
    finally:
        for p in patches:
            p.stop()
    assert resp.status_code == 503
    assert resp.json()["queue_reachable"] is False


def test_plain_health_is_still_a_constant():
    """Ruling 1: /health stays the cheap liveness probe. It checks nothing."""
    import inspect

    import main

    src = inspect.getsource(main.health)
    assert "AsyncSessionLocal" not in src and "await" not in src


# ── the code head is read from the migrations directory, wherever cwd is ──────

def test_the_code_head_is_the_newest_migration_and_does_not_depend_on_cwd(tmp_path, monkeypatch):
    """alembic.ini's script_location is cwd-relative; this must not be. Asserted
    against the repo's own migration files rather than a literal, so adding a
    migration does not break it and a wrong directory would."""
    api_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    versions = os.path.join(api_dir, "db", "migrations", "versions")
    newest = sorted(f for f in os.listdir(versions) if re.match(r"\d{3}_.*\.py$", f))[-1]

    monkeypatch.chdir(tmp_path)
    assert health._code_head() == newest[:-3]


# ── the one number shared with the workflow ───────────────────────────────────

def test_the_stale_threshold_is_four_beats_and_the_workflow_agrees():
    """workers/heartbeat.py and .github/workflows/worker-liveness.yml each carry
    40. Neither can import the other, so this test is the coupling."""
    assert HEARTBEAT_STALE_AFTER_MINUTES == 4 * HEARTBEAT_EVERY_MINUTES == 40
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))))
    workflow = open(os.path.join(repo_root, ".github", "workflows", "worker-liveness.yml"), encoding="utf-8").read()
    default = re.search(r"default:\s*'(\d+)'", workflow)
    assert default and int(default.group(1)) == HEARTBEAT_STALE_AFTER_MINUTES
    assert "/health/deep" in workflow
