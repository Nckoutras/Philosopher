"""DEBUG must be OFF unless something turns it on.

DEBUG serves /docs (main.py) and echoes every SQL statement to the log
(db/session.py). It used to default to True, so a deploy that simply did not
set it came up with both on. Production is safe today only because Render
happens to set it (/docs answered 404 on 2026-09-24); the default must not be
the thing that decides.

Local development keeps DEBUG on through .env (.env.example: DEBUG=true).
"""
import logging

import pytest

import config as config_module
from config import Settings


def test_debug_defaults_to_off(monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    settings = Settings(_env_file=None)
    assert settings.DEBUG is False


def test_debug_on_in_production_is_an_error(monkeypatch, caplog):
    import main

    monkeypatch.setattr(config_module.config, "DEBUG", True)
    monkeypatch.setattr(config_module.config, "ENV", "production")
    with caplog.at_level(logging.WARNING, logger=main.logger.name):
        main._warn_if_debug()

    records = [r for r in caplog.records if "DEBUG is ON" in r.getMessage()]
    assert len(records) == 1
    # ERROR, not WARNING: Sentry's logging integration turns ERROR into an event.
    assert records[0].levelno == logging.ERROR


def test_debug_on_in_development_is_a_warning(monkeypatch, caplog):
    import main

    monkeypatch.setattr(config_module.config, "DEBUG", True)
    monkeypatch.setattr(config_module.config, "ENV", "development")
    with caplog.at_level(logging.WARNING, logger=main.logger.name):
        main._warn_if_debug()

    records = [r for r in caplog.records if "DEBUG is ON" in r.getMessage()]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING


def test_debug_off_logs_nothing(monkeypatch, caplog):
    import main

    monkeypatch.setattr(config_module.config, "DEBUG", False)
    monkeypatch.setattr(config_module.config, "ENV", "production")
    with caplog.at_level(logging.WARNING, logger=main.logger.name):
        main._warn_if_debug()

    assert not [r for r in caplog.records if "DEBUG is ON" in r.getMessage()]
