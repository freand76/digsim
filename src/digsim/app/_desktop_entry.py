# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
The Linux desktop entry, needed for the application icon on Wayland
(kept free from Qt imports so that it can be tested without a display)
"""

import os
import shutil
import sys
from pathlib import Path


APP_ID = "freand76.digsim"  # Wayland app_id / Desktop filename
APP_NAME = "Digsim"

PACKAGE_NAME = "digsim-logic-simulator"


def _desktop_exec() -> str | None:
    """
    The command for starting DigSim from the desktop menu, always the PyPI release:
    an installed 'digsim-logic-simulator' tool (fast, works offline) or else 'uvx'.
    None if neither is available.
    """
    if getattr(sys, "frozen", False):
        return _desktop_quote(sys.argv[0])
    # Absolute paths, the desktop session PATH may not include ~/.local/bin
    installed = shutil.which(PACKAGE_NAME)
    # Skip the script of the running environment ('uv run', 'uvx .', a dev venv),
    # tools installed with 'uv tool install' or 'pipx' are linked from elsewhere
    running_env_bin = (Path(sys.prefix) / "bin").resolve()
    if installed is not None and Path(installed).parent.resolve() != running_env_bin:
        return _desktop_quote(installed)
    uvx = shutil.which("uvx")
    if uvx is not None:
        return f"{_desktop_quote(uvx)} {PACKAGE_NAME}"
    return None


def _desktop_quote(arg: str) -> str:
    """Quote an Exec argument according to the desktop entry specification"""
    if not any(char in arg for char in " \t\n\"'\\><~|&;$*?#()`"):
        return arg
    escaped = "".join(f"\\{char}" if char in '"`$\\' else char for char in arg)
    # Backslashes are unescaped once more as a string value, before the quoting
    return f'"{escaped}"'.replace("\\", "\\\\")


def _desktop_entry_content() -> str:
    exec_cmd = _desktop_exec()
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={APP_NAME}",
        "Comment=Interactive Digital Logic Simulator",
        f"Exec={exec_cmd if exec_cmd is not None else PACKAGE_NAME}",
        f"Icon={APP_ID}",
        "Terminal=false",
        "Categories=Development;Engineering;",
        f"StartupWMClass={APP_ID}",
    ]
    if exec_cmd is None:
        # Nothing to start from the menu, keep the entry only for the window icon
        lines.append("NoDisplay=true")
    return "\n".join(lines) + "\n"


def setup_wayland_desktop_entry(icon_resource_path: Path) -> None:
    """
    Install the .desktop file and icon in the user data folder, so that Wayland
    compositors can show the application icon (matched by APP_ID). The files are
    rewritten whenever their content is out of date.
    """
    # Ensure this runs primarily on Linux/Wayland environments
    if not sys.platform.startswith("linux"):
        return

    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    apps_dir = data_home / "applications"
    theme_dir = data_home / "icons" / "hicolor"
    icons_dir = theme_dir / "256x256" / "apps"
    desktop_file = apps_dir / f"{APP_ID}.desktop"
    target_icon = icons_dir / f"{APP_ID}.png"

    if icon_resource_path.exists():
        icon_data = icon_resource_path.read_bytes()
        if not target_icon.exists() or target_icon.read_bytes() != icon_data:
            icons_dir.mkdir(parents=True, exist_ok=True)
            target_icon.write_bytes(icon_data)
            # GNOME Shell keeps showing the old icon until the theme folder changes
            os.utime(theme_dir)

    content = _desktop_entry_content()
    if not desktop_file.exists() or desktop_file.read_text(encoding="utf-8") != content:
        apps_dir.mkdir(parents=True, exist_ok=True)
        desktop_file.write_text(content, encoding="utf-8")
