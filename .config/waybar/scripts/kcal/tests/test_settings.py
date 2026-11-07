import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import settings  # noqa: E402


def write(tmp_path, obj):
    p = tmp_path / "config.json"
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj), encoding="utf-8")
    return str(p)


def test_missing_file_gives_defaults(tmp_path):
    assert settings.load(str(tmp_path / "nope.json")) == settings.DEFAULTS


def test_default_masthead_is_neutral_malayalam():
    assert settings.DEFAULTS["masthead_text"] == "കേരള കലണ്ടർ"
    assert settings.DEFAULTS["masthead_image"] == ""


def test_relative_image_is_read_from_config_folder(tmp_path):
    s = settings.load(write(tmp_path, {"masthead_image": "logo.png", "masthead_height": 60}))
    assert s["masthead_image"] == str(tmp_path / "logo.png")
    assert s["masthead_height"] == 60


def test_home_and_absolute_image_paths(tmp_path):
    s = settings.load(write(tmp_path, {"masthead_image": "~/x.png"}))
    assert s["masthead_image"] == os.path.expanduser("~/x.png")
    s = settings.load(write(tmp_path, {"masthead_image": "/abs/x.svg"}))
    assert s["masthead_image"] == "/abs/x.svg"


def test_broken_json_falls_back(tmp_path):
    assert settings.load(write(tmp_path, "{ not json")) == settings.DEFAULTS


def test_wrong_types_and_unknown_keys_are_ignored(tmp_path):
    s = settings.load(write(tmp_path, {"masthead_height": "big", "search_command": "zen", "x": 1,
                                       "masthead_text": "എന്റെ കലണ്ടർ"}))
    assert s["masthead_height"] == 88
    assert s["search_command"] == []
    assert "x" not in s
    assert s["masthead_text"] == "എന്റെ കലണ്ടർ"


def test_height_bounds_and_bool(tmp_path):
    for bad in (0, 4000, True):
        assert settings.load(write(tmp_path, {"masthead_height": bad}))["masthead_height"] == 88


def test_non_object_json(tmp_path):
    assert settings.load(write(tmp_path, [1, 2])) == settings.DEFAULTS


def test_env_and_xdg_paths(tmp_path, monkeypatch):
    monkeypatch.delenv("KCAL_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert settings.config_path() == str(tmp_path / "kcal" / "config.json")
    monkeypatch.setenv("KCAL_CONFIG", "/elsewhere/c.json")
    assert settings.config_path() == "/elsewhere/c.json"


def test_user_css_only_when_present(tmp_path, monkeypatch):
    monkeypatch.setenv("KCAL_CONFIG", str(tmp_path / "config.json"))
    assert settings.user_css() is None
    (tmp_path / "style.css").write_text("*{}")
    assert settings.user_css() == str(tmp_path / "style.css")
