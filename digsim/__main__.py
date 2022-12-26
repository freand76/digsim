import pathlib
import sys

from PyQt5.QtWidgets import QApplication

sys.path.append(pathlib.Path(__file__).parent.resolve())

from digsim.gui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
