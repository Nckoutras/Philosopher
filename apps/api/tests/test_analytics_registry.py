"""ANALYTICS_EVENTS is the taxonomy, and this file is what makes that true.

The dict used to be inert: 21 declared names, 15 that no code had ever fired,
one name firing undeclared (user_signed_in), and nothing anywhere importing it.
It documented an intention and drifted from the code for months.

These tests close both directions by walking the AST of every module under
apps/api:

  * every analytics_service.track("...") literal is declared, and
  * every declared name has at least one call site.

Enforcement is here rather than at runtime on purpose. An unknown event name
must never raise inside a request that was otherwise going to succeed —
analytics is an observer and may not change what the product does. A test can
be strict precisely because it cannot reach production traffic.

HOW THESE CAN FAIL. Adding a track() call with a new name fails
test_every_fired_event_is_declared. Deleting the last call site for a declared
name fails test_every_declared_event_has_a_call_site. Passing a non-literal
event name fails test_event_names_are_string_literals, which is what keeps the
other two honest — a computed name is invisible to an AST walk.
"""
import ast
import pathlib

import pytest

from constants import ANALYTICS_EVENTS

API_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _modules():
    """Every module that ships. Tests are excluded: a fixture may legitimately
    reference an event name that no production path fires."""
    for path in API_ROOT.rglob("*.py"):
        rel = path.relative_to(API_ROOT).as_posix()
        if rel.startswith("tests/") or "/.venv/" in rel or rel.startswith(".venv/"):
            continue
        yield path


def _track_calls():
    """(path, lineno, node) for every analytics_service.track(...) call."""
    for path in _modules():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - a broken module fails elsewhere
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "track"
                and isinstance(func.value, ast.Name)
                and func.value.id == "analytics_service"
            ):
                yield path, node.lineno, node


def test_event_names_are_string_literals():
    """A computed event name would be invisible to the two checks below."""
    for path, lineno, node in _track_calls():
        assert node.args, f"{path}:{lineno} track() called with no event name"
        first = node.args[0]
        assert isinstance(first, ast.Constant) and isinstance(first.value, str), (
            f"{path}:{lineno} event name must be a string literal so the registry "
            f"can be checked statically"
        )


def test_every_fired_event_is_declared():
    undeclared = {}
    for path, lineno, node in _track_calls():
        name = node.args[0].value
        if name not in ANALYTICS_EVENTS:
            undeclared.setdefault(name, []).append(
                f"{path.relative_to(API_ROOT).as_posix()}:{lineno}"
            )
    assert not undeclared, (
        "these events fire but are not declared in constants.ANALYTICS_EVENTS: "
        + repr(undeclared)
    )


def test_every_declared_event_has_a_call_site():
    fired = {node.args[0].value for _, _, node in _track_calls()}
    orphans = sorted(set(ANALYTICS_EVENTS) - fired)
    assert not orphans, (
        "these events are declared but nothing fires them — delete them rather "
        f"than leaving an aspiration in the registry: {orphans}"
    )


@pytest.mark.parametrize("name,props", sorted(ANALYTICS_EVENTS.items()))
def test_declared_properties_are_snake_case_identifiers(name, props):
    """Property names are keys in a dashboard, so a typo is permanent."""
    for prop in props:
        assert prop == prop.lower(), f"{name}: property {prop!r} is not lower-case"
        assert prop.isidentifier(), f"{name}: property {prop!r} is not an identifier"


def test_no_property_name_suggests_free_text():
    """A blunt guard on the privacy rule. Properties carry ids, enums, counts and
    buckets — never conversation text, memory text, letter text, an email, or the
    council `matter`. A property NAMED for content is the cheapest signal that
    content is about to be sent, and this catches it at review time.

    This checks names, not values; values are asserted at each call site's own
    test. It is a smoke alarm, not a lock.
    """
    banned = ("text", "body", "content", "message", "matter", "email", "title", "excerpt")
    offenders = []
    for name, props in ANALYTICS_EVENTS.items():
        for prop in props:
            if any(b in prop for b in banned):
                offenders.append(f"{name}.{prop}")
    assert not offenders, (
        "these property names suggest free text, which may never be sent: "
        f"{offenders}"
    )
