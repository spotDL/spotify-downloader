from typing import Optional

from spotdl.types.result import Result
from spotdl.types.song import Song
from spotdl.utils.matching import check_forbidden_words, order_results


def create_dummy_song(
    name: str, artist: str = "The Living Tombstone", album: str = "My Ordinary Life"
) -> Song:
    return Song.from_missing_data(
        name=name,
        artists=[artist],
        artist=artist,
        genres=[],
        disc_number=1,
        disc_count=1,
        album_name=album,
        album_artist=artist,
        duration=220,
        year=2017,
        date="2017-11-23",
        track_number=1,
        tracks_count=1,
        song_id="dummy_song_id_123",
        explicit=False,
        publisher="",
        url="https://open.spotify.com/track/dummy",
        isrc="US1234567890",
    )


def create_dummy_result(
    name: str,
    author: str,
    url_id: str,
    verified: bool = False,
    source: str = "youtube",
    artists: Optional[tuple] = None,
) -> Result:
    return Result(
        source=source,
        url=f"https://www.youtube.com/watch?v={url_id}",
        verified=verified,
        name=name,
        duration=220.0,
        author=author,
        artists=artists or (author.replace(" - Topic", ""),),
        result_id=url_id,
    )


def test_forbidden_words_detection():
    song = create_dummy_song("My Ordinary Life")

    official_res = create_dummy_result(
        "The Living Tombstone - My Ordinary Life",
        "The Living Tombstone - Topic",
        "off_1",
        verified=True,
    )
    has_fwords, words = check_forbidden_words(song, official_res)
    assert not has_fwords
    assert not words

    slowed_res = create_dummy_result(
        "My Ordinary Life (Slowed + Reverb)", "TikTok Tunes", "slow_1"
    )
    has_fwords, words = check_forbidden_words(song, slowed_res)
    assert has_fwords
    assert "slowed" in words or "slow" in words
    assert "reverb" in words or "reverbed" in words


def test_order_results_penalizes_slowed_reverb():
    song = create_dummy_song("My Ordinary Life")

    official_res = create_dummy_result(
        "My Ordinary Life",
        "The Living Tombstone - Topic",
        "res_official",
        verified=True,
        source="youtube-music",
    )
    slowed_res = create_dummy_result(
        "My Ordinary Life - The Living Tombstone (Slowed + Reverb)",
        "The Living Tombstone",
        "res_slowed",
    )

    ordered = order_results([slowed_res, official_res], song)

    assert official_res in ordered
    if slowed_res in ordered:
        assert ordered[official_res] > ordered[slowed_res]


def test_live_vs_studio_matching():
    studio_song = create_dummy_song("Hotel California", artist="Eagles")
    live_result = create_dummy_result(
        "Hotel California (Live at MTV)", "Eagles", "res_live"
    )
    studio_result = create_dummy_result(
        "Hotel California", "Eagles - Topic", "res_studio", verified=True
    )

    ordered = order_results([live_result, studio_result], studio_song)
    assert studio_result in ordered
    if live_result in ordered:
        assert ordered[studio_result] > ordered[live_result]

    live_song = create_dummy_song("Hotel California (Live at MTV)", artist="Eagles")
    ordered_live = order_results([live_result, studio_result], live_song)
    assert live_result in ordered_live
    if studio_result in ordered_live:
        assert ordered_live[live_result] > ordered_live[studio_result]
