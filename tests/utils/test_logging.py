from logging import LogRecord

import pytest

from logging import LogRecord, DEBUG, INFO, WARNING, ERROR, CRITICAL, NOTSET
import pytest
from spotdl.utils.logging import SpotdlFormatter
import tests.instrumentation as instrumentation

@pytest.mark.vcr()
def test_spotdl_formatter_format():
    # cf. https://rich.readthedocs.io/en/stable/markup.html#escaping
    formatter = SpotdlFormatter()

    input_output_map = {
        ("[as it is, infinite]", DEBUG): "[blue]\\[as it is, infinite]",
        ("[effluvium]", NOTSET): "\\[effluvium]",
        ("DRIP", DEBUG): "[blue]DRIP",
        ("FOREIGN TONGUES", NOTSET): "FOREIGN TONGUES",
        ("INFO MESSAGE", INFO): "[green]INFO MESSAGE",
        ("WARNING MESSAGE", WARNING): "[yellow]WARNING MESSAGE",
        ("ERROR MESSAGE", ERROR): "[red]ERROR MESSAGE",
        ("CRITICAL MESSAGE", CRITICAL): "[bold red]CRITICAL MESSAGE",
    }

    for (msg, level), escaped_msg in input_output_map.items():
        assert (
            formatter.format(
                LogRecord("spotdl", level, "", 0, msg, None, None, None, None)
            )
            == escaped_msg
        )
    instrumentation.print_coverage_dict(["branch-2003", "branch-2004","branch-2005", "branch-2006","branch-2007", "branch-2008"])



