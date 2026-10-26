from spotdl.utils.web import validate_search_term


def test_web_searchterms():
    url = "https://open.spotify.com/intl-pt/track/example"
    result = validate_search_term(url)
    assert result is True
