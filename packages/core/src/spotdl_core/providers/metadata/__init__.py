"""Metadata providers (Spotify, Deezer, iTunes, MusicBrainz).

Modules in this sub-package are imported **lazily** by the registry factories
(see :func:`spotdl_core.providers.registry.build_default_registry`) so that a
broken or missing optional dependency degrades exactly one provider instead of
breaking ``import spotdl_core.providers``. Nothing is imported at package import
time here for the same reason.
"""
