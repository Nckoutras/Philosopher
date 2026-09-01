"""The analytics client must point at the EU host, and person profiles must
carry no email.

WHY THIS FILE EXISTS. `analytics_service` hardcoded `host="https://app.posthog.com"`
while the project is EU-hosted and the privacy policy names PostHog as an EU
processor — every server event went to the US regardless of what POSTHOG_HOST
was set to on Render, because `config` had no such field to read.

HOW THESE CAN FAIL. The first test reloads the module with a key present and
asserts on the host actually handed to the Posthog constructor, so a reinstated
literal fails it. The identify tests assert on the payload dicts at the three
call sites; re-adding `"email": ...` to any of them fails one.
"""
import ast
import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch

from config import config


def test_config_defaults_to_the_eu_host():
    # The default matters on its own: if the Render env var is ever unset, the
    # fallback must not silently contradict the privacy policy.
    assert config.POSTHOG_HOST == "https://eu.i.posthog.com"


def test_client_is_constructed_with_the_configured_host():
    fake_posthog_cls = MagicMock()
    fake_module = MagicMock(Posthog=fake_posthog_cls)

    with patch.dict("sys.modules", {"posthog": fake_module}), \
         patch.object(config, "POSTHOG_API_KEY", "phc_test"), \
         patch.object(config, "POSTHOG_HOST", "https://eu.i.posthog.com"):
        import services.analytics_service as mod
        importlib.reload(mod)

    _, kwargs = fake_posthog_cls.call_args
    assert kwargs["host"] == "https://eu.i.posthog.com"
    assert "app.posthog.com" not in kwargs["host"]

    # Leave the module as the rest of the suite expects to find it.
    import services.analytics_service as mod
    importlib.reload(mod)


def _identify_payloads(relative_path: str) -> list[ast.Dict]:
    """Every dict literal passed as the 2nd arg to analytics_service.identify()."""
    source = Path(__file__).resolve().parents[2] / relative_path
    tree = ast.parse(source.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "identify"
            and isinstance(func.value, ast.Name)
            and func.value.id == "analytics_service"
        ):
            assert len(node.args) == 2, "identify(user_id, traits) shape changed"
            found.append(node.args[1])
    return found


def test_identify_never_sends_an_email_property():
    # Read as source, not by calling the endpoints: these three sites sit behind
    # OTP, signup and OAuth flows, and the property list is what is being
    # asserted — not the routing that reaches it.
    call_sites = {
        "routers/auth.py": 2,
        "routers/auth_oauth.py": 1,
    }
    total = 0
    for path, expected in call_sites.items():
        payloads = _identify_payloads(path)
        assert len(payloads) == expected, f"{path}: expected {expected} identify() calls"
        for payload in payloads:
            keys = [k.value for k in payload.keys if isinstance(k, ast.Constant)]
            assert "email" not in keys, f"{path}: identify() must not send an email property"
            total += 1
    assert total == 3
