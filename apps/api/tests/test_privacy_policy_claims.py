"""The Privacy Policy's checkable claims, pinned to the code that keeps them.

WHY THIS FILE EXISTS. The policy and the API shared no assertion. #588 had to
amend the policy because it promised a soft delete with a recovery window that
was never built, and that mismatch survived for as long as it did because a
legal document and an endpoint had nothing in common that could fail. TD-72
(#637) then found two more in §6 alone: a published one-hour OTP retention
window that nothing enforced, and a deletion promised as total that left the
person's email address in otp_codes. Both are the same defect class, and both
looked exactly like working software.

§6's claims are TRUE as of #637, which is what makes this file worth writing:
it pins a policy that is currently honest, rather than freezing a lie in place.

WHICH SIDE IS THE SOURCE OF TRUTH. The code is the source of truth for what the
product DOES. The policy is the source of truth for what was PROMISED. They are
not interchangeable, and when they drift the default is to FIX THE CODE — a
published promise is a commitment already made to real users, and silently
narrowing it is the worse failure. Amending and re-dating the policy is correct
only where the promise described a feature that was never built and is not
legally required. That is what #588 did, and it cost a version bump and a new
effective date, not just a reworded sentence. Every failure message below names
both options and the cost of the second.

WHAT IS NOT PINNED, and cannot be. These are commitments about human process,
infrastructure or third-party contracts, with no code to point at. A green run
here says nothing about any of them:

  §4  Standard Contractual Clauses; "we do not sell your personal data"
  §5  "We do not use your conversations to train models" — Anthropic's terms
  §6  "Server logs: up to 30 days" — Render's retention, not this repo's
  §7  restrict/object to processing; complaint to a DPA; "we respond within
      30 days"; the email route by which rights are exercised
  §9  TLS in transit; encryption at rest; need-to-know access
  §11 jurisdiction
  §12 "material changes will be communicated"

ALREADY PINNED ELSEWHERE, deliberately not duplicated here:
  §2  "Analytics events never contain the text of your conversations" —
      tests/test_analytics_call_sites.py
  §7  the support address the rights route publishes —
      tests/test_data_export.py::test_the_413_detail_names_the_published_support_address

PROSE IS MATCHED AS LITTLE AS POSSIBLE. Each claim is identified by the shortest
fragment that distinguishes it, never by its full sentence, so that an ordinary
copy edit survives. When a fragment does stop matching, the failure says so and
asks for the anchor to be re-pointed — it does not claim the code is broken.

AND ONE TEST REDDENS ON A WHOLESALE REWORDING, DELIBERATELY. That is a decision,
not a shortfall. Knowing a claim is still BEING MADE requires matching some
string, and any string can be rewritten; the only way to zero is to stop reading
the policy at all, which removes the cross-document link this file exists to
create. Shortening the anchors further was considered and rejected — a shorter
anchor identifies its claim less precisely and can start matching text elsewhere
as the document grows, which is the worse trade.

So a rewritten §6 puts a human back in the loop to confirm the code still matches
the new words. That is #588's lesson pointed forward rather than a cost to be
engineered away: the mismatch that PR had to fix survived precisely because
nobody was ever made to re-read the promise beside the code. DO NOT "fix" this by
loosening the anchors.
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from pathlib import Path

import pytest

# parents: [0]=tests [1]=api [2]=apps — the web app is apps/web.
POLICY_PATH = Path(__file__).resolve().parents[2] / "web" / "app" / "legal" / "privacy" / "page.tsx"
POLICY = POLICY_PATH.read_text(encoding="utf-8")

# Where the version and effective date live. ONE place — checked, because a
# policy amended in one spot and not the others is #588 in a different form.
VERSION_LINE = re.compile(r"Effective:\s*(.+?)\s*·\s*Version\s*([\d.]+)")


def _amend_or_fix(section: str, claim: str, code_site: str) -> str:
    """The failure message, in one shape everywhere.

    Names both documents, both remedies, and the cost of the second — a reader
    who reaches this has to know that amending is not free.
    """
    return (
        f"Privacy Policy {section} promises: {claim}\n"
        f"The code that keeps it is {code_site}, and it no longer does.\n"
        f"Either fix the code, or amend {section} and bump Version + Effective "
        f"date at apps/web/app/legal/privacy/page.tsx:24 — a published promise "
        f"is a commitment already made to users, so narrowing it is a policy "
        f"change with a version bump, not a test edit."
    )


def _claim_still_published(fragment: str, section: str) -> None:
    """Assert the policy still makes the claim this test is about.

    If this fails the claim was reworded or withdrawn, which is NOT a code
    defect — the anchor needs re-pointing, or the test needs deleting along with
    the promise.
    """
    assert fragment in POLICY, (
        f"the fragment identifying a {section} claim no longer appears in the "
        f"policy: {fragment!r}\n"
        f"If {section} was reworded, re-point this anchor at the new wording. "
        f"If the claim was withdrawn, delete this test with it — a test for a "
        f"promise nobody makes is worse than no test."
    )


# ── The version string is single-sourced ──────────────────────────────────────

def test_the_version_and_effective_date_appear_exactly_once():
    """Amending a policy in one place and not the others is the #588 failure in
    another form. Today there is one place, and this keeps it that way: a second
    copy is a second thing to forget."""
    matches = VERSION_LINE.findall(POLICY)
    assert len(matches) == 1, matches


def test_nothing_in_the_api_hardcodes_the_policy_version():
    """The API deliberately knows nothing about the policy's version or date. If
    it ever does, the two must be updated together, and this test should be
    replaced by one that asserts they agree."""
    api = Path(__file__).resolve().parents[1]
    effective, version = VERSION_LINE.findall(POLICY)[0]
    offenders = [
        str(p.relative_to(api))
        for p in api.rglob("*.py")
        if "__pycache__" not in str(p) and p.name != Path(__file__).name
        and (effective in p.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert offenders == [], offenders


# ── §7: the four rights that have an endpoint ────────────────────────────────

def test_section_7_access_has_an_endpoint():
    _claim_still_published("access the personal data", "§7")

    from routers.auth import router
    paths = {r.path for r in router.routes}
    assert "/auth/me" in paths and "/auth/me/export" in paths, _amend_or_fix(
        "§7", "the right to access the personal data we hold",
        "GET /auth/me and GET /auth/me/export in routers/auth.py",
    )


def test_section_7_rectification_has_an_endpoint():
    _claim_still_published("rectify inaccurate personal data", "§7")

    from routers.auth import router
    methods = {(r.path, m) for r in router.routes for m in getattr(r, "methods", set())}
    assert ("/auth/me", "PATCH") in methods, _amend_or_fix(
        "§7", "the right to rectify inaccurate personal data",
        "PATCH /auth/me in routers/auth.py",
    )


def test_section_7_erasure_has_an_endpoint():
    _claim_still_published("erase your account", "§7")

    from routers.auth import router
    methods = {(r.path, m) for r in router.routes for m in getattr(r, "methods", set())}
    assert ("/auth/me", "DELETE") in methods, _amend_or_fix(
        "§7", "the right to erase your account and associated personal data",
        "DELETE /auth/me in routers/auth.py",
    )


def test_section_7_portability_returns_a_versioned_machine_readable_document():
    """"Structured, machine-readable" is the portability wording, and a schema
    version is what makes the structure something a consumer can rely on."""
    _claim_still_published("machine-readable", "§7")

    from services.data_export_service import SCHEMA_VERSION, build_export
    assert isinstance(SCHEMA_VERSION, int) and SCHEMA_VERSION >= 1, _amend_or_fix(
        "§7", "your data in a structured, machine-readable format",
        "SCHEMA_VERSION in services/data_export_service.py",
    )
    assert callable(build_export)


# ── §6: retention and deletion ───────────────────────────────────────────────

def test_section_6_deletion_is_hard_not_soft():
    """THE #588 CLAIM. The policy used to describe a recovery window that did not
    exist; it now says the deletion is immediate and irreversible, and the code
    has no soft-delete flag on users to contradict that with."""
    _claim_still_published("deleted immediately and permanently", "§6")

    from models import User
    columns = {c.name for c in User.__table__.columns}
    assert "deleted_at" not in columns, _amend_or_fix(
        "§6", "deletion is immediate and permanent, and cannot be undone",
        "the absence of a soft-delete column on models.User",
    )

    import inspect
    from services import account_deletion_service
    source = inspect.getsource(account_deletion_service.delete_account)
    assert "delete(User)" in source, _amend_or_fix(
        "§6", "deletion is immediate and permanent",
        "the delete(User) statement in services/account_deletion_service.py",
    )


def test_section_6_otp_retention_is_enforced_not_merely_published():
    """FALSE UNTIL #637, which is why this file could not have been written
    before it. OTP_EXPIRY_MINUTES gates whether a code still VERIFIES; it never
    deleted anything. The purge is what makes the published hour true.

    Asserts the BOUND, not the schedule — the purge's own arithmetic is pinned in
    tests/workers/test_otp_purge.py. What matters here is that the number the
    policy publishes is the number the code is measured against.
    """
    _claim_still_published("OTP codes: up to 1 hour", "§6")

    from workers.arq_worker import (
        OTP_PURGE_CUTOFF_MINUTES, OTP_PURGE_INTERVAL_MINUTES, WorkerSettings,
    )

    published_minutes = 60
    worst_case = OTP_PURGE_CUTOFF_MINUTES + OTP_PURGE_INTERVAL_MINUTES
    assert worst_case <= published_minutes, _amend_or_fix(
        "§6", f"OTP codes are retained up to {published_minutes} minutes "
              f"(the purge's worst case is {worst_case})",
        "OTP_PURGE_CUTOFF_MINUTES + OTP_PURGE_INTERVAL_MINUTES in workers/arq_worker.py",
    )

    scheduled = {c.coroutine.__name__ for c in WorkerSettings.cron_jobs}
    assert "purge_expired_otp_codes" in scheduled, _amend_or_fix(
        "§6", "OTP codes are retained up to 1 hour",
        "the purge_expired_otp_codes cron in workers/arq_worker.py",
    )


def test_section_6_deletion_reaches_the_table_the_cascade_cannot_see():
    """The other claim #637 made true. otp_codes carries no user_id, so
    DELETE FROM users leaves it alone and the person's EMAIL ADDRESS survived a
    deletion the policy calls total. An email address is personal data and is not
    one of §6's three named exceptions."""
    _claim_still_published("all personal data associated with it", "§6")

    import inspect
    from services import account_deletion_service
    source = inspect.getsource(account_deletion_service)
    assert "_delete_otp_codes" in source, _amend_or_fix(
        "§6", "all personal data associated with the account is deleted",
        "_delete_otp_codes in services/account_deletion_service.py",
    )
    assert "OtpCode.email" in source, _amend_or_fix(
        "§6", "all personal data associated with the account is deleted",
        "the delete-by-email in _delete_otp_codes (otp_codes has no user_id, so "
        "the cascade cannot reach it)",
    )


