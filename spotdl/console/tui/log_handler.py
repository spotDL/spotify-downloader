"""
Logging handler that forwards records to the TUI.
"""

import logging
from typing import Callable


class BufferLogHandler(logging.Handler):
    """
    Handler that passes every formatted record to a callback.
    """

    def __init__(self, callback: Callable[[str], None]) -> None:
        """
        Create the handler.

        ### Arguments
        - callback: Function that receives each formatted message.
        """

        super().__init__()
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        """
        Format the record and pass it to the callback.
        """

        try:
            self._callback(self.format(record))
        except Exception:
            self.handleError(record)
