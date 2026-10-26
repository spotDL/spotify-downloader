from spotdl.utils.matching import calc_album_match, calc_main_artist_match


def test_calc_main_artist_match_single_result_artist(mocker):
    """
    Test main artist matching when the song has multiple artists but the
    result only lists the main one (the others are folded into the title).
    """

    song = mocker.Mock(song_id="song", artists=["LUCO", "Alice Gray"])
    result = mocker.Mock(result_id="result", artists=["LUCO"])

    assert calc_main_artist_match(song, result) == 50.0

    # All artists folded into the result's single artist name
    result = mocker.Mock(result_id="result", artists=["LUCO & Alice Gray"])
    assert calc_main_artist_match(song, result) == 100.0

    # Similarly named but different main artist gets no credit
    result = mocker.Mock(result_id="result", artists=["LUCA"])
    assert calc_main_artist_match(song, result) == 0.0


def test_calc_album_match_without_song_album(mocker):
    """
    Test album matching when the song has no album name.
    """

    song = mocker.Mock(album_name=None)
    result = mocker.Mock(album="Album")

    assert calc_album_match(song, result) == 0.0
