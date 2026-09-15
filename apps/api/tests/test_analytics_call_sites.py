"""What each backend call site actually sends.

test_analytics_registry.py checks that names are declared and declared names
fire. This file checks the payloads: the property KEYS at each site, and that no
property VALUE could be free text.

The value rule is the one that matters. A property named `week` looks harmless
and stays harmless; the leak this guards against is a future edit that puts
`letter.payload["title"]` behind a well-behaved name. So the assertions here are
about SHAPE — ids, slugs, enums, counts, buckets — not about specific values
that would need fixtures.

Keys are read from the source AST rather than by executing the endpoints: the
sites sit behind Stripe webhooks, an SSE generator, an arq worker and six
auth-gated routes, and standing all of that up would test the plumbing rather
than the payload. What is asserted is exactly what a reviewer would check by
eye, made mechanical.
"""
import ast
import pathlib

import pytest

from constants import ANALYTICS_EVENTS

API_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Values that are allowed to appear as a property, by AST shape. Anything that
# is a plain string literal must additionally look like an enum (see below).
_SAFE_CALL_NAMES = {
    "len",           # counts
    "bool",          # flags
    "str",           # id coercion
    "_tenure_days",  # int days
    "_interval_of",  # 'month' | 'year'
    "_latency_bucket",
    "strftime",      # ISO week bucket
    "_source_of",       # allow-listed enum from Stripe metadata
    "_cancel_reason",   # closed 3-value enum derived from Stripe
    "_cancel_feedback", # closed Stripe enum, never the free-text `comment`
    # Data export. Both read the assembled payload, and both are registered
    # here rather than allowed implicitly: _export_record_count SUMS list
    # lengths and never reads a value, _export_size_bucket measures the
    # serialised length and returns one of four fixed strings. Neither can
    # return anything a user wrote.
    "_export_record_count",  # int, sum of section lengths
    "_export_size_bucket",   # closed 4-value enum
    # Γ-3. Hours since a conversation's last message, mapped to one of six fixed
    # strings (five buckets + "unknown"). Takes a TIMESTAMP and returns a bucket
    # — there is no path by which user text could enter it, and the test below
    # pins the closed set so a future edit cannot widen it into free text.
    "gap_bucket",
}


def _track_calls():
    for path in API_ROOT.rglob("*.py"):
        rel = path.relative_to(API_ROOT).as_posix()
        if rel.startswith("tests/") or rel.startswith(".venv/"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "track"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "analytics_service"
            ):
                yield rel, node


def _payload_keys(node) -> set[str] | None:
    """The literal dict keys passed as the 3rd argument, or None if not a literal."""
    if len(node.args) < 3:
        return set()
    payload = node.args[2]
    if not isinstance(payload, ast.Dict):
        return None
    keys = set()
    for k in payload.keys:
        if not isinstance(k, ast.Constant):
            return None
        keys.add(k.value)
    return keys


def test_every_payload_is_a_literal_dict():
    """A computed payload cannot be reviewed, here or in a pull request."""
    for rel, node in _track_calls():
        assert _payload_keys(node) is not None, (
            f"{rel}:{node.lineno} passes a non-literal properties dict — keep it a "
            f"dict literal so the keys can be checked"
        )


def test_payload_keys_match_the_registry():
    """Each site sends a subset of what its event declares. A subset rather than
    an exact match: signup_completed's password path has no `method` in the same
    sense as the OTP path, and a site is allowed to omit a property it cannot
    know. Sending an UNDECLARED key is the error."""
    for rel, node in _track_calls():
        name = node.args[0].value
        keys = _payload_keys(node) or set()
        declared = set(ANALYTICS_EVENTS.get(name, []))
        extra = keys - declared
        assert not extra, (
            f"{rel}:{node.lineno} {name} sends undeclared properties {sorted(extra)} "
            f"— add them to ANALYTICS_EVENTS or drop them"
        )


