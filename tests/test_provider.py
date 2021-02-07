from spotdl.search.provider import __parse_duration

def test_parse_duration():
    """
    Test the duration parsing
    """

    assert __parse_duration("20") == float(20.0)
    assert __parse_duration("25:59:59") == float(93599.0)
    assert __parse_duration("25:59") == float(1559.0)
    assert __parse_duration("likes") == float(0.0)
    assert __parse_duration("views") == float(0.0)
    assert __parse_duration([1, 2, 3]) == float(0.0)
    assert __parse_duration({"json": "data"}) == float(0.0)