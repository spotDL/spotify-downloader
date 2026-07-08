"""Tests for the single-source URL / ``provider:type:id`` parser.

The accepted-forms table in the Task 2 brief is a CONTRACT: every accepted
input must parse to exactly the listed ``(provider, entity_type, entity_id)``
and every reject case must raise ``UnsupportedURL``. These tests are offline;
only ``resolve_shortlink`` touches the network and is exercised via ``respx``.
"""

import httpx
import pytest
import respx
from spotdl_core.model import EntityType, ProviderId
from spotdl_core.providers import PlatformRef, UnsupportedURL, parse, resolve_shortlink, strip_intl

# A concrete MusicBrainz UUID stands in for the ``<uuid>`` placeholders.
_MB_RECORDING = "b1a9c0e9-d987-4042-ae91-78d6a3267d69"
_MB_RELEASE = "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
_MB_ARTIST = "f27ec8db-af05-4f36-916e-3d57f91ecf5e"

# (input, provider, entity_type, entity_id)
ACCEPTED: list[tuple[str, ProviderId, EntityType, str]] = [
    # --- Spotify URIs ---
    (
        "spotify:track:6rqhFgbbKwnb9MLmUQDhG6",
        ProviderId.SPOTIFY,
        EntityType.TRACK,
        "6rqhFgbbKwnb9MLmUQDhG6",
    ),
    (
        "spotify:album:4aawyAB9vmqN3uQ7FjRGTy",
        ProviderId.SPOTIFY,
        EntityType.ALBUM,
        "4aawyAB9vmqN3uQ7FjRGTy",
    ),
    (
        "spotify:artist:0OdUWJ0sBjDrqHygGUXeCF",
        ProviderId.SPOTIFY,
        EntityType.ARTIST,
        "0OdUWJ0sBjDrqHygGUXeCF",
    ),
    (
        "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
        ProviderId.SPOTIFY,
        EntityType.PLAYLIST,
        "37i9dQZF1DXcBWIGoYBM5M",
    ),
    # --- Spotify URLs ---
    (
        "https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6",
        ProviderId.SPOTIFY,
        EntityType.TRACK,
        "6rqhFgbbKwnb9MLmUQDhG6",
    ),
    (
        "https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6?si=abc",
        ProviderId.SPOTIFY,
        EntityType.TRACK,
        "6rqhFgbbKwnb9MLmUQDhG6",
    ),
    (
        "https://open.spotify.com/intl-de/track/6rqhFgbbKwnb9MLmUQDhG6",
        ProviderId.SPOTIFY,
        EntityType.TRACK,
        "6rqhFgbbKwnb9MLmUQDhG6",
    ),
    (
        "https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy",
        ProviderId.SPOTIFY,
        EntityType.ALBUM,
        "4aawyAB9vmqN3uQ7FjRGTy",
    ),
    (
        "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        ProviderId.SPOTIFY,
        EntityType.PLAYLIST,
        "37i9dQZF1DXcBWIGoYBM5M",
    ),
    (
        "https://open.spotify.com/artist/0OdUWJ0sBjDrqHygGUXeCF",
        ProviderId.SPOTIFY,
        EntityType.ARTIST,
        "0OdUWJ0sBjDrqHygGUXeCF",
    ),
    # --- Deezer ---
    ("deezer:track:3135556", ProviderId.DEEZER, EntityType.TRACK, "3135556"),
    ("https://www.deezer.com/track/3135556", ProviderId.DEEZER, EntityType.TRACK, "3135556"),
    ("https://www.deezer.com/en/album/302127", ProviderId.DEEZER, EntityType.ALBUM, "302127"),
    ("https://deezer.com/us/playlist/1234", ProviderId.DEEZER, EntityType.PLAYLIST, "1234"),
    ("https://www.deezer.com/artist/27", ProviderId.DEEZER, EntityType.ARTIST, "27"),
    # --- Apple Music / iTunes ---
    (
        "https://music.apple.com/us/album/1989/1440935467?i=1440935485",
        ProviderId.ITUNES,
        EntityType.TRACK,
        "1440935485",
    ),
    (
        "https://music.apple.com/gb/album/1989/1440935467",
        ProviderId.ITUNES,
        EntityType.ALBUM,
        "1440935467",
    ),
    (
        "https://music.apple.com/us/artist/taylor-swift/159260351",
        ProviderId.ITUNES,
        EntityType.ARTIST,
        "159260351",
    ),
    (
        "https://music.apple.com/us/playlist/todays-hits/pl.abc123",
        ProviderId.ITUNES,
        EntityType.PLAYLIST,
        "pl.abc123",
    ),
    ("itunes:track:1440935485", ProviderId.ITUNES, EntityType.TRACK, "1440935485"),
    # --- MusicBrainz ---
    (
        f"https://musicbrainz.org/recording/{_MB_RECORDING}",
        ProviderId.MUSICBRAINZ,
        EntityType.TRACK,
        _MB_RECORDING,
    ),
    (
        f"https://musicbrainz.org/release/{_MB_RELEASE}",
        ProviderId.MUSICBRAINZ,
        EntityType.ALBUM,
        _MB_RELEASE,
    ),
    (
        f"https://musicbrainz.org/artist/{_MB_ARTIST}",
        ProviderId.MUSICBRAINZ,
        EntityType.ARTIST,
        _MB_ARTIST,
    ),
    (f"musicbrainz:track:{_MB_RECORDING}", ProviderId.MUSICBRAINZ, EntityType.TRACK, _MB_RECORDING),
    # --- YouTube Music ---
    (
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        ProviderId.YTMUSIC,
        EntityType.TRACK,
        "dQw4w9WgXcQ",
    ),
    (
        "https://music.youtube.com/playlist?list=OLAK5uy_xxx",
        ProviderId.YTMUSIC,
        EntityType.ALBUM,
        "OLAK5uy_xxx",
    ),
    # --- YouTube ---
    (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ProviderId.YOUTUBE,
        EntityType.TRACK,
        "dQw4w9WgXcQ",
    ),
    (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxx",
        ProviderId.YOUTUBE,
        EntityType.TRACK,
        "dQw4w9WgXcQ",
    ),
    ("https://youtu.be/dQw4w9WgXcQ", ProviderId.YOUTUBE, EntityType.TRACK, "dQw4w9WgXcQ"),
    (
        "https://www.youtube.com/playlist?list=PLxxx",
        ProviderId.YOUTUBE,
        EntityType.PLAYLIST,
        "PLxxx",
    ),
    ("youtube:track:dQw4w9WgXcQ", ProviderId.YOUTUBE, EntityType.TRACK, "dQw4w9WgXcQ"),
    # --- SoundCloud ---
    (
        "https://soundcloud.com/artist/track-slug",
        ProviderId.SOUNDCLOUD,
        EntityType.TRACK,
        "artist/track-slug",
    ),
    (
        "https://soundcloud.com/artist/sets/playlist-slug",
        ProviderId.SOUNDCLOUD,
        EntityType.PLAYLIST,
        "artist/sets/playlist-slug",
    ),
    ("https://soundcloud.com/artist", ProviderId.SOUNDCLOUD, EntityType.ARTIST, "artist"),
    # --- Bandcamp ---
    (
        "https://artist.bandcamp.com/track/song-slug",
        ProviderId.BANDCAMP,
        EntityType.TRACK,
        "artist/track/song-slug",
    ),
    (
        "https://artist.bandcamp.com/album/album-slug",
        ProviderId.BANDCAMP,
        EntityType.ALBUM,
        "artist/album/album-slug",
    ),
    # --- Piped ---
    ("https://piped.video/watch?v=dQw4w9WgXcQ", ProviderId.PIPED, EntityType.TRACK, "dQw4w9WgXcQ"),
]

