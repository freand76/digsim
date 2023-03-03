# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" The main class module of the digsim.app namespace """

import argparse
import sys

from PySide6.QtWidgets import QApplication

from digsim.app.gui import MainWindow
from digsim.app.model import AppModel


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_model = AppModel()
    window = MainWindow(app_model)

    parser = argparse.ArgumentParser()
    parser.add_argument("--load", help="The circuit to load when starting the application")
    args = parser.parse_args()

    window.show()

    if args.load is not None:
        app_model.load_circuit(args.load)

    sys.exit(app.exec())
