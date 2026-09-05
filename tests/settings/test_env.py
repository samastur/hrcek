import pytest
from django.core.exceptions import ImproperlyConfigured

from hrcek.settings import env


def test_env_str_returns_value(monkeypatch):
    monkeypatch.setenv("HRCEK_TEST_STR", "hello")
    assert env.env_str("HRCEK_TEST_STR") == "hello"


def test_env_str_returns_default_when_unset(monkeypatch):
    monkeypatch.delenv("HRCEK_TEST_STR", raising=False)
    assert env.env_str("HRCEK_TEST_STR", "fallback") == "fallback"


def test_env_str_raises_when_required_and_unset(monkeypatch):
    monkeypatch.delenv("HRCEK_TEST_STR", raising=False)
    with pytest.raises(ImproperlyConfigured) as excinfo:
        env.env_str("HRCEK_TEST_STR")
    assert "HRCEK_TEST_STR" in str(excinfo.value)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("true", True),
        ("YES", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("No", False),
        ("off", False),
    ],
)
def test_env_bool_parses_common_spellings(monkeypatch, raw, expected):
    monkeypatch.setenv("HRCEK_TEST_BOOL", raw)
    assert env.env_bool("HRCEK_TEST_BOOL") is expected


def test_env_bool_rejects_nonsense(monkeypatch):
    monkeypatch.setenv("HRCEK_TEST_BOOL", "maybe")
    with pytest.raises(ImproperlyConfigured):
        env.env_bool("HRCEK_TEST_BOOL")


def test_env_int_parses_and_rejects(monkeypatch):
    monkeypatch.setenv("HRCEK_TEST_INT", "42")
    assert env.env_int("HRCEK_TEST_INT") == 42
    monkeypatch.setenv("HRCEK_TEST_INT", "forty-two")
    with pytest.raises(ImproperlyConfigured):
        env.env_int("HRCEK_TEST_INT")


def test_env_list_splits_and_strips(monkeypatch):
    monkeypatch.setenv("HRCEK_TEST_LIST", "a, b ,c")
    assert env.env_list("HRCEK_TEST_LIST") == ["a", "b", "c"]


def test_env_list_returns_empty_for_blank(monkeypatch):
    monkeypatch.setenv("HRCEK_TEST_LIST", "  ")
    assert env.env_list("HRCEK_TEST_LIST") == []


def test_load_dotenv_sets_only_missing_keys(monkeypatch, tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "# a comment\n"
        "HRCEK_FROM_FILE=file-value\n"
        "HRCEK_ALREADY_SET=file-value\n"
        "\n"
        'HRCEK_QUOTED="quoted value"\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("HRCEK_FROM_FILE", raising=False)
    monkeypatch.setenv("HRCEK_ALREADY_SET", "real-value")
    monkeypatch.delenv("HRCEK_QUOTED", raising=False)

    env.load_dotenv(dotenv)

    assert env.env_str("HRCEK_FROM_FILE") == "file-value"
    assert env.env_str("HRCEK_ALREADY_SET") == "real-value"
    assert env.env_str("HRCEK_QUOTED") == "quoted value"


def test_load_dotenv_is_silent_when_absent(tmp_path):
    env.load_dotenv(tmp_path / "nope.env")


def test_env_float_parses_and_rejects(monkeypatch):
    monkeypatch.setenv("HRCEK_TEST_FLOAT", "0.25")
    assert env.env_float("HRCEK_TEST_FLOAT") == 0.25
    monkeypatch.setenv("HRCEK_TEST_FLOAT", "a quarter")
    with pytest.raises(ImproperlyConfigured):
        env.env_float("HRCEK_TEST_FLOAT")


def test_env_float_uses_its_default(monkeypatch):
    monkeypatch.delenv("HRCEK_TEST_FLOAT", raising=False)
    assert env.env_float("HRCEK_TEST_FLOAT", 1.0) == 1.0
