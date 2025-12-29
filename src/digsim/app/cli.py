# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The main class module of the digsim.app namespace"""

import argparse
import importlib
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from digsim.app.gui import MainWindow
from digsim.app.model import AppModel


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


def _start(args, package_version):
    app = QApplication(sys.argv)
    main_path = Path(__file__).parent
    image_path = main_path / "images/app_icon.png"
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