def test_every_declared_property_is_actually_sent():
    """The other half of the registry rule, and the one that was missing.

    test_payload_keys_match_the_registry catches a site sending an UNDECLARED
    key. Nothing caught the reverse: a property declared in ANALYTICS_EVENTS
    that no call site ever sends. That is the same aspirational drift the whole
    registry exists to stop — `used_memory` was declared on both council events
    while council_service passes memories=[] unconditionally, and it survived
    the first pass of these tests.

    A property is satisfied if ANY call site for that event sends it: a site is
    allowed to omit what it cannot know, but the taxonomy may not declare a
    property nothing anywhere populates.
    """
    sent: dict[str, set] = {}
    for _rel, node in _track_calls():
        name = node.args[0].value
        sent.setdefault(name, set()).update(_payload_keys(node) or set())

    unsent = {}
    for name, props in ANALYTICS_EVENTS.items():
        missing = sorted(set(props) - sent.get(name, set()))
        if missing:
            unsent[name] = missing
    assert not unsent, (
        "these properties are declared but no call site sends them — send them "
        f"or delete the declaration: {unsent}"
    )


def test_no_property_value_can_be_free_text():
    """The leak this exists to prevent.

    Every property value must be one of: a literal that looks like an enum, a
    number, a boolean, None, an attribute access (an id or slug off a model), a
    subscript, or a call from the allow-list above. A bare Name is allowed only
    when it is a local that the value tests below cover.

    What is REJECTED is the shape a leak takes: an f-string, a concatenation, a
    .format(), a slice of user text, or a string literal long enough to be prose.
    """
    offenders = []
    for rel, node in _track_calls():
        if len(node.args) < 3 or not isinstance(node.args[2], ast.Dict):
            continue
        for key, value in zip(node.args[2].keys, node.args[2].values):
            kname = key.value if isinstance(key, ast.Constant) else "?"
            where = f"{rel}:{node.lineno} {node.args[0].value}.{kname}"

            if isinstance(value, ast.JoinedStr):
                offenders.append(f"{where} is an f-string")
                continue
            if isinstance(value, ast.BinOp):
                offenders.append(f"{where} is a concatenation/expression")
                continue
            if isinstance(value, ast.Constant):
                if isinstance(value.value, str):
                    if len(value.value) > 32 or " " in value.value:
                        offenders.append(f"{where} is a prose literal")
                continue
            # `await f()` is ast.Await wrapping ast.Call. Unwrapped here because
            # the bare isinstance(value, ast.Call) below did not match it, so an
            # awaited helper reached the permissive tail and was never checked —
            # a hole this PR would have been the first to walk through.
            if isinstance(value, ast.Await):
                value = value.value

            if isinstance(value, ast.Call):
                fn = value.func
                fname = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "?")
                if fname not in _SAFE_CALL_NAMES:
                    offenders.append(f"{where} calls {fname}(), which is not allow-listed")
                continue
            # Attribute / Name / Subscript / IfExp / BoolOp: ids, slugs, locals.
    assert not offenders, offenders


def test_the_council_matter_never_becomes_a_property():
    """The single most sensitive string on any instrumented route: the user's
    question, in their own words. Asserted by name AND by the absence of the
    local that holds it."""
    for rel, node in _track_calls():
        if not rel.endswith("council.py") and not rel.endswith("council_service.py"):
            continue
        for value in (node.args[2].values if len(node.args) > 2 and isinstance(node.args[2], ast.Dict) else []):
            src = ast.dump(value)
            assert "'matter'" not in src and "matter" not in src, (
                f"{rel}:{node.lineno} references `matter` in an analytics property"
            )


@pytest.mark.parametrize(
    "event,expected",
    [
        ("conversation_started", {"persona_slug", "ritual_id", "seeded_topic", "via"}),
        ("council_started", {"source"}),
        ("council_completed", {"member_count", "latency_bucket"}),
        ("share_created", {"artifact_type"}),
        ("letter_delivered", {"week", "host", "reading_label"}),
        ("subscription_canceled", {"plan", "tenure_days", "reason",
                                   "cancel_feedback", "last_14d_features"}),
        ("subscription_activated", {"plan", "interval", "source"}),
        ("checkout_started", {"plan", "interval", "source"}),
        ("data_exported", {"conversation_count", "record_count", "size_bucket"}),
    ],
)
def test_specific_sites_send_the_expected_keys(event, expected):
    """Pins the keys per event so a silently dropped property is a failure. Every
    site for the event must agree — share_created fires from six routers and all
    six must carry artifact_type."""
    seen = [
        (rel, node.lineno, _payload_keys(node) or set())
        for rel, node in _track_calls()
        if node.args[0].value == event
    ]
    assert seen, f"{event} has no call site"
    for rel, lineno, keys in seen:
        assert keys == expected, f"{rel}:{lineno} {event} sends {sorted(keys)}, expected {sorted(expected)}"


