from spotdl.types.result import Result
from spotdl.types.song import Song
from spotdl.utils.matching import (
    calc_album_match,
    calc_main_artist_match,
    order_results,
)


def test_calc_album_match_without_song_album(mocker):
    """
    Test album matching when the song has no album name.
    """

    song = mocker.Mock(album_name=None)
    result = mocker.Mock(album="Album")

    assert calc_album_match(song, result) == 0.0


def test_calc_main_artist_match_multiple_song_artists_single_result_artist():
    """
    Test calc_main_artist_match when song has multiple artists but result has one
    (issue #2729). Should not return 0.0 when main artists match exactly.
    """
    song = Song.from_missing_data(
        name="Wasted",
        artists=["LUCØ", "Alice Gray"],
        artist="LUCØ",
        album_name="Wasted",
        duration=107,
    )
    result = Result(
        source="YouTubeMusic",
        url="https://music.youtube.com/watch?v=0X93DSg2ZQg",
        verified=True,
        name="Wasted (feat. Alice Gray)",
        duration=108.0,
        author="LUCØ",
        result_id="0X93DSg2ZQg",
        isrc_search=False,
        search_query="LUCØ, Alice Gray - Wasted",
        artists=("LUCØ",),
        views=None,
        explicit=None,
        album=None,
        year=None,
        track_number=None,
        genre=None,
        lyrics=None,
    )

    match = calc_main_artist_match(song, result)
    assert match > 0.0, f"Expected match > 0, got {match}"

    ordered = order_results([result], song, None)
    assert len(ordered) == 1, f"Expected result to be kept, got {len(ordered)}"
