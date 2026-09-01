"""`source` from the paywall to Stripe and back out as an analytics property.

The ratio this exists to make measurable is upgrade_clicked → checkout_started
per source. That only works if the source survives the round trip: browser →
create_checkout → Stripe → webhook → subscription_activated.

THE PART THAT IS EASY TO GET WRONG, and what these tests pin: Stripe's two
webhook cases receive DIFFERENT objects. `checkout.session.completed` gets the
Session, `customer.subscription.created|updated` gets the Subscription. Session
metadata is not visible on the Subscription. Both cases fire
subscription_activated, so create_checkout must set BOTH `metadata` (for the
session) and `subscription_data.metadata` (which Stripe copies onto the
subscription). A version that sets only one is silently half-instrumented — the
event still fires, with source=None on half the traffic.
"""
import ast
import pathlib

import pytest

API_ROOT = pathlib.Path(__file__).resolve().parents[1]
BILLING = API_ROOT / "routers" / "billing.py"


def _create_checkout_fn():
    tree = ast.parse(BILLING.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "create_checkout":
            return node
    raise AssertionError("create_checkout not found")


def _session_create_call(fn):
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "create"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "Session"
        ):
            return node
    raise AssertionError("stripe.checkout.Session.create not found")


def _conditional_metadata_keys(fn):
    """The kwargs keys assigned inside the `if body.source:` guard."""
    keys = {}
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        test_src = ast.dump(node.test)
        if "source" not in test_src:
            continue
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Subscript)
                and isinstance(stmt.targets[0].slice, ast.Constant)
            ):
                keys[stmt.targets[0].slice.value] = ast.dump(stmt.value)
    return keys


def test_checkout_session_sets_both_metadata_bags():
    """Both bags, or one webhook case reports source=None on half the traffic."""
    keys = _conditional_metadata_keys(_create_checkout_fn())
    assert "metadata" in keys, (
        "session metadata missing — checkout.session.completed reads the SESSION, "
        "so without this that webhook case reports source=None"
    )
    assert "subscription_data" in keys, (
        "subscription_data missing — customer.subscription.* receives the "
        "SUBSCRIPTION, which never sees session metadata, so without this that "
        "webhook case reports source=None"
    )
    # Both must actually carry the source, not merely exist.
    assert "'source'" in keys["metadata"]
    assert "'source'" in keys["subscription_data"]
    assert "'metadata'" in keys["subscription_data"], (
        "subscription_data must wrap the source in a metadata dict"
    )


def test_metadata_is_omitted_entirely_when_there_is_no_source():
    """A checkout with no source must reach Stripe exactly as it did before this
    field existed. Passing metadata={} would change the request for every caller
    that buys without one — the same reason lib/api.ts omits the key rather than
    sending undefined."""
    fn = _create_checkout_fn()
    call = _session_create_call(fn)

    # No literal metadata / subscription_data keyword on the call itself...
    literal_kwargs = {k.arg for k in call.keywords if k.arg}
    assert "metadata" not in literal_kwargs, (
        "metadata is passed unconditionally — it must only be sent when a source exists"
    )
    assert "subscription_data" not in literal_kwargs

    # ...it arrives through a ** unpacking of the conditionally-built dict.
    unpackings = [k for k in call.keywords if k.arg is None]
    assert unpackings, "expected the conditional kwargs to be passed with **"

    # And that dict starts empty.
    empty_init = [
        n for n in ast.walk(fn)
        if isinstance(n, ast.AnnAssign)
        and isinstance(n.target, ast.Name)
        and isinstance(n.value, ast.Dict)
        and not n.value.keys
    ]
    assert empty_init, "the kwargs dict should be initialised empty"


def test_both_subscription_activated_sites_read_a_source():
    """Both webhook cases fire subscription_activated; both must carry source."""
    tree = ast.parse(BILLING.read_text(encoding="utf-8"))
    sites = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "track"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "subscription_activated"
        ):
            keys = {
                k.value for k in node.args[2].keys if isinstance(k, ast.Constant)
            }
            sites.append((node.lineno, keys))
    assert len(sites) == 2, f"expected 2 subscription_activated sites, found {len(sites)}"
    for lineno, keys in sites:
        assert "source" in keys, f"billing.py:{lineno} subscription_activated has no source"


def test_source_helper_never_raises_on_any_shape():
    """A webhook that 500s because analytics could not read a field would cost a
    real subscription update. Every shape Stripe could hand us must return
    cleanly."""
    import sys

    sys.path.insert(0, str(API_ROOT))
    from routers.billing import _source_of

    assert _source_of({"metadata": {"source": "council"}}) == "council"
    assert _source_of({"metadata": {}}) is None
    assert _source_of({"metadata": None}) is None
    assert _source_of({}) is None
    assert _source_of(None) is None
    assert _source_of({"metadata": {"source": ""}}) is None


@pytest.mark.parametrize(
    "value,valid",
    [
        ("council", True),
        ("persona_locked", True),
        ("self_portrait", True),
        (None, True),
        ("Council", False),        # upper case
        ("a" * 33, False),         # too long
        ("has space", False),
        ("<script>", False),
        ("drop-dash", False),
    ],
)
def test_checkout_request_validates_source_shape(value, valid):
    """Shape only, not membership. The enum lives in the web app, where it is
    read and rendered; duplicating it here would give two sources of truth. An
    unrecognised source is a reporting gap, never a reason to refuse a payment —
    but it must still be a bounded token, not free text."""
    import sys

    sys.path.insert(0, str(API_ROOT))
    from pydantic import ValidationError
    from schemas import CheckoutRequest

    payload = {"plan": "pro", "interval": "monthly"}
    if value is not None:
        payload["source"] = value

    if valid:
        assert CheckoutRequest(**payload).source == value
    else:
        with pytest.raises(ValidationError):
            CheckoutRequest(**payload)
