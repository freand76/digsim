# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The main class module of the digsim.app namespace"""

import argparse
import importlib
import os
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLoggingCategory, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from digsim.app.gui import MainWindow
from digsim.app.model import AppModel


APP_ID = "freand76.digsim"  # Wayland app_id / Desktop filename
APP_NAME = "Digsim"

PACKAGE_NAME = "digsim-logic-simulator"


def _create_app_icon(image_path: Path) -> QIcon:
    image_pixmap = QPixmap(image_path)
    size = max(image_pixmap.size().height(), image_pixmap.size().width())
    icon_pixmap = QPixmap(size, size)
    icon_pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(icon_pixmap)
    painter.drawPixmap(
        (icon_pixmap.size().width() - image_pixmap.size().width()) // 2,
        (icon_pixmap.size().height() - image_pixmap.size().height()) // 2,
        image_pixmap,
    )
    painter.end()
    return QIcon(icon_pixmap)


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
    icons_dir = data_home / "icons" / "hicolor" / "256x256" / "apps"
    desktop_file = apps_dir / f"{APP_ID}.desktop"
    target_icon = icons_dir / f"{APP_ID}.png"

    if icon_resource_path.exists():
        icon_data = icon_resource_path.read_bytes()
        if not target_icon.exists() or target_icon.read_bytes() != icon_data:
            icons_dir.mkdir(parents=True, exist_ok=True)
            target_icon.write_bytes(icon_data)

    content = _desktop_entry_content()
    if not desktop_file.exists() or desktop_file.read_text(encoding="utf-8") != content:
        apps_dir.mkdir(parents=True, exist_ok=True)
        desktop_file.write_text(content, encoding="utf-8")


def _start(args: argparse.Namespace, package_version: str) -> int:
    # Ensure system files are created for Wayland compositors
    main_path = Path(__file__).parent
    image_path = main_path / "images/app_icon.png"
    setup_wayland_desktop_entry(image_path)

    # Qt's Wayland text-input support logs a warning on focus changes when no
    # surface is focused; it is harmless and floods the terminal.
    # A QT_LOGGING_RULES environment variable still overrides this rule.
    QLoggingCategory.setFilterRules("qt.qpa.wayland.textinput=false")

    # Wayland critical step: links the PySide6 app window to the .desktop entry
    QCoreApplication.setApplicationName("digsim")
    QCoreApplication.setOrganizationDomain("io.github.freand76")
    QGuiApplication.setDesktopFileName(APP_ID)
    app = QApplication(sys.argv)

    icon = _create_app_icon(image_path)
    app.setWindowIcon(icon)

    app_model = AppModel()
    window = MainWindow(app_model, package_version)
    window.show()

    if args.load is not None:
        app_model.load_circuit(args.load)

    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", "-v", action="store_true", help="Print the version of digsim.app"
    )
    parser.add_argument("--load", "-l", help="The circuit to load when starting the application")
    args = parser.parse_args()

    package_version = importlib.metadata.version(PACKAGE_NAME)

    if args.version:
        print(f"DigSim '{PACKAGE_NAME}' [v{package_version}]")
        return 0
    else:
        return _start(args, package_version)
