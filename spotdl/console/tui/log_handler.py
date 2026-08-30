import logging
from typing import List


class BufferLogHandler(logging.Handler):
    def __init__(self, buffer: List[str]) -> None:
        super().__init__()
        self._buffer = buffer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._buffer.append(self.format(record))
        except Exception:
            pass
