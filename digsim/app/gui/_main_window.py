from PySide6.QtCore import (QByteArray, QDataStream, QIODevice, QMimeData,
                            QPoint, QRectF, Qt)
from PySide6.QtGui import QDrag, QFont, QPainter, QStaticText
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QMainWindow, QPushButton,
                               QSplitter, QStatusBar, QVBoxLayout, QWidget)


class ComponentWidget(QPushButton):
    TOP_BOTTOM_MARGIN = 20
    PORT_SIDE = 8

    def __init__(self, app_model, placed_component, parent):
        super().__init__(parent, objectName=placed_component.component.name)
        self.resize(120, 100)
        self._app_model = app_model
        self._placed_component = placed_component
        self._name = placed_component.component.name
        self._app_model.sig_notify.connect(self._component_update)
        self.move(self._placed_component.pos)
        self._mouse_grab_pos = None

    @property
    def component(self):
        return self._placed_component.component

    def _component_update(self, component):
        if component == self.component:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        comp_rect = QRectF(event.rect())
        comp_rect.setBottom(comp_rect.bottom() - 1)
        comp_rect.setRight(comp_rect.right() - 4)
        comp_rect.setLeft(comp_rect.left() + 4)
        painter.setPen(Qt.black)
        painter.setBrush(Qt.SolidPattern)
        if self.component.active:
            painter.setBrush(Qt.green)
        else:
            painter.setBrush(Qt.gray)
        painter.drawRoundedRect(comp_rect, 5, 5)
        painter.setFont(QFont("Arial", 8))
        painter.drawText(comp_rect, Qt.AlignCenter, self._name)

        port_rect = QRectF(event.rect())
        painter.setBrush(Qt.SolidPattern)
        painter.setBrush(Qt.gray)
        painter.setFont(QFont("Arial", 8))
        for portname, point in self._placed_component.ports.items():
            painter.drawRect(
                point.x(),
                point.y() - self.PORT_SIDE / 2,
                self.PORT_SIDE,
                self.PORT_SIDE,
            )
        painter.end()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            # print(f"press {self._name}")
            self.component.onpress()
            self.component.circuit.run(ms=1)
        elif event.button() == Qt.RightButton:
            # save the click position to keep it consistent when dragging
            self._mouse_grab_pos = event.pos()
            # self.move(self._mouse_grab_pos)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            # print(f"release {self._name}")
            self.component.onrelease()
            self.component.circuit.run(ms=1)
        elif event.button() == Qt.RightButton:
            # save the click position to keep it consistent when dragging
            self._mouse_grab_pos = None
            self._placed_component.pos = self.pos()
            self._app_model.update_wires()
            self.parent().update()

    def mouseMoveEvent(self, event):
        if event.buttons() != Qt.RightButton:
            return
        if self._mouse_grab_pos is not None:
            self.move(self.pos() + event.pos() - self._mouse_grab_pos)
            self._placed_component.pos = self.pos()
            self._app_model.update_wires()
            self.parent().update()


class CircuitArea(QWidget):
    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model

        for placed_comp in self._app_model.get_placed_components():
            compWidget = ComponentWidget(app_model, placed_comp, self)

    def paintEvent(self, event):
        painter = QPainter(self)
        wires = self._app_model.get_wires()
        for wire in wires:
            painter.drawLine(wire.src, wire.dst)
        painter.end()


class ComponentSelection(QWidget):
    def __init__(self, app_model, parent):
        super().__init__(parent)
        self.app_model = app_model


class CircuitEditor(QSplitter):
    def __init__(self, app_model, parent):
        super().__init__(parent)

        self.app_model = app_model
        self.setLayout(QHBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        selection_area = ComponentSelection(app_model, self)
        selection_area.setMinimumWidth(250)
        selection_area.setMaximumWidth(350)
        self.layout().addWidget(selection_area)
        self.layout().setStretchFactor(selection_area, 0)

        circuit_area = CircuitArea(app_model, self)
        self.layout().addWidget(circuit_area)
        self.layout().setStretchFactor(circuit_area, 1)


class TopBar(QFrame):
    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model

        self.setObjectName("TopBar")
        self.setStyleSheet("QFrame#TopBar {background: #ebebeb;}")

        self.setLayout(QHBoxLayout(self))


class CentralWidget(QWidget):
    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model

        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        top_bar = TopBar(app_model, self)
        self.layout().addWidget(top_bar)
        self.layout().setStretchFactor(top_bar, 0)

        working_area = CircuitArea(app_model, self)
        self.layout().addWidget(working_area)
        self.layout().setStretchFactor(working_area, 1)


class StatusBar(QStatusBar):
    def __init__(self, app_model, parent):
        super().__init__(parent)


class MainWindow(QMainWindow):
    def __init__(self, app_model):
        super().__init__()
        self._app_model = app_model

        self.resize(1280, 720)
        centralWidget = CentralWidget(app_model, self)
        self.setCentralWidget(centralWidget)

        self.setStatusBar(StatusBar(app_model, self))
        self.setWindowTitle("DigSim Logic Simulator")
