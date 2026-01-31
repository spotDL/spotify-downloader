from logging import LogRecord

import pytest

from spotdl.utils.logging import DEBUG, NOTSET, SpotdlFormatter


def test_spotdl_formatter_format():
    # cf. https://rich.readthedocs.io/en/stable/markup.html#escaping
    formatter = SpotdlFormatter()

    input_output_map = {
        ("[as it is, infinite]", DEBUG): "[blue]\\[as it is, infinite]",
        ("[effluvium]", NOTSET): "\\[effluvium]",
        ("DRIP", DEBUG): "[blue]DRIP",
        ("FOREIGN TONGUES", NOTSET): "FOREIGN TONGUES",
    }

    for (msg, level), escaped_msg in input_output_map.items():
        assert (
            formatter.format(
                LogRecord("spotdl", level, "", 0, msg, None, None, None, None)
            )
            == escaped_msg
        )
