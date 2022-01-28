from spotdl.utils.providers import match_percentage


def test_match_percentage():
    """
    Test match_percentage function
    """

    assert match_percentage("test", "test") == 100.0
    assert match_percentage("test", "test", score_cutoff=0.5) == 100.0
    assert match_percentage("test", "test", score_cutoff=101.0) == 0.0
    assert match_percentage("test", "💩") == 0.0
