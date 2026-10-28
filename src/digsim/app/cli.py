# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The main class module of the digsim.app namespace"""

import argparse
import importlib.metadata
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLoggingCategory, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from digsim.app.gui import MainWindow
from digsim.app.model import AppModel

from ._desktop_entry import APP_ID, PACKAGE_NAME, setup_wayland_desktop_entry


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
        window.open_file(args.load)

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
