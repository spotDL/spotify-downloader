"""Lyrics providers (LRCLIB, Genius, Musixmatch, AZLyrics).

Each module here implements :class:`spotdl_core.providers.base.ProvidesLyrics`
and is imported **lazily** by the registry factories (see
:func:`spotdl_core.providers.registry.build_default_registry`). The providers are
deliberately isolated: one provider's scraper breaking (a rotted selector, a
missing ``beautifulsoup4``) must never affect another, so every module is
independent, imports ``bs4`` lazily inside its parse helpers, confines parse
failures to ``None`` (not found is not an error), and raises
:class:`~spotdl_core.providers.errors.ProviderUnavailable` only on transport
failure. Nothing is imported at package import time here.
"""
