import pathlib
import sys

from PySide6.QtWidgets import QApplication


sys.path.append(str(pathlib.Path(__file__).parent.parent.parent.resolve()))

from digsim.app.gui import MainWindow
from digsim.app.model import AppModel


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_model = AppModel()
    window = MainWindow(app_model)
    window.show()
    sys.exit(app.exec())
