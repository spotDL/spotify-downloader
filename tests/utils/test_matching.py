from spotdl.types.result import Result
from spotdl.types.song import Song
from spotdl.utils.matching import (
    calc_album_match,
    calc_artists_match,
    calc_main_artist_match,
    order_results,
)


def create_song_and_result(name, artists, result_name, result_artists, verified=True):
    """
    Create a song and a verified YouTube Music result for it
    with a matching duration.
    """

    song = Song.from_missing_data(
        name=name,
        artists=artists,
        artist=artists[0],
        album_name=name,
        duration=107,
    )
    result = Result(
        source="YouTubeMusic",
        url="https://music.youtube.com/watch?v=0X93DSg2ZQg",
        verified=verified,
        name=result_name,
        duration=108.0,
        author=result_artists[0],
        result_id="0X93DSg2ZQg",
        isrc_search=False,
        search_query=f"{', '.join(artists)} - {name}",
        artists=tuple(result_artists),
        views=None,
        explicit=None,
        album=None,
        year=None,
        track_number=None,
        genre=None,
        lyrics=None,
    )

    return song, result


def test_calc_main_artist_match_single_result_artist(mocker):
    """
    Test main artist matching when the song has multiple artists but the
    result only lists one artist.
    """

    song = mocker.Mock(song_id="song", artists=["LUCO", "Alice Gray"])

    result = mocker.Mock(result_id="result", artists=["LUCO"])
    assert calc_main_artist_match(song, result) == 100.0

    # All artists folded into the result's single artist name
    result = mocker.Mock(result_id="result", artists=["LUCO & Alice Gray"])
    assert calc_main_artist_match(song, result) == 100.0

    # Similarly named but different main artist gets no credit
    result = mocker.Mock(result_id="result", artists=["LUCA"])
    assert calc_main_artist_match(song, result) == 0.0

    # Main artist name only as part of a word gets no credit
    song = mocker.Mock(song_id="song", artists=["Queen", "David Bowie"])
    result = mocker.Mock(result_id="result", artists=["Queens of the Stone Age"])
    assert calc_main_artist_match(song, result) == 0.0

    # Artists joined with the German "mit"
    song = mocker.Mock(song_id="song", artists=["LUCO", "Alice Gray"])
    result = mocker.Mock(result_id="result", artists=["LUCO mit Alice Gray"])
    assert calc_main_artist_match(song, result) == 100.0

    # Different artist whose name contains the main artist gets no credit
    song = mocker.Mock(song_id="song", artists=["Drake", "Rihanna"])
    result = mocker.Mock(result_id="result", artists=["Drake Bell"])
    assert calc_main_artist_match(song, result) == 0.0

    # Repeated words are not matched against a single word
    song = mocker.Mock(song_id="song", artists=["The The", "Alice Gray"])
    result = mocker.Mock(result_id="result", artists=["The Weeknd"])
    assert calc_main_artist_match(song, result) == 0.0

    # Spelling differences in the main artist still get credit
    song = mocker.Mock(song_id="song", artists=["A$AP Rocky", "Skepta"])
    result = mocker.Mock(result_id="result", artists=["ASAP Rocky"])
    assert calc_main_artist_match(song, result) >= 85

    # Artist named like part of another artist doesn't break up the longer name
    result = mocker.Mock(result_id="result", artists=["Alpha Bravo & Alpha"])
    song = mocker.Mock(song_id="song", artists=["Alpha Bravo", "Alpha"])
    assert calc_main_artist_match(song, result) == 100.0
    song = mocker.Mock(song_id="song", artists=["Alpha", "Alpha Bravo"])
    assert calc_main_artist_match(song, result) == 100.0