REJECT: list[str] = [
    # bare 11-char id (looks like a YouTube id) must not parse without a prefix
    "dQw4w9WgXcQ",
    # provider:type:id with unknown provider
    "notaprovider:track:123",
    # provider:type:id with unknown type
    "spotify:episode:123",
    # unrelated URL
    "https://example.com/foo",
    # empty / whitespace
    "",
    "   ",
    # short-link hosts are not resolved by parse (require resolve_shortlink first)
    "https://spotify.link/abc",
]


@pytest.mark.parametrize(("value", "provider", "entity_type", "entity_id"), ACCEPTED)
def test_parse_accepted(
    value: str, provider: ProviderId, entity_type: EntityType, entity_id: str
) -> None:
    ref = parse(value)
    assert (ref.provider, ref.entity_type, ref.entity_id) == (provider, entity_type, entity_id)


@pytest.mark.parametrize("value", REJECT)
def test_parse_rejected(value: str) -> None:
    with pytest.raises(UnsupportedURL):
        parse(value)


def test_parse_ignores_trailing_slash() -> None:
    ref = parse("https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6/")
    assert (ref.provider, ref.entity_type, ref.entity_id) == (
        ProviderId.SPOTIFY,
        EntityType.TRACK,
        "6rqhFgbbKwnb9MLmUQDhG6",
    )


def test_platform_ref_is_frozen() -> None:
    ref = parse("spotify:track:6rqhFgbbKwnb9MLmUQDhG6")
    assert isinstance(ref, PlatformRef)
    with pytest.raises((AttributeError, TypeError)):
        ref.entity_id = "other"  # type: ignore[misc]


def test_url_input_populates_url_field() -> None:
    ref = parse("https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6")
    assert ref.url == "https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6"


def test_uri_input_has_no_url() -> None:
    ref = parse("spotify:track:6rqhFgbbKwnb9MLmUQDhG6")
    assert ref.url is None


def test_strip_intl_removes_locale_segment() -> None:
    assert (
        strip_intl("https://open.spotify.com/intl-de/track/X") == "https://open.spotify.com/track/X"
    )
    assert strip_intl("https://open.spotify.com/track/X") == "https://open.spotify.com/track/X"


@pytest.mark.parametrize(
    ("host", "canonical"),
    [
        ("spotify.link", "https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6"),
        ("deezer.page.link", "https://www.deezer.com/track/3135556"),
        ("deezer.app.link", "https://www.deezer.com/track/3135556"),
    ],
)
async def test_resolve_shortlink_follows_redirect(
    respx_mock: respx.MockRouter, host: str, canonical: str
) -> None:
    short = f"https://{host}/abc"
    respx_mock.get(short).mock(return_value=httpx.Response(302, headers={"Location": canonical}))
    respx_mock.get(canonical).mock(return_value=httpx.Response(200))
    async with httpx.AsyncClient() as client:
        resolved = await resolve_shortlink(client, short)
    assert resolved == canonical


async def test_resolve_shortlink_passthrough_for_non_short_url(
    respx_mock: respx.MockRouter,
) -> None:
    url = "https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6"
    async with httpx.AsyncClient() as client:
        resolved = await resolve_shortlink(client, url)
    assert resolved == url
    assert not respx_mock.calls  # no network request was issued
