"""CONTRACT A4 — optional Sentry, disabled by default and lazily imported."""

from __future__ import annotations

import sys

from spotdl_server.observability import sentry
from spotdl_server.settings import Settings


def test_init_is_a_noop_without_a_dsn() -> None:
    assert sentry.init_sentry(Settings()) is False


def test_importing_the_module_does_not_import_sentry_sdk() -> None:
    # The optional ``sentry-sdk`` dependency must not be imported unless a DSN is
    # configured, so importing the observability module stays cheap and the extra
    # stays truly optional.
    assert "sentry_sdk" not in sys.modules
