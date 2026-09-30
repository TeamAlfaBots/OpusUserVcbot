import json
import os

from config import Config

_locale_cache = {}


def _load_locale(locale: str) -> dict:
    if locale not in _locale_cache:
        path = os.path.join("locales", f"{locale}.json")
        if not os.path.exists(path):
            path = os.path.join("locales", "en.json")
        with open(path, "r", encoding="utf-8") as f:
            _locale_cache[locale] = json.load(f)
    return _locale_cache[locale]


def t(key: str, **kwargs) -> str:
    """
    Fetch a text string by key from the active locale file and format it.
    Usage: t("login_success", bot_name="OpusUserbot")
    """
    strings = _load_locale(Config.LOCALE)
    text = strings.get(key, key)
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text