def test_calc_artists_match_single_result_artist(mocker):
    """
    Test other artists matching when the song has multiple artists but the
    result only lists one artist.
    """

    song = mocker.Mock(artists=["LUCO", "Alice Gray"])
    song.name = "Wasted"

    # Other artist folded into the title
    result = mocker.Mock(artists=["LUCO"])
    result.name = "Wasted (feat. Alice Gray)"
    assert calc_artists_match(song, result) == 100.0

    # Song name with its own feature
    song.name = "Wasted (feat. Alice Gray)"
    assert calc_artists_match(song, result) == 100.0
    song.name = "Wasted"

    # Other artist folded into the result's artist name
    result.name = "Wasted"
    result.artists = ["LUCO & Alice Gray"]
    assert calc_artists_match(song, result) == 100.0

    # Other artist missing
    result.artists = ["LUCO"]
    assert calc_artists_match(song, result) == 0.0

    # Other artist named like a word of the song name, without a feature
    song = mocker.Mock(artists=["LUCO", "Love"])
    song.name = "Love Me"
    result.name = "Love Me"
    assert calc_artists_match(song, result) == 0.0

    # Other artist split between the result's artist name and title
    song = mocker.Mock(artists=["Gray", "Alice Gray"])
    song.name = "Wasted"
    result.artists = ["Gray"]
    result.name = "Wasted (feat. Alice)"
    assert calc_artists_match(song, result) == 0.0

    # Other artist whose name has no slug
    song = mocker.Mock(artists=["LUCO", "🔥"])
    song.name = "🔥"
    result.artists = ["LUCO"]
    result.name = "🔥"
    assert calc_artists_match(song, result) == 0.0

    # Other artists before the song name in the title ("Artist/Artist - Song")
    song = mocker.Mock(artists=["Hodak", "Miroff", "DJ Eprom"])
    song.name = "zapach zimy i papierosów"
    result.artists = ["Hodak"]
    result.name = "Hodak/Miroff - zapach zimy i papierosów (feat. DJ Eprom)"
    assert calc_artists_match(song, result) == 100.0

    # Song name with a joining word, other artist after it
    song = mocker.Mock(artists=["LUCO", "Alice Gray"])
    song.name = "With or Without You"
    result.name = "With or Without You (feat. Alice Gray)"
    assert calc_artists_match(song, result) == 100.0

    # Song name not in the title, other artist after the German "mit"
    song.name = "Wasted - Remix"
    result.name = "Wasted (mit Alice Gray) [Remix]"
    assert calc_artists_match(song, result) == 100.0

    # Other artist named like part of the main artist isn't found in its name
    song = mocker.Mock(artists=["DJ Khalid", "Khalid"])
    song.name = "Song"
    result = mocker.Mock(artists=["DJ Khalid"])
    result.name = "Song"
    assert calc_artists_match(song, result) == 0.0
    result.name = "DJ Khalid - Song"
    assert calc_artists_match(song, result) == 0.0

    # but is found when credited too
    result.artists = ["DJ Khalid & Khalid"]
    result.name = "Song"
    assert calc_artists_match(song, result) == 100.0
    result.artists = ["DJ Khalid"]
    result.name = "Song (feat. Khalid)"
    assert calc_artists_match(song, result) == 100.0

    # Other artist whose name contains the main artist is still found
    song = mocker.Mock(artists=["Khalid", "DJ Khalid"])
    song.name = "Song"
    result.artists = ["DJ Khalid"]
    result.name = "Song"
    assert calc_artists_match(song, result) == 100.0


def test_order_results_single_result_artist():
    """
    Test that verified results crediting only the main artist are kept,
    and results by an artist that merely contains the main artist's name are not.
    """

    song, result = create_song_and_result(
        "Wasted", ["LUCØ", "Alice Gray"], "Wasted (feat. Alice Gray)", ["LUCØ"]
    )
    assert result in order_results([result], song)

    song, result = create_song_and_result(
        "U Da One", ["Velmar", "Misdemeanor"], "U Da One", ["Velmar und Misdemeanor"]
    )
    assert result in order_results([result], song)

    song, result = create_song_and_result(
        "Under Pressure",
        ["Queen", "David Bowie"],
        "Under Pressure",
        ["Queens of the Stone Age"],
    )
    assert result not in order_results([result], song)

    song, result = create_song_and_result(
        "Too Good", ["Drake", "Rihanna"], "Too Good (feat. Rihanna)", ["Drake Bell"]
    )
    assert result not in order_results([result], song)

    # Unverified upload crediting some artists before the song name
    song, result = create_song_and_result(
        "Song Title",
        ["Alpha", "Bravo", "Charlie", "Delta"],
        "Alpha/Bravo - Song Title (feat. Charlie)",
        ["Alpha"],
        verified=False,
    )
    assert result in order_results([result], song)


def test_calc_album_match_without_song_album(mocker):
    """
    Test album matching when the song has no album name.
    """

    song = mocker.Mock(album_name=None)
    result = mocker.Mock(album="Album")

    assert calc_album_match(song, result) == 0.0
