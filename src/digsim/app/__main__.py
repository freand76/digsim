# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

import sys

from PySide6.QtWidgets import QApplication

from digsim.app.gui import MainWindow
from digsim.app.model import AppModel


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_model = AppModel()
    window = MainWindow(app_model)
    window.show()
    sys.exit(app.exec())
