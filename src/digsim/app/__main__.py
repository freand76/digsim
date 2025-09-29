# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The main class module of the digsim.app namespace"""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from digsim.app.gui import MainWindow
from digsim.app.model import AppModel


if __name__ == "__main__":

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

    app = QApplication(sys.argv)
    main_path = Path(__file__).parent
    image_path = main_path / "images/app_icon.png"
    icon = _create_app_icon(image_path)
    app.setWindowIcon(icon)
    app_model = AppModel()
    window = MainWindow(app_model)

    parser = argparse.ArgumentParser()
    parser.add_argument("--load", help="The circuit to load when starting the application")
    args = parser.parse_args()

    window.show()

    if args.load is not None:
        app_model.load_circuit(args.load)

    sys.exit(app.exec())
