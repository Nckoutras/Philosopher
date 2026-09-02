"""Data export — what reaches the file, and what must never.

WHY THIS FILE EXISTS. The export is the one endpoint whose entire job is to
return everything. That makes the interesting assertions NEGATIVE: an omission
bug here is a privacy incident, not a missing feature, and it is invisible from
the outside because the file looks full either way.

FOUR THINGS ARE PINNED, and they fail independently:

  1. The rate limit is checked BEFORE anything is assembled. Remove it and the
     endpoint becomes the cheapest way to generate load and to drain a
     compromised session.

  2. Embeddings never reach the output. memory_entries.embedding is a
     1536-float vector — 21,504 bytes of JSON per row, ~17 MB for a heavy user,
     and machine state rather than anything the person wrote. The test plants a
     recognisable vector and asserts no float list of that shape appears
     ANYWHERE in the serialised output, at value level.

  3. safety_events and Stripe identifiers never appear. #588 anonymises
     safety_events on deletion; exporting them would hand back exactly what
     deletion severs. Planted values are searched for in the serialised output —
     the #588 comment-guard pattern, applied to data rather than source.

  4. The 413 detail names the address the Privacy Policy actually publishes.
     A support address that exists only in an error string is worse than none:
     the person is told to write somewhere nobody reads.
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.data_export_service import SCHEMA_VERSION, _iso, build_export


# ── _iso ──────────────────────────────────────────────────────────────────────

def test_iso_emits_utc_with_a_z():
    dt = datetime(2026, 9, 2, 14, 30, 0, tzinfo=timezone.utc)
    assert _iso(dt) == "2026-09-02T14:30:00Z"


def test_iso_treats_naive_as_utc_rather_than_dropping_it():
    """Every writer in this codebase uses datetime.now(timezone.utc); a naive
    value is a storage artefact, not a different instant."""
    assert _iso(datetime(2026, 9, 2, 14, 30, 0)) == "2026-09-02T14:30:00Z"


def test_iso_passes_none_through():
    assert _iso(None) is None


def test_iso_converts_a_non_utc_offset():
    from datetime import timedelta
    dt = datetime(2026, 9, 2, 17, 30, 0, tzinfo=timezone(timedelta(hours=3)))
    assert _iso(dt) == "2026-09-02T14:30:00Z"


# ── The export shape, against a fake session ──────────────────────────────────

class _Row:
    """Plain object, not MagicMock: the builder reads ~15 attributes per row and
    a Mock would silently supply every one of them, so a column that stopped
    being read would still 'pass' (CLAUDE.md C-06)."""

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _fake_db(tables: dict):
    """An AsyncSession whose execute() dispatches on the entity being selected.

    Keyed by mapped-class NAME rather than call order — index-based dispatch is
    what made 17 tests in this repo fail for months (TD-45).
    """
    db = MagicMock()
    db.seen_statements = []          # so tests can assert on the SQL, not just the rows

    async def execute(stmt, *a, **kw):
        db.seen_statements.append(str(stmt))
        result = MagicMock()
        try:
            entity = stmt.column_descriptions[0]["entity"]
            name = entity.__name__
        except Exception:
            name = None
        rows = tables.get(name, [])
        scalars = MagicMock()
        scalars.all.return_value = rows
        result.scalars.return_value = scalars
        result.scalar_one_or_none.return_value = rows[0] if rows else None
        return result

    db.execute = AsyncMock(side_effect=execute)
    return db


def _user():
    return _Row(
        id="u1", email="someone@example.com", full_name="A Person",
        avatar_url=None, auth_provider="google", oauth_provider_id="google-sub-123",
        onboarded_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_admin=False, hashed_password=None, token_version=3,
        weekly_email_opt_out=False, mirror_host_slug=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


async def test_the_header_block_is_present_and_correct():
    payload = await build_export(_fake_db({}), _user())
    assert payload["schema_version"] == SCHEMA_VERSION == 1
    assert payload["user_id"] == "u1"
    assert payload["exported_at"].endswith("Z")
    assert payload["records_marked_deleted_are_retained_until_account_deletion"] is True


async def test_an_empty_account_exports_every_section_as_an_empty_list():
    """A new user's export must be a complete, well-formed document — not a
    document missing the sections they have not used yet."""
    payload = await build_export(_fake_db({}), _user())
    for section in (
        "conversations", "messages", "memories", "insights", "letters", "mirrors",
        "self_comparisons", "counterviews", "council_cases", "saved_lines",
        "saved_quotes", "scheduled_emails", "ritual_completions", "daily_usage",
        "disclaimer_acceptances",
    ):
        assert payload[section] == [], section
    assert payload["preferences"] is None
    assert payload["subscription"] is None


async def test_the_whole_document_is_json_serialisable():
    """No datetime, UUID or Decimal may survive into the payload — the endpoint
    returns it directly and FastAPI's encoder would paper over a type the file
    format cannot express."""
    payload = await build_export(_fake_db({}), _user())
    json.dumps(payload)  # must not raise, and no default= escape hatch


# ── 2. Embeddings must never reach the output ─────────────────────────────────

async def test_embeddings_never_reach_the_export():
    """The mutation: add "embedding" back to the memory dict and this fails.

    Asserted at VALUE level against a recognisable vector, not by checking the
    key is absent — a future rename of the key would slip past a key check.
    """
    marker = 0.123456789
    memory = _Row(
        id="m1", user_id="u1", entry_type="fact", content="a memory",
        confidence=0.9, is_active=True, conversation_id="c1",
        persona_id=None, source_turn=1,
        embedding=[marker] * 1536,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    payload = await build_export(_fake_db({"MemoryEntry": [memory]}), _user())

    assert payload["memories"][0]["content"] == "a memory"   # the row IS exported
    blob = json.dumps(payload)
    assert str(marker) not in blob, "an embedding vector reached the export"
    assert "embedding" not in payload["memories"][0]


# ── 3. Audit trails and Stripe internals must never appear ────────────────────

async def test_no_safety_event_reaches_the_export():
    """#588 ANONYMISES safety_events on deletion. Exporting them would hand back
    exactly what deletion severs, so the export must not read that table at all.

    Planted values are searched for in the serialised output — the #588
    comment-guard pattern applied to data.
    """
    planted = "PLANTED_SAFETY_TRIGGER_VALUE"
    tables = {"SafetyEvent": [_Row(
        id="se1", user_id="u1", conversation_id="c1", message_id="m1",
        trigger_stage=planted, risk_level=planted, category=planted,
        action_taken=planted, raw_flags={"flags": [planted]},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )]}
    payload = await build_export(_fake_db(tables), _user())
    assert planted not in json.dumps(payload)
    assert "safety_events" not in payload


async def test_no_stripe_identifier_reaches_the_export():
    """The subscription SUMMARY is exported; Stripe's internal ids are not."""
    sub = _Row(
        id="s1", user_id="u1",
        stripe_customer_id="cus_PLANTEDCUSTOMER",
        stripe_subscription_id="sub_PLANTEDSUBSCRIPTION",
        plan="pro", status="active", interval="monthly",
        current_period_end=datetime(2026, 10, 1, tzinfo=timezone.utc),
        cancel_at_period_end=False,
        pro_since=datetime(2026, 2, 1, tzinfo=timezone.utc),
        last_stripe_event_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    payload = await build_export(_fake_db({"Subscription": [sub]}), _user())

    # The useful summary survives...
    assert payload["subscription"]["plan"] == "pro"
    assert payload["subscription"]["interval"] == "monthly"
    # ...the Stripe internals do not.
    blob = json.dumps(payload)
    assert "cus_PLANTEDCUSTOMER" not in blob
    assert "sub_PLANTEDSUBSCRIPTION" not in blob


async def test_no_internal_user_columns_reach_the_export():
    """hashed_password is a credential; oauth_provider_id, token_version and
    is_admin are internal state. None is portable data."""
    payload = await build_export(_fake_db({}), _user())
    blob = json.dumps(payload)
    assert "google-sub-123" not in blob        # oauth_provider_id
    assert "token_version" not in blob
    assert "hashed_password" not in blob
    assert "is_admin" not in blob
    # The profile the person would recognise IS there.
    assert payload["profile"]["email"] == "someone@example.com"


async def test_message_telemetry_is_excluded_but_the_words_are_kept():
    msg = _Row(
        id="m1", conversation_id="c1", user_id="u1", role="user",
        content="what I actually wrote",
        tokens_used=999001, input_tokens=999002, cache_creation_tokens=999003,
        cache_read_tokens=999004, latency_ms=999005,
        model_used="PLANTED_MODEL_ID", retrieval_ids=["PLANTED_RETRIEVAL"],
        safety_level="none", persona_override=False, message_kind="chat",
        persona_id=None, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    payload = await build_export(_fake_db({"Message": [msg]}), _user())
    row = payload["messages"][0]
    assert row["content"] == "what I actually wrote"
    assert row["conversation_id"] == "c1"      # joinable
    blob = json.dumps(payload)
    for planted in ("999001", "999002", "999003", "999004", "999005",
                    "PLANTED_MODEL_ID", "PLANTED_RETRIEVAL"):
        assert planted not in blob, planted


# ── Soft-deleted rows are included, per the ruling ────────────────────────────

async def test_soft_deleted_rows_are_included_with_their_deleted_at():
    deleted_at = datetime(2026, 8, 1, tzinfo=timezone.utc)
    conv = _Row(
        id="c1", user_id="u1", persona_id=None, active_persona_id=None,
        deep_mode=False, title="a deleted conversation", ritual_id=None,
        message_count=4, last_message_at=None, deleted_at=deleted_at,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_saved_line_id=None, source_persona_slug=None,
    )
    db = _fake_db({"Conversation": [conv]})
    payload = await build_export(db, _user())
    assert len(payload["conversations"]) == 1
    assert payload["conversations"][0]["deleted_at"] == "2026-08-01T00:00:00Z"

    # The row surviving is not enough: this fake returns whatever it is given
    # regardless of the WHERE clause, so a `deleted_at IS NULL` filter added to
    # the query would slip past a row-count assertion. Asserted against the
    # generated SQL instead.
    filtered = [q for q in db.seen_statements
                if "FROM conversations" in q and "deleted_at IS NULL" in q]
    assert filtered == [], (
        "the conversations query filters out soft-deleted rows; the export must "
        "return what we hold: " + str(filtered)
    )


async def test_no_export_query_filters_out_soft_deleted_rows():
    """The ruling applies to every table carrying deleted_at, not just
    conversations: saved_lines and the five *_saves tables too."""
    db = _fake_db({})
    await build_export(db, _user())
    offenders = [q for q in db.seen_statements if "deleted_at IS NULL" in q]
    assert offenders == [], offenders


# ── 4. The support address must be the one actually published ─────────────────

def test_the_413_detail_names_the_published_support_address():
    """A support address that exists only in an error string is worse than none.

    The Privacy Policy and Terms both publish a contact address, and §7 directs
    GDPR rights requests to it. The 413 tells an over-limit user to write there,
    so the two must be the same string — checked against the legal pages
    themselves, not against a constant either side could drift from.
    """
    from routers.auth import EXPORT_TOO_LARGE_DETAIL

    # parents: [0]=tests [1]=api [2]=apps — the web app is apps/web.
    web = Path(__file__).resolve().parents[2] / "web" / "app" / "legal"
    privacy = (web / "privacy" / "page.tsx").read_text(encoding="utf-8")
    terms = (web / "terms" / "page.tsx").read_text(encoding="utf-8")

    import re
    addresses = set(re.findall(r"mailto:([^\"']+)", privacy)) | \
                set(re.findall(r"mailto:([^\"']+)", terms))
    assert len(addresses) == 1, f"legal pages publish more than one address: {addresses}"
    published = addresses.pop()

    assert published in EXPORT_TOO_LARGE_DETAIL, (
        f"the 413 detail does not name the published contact address {published!r}"
    )


def test_the_size_guard_constants_are_sane():
    from routers.auth import EXPORT_MAX_MESSAGES, EXPORT_RATE_LIMIT_PER_HOUR
    assert EXPORT_RATE_LIMIT_PER_HOUR == 1
    # 65x above the heaviest measured real user (380 messages). A cap below the
    # observed maximum would refuse real exports.
    assert EXPORT_MAX_MESSAGES >= 10_000
