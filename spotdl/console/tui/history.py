import json
import time
from typing import Any, Dict, List, Optional

from spotdl.utils.config import get_spotdl_path

MAX_ENTRIES = 15

HISTORY_FILE = get_spotdl_path() / "tui_history.json"


def _empty_history() -> Dict[str, List[Dict[str, Any]]]:
    return {"urls": [], "downloads": []}


def load_history() -> Dict[str, List[Dict[str, Any]]]:
    if not HISTORY_FILE.exists():
        return _empty_history()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as history_file:
            data = json.load(history_file)
        if not isinstance(data, dict):
            return _empty_history()
        data.setdefault("urls", [])
        data.setdefault("downloads", [])
        return data
    except Exception:
        return _empty_history()


def _save_history(data: Dict[str, List[Dict[str, Any]]]) -> None:
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as history_file:
            json.dump(data, history_file, indent=2, ensure_ascii=False)
    except Exception:
        pass


def add_url_entry(query: str, operation: str) -> None:
    if not query:
        return
    data = load_history()
    data["urls"] = [entry for entry in data["urls"] if entry.get("query") != query]
    data["urls"].insert(
        0,
        {
            "query": query,
            "operation": operation,
            "time": time.time(),
        },
    )
    data["urls"] = data["urls"][:MAX_ENTRIES]
    _save_history(data)


def add_download_entry(
    name: str, url: Optional[str], count: int, ok: int, err: int
) -> None:
    data = load_history()
    data["downloads"].insert(
        0,
        {
            "name": name,
            "url": url or "",
            "count": count,
            "ok": ok,
            "err": err,
            "time": time.time(),
        },
    )
    data["downloads"] = data["downloads"][:MAX_ENTRIES]
    _save_history(data)
