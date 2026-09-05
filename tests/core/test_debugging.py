import sys
from unittest.mock import MagicMock

from hrcek.core.debugging import maybe_start_debugger


def test_disabled_debugger_does_nothing_and_imports_nothing(monkeypatch):
    monkeypatch.delitem(sys.modules, "debugpy", raising=False)
    assert maybe_start_debugger(enabled=False, port=5678, wait=False) is False
    assert "debugpy" not in sys.modules


def test_enabled_debugger_listens_on_the_configured_port(monkeypatch):
    fake = MagicMock()
    monkeypatch.setitem(sys.modules, "debugpy", fake)

    assert maybe_start_debugger(enabled=True, port=5679, wait=False) is True
    fake.listen.assert_called_once_with(("127.0.0.1", 5679))
    fake.wait_for_client.assert_not_called()


def test_enabled_debugger_can_wait_for_a_client(monkeypatch):
    fake = MagicMock()
    monkeypatch.setitem(sys.modules, "debugpy", fake)

    maybe_start_debugger(enabled=True, port=5680, wait=True)
    fake.wait_for_client.assert_called_once_with()
