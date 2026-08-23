from spotdl.providers.lyrics.azlyrics import AzLyrics


def test_azlyrics_blocked_detection():
    azlyrics = AzLyrics()

    # real content from a healthy page must not be flagged
    assert azlyrics._blocked(
        "<html><body><div>lyrics here</div></body></html>",
        "https://www.azlyrics.com/lyrics/artist/song.html",
    ) is False

    # the "request for access" interstitial
    assert azlyrics._blocked(
        "<title>AZLyrics - request for access</title>",
        "https://www.azlyrics.com/search/",
    ) is True

    # unusual activity message
    assert azlyrics._blocked(
        "Our systems have detected unusual activity from your IP address",
        "https://www.azlyrics.com/lyrics/artist/song.html",
    ) is True

    # redirect to the anti-bot b.azlyrics.com subnet
    assert azlyrics._blocked(
        "", "https://b.azlyrics.com/?u=/search/"
    ) is True
