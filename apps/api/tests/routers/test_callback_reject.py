"""MEM2-C-2 — POST /memory/callbacks/{id}/reject ("that's not right", Ruling 5).

The router's job is narrow: 404 for anything that is not this user's callback
(including a non-UUID id, which would otherwise reach the uuid column as a 500),
hand the user's id to the service, and serialise what it returns. What the
rejection retires and blocks is executed against Postgres in
tests/db_live/test_memory_callbacks_live.py.

NOT flag-gated, by ruling: an offer made before CALLBACKS_ENABLED went off must
stay rejectable. Asserted below with the flag off (its test default).

Run: cd apps/api && pytest tests/routers/test_callback_reject.py -v
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services import callback_service as cs

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
CALLBACK_ID = "cccccccc-0000-0000-0000-000000000003"
URL = f"/api/v1/memory/callbacks/{CALLBACK_ID}/reject"


@pytest.fixture
def client():
    from main import app
    from auth import get_current_user
    from db.session import get_db

    user = MagicMock()
    user.id = USER_ID

    async def override_db():
        yield AsyncMock()

    async def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    yield TestClient(app, raise_server_exceptions=True)
    app.dependency_overrides.clear()


def test_a_rejection_returns_the_counts(client):
    out = cs.Rejection(callback_id=CALLBACK_ID, memory_id="m-1", already_rejected=False,
                       retired=1, blocked=2, blocked_near_duplicates=3)
    with patch.object(cs, "reject_callback", AsyncMock(return_value=out)) as reject, \
         patch.object(cs.config, "CALLBACKS_ENABLED", False):
        resp = client.post(URL)
    assert resp.status_code == 200
    assert resp.json() == {"callback_id": CALLBACK_ID, "memory_id": "m-1",
                           "already_rejected": False, "retired": 1, "blocked": 2,
                           "blocked_near_duplicates": 3}
    assert reject.await_args.kwargs == {"user_id": USER_ID, "callback_id": CALLBACK_ID}


def test_someone_elses_callback_is_a_404(client):
    with patch.object(cs, "reject_callback", AsyncMock(return_value=None)):
        assert client.post(URL).status_code == 404


def test_a_non_uuid_id_is_a_404_and_reaches_no_query(client):
    with patch.object(cs, "reject_callback", AsyncMock()) as reject:
        assert client.post("/api/v1/memory/callbacks/not-a-uuid/reject").status_code == 404
    reject.assert_not_awaited()
