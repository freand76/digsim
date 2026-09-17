# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The main class module of the digsim.app namespace"""

import argparse
import importlib
import os
import sys
import textwrap
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt
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
    icon_pixmap.fill(Qt.transparent)
    painter = QPainter(icon_pixmap)
    painter.drawPixmap(
        (icon_pixmap.size().width() - image_pixmap.size().width()) // 2,
        (icon_pixmap.size().height() - image_pixmap.size().height()) // 2,
        image_pixmap,
    )
    painter.end()
    return QIcon(icon_pixmap)


def setup_wayland_desktop_entry(icon_resource_path: Path):
    """Generates the .desktop file and places the icon in user data locations on first run."""
    # Ensure this runs primarily on Linux/Wayland environments
    if not sys.platform.startswith("linux"):
        return

    # 1. Define target paths
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    apps_dir = data_home / "applications"
    icons_dir = data_home / "icons" / "hicolor" / "256x256" / "apps"

    desktop_file = apps_dir / f"{APP_ID}.desktop"
    target_icon = icons_dir / f"{APP_ID}.png"

    # 2. Install icon if missing
    if not target_icon.exists() and icon_resource_path.exists():
        icons_dir.mkdir(parents=True, exist_ok=True)
        target_icon.write_bytes(icon_resource_path.read_bytes())

    # 3. Create .desktop file if missing
    if not desktop_file.exists():
        apps_dir.mkdir(parents=True, exist_ok=True)

        # Get path to executable or script
        exec_path = (
            sys.argv[0] if getattr(sys, "frozen", False) else f"{sys.executable} -m digsim.app.cli"
        )

        content = textwrap.dedent(f"""\
        [Desktop Entry]
            Type=Application
            Name={APP_NAME}
            Exec={exec_path}
            Icon={APP_ID}
            Terminal=false
            Categories=Development;Engineering;
            StartupWMClass={APP_ID}
            """)
        desktop_file.write_text(content, encoding="utf-8")


def _start(args, package_version):
    # Ensure system files are created for Wayland compositors
    main_path = Path(__file__).parent
    image_path = main_path / "images/app_icon.png"
    setup_wayland_desktop_entry(image_path)

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


def main():
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
