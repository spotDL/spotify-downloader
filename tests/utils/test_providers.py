import pytest

from spotdl.utils.providers import match_percentage


@pytest.mark.parametrize(
    "str1, str2, score_cutoff, expected",
    [
        ("", "", 0, 100.0),
        ("test", "test", 0, 100.0),
        ("test", "test", 20, 100.0),
        ("test", "test", 101.0, 0.0),
        ("test", "💩", 0, 0.0),
        (None, None, 0, 0.0),
        ("test", None, 0, 0.0),
        (123, "test", 0, 0.0),
    ],
)
def test_match_percentage(str1, str2, score_cutoff, expected):
    """
    Test match_percentage function
    """

    if isinstance(str1, int):
        with pytest.raises(TypeError):
            match_percentage(str1, str2, score_cutoff)  # type: ignore
    else:
        assert match_percentage(str1, str2, score_cutoff) == expected