def test_section_6_names_exactly_three_things_that_survive_a_deletion():
    """The exceptions are a closed list in the policy, so they must be a closed
    list in the code's account of itself. A fourth surviving table is either a
    defect or a policy amendment — TD-72 was the former, found this way."""
    for fragment in (
        "anonymized safety records",
        "billing records",
        "aggregated, non-identifying analytics",
    ):
        _claim_still_published(fragment, "§6")

    import inspect
    from services import account_deletion_service
    doc = inspect.getdoc(account_deletion_service) or ""
    assert "stripe_events" in doc and "safety_events" in doc, _amend_or_fix(
        "§6", "only anonymized safety records, billing records and aggregated "
              "analytics survive a deletion",
        "the WHAT SURVIVES A DELETION inventory in "
        "services/account_deletion_service.py's module docstring",
    )


def test_section_6_safety_records_are_anonymised_not_merely_unlinked():
    """"with all personal identifiers removed" is stronger than dropping the
    user_id: the message and conversation references are identifiers too, and
    #588 nulls all three."""
    _claim_still_published("personal identifiers removed", "§6")

    import inspect
    from services.account_deletion_service import _anonymise_safety_events
    source = inspect.getsource(_anonymise_safety_events)
    for column in ("user_id=None", "message_id=None", "conversation_id=None"):
        assert column in source, _amend_or_fix(
            "§6", "anonymized safety records with ALL personal identifiers removed",
            f"_anonymise_safety_events, which must null {column.split('=')[0]}",
        )


