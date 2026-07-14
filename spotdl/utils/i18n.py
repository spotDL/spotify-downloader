"""
Módulo de internacionalização (i18n) para spotDL.
Suporta tradução de strings via arquivos JSON.
"""

import gettext
import json
import locale as _locale
import os
from pathlib import Path
from typing import Dict, Optional

_LOCALES_DIR = Path(__file__).parent.parent / "locales"
_current_lang: str = "en"

try:
    _system_lang, _ = _locale.getdefaultlocale()
    if _system_lang and _system_lang.startswith("pt"):
        _current_lang = "pt_BR"
except (ValueError, Exception):
    pass

_translations: Dict[str, Dict[str, str]] = {}
_available_lang: Dict[str, str] = {}


def _lang_to_name(lang: str) -> str:
    names = {
        "en": "English (Inglês)",
        "pt_BR": "Português (Brasil)",
    }
    return names.get(lang, lang)


def _auto_detect_lang() -> str:
    try:
        sys_lang, _ = _locale.getdefaultlocale()
        if sys_lang and sys_lang.startswith("pt"):
            return "pt_BR"
    except (ValueError, Exception):
        pass
    return "en"


def _load_locales():
    if not _LOCALES_DIR.exists():
        return
    for f in sorted(_LOCALES_DIR.glob("*.json")):
        lang = f.stem
        try:
            with open(f, encoding="utf-8") as fh:
                _translations[lang] = json.load(fh)
            _available_lang[lang] = _lang_to_name(lang)
        except (json.JSONDecodeError, OSError):
            pass


def set_language(lang: str):
    global _current_lang
    lang = lang.strip()
    if lang not in _translations:
        _load_locales()
    if lang in _translations:
        _current_lang = lang
    else:
        _current_lang = "en"


def get_language() -> str:
    return _current_lang


def available_languages() -> Dict[str, str]:
    return dict(_available_lang)


def _(text: str) -> str:
    if _current_lang == "en":
        return text
    translations = _translations.get(_current_lang, {})
    return translations.get(text, text)


class I18nHelpFormatterMixin:
    """
    Mixin para traduzir strings de help e description no argparse.
    Uso: MyFormatter(I18nHelpFormatterMixin, argparse.HelpFormatter)
    """

    def _format_text(self, text):
        text = _(text) if text else text
        return super()._format_text(text)

    def _format_usage(self, usage, actions, groups, prefix):
        usage = _(usage) if usage else usage
        return super()._format_usage(usage, actions, groups, prefix)


def ngettext(singular: str, plural: str, n: int) -> str:
    if _current_lang == "en":
        return singular if n == 1 else plural
    translations = _translations.get(_current_lang, {})
    plural_trans = translations.get(plural, plural)
    singular_trans = translations.get(singular, singular)
    return singular_trans if n == 1 else plural_trans


_load_locales()
