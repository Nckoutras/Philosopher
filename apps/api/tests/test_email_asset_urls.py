"""No dead domain reaches a rendered email.

WHAT WENT WRONG. `PUBLIC_ASSET_BASE_URL` defaulted to `https://thinkalike.netlify.app`
— an earlier name for this product — and was never set on Render, because it
appeared in no `.env.example`, no DEPLOY_NOTES row and no ops checklist. Nothing
in the repository told anyone the variable existed. So every OTP email loaded its
logo from that host, and every future-self email printed the hostname to the
reader: `future_self_email.html` renders the value as the footer's visible link
text, not only as an `<img src>`.

WHY IT SURVIVED. The old Netlify site still answers 200. No image 404'd, no link
broke, nothing was logged. Compare the neighbouring URL defaults, which fail
loudly — `API_BASE_URL` at localhost suppresses the send and says so in the log;
`FRONTEND_URL` at localhost produces obviously dead links. A default that quietly
succeeds at the wrong thing is worse than one that fails, which is the point
OPS-007 already makes in the backlog.

`FROM_EMAIL` was the same class and a milder case: also a dead domain
(`philosopher.app`), but documented in three places and reported set on both
services on 2026-09-07, so production was correct and only the default was wrong.

WHAT THESE TESTS PIN. Not the live Render values — nothing here can read those.
They pin the two things this repository controls: the defaults are the current
domain, and a rendered email body contains no earlier one. The substring check is
deliberately blunt; the failure mode was a hostname appearing in output, and a
blunt check is exactly the shape of that failure.
"""
import pytest

from config import config
from services.template_service import render_future_self_email, render_otp_email

# Every name this product has shipped under. A rendered email may contain none of
# them. Kept as a list rather than folded into the assertions so adding a future
# rename is one line here.
DEAD_DOMAINS = ["thinkalike", "philosopher.app", "thegreatminds", "greatminds"]

LIVE_DOMAIN = "thewiseroom.app"


# ── The defaults themselves ───────────────────────────────────────────────────

def test_the_asset_base_url_default_is_the_live_site():
    """Must be the public SITE, not the API host: the paths it prefixes are the
    web app's static assets (/self-portrait/…, /personas/…)."""
    assert config.PUBLIC_ASSET_BASE_URL == f"https://{LIVE_DOMAIN}"


def test_the_sender_default_is_the_live_domain():
    assert config.FROM_EMAIL == f"hello@{LIVE_DOMAIN}"


@pytest.mark.parametrize("dead", DEAD_DOMAINS)
def test_no_default_carries_a_dead_domain(dead):
    assert dead not in config.PUBLIC_ASSET_BASE_URL
    assert dead not in config.FROM_EMAIL


# ── The rendered bodies ───────────────────────────────────────────────────────

def _otp() -> str:
    """Rendered exactly as otp_service.py:82 builds it, from the CONFIG value —
    not a literal, so this fails if the default regresses."""
    image_url = f"{config.PUBLIC_ASSET_BASE_URL.rstrip('/')}/self-portrait/appbutton.png"
    return render_otp_email(code="123456", image_url=image_url)


def _future_self() -> str:
    """Rendered as cron.py:159-188 builds it: a relative portrait_url prefixed
    with the config value, and the same value passed as public_base_url."""
    base = config.PUBLIC_ASSET_BASE_URL.rstrip("/")
    return render_future_self_email(
        persona_name="Socrates",
        persona_portrait_url=f"{base}/personas/socrates.webp",
        quote_content="The unexamined life is not worth living.",
        note="Remember why you started.",
        scheduled_for_display="September 11, 2026",
        public_base_url=config.PUBLIC_ASSET_BASE_URL,
        arrived_url="https://thewiseroom.app/app/scheduled-letters/abc",
    )


@pytest.mark.parametrize("dead", DEAD_DOMAINS)
def test_the_otp_email_contains_no_dead_domain(dead):
    assert dead not in _otp().lower()


@pytest.mark.parametrize("dead", DEAD_DOMAINS)
def test_the_future_self_email_contains_no_dead_domain(dead):
    assert dead not in _future_self().lower()


def test_the_otp_email_points_its_image_at_the_live_site():
    """Positive half. "No dead domain" alone would pass on an email that had lost
    the image entirely."""
    body = _otp()
    assert f"https://{LIVE_DOMAIN}/self-portrait/appbutton.png" in body


def test_the_future_self_email_shows_the_live_domain_in_its_footer():
    """THE ONE THAT MATTERS MOST. This value is not merely an attribute here —
    the template renders it as the footer's visible link TEXT, with the scheme
    stripped. A wrong value is read by the recipient, not just fetched."""
    body = _future_self()
    assert LIVE_DOMAIN in body
    assert f"https://{LIVE_DOMAIN}/personas/socrates.webp" in body


def test_every_url_in_a_rendered_email_is_absolute():
    """A relative src in an email client resolves against nothing and shows a
    broken image — the failure the base-url prefixing exists to prevent."""
    for body in (_otp(), _future_self()):
        for marker in ('src="', 'href="'):
            start = 0
            while (i := body.find(marker, start)) != -1:
                value = body[i + len(marker):body.find('"', i + len(marker))]
                assert value.startswith(("http://", "https://", "mailto:")), (
                    f"non-absolute URL in a rendered email: {value!r}"
                )
                start = i + len(marker)