def test_conversation_started_fires_from_every_creation_endpoint():
    """Three doors into a conversation, three events. A new creation endpoint
    that forgets this leaves the funnel silently short at the top — the failure
    mode that is hardest to notice, because the number still looks plausible."""
    vias = set()
    for rel, node in _track_calls():
        if node.args[0].value != "conversation_started":
            continue
        for k, v in zip(node.args[2].keys, node.args[2].values):
            if isinstance(k, ast.Constant) and k.value == "via":
                assert isinstance(v, ast.Constant), f"{rel}: via must be a literal enum"
                vias.add(v.value)
    assert vias == {"direct", "cross_persona", "reading_revisit"}, vias


def test_share_created_fires_from_every_share_endpoint():
    """Six artifact types, six routers. A new share surface that forgets the
    event is invisible in the funnel, so the count is pinned."""
    kinds = set()
    for rel, node in _track_calls():
        if node.args[0].value != "share_created":
            continue
        payload = node.args[2]
        for k, v in zip(payload.keys, payload.values):
            if isinstance(k, ast.Constant) and k.value == "artifact_type":
                assert isinstance(v, ast.Constant), f"{rel}: artifact_type must be a literal"
                kinds.add(v.value)
    assert kinds == {"screenshot", "counterview", "quote", "mirror", "letter", "council"}, kinds


# ── `source` is the one property name that has been a bare str twice ─────────

_SOURCE_HELPERS = {
    # Reads Stripe metadata, which is OUR OWN CheckoutRequest.source making a
    # round trip — written at create_checkout from a pattern-bound field. Listed
    # by name rather than allowed as "some call" so a future helper that reads an
    # unvalidated field has to be added here deliberately.
    "_source_of",
}


def _schema_classes():
    """{class name: ClassDef} for apps/api/schemas/__init__.py."""
    tree = ast.parse((API_ROOT / "schemas" / "__init__.py").read_text(encoding="utf-8"))
    return {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}


def _field_has_pattern(cls_node, field: str) -> bool:
    for st in cls_node.body:
        if isinstance(st, ast.AnnAssign) and getattr(st.target, "id", None) == field:
            if not isinstance(st.value, ast.Call):
                return False
            return any(kw.arg == "pattern" for kw in st.value.keywords)
    return False


def _functions_with_track_calls():
    """(rel, FunctionDef, track-call node) for every site, so a value that is a
    bare local can be resolved against the function that bound it."""
    for path in API_ROOT.rglob("*.py"):
        rel = path.relative_to(API_ROOT).as_posix()
        if rel.startswith("tests/") or rel.startswith(".venv/"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(fn):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "track"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "analytics_service"
                ):
                    yield rel, fn, node


def _local_is_membership_bound(fn, name: str) -> bool:
    """True if `name` is assigned in `fn` from an expression that tests membership
    against a literal collection — i.e. the value is one of a fixed set by the time
    it is read, whatever arrived on the request."""
    for st in ast.walk(fn):
        if not isinstance(st, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == name for t in st.targets):
            continue
        for sub in ast.walk(st.value):
            if isinstance(sub, ast.Compare) and any(isinstance(o, ast.In) for o in sub.ops):
                if all(isinstance(c, ast.Constant) for c in getattr(sub.comparators[0], "elts", [None])):
                    return True
    return False


def _annotation_name(fn, arg_name: str) -> str | None:
    for a in list(fn.args.args) + list(fn.args.kwonlyargs):
        if a.arg == arg_name and isinstance(a.annotation, ast.Name):
            return a.annotation.id
    return None


