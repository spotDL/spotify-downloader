"""
Persistent history of queries and downloads made from the TUI.
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from spotdl.utils.config import get_spotdl_path

logger = logging.getLogger(__name__)

MAX_ENTRIES = 30

HISTORY_FILE = get_spotdl_path() / "tui_history.json"


def _empty_history() -> Dict[str, List[Dict[str, Any]]]:
    return {"urls": [], "downloads": []}


def load_history() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load the history file.

    ### Returns
    - Dictionary with the `urls` and `downloads` entries, empty when the
    file is missing or unreadable.
    """

    if not HISTORY_FILE.exists():
        return _empty_history()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as history_file:
            data = json.load(history_file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Could not read history file: %s", exc)
        return _empty_history()
    if not isinstance(data, dict):
        return _empty_history()
    data.setdefault("urls", [])
    data.setdefault("downloads", [])
    return data


def _save_history(data: Dict[str, List[Dict[str, Any]]]) -> None:
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as history_file:
            json.dump(data, history_file, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.debug("Could not save history file: %s", exc)


def add_url_entry(query: str, operation: str) -> None:
    """
    Store a query at the top of the recent queries, removing older copies.

    ### Arguments
    - query: The query that was run.
    - operation: Operation used with the query.
    """

    if not query:
        return
    data = load_history()
    data["urls"] = [entry for entry in data["urls"] if entry.get("query") != query]
    data["urls"].insert(
        0,
        {
            "id": str(uuid.uuid4())[:8],
            "query": query,
            "operation": operation,
            "time": time.time(),
        },
    )
    data["urls"] = data["urls"][:MAX_ENTRIES]
    _save_history(data)


def add_download_entry(
    name: str,
    url: Optional[str],
    count: int,
    ok: int,
    err: int,
    skipped: int = 0,
    operation: str = "download",
    log_summary: Optional[str] = None,
) -> None:
    """
    Store the result of a finished operation.

    ### Arguments
    - name: Name shown in the history table.
    - url: Query or url that was processed.
    - count: Number of songs processed.
    - ok: Number of songs that succeeded.
    - err: Number of songs that failed.
    - skipped: Number of songs that were skipped.
    - operation: Operation that was run.
    - log_summary: Log text saved with the entry.
    """

    data = load_history()
    data["downloads"].insert(
        0,
        {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "url": url or "",
            "count": count,
            "ok": ok,
            "err": err,
            "skipped": skipped,
            "operation": operation,
            "time": time.time(),
            "log_summary": log_summary or "",
        },
    )
    data["downloads"] = data["downloads"][:MAX_ENTRIES]
    _save_history(data)


def clear_history() -> None:
    """
    Remove every history entry.
    """

    _save_history(_empty_history())


def delete_download_entry(entry_id: str) -> None:
    """
    Remove one download entry.

    ### Arguments
    - entry_id: Id of the entry to remove.
    """

    data = load_history()
    data["downloads"] = [e for e in data["downloads"] if e.get("id") != entry_id]
    _save_history(data)
