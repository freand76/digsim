from PySide6.QtCore import (QByteArray, QDataStream, QIODevice, QMimeData,
                            QPoint, QRectF, Qt)
from PySide6.QtGui import QDrag, QFont, QPainter, QStaticText
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QMainWindow, QPushButton,
                               QSplitter, QStatusBar, QVBoxLayout, QWidget)


class ComponentWidget(QPushButton):
    TOP_BOTTOM_MARGIN = 20
    PORT_SIDE = 8

    @classmethod
    def get_port_points(cls, ports, x, height):
        port_dict = {}
        if len(ports) == 1:
            port_dict[ports[0].name] = QPoint(x, height / 2)
        elif len(ports) > 1:
            port_distance = (height - 2 * cls.TOP_BOTTOM_MARGIN) / (len(ports) - 1)
            for idx, port in enumerate(ports):
                port_dict[port.name] = QPoint(
                    x, cls.TOP_BOTTOM_MARGIN + idx * port_distance
                )
        return port_dict

    def __init__(self, app_model, component, parent):
        super().__init__(parent, objectName=component.name)
        self.resize(120, 100)
        self._app_model = app_model
        self._component = component
        self._name = component.name
        self._active = False
        self._app_model.sig_notify.connect(self._component_update)
        self._inports = self.get_port_points(self._component.inports, 0, self.height())
        self._outports = self.get_port_points(
            self._component.outports, self.width() - self.PORT_SIDE - 1, self.height()
        )

    @property
    def component(self):
        return self._component

    def get_port_pos(self, portname):
        if portname in self._inports:
            return self._inports[portname]
        if portname in self._outports:
            return self._outports[portname]
        return None

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
        comp_rect = QRectF(event.rect())
        comp_rect.setBottom(comp_rect.bottom() - 1)
        comp_rect.setRight(comp_rect.right() - 4)
        comp_rect.setLeft(comp_rect.left() + 4)
        painter.setPen(Qt.black)
        if self._active:
            painter.setBrush(Qt.SolidPattern)
            painter.setBrush(Qt.red)
        else:
            painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(comp_rect, 5, 5)
        painter.setFont(QFont("Arial", 8))
        painter.drawText(comp_rect, Qt.AlignCenter, self._name)

        port_rect = QRectF(event.rect())
        painter.setBrush(Qt.SolidPattern)
        painter.setBrush(Qt.green)
        painter.setFont(QFont("Arial", 8))
        for portname, point in self._inports.items():
            painter.drawRect(
                point.x(),
                point.y() - self.PORT_SIDE / 2,
                self.PORT_SIDE,
                self.PORT_SIDE,
            )
            port_text = QStaticText(portname)
            painter.drawStaticText(
                point.x() + 15,
                point.y() - port_text.size().height() / 3,
                port_text,
            )
        for portname, point in self._outports.items():
            painter.drawRect(
                point.x(),
                point.y() - self.PORT_SIDE / 2,
                self.PORT_SIDE,
                self.PORT_SIDE,
            )
            port_text = QStaticText(portname)
            painter.drawStaticText(
                point.x() - port_text.textWidth() - 15,
                point.y() - port_text.size().height() / 3,
                port_text,
            )
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
        self.parent().update()


class CircuitArea(QWidget):
    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model
        self._component_widgets = {}

        circuit = self._app_model.circuit
        for idx, comp in enumerate(circuit.components):
            compWidget = ComponentWidget(app_model, comp, self)
            compWidget.move(self._app_model.get_position(comp))
            self._component_widgets[comp] = compWidget
        self.setAcceptDrops(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        for comp, comp_widget in self._component_widgets.items():
            outports = comp.outports
            for port in outports:
                for dst in port.wires:
                    dst_comp = dst.parent
                    dst_widget = self._component_widgets[dst_comp]

                    src_point = comp_widget.pos() + comp_widget.get_port_pos(port.name)
                    dst_point = dst_widget.pos() + dst_widget.get_port_pos(dst.name)
                    painter.drawLine(src_point, dst_point)
        painter.end()

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
