"""User settings for kcal: masthead, search and style overrides.

Read from $KCAL_CONFIG, else $XDG_CONFIG_HOME/kcal/config.json (~/.config/kcal/config.json).
Every key is optional; see config.example.json. Unknown keys are ignored, a bad file falls back
to the defaults (a broken config must never stop the popup from opening).
"""
import json
import os
import sys

DEFAULTS = {
    "masthead_text": "കേരള കലണ്ടർ",  # "Kerala calendar"
    "masthead_image": "",  # PNG/SVG/JPEG path; relative paths are read from the config folder
    "masthead_height": 88,  # px; the mini month boxes beside it are ~87px
    "search_command": [],  # e.g. ["firefox", "--search", "{query}"]; empty = default browser
    "search_url": "https://www.google.com/search?q={query}",
}


def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "kcal")


def config_path():
    return os.environ.get("KCAL_CONFIG") or os.path.join(config_dir(), "config.json")


def _check(key, val):
    want = type(DEFAULTS[key])
    if want is int:
        return isinstance(val, int) and not isinstance(val, bool) and 8 <= val <= 400
    if want is list:
        return isinstance(val, list) and all(isinstance(x, str) for x in val)
    return isinstance(val, want)


def load(path=None):
    path = path or config_path()
    out = dict(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        raw = {}
    except (OSError, ValueError) as e:
        print(f"kcal: ignoring {path}: {e}", file=sys.stderr)
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    for k, v in raw.items():
        if k in DEFAULTS:
            if _check(k, v):
                out[k] = v
            else:
                print(f"kcal: ignoring {k!r} in {path}: expected {type(DEFAULTS[k]).__name__}", file=sys.stderr)
    out["masthead_image"] = resolve(out["masthead_image"], os.path.dirname(os.path.abspath(path)))
    return out


def resolve(p, base):
    if not p:
        return ""
    p = os.path.expanduser(os.path.expandvars(p))
    return p if os.path.isabs(p) else os.path.join(base, p)


def user_css():
    """Optional style override next to the config, loaded after the built-in style.css."""
    p = os.path.join(os.path.dirname(config_path()), "style.css")
    return p if os.path.isfile(p) else None
