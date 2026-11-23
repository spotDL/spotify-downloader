"""
Translations of the interface, loaded from the YAML files in `locales`.
"""

import locale
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from spotdl.utils.config import get_spotdl_path

__all__ = [
    "LANGUAGES",
    "get_language",
    "set_language",
    "available_languages",
    "tr",
    "init",
]

logger = logging.getLogger(__name__)

LANGUAGES: Dict[str, str] = {
    "es": "Español",
    "en": "English",
}

_DEFAULT_LANGUAGE = "en"
_current_language = _DEFAULT_LANGUAGE
_translations: Dict[str, Any] = {}

_LOCALES_DIR = Path(__file__).parent / "locales"
_LANGUAGE_FILE = get_spotdl_path() / "language"


def _load_translations(code: str) -> Dict[str, Any]:
    locale_path = _LOCALES_DIR / f"{code}.yaml"
    if not locale_path.exists():
        locale_path = _LOCALES_DIR / f"{_DEFAULT_LANGUAGE}.yaml"

    with open(locale_path, "r", encoding="utf-8") as locale_file:
        data = yaml.safe_load(locale_file) or {}

    flat: Dict[str, Any] = {}

    def _flatten(node: Dict[str, Any], prefix: str = "") -> None:
        for key, value in node.items():
            path = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
            if isinstance(value, dict):
                _flatten(value, path)
            else:
                flat[path] = value

    _flatten(data)
    return flat


def _system_language() -> str:
    env_lang = os.environ.get("LANG") or os.environ.get("LC_ALL")
    if env_lang and env_lang.lower().startswith("es"):
        return "es"

    try:
        system_locale = locale.getlocale()[0] or ""
    except (locale.Error, ValueError):
        system_locale = ""

    return "es" if system_locale.lower().startswith("es") else _DEFAULT_LANGUAGE


def available_languages() -> Dict[str, str]:
    """
    Get the languages that can be selected.

    ### Returns
    - Mapping of language code to language name.
    """

    return dict(LANGUAGES)


def get_language() -> str:
    """
    Get the active language code.
    """

    return _current_language


def set_language(code: str, persist: bool = True) -> str:
    """
    Switch the interface language.

    ### Arguments
    - code: Language code, unknown codes fall back to English.
    - persist: Whether to remember the choice for the next start.

    ### Returns
    - The language code that was applied.
    """

    global _current_language, _translations  # pylint: disable=global-statement

    if code not in LANGUAGES:
        code = _DEFAULT_LANGUAGE

    _current_language = code
    _translations = _load_translations(code)

    if persist:
        try:
            _LANGUAGE_FILE.write_text(code, encoding="utf-8")
        except OSError as exc:
            logger.debug("Could not persist language choice: %s", exc)

    return code


def init() -> str:
    """
    Load the language from `SPOTDL_LANG`, the saved choice or the system locale.

    ### Returns
    - The language code that was applied.
    """

    code: Optional[str] = os.environ.get("SPOTDL_LANG")
    if code is None:
        try:
            if _LANGUAGE_FILE.exists():
                stored = _LANGUAGE_FILE.read_text(encoding="utf-8").strip()
                code = stored if stored in LANGUAGES else None
        except OSError as exc:
            logger.debug("Could not read language file: %s", exc)

    if code is None:
        code = _system_language()

    return set_language(code, persist=False)


def tr(key: str, **kwargs: Any) -> str:
    """
    Translate a key to the active language.

    ### Arguments
    - key: Dotted translation key, such as "home.title".
    - kwargs: Values used to fill the placeholders of the text.

    ### Returns
    - The translated text, or the key itself when it is missing.
    """

    if not _translations:
        init()

    value = _translations.get(key, key)

    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError, ValueError) as exc:
            logger.debug("Error interpolating %s: %s", key, exc)
            return value

    return value