def test_section_6_disclaimer_audit_is_kept_until_account_deletion():
    """"Kept until account deletion" is a claim in both directions: the rows are
    retained while the account lives, AND they go when it does. The CASCADE is
    what makes the second half true."""
    _claim_still_published("kept until account deletion", "§6")

    from models import DisclaimerAcceptance
    fks = [
        fk for c in DisclaimerAcceptance.__table__.columns
        for fk in c.foreign_keys if fk.column.table.name == "users"
    ]
    assert fks, "disclaimer_acceptances no longer references users"
    assert all(fk.ondelete == "CASCADE" for fk in fks), _amend_or_fix(
        "§6", "the disclaimer acceptance audit trail is kept until account deletion",
        "the ON DELETE CASCADE on disclaimer_acceptances.user_id",
    )


# ── §2 and §10: what is collected ────────────────────────────────────────────

def test_section_2_stores_the_three_disclaimer_fields_it_names():
    """§2 tells the reader exactly what the disclaimer record contains. Each named
    field must exist, and — the direction that matters for a privacy policy — a
    field NOT named must not be quietly collected alongside them."""
    _claim_still_published("timestamp, IP address, and browser", "§2")

    from models import DisclaimerAcceptance
    columns = {c.name for c in DisclaimerAcceptance.__table__.columns}
    for named in ("accepted_at", "ip_address", "user_agent"):
        assert named in columns, _amend_or_fix(
            "§2", "the disclaimer record includes timestamp, IP address and browser",
            f"models.DisclaimerAcceptance.{named}",
        )


def test_section_10_records_the_age_confirmation_it_requires():
    _claim_still_published("under 18", "§10")

    from models import DisclaimerAcceptance
    col = DisclaimerAcceptance.__table__.columns.get("confirmed_age_18")
    assert col is not None and not col.nullable, _amend_or_fix(
        "§10", "the Service is not intended for users under 18",
        "models.DisclaimerAcceptance.confirmed_age_18, which must be non-nullable",
    )


# ── The blind spot, named ────────────────────────────────────────────────────

def test_the_uncheckable_claims_are_listed_in_this_module_docstring():
    """A green run here is not a compliant policy, and the module docstring is
    where that is said. This asserts the disclaimer exists rather than trusting a
    reader to scroll: if the WHAT IS NOT PINNED block is ever deleted, a future
    reader would have no way to know how much of §4, §5, §9 and §11 this file
    never touched."""
    doc = __doc__ or ""
    assert "WHAT IS NOT PINNED" in doc
    for section in ("§4", "§5", "§9", "§11", "§12"):
        assert section in doc, f"{section} is unpinned but unlisted"
