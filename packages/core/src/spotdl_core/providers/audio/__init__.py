"""Audio providers (YTMusic, YouTube, SoundCloud, Bandcamp, Piped).

Modules in this sub-package are imported **lazily** by the registry factories
(see :func:`spotdl_core.providers.registry.build_default_registry`) so that a
broken or missing fragile dependency (``ytmusicapi``, ``yt-dlp``, scrapers)
degrades exactly one provider instead of breaking ``import
spotdl_core.providers``. Nothing is imported at package import time here, and the
heavy third-party libraries are imported inside the code paths that use them.
"""
