from PySide6.QtCore import (QByteArray, QDataStream, QIODevice, QMimeData,
                            QRectF, Qt)
from PySide6.QtGui import QDrag, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QMainWindow, QPushButton,
                               QSplitter, QStatusBar, QVBoxLayout, QWidget)


class MyButton(QPushButton):
    def __init__(self, app_model, component, parent):
        super().__init__(parent, objectName=component.name)
        self.resize(120, 100)
        self._app_model = app_model
        self._component = component
        self._name = component.name
        self._active = False
        self._app_model.sig_notify.connect(self._component_update)

    def _component_update(self, component):
        if component == self._component:
            action_port = component.ports[0]
            if action_port.intval == 1:
                self._active = True
            else:
                self._active = False
            self.parent().update()

    def paintEvent(self, event):
        painter = QPainter(self)
        path = QPainterPath()
        object_rect = QRectF(event.rect())
        object_rect.setBottom(object_rect.bottom() - 1)
        object_rect.setRight(object_rect.right() - 1)
        painter.setPen(Qt.black)
        path.addRoundedRect(object_rect, 5, 5)
        if self._active:
            painter.fillPath(path, Qt.red)
        painter.drawPath(path)
        painter.setFont(QFont("Arial", 12))
        painter.drawText(object_rect, Qt.AlignCenter, self._name)

        inports = self._component.inports
        outports = self._component.outports
        # print("IN", inports, "\nOUT", outports)
        painter.end()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            # print(f"press {self._name}")
            self._component.onpress()
            self._component.circuit.run(ms=1)
        elif event.button() == Qt.RightButton:
            # save the click position to keep it consistent when dragging
            self.mousePos = event.pos()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            # print(f"release {self._name}")
            self._component.onrelease()
            self._component.circuit.run(ms=1)

    def mouseMoveEvent(self, event):
        if event.buttons() != Qt.RightButton:
            return
        mimeData = QMimeData()
        # create a byte array and a stream that is used to write into
        byteArray = QByteArray()
        stream = QDataStream(byteArray, QIODevice.WriteOnly)
        # set the objectName and click position to keep track of the widget
        # that we're moving and it's click position to ensure that it will
        # be moved accordingly
        stream.writeQString(self.objectName())
        stream.writeQVariant(self.mousePos)
        # create a custom mimeData format to save the drag info
        mimeData.setData("myApp/QtWidget", byteArray)
        drag = QDrag(self)
        # add a pixmap of the widget to show what's actually moving
        drag.setPixmap(self.grab())
        drag.setMimeData(mimeData)
        # set the hotspot according to the mouse press position
        drag.setHotSpot(self.mousePos - self.rect().topLeft())
        drag.exec_()


class CircuitArea(QWidget):
    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model

        circuit = self._app_model.circuit
        for idx, comp in enumerate(circuit.components):
            pushButton = MyButton(app_model, comp, self)
            pushButton.move(20 + 200 * idx, 20)
            self.setAcceptDrops(True)

    def paintEvent(self, event):
        # Prepare to draw wires
        path = QPainterPath()
        # path.moveTo(50, 50)
        # path.cubicTo(0, 60, 40, 100, 120, 120)
        # painter = QPainter(self)
        # painter.drawPath(path)

    def dragEnterEvent(self, event):
        # only accept our mimeData format, ignoring any other data content
        if event.mimeData().hasFormat("myApp/QtWidget"):
            event.accept()

    def dropEvent(self, event):
        stream = QDataStream(event.mimeData().data("myApp/QtWidget"))
        # QDataStream objects should be read in the same order as they were written
        objectName = stream.readQString()
        # find the child widget that has the objectName set within the drag event
        widget = self.findChild(QWidget, objectName)
        if not widget:
            return
        # move the widget relative to the original mouse position, so that
        # it will be placed exactly where the user drags it and according to
        # the original click position
        widget.move(event.pos() - stream.readQVariant())


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
