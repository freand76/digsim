# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the generated Linux desktop entry"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from digsim.app import cli


ICON = b"\x89PNG fake icon"


@pytest.fixture
def data_home(tmp_path, monkeypatch):
    """Use a temporary XDG data folder on a (pretend) Linux system"""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delattr(sys, "frozen", raising=False)
    return tmp_path / "share"


@pytest.fixture
def icon(tmp_path):
    """A fake application icon"""
    path = tmp_path / "app_icon.png"
    path.write_bytes(ICON)
    return path


def _which(found):
    return lambda name: found.get(name)


def _entry(data_home):
    return (data_home / "applications" / f"{cli.APP_ID}.desktop").read_text(encoding="utf-8")


def test_installed_tool_is_preferred(data_home, icon, monkeypatch):
    """An installed digsim-logic-simulator is started directly"""
    monkeypatch.setattr(
        cli.shutil,
        "which",
        _which({"digsim-logic-simulator": "/opt/bin/digsim-logic-simulator", "uvx": "/u/uvx"}),
    )
    cli.setup_wayland_desktop_entry(icon)
    entry = _entry(data_home)
    assert "Exec=/opt/bin/digsim-logic-simulator\n" in entry
    assert "NoDisplay" not in entry
    assert (data_home / "icons/hicolor/256x256/apps" / f"{cli.APP_ID}.png").read_bytes() == ICON


def test_uvx_runs_pypi_release(data_home, icon, monkeypatch):
    """Without an installed tool, the PyPI release is started with uvx"""
    monkeypatch.setattr(cli.shutil, "which", _which({"uvx": "/home/me/.local/bin/uvx"}))
    cli.setup_wayland_desktop_entry(icon)
    assert "Exec=/home/me/.local/bin/uvx digsim-logic-simulator\n" in _entry(data_home)


def test_exec_path_with_space_is_quoted(data_home, icon, monkeypatch):
    """Paths with special characters are quoted in Exec"""
    monkeypatch.setattr(cli.shutil, "which", _which({"uvx": "/home/my user/bin/uvx"}))
    cli.setup_wayland_desktop_entry(icon)
    assert 'Exec="/home/my user/bin/uvx" digsim-logic-simulator\n' in _entry(data_home)


def test_running_environment_script_is_skipped(data_home, icon, monkeypatch):
    """The script of the running environment (uv run, a dev venv) is not an installed tool"""
    running_script = str(Path(sys.prefix) / "bin" / "digsim-logic-simulator")
    monkeypatch.setattr(
        cli.shutil, "which", _which({"digsim-logic-simulator": running_script, "uvx": "/u/uvx"})
    )
    cli.setup_wayland_desktop_entry(icon)
    assert "Exec=/u/uvx digsim-logic-simulator\n" in _entry(data_home)


def test_hidden_when_nothing_to_start(data_home, icon, monkeypatch):
    """Without a launcher the entry is kept (for the window icon) but hidden from menus"""
    monkeypatch.setattr(cli.shutil, "which", _which({}))
    cli.setup_wayland_desktop_entry(icon)
    assert "NoDisplay=true\n" in _entry(data_home)


def test_outdated_entry_is_rewritten(data_home, icon, monkeypatch):
    """An entry from an older version (e.g. a stale interpreter path) is replaced"""
    monkeypatch.setattr(cli.shutil, "which", _which({"uvx": "/u/uvx"}))
    desktop_file = data_home / "applications" / f"{cli.APP_ID}.desktop"
    desktop_file.parent.mkdir(parents=True)
    desktop_file.write_text("[Desktop Entry]\n    Exec=/old/python -m digsim.app.cli\n")
    cli.setup_wayland_desktop_entry(icon)
    entry = _entry(data_home)
    assert "/old/python" not in entry
    assert all(not line.startswith(" ") for line in entry.splitlines())


def test_not_linux(data_home, icon, monkeypatch):
    """Nothing is written on other platforms"""
    monkeypatch.setattr(sys, "platform", "win32")
    cli.setup_wayland_desktop_entry(icon)
    assert not data_home.exists()


@pytest.mark.skipif(
    shutil.which("desktop-file-validate") is None, reason="needs desktop-file-utils"
)
@pytest.mark.parametrize("found", [{"uvx": "/home/my user/bin/uvx"}, {}])
def test_entry_is_valid(data_home, icon, monkeypatch, found):
    """The generated entry passes desktop-file-validate"""
    monkeypatch.setattr(cli.shutil, "which", _which(found))
    cli.setup_wayland_desktop_entry(icon)
    desktop_file = data_home / "applications" / f"{cli.APP_ID}.desktop"
    result = subprocess.run(
        ["desktop-file-validate", str(desktop_file)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