def test_every_source_property_is_shape_constrained():
    """`source` is client-supplied at every door that has one, and the generic
    value guard above cannot catch it: `body.source` is an ast.Attribute, which
    that test's permissive tail waves through as "an id or slug off a model".

    It was wrong twice for exactly that reason — council_started sent an
    unbounded `body.source` straight to PostHog, and the field carried no bound
    at all. So this pins the one property name with a history, at every site:

      constant          — a server-side literal
      local             — bound by a membership test in the same function
      <body>.source     — annotated by a schema class whose field has a pattern
      _source_of(...)   — an allow-listed server-side helper

    Anything else is a new way for a user-supplied string to reach analytics.
    """
    schemas = _schema_classes()
    offenders = []

    for rel, fn, node in _functions_with_track_calls():
        if len(node.args) < 3 or not isinstance(node.args[2], ast.Dict):
            continue
        for key, value in zip(node.args[2].keys, node.args[2].values):
            if not (isinstance(key, ast.Constant) and key.value == "source"):
                continue
            where = f"{rel}:{node.lineno} {node.args[0].value}.source"

            if isinstance(value, ast.Constant):
                continue
            if isinstance(value, ast.Name):
                if not _local_is_membership_bound(fn, value.id):
                    offenders.append(
                        f"{where} is the local `{value.id}`, which is not bound by a "
                        f"membership test in {fn.name}() — an unchecked local is a "
                        f"bare str with extra steps"
                    )
                continue
            if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
                cls = _annotation_name(fn, value.value.id)
                if cls is None or cls not in schemas:
                    offenders.append(f"{where} reads `{value.value.id}`, whose schema could not be resolved")
                elif not _field_has_pattern(schemas[cls], value.attr):
                    offenders.append(
                        f"{where} reads {cls}.{value.attr}, which has no pattern= — "
                        f"a client may send any string and it reaches PostHog verbatim"
                    )
                continue
            if isinstance(value, ast.Call):
                fname = value.func.attr if isinstance(value.func, ast.Attribute) else getattr(value.func, "id", "?")
                if fname not in _SOURCE_HELPERS:
                    offenders.append(f"{where} calls {fname}(), which is not an allow-listed source helper")
                continue
            offenders.append(f"{where} has shape {type(value).__name__}, which is not one of the four safe forms")

    assert not offenders, offenders


def test_request_models_never_declare_source_as_a_bare_str():
    """The same rule one level earlier, so a NEW request body with a `source`
    fails here before it ever grows a call site.

    Response models are exempt and named rather than pattern-matched: they carry
    a source OUT of the system (a quote's locator, a counterview's origin) and
    are never parsed from a request, so a pattern on them would constrain our own
    output for no benefit.
    """
    response_models = {"CounterviewOut", "ReflectionFeedCounterview"}
    offenders = []
    for name, cls in _schema_classes().items():
        if name in response_models:
            continue
        for st in cls.body:
            if isinstance(st, ast.AnnAssign) and getattr(st.target, "id", None) == "source":
                if not _field_has_pattern(cls, "source"):
                    offenders.append(f"{name}.source (schemas:{st.lineno}) is not pattern-constrained")
    assert not offenders, offenders


def test_gap_bucket_returns_a_closed_set():
    """The allow-list entry above is a promise; this is the check on it.

    gap_bucket is the only allow-listed helper whose input is a user-influenced
    VALUE (when they last spoke) rather than a count or an enum off a model. It
    is safe because it maps a timestamp onto six fixed strings — asserted here
    against real timestamps rather than by reading the source, so a future edit
    that interpolated anything into the return value fails.
    """
    from datetime import datetime, timedelta, timezone
    from services.conversation_service import gap_bucket

    allowed = {"under_1h", "under_24h", "under_72h", "under_7d", "under_14d", "unknown"}
    now = datetime.now(timezone.utc)
    seen = {gap_bucket(None)}
    for hours in (0, 0.5, 1, 23, 24, 71, 72, 167, 168, 300, 336, 1000):
        seen.add(gap_bucket(now - timedelta(hours=hours)))
    assert seen <= allowed, f"gap_bucket returned something outside the closed set: {seen - allowed}"
    # And a naive timestamp must not raise — old rows may carry one (TD-76).
    assert gap_bucket(datetime.utcnow() - timedelta(hours=2)) in allowed
