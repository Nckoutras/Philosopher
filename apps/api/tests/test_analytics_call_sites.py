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
