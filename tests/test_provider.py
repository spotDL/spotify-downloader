from spotdl.search.provider import __parse_duration

def test_parse_duration():
    """
    Test the duration parsing
    """

    assert __parse_duration("3:16") == float(196.0)         # 3 min song
    assert __parse_duration("20") == float(20.0)            # 20 second song
    assert __parse_duration("25:59") == float(1559.0)       # 26 min result
    assert __parse_duration("25:59:59") == float(93599.0)   # 26 hour result
    assert __parse_duration("likes") == float(0.0)          # bad values
    assert __parse_duration("views") == float(0.0)
    assert __parse_duration([1, 2, 3]) == float(0.0)
    assert __parse_duration({"json": "data"}) == float(0.0)