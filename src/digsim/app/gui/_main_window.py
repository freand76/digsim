# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" The main window and widgets of the digsim gui application """

# pylint: disable=too-few-public-methods

from functools import partial

from PySide6.QtCore import QMimeData, QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import digsim.app.gui_objects
from digsim.circuit.components.atoms import PortConnectionError

from ._component_settings import ComponentSettingsDialog
from ._top_bar import TopBar


class ComponentWidget(QPushButton):
    """A component widget, a 'clickable' widget with a custom paintEvent"""

    def __init__(self, app_model, component_object, parent):
        super().__init__(parent, objectName=component_object.component.name())
        self._app_model = app_model
        self._app_model.sig_component_notify.connect(self._component_notify)
        self._component_object = component_object
        self._mouse_grab_pos = None
        self._active_port = None

        self.setMouseTracking(True)
        self.move(self._component_object.pos)

    def sizeHint(self):
        """QT event callback function"""
        return self._component_object.size

    @property
    def component(self):
        """Get component from widget"""
        return self._component_object.component

    def _component_notify(self, component):
        if component == self.component:
            self.update()

    def paintEvent(self, _):
        """QT event callback function"""
        painter = QPainter(self)
        self._component_object.paint_component(painter)
        self._component_object.paint_ports(painter, self._active_port)
        painter.end()

    def enterEvent(self, _):
        """QT event callback function"""
        if self._app_model.is_running and self.component.has_action:
            self.setCursor(Qt.PointingHandCursor)

    def leaveEvent(self, _):
        """QT event callback function"""
        self.setCursor(Qt.ArrowCursor)
        self._active_port = None

    def _new_wire_end(self):
        try:
            self._app_model.new_wire_end(self.component, self._active_port)
        except PortConnectionError as exc:
            self._app_model.new_wire_abort()
            self._app_model.sig_error.emit(str(exc))
            self.parent().update()

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                self._app_model.add_gui_event(self.component.onpress)
            elif self._app_model.has_new_wire():
                if self._active_port is not None:
                    self._new_wire_end()
            else:
                self._app_model.select(self._component_object)
                if self._active_port is None:
                    # Prepare to move
                    self.setCursor(Qt.ClosedHandCursor)
                    self._mouse_grab_pos = event.pos()
                else:
                    self._app_model.new_wire_start(self.component, self._active_port)
        elif event.button() == Qt.RightButton:
            if self._app_model.is_running:
                return
            if self._app_model.has_new_wire():
                self._app_model.new_wire_abort()
            else:
                self._component_object.create_context_menu(self, event)
                self.adjustSize()
                self.update()

    def mouseReleaseEvent(self, event):
        """QT event callback function"""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                self._app_model.add_gui_event(self.component.onrelease)
            else:
                # Move complete
                self.setCursor(Qt.ArrowCursor)
                self._mouse_grab_pos = None
                self._component_object.pos = self.pos()
                self._app_model.update_wires()
                self.parent().update()

    def mouseMoveEvent(self, event):
        """QT event callback function"""
        if self._app_model.is_running:
            return

        active_port = self._component_object.get_port_for_point(event.pos())
        if active_port != self._active_port:
            self._active_port = active_port
            if self._active_port is not None:
                self.setCursor(Qt.CrossCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            self.update()

        if self._app_model.has_new_wire():
            end_pos = event.pos()
            if self._active_port:
                end_pos = self._component_object.get_port_pos(self._active_port)
            self._app_model.set_new_wire_end_pos(self.pos() + end_pos)
            self.parent().update()

        elif self._mouse_grab_pos is not None:
            self.move(self.pos() + event.pos() - self._mouse_grab_pos)
            self._component_object.pos = self.pos()
            self._app_model.update_wires()
            self.parent().update()


class CircuitArea(QWidget):
    """The circuit area class, this is where the component widgets are placed"""

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model
        self._app_model.sig_update_gui_components.connect(self._update_gui_components)

        for component_object in self._app_model.get_component_objects():
            ComponentWidget(app_model, component_object, self)

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

    def keyPressEvent(self, event):
        """QT event callback function"""
        if self._app_model.is_running:
            return
        if event.key() == Qt.Key_Delete:
            self._app_model.delete()
        event.accept()

    def paintEvent(self, _):
        """QT event callback function"""
        painter = QPainter(self)
        self._app_model.paint_wires(painter)
        painter.end()

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                return
            if self._app_model.has_new_wire():
                return
            self._app_model.select_pos(event.pos())
            self.setFocus()
            self.update()
        elif event.button() == Qt.RightButton:
            if self._app_model.is_running:
                return
            if self._app_model.has_new_wire():
                self._app_model.new_wire_abort()
                self.update()

    def mouseMoveEvent(self, event):
        """QT event callback function"""
        if self._app_model.is_running:
            return

        if self._app_model.has_new_wire():
            self._app_model.set_new_wire_end_pos(event.pos())
            self.update()

    def dragEnterEvent(self, event):
        """QT event callback function"""
        event.accept()

    def dropEvent(self, event):
        """QT event callback function"""
        event.setDropAction(Qt.IgnoreAction)
        event.accept()
        self.setFocus()

        component_name = event.mimeData().text()
        QTimer.singleShot(0, partial(self.add_component, component_name, event.pos()))

    def add_component(self, name, position):
        """
        Add componnent to circuit area
        Used be drag'n'drop into Circuit area or double click in SelectableComponentWidget
        """
        if position == QPoint(0, 0):
            position = self.rect().center()

        component_parameters = self._app_model.get_component_parameters(name)
        ok, settings = ComponentSettingsDialog.start(
            self, self._app_model, name, component_parameters
        )
        if ok:
            component_object = self._app_model.add_component_by_name(name, position, settings)
            comp = ComponentWidget(self._app_model, component_object, self)
            comp.show()
            self._app_model.select(component_object)

    def _update_gui_components(self):
        children = self.findChildren(ComponentWidget)
        for child in children:
            child.deleteLater()

        component_objects = self._app_model.get_component_objects()
        for component_object in component_objects:
            comp = ComponentWidget(self._app_model, component_object, self)
            comp.show()
        self._app_model.update_wires()
        self.update()


class SelectableComponentWidget(QPushButton):
    """
    The selectable component class,
    this is the component widget than can be dragged into the circuit area.
    """

    def __init__(self, name, parent, circuit_area, display_name=None):
        super().__init__(parent)
        self._name = name
        self._circuit_area = circuit_area
        self._paint_class = digsim.app.gui_objects.class_factory(name)
        if display_name is not None:
            self._display_name = display_name
        else:
            self._display_name = name

    def sizeHint(self):
        """QT event callback function"""
        return QSize(80, 105)

    def mousePressEvent(self, event):
        """QT event callback function"""
        if event.buttons() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self._name)
            drag.setMimeData(mime)
            drag.setHotSpot(event.pos() - self.rect().topLeft())
            pixmap = QPixmap(self.size().width(), self.size().width())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.exec_(Qt.CopyAction | Qt.MoveAction, Qt.CopyAction)

    def mouseDoubleClickEvent(self, _):
        """QT event callback function"""
        QTimer.singleShot(0, partial(self._circuit_area.add_component, self._name, QPoint(0, 0)))

    def paintEvent(self, event):
        """QT event callback function"""
        if self._paint_class is None:
            super().paintEvent(event)
        else:
            painter = QPainter(self)
            self._paint_class.paint_selectable_component(painter, self.size(), self._display_name)


class HorizontalLine(QFrame):
    """
    Horizontal line for the component selection
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class DescriptionText(QWidget):
    """
    Text label for the component selection
    """

    def __init__(self, parent, text):
        super().__init__(parent)
        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(HorizontalLine(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(label)
        self.layout().addWidget(HorizontalLine(self))


class ComponentSelection(QWidget):
    """
    The component selection area,
    these are the components than can be dragged into the circuit area.
    """

    def __init__(self, app_model, circuit_area, parent):
        super().__init__(parent)
        self.app_model = app_model
        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(5, 5, 5, 5)
        self.layout().setSpacing(5)
        self.layout().addWidget(DescriptionText(self, "Input"))
        self.layout().addWidget(SelectableComponentWidget("PushButton", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("OnOffSwitch", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("Clock", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("StaticValue", self, circuit_area))
        self.layout().addWidget(DescriptionText(self, "Output"))
        self.layout().addWidget(SelectableComponentWidget("Led", self, circuit_area))
        self.layout().addWidget(
            SelectableComponentWidget("HexDigit", self, circuit_area, display_name="Hex-digit")
        )
        self.layout().addWidget(
            SelectableComponentWidget("SevenSegment", self, circuit_area, display_name="7-Seg")
        )
        self.layout().addWidget(DescriptionText(self, "Gates"))
        self.layout().addWidget(SelectableComponentWidget("OR", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("AND", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("NOT", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("XOR", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("NAND", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("NOR", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("DFF", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("MUX", self, circuit_area))
        self.layout().addWidget(DescriptionText(self, "Bus / Bits"))
        self.layout().addWidget(SelectableComponentWidget("Bus2Bits", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("Bits2Bus", self, circuit_area))
        self.layout().addWidget(DescriptionText(self, "IC / Verilog"))
        self.layout().addWidget(
            SelectableComponentWidget("IntegratedCircuit", self, circuit_area, display_name="IC")
        )
        self.layout().addWidget(
            SelectableComponentWidget("YosysComponent", self, circuit_area, display_name="Yosys")
        )


class CircuitEditor(QSplitter):
    """
    The circuit editor, the component selction widget and the circuit area widget.
    """

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model
        self._app_model.sig_control_notify.connect(self._control_notify)

        self.setLayout(QHBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self._selection_area = QScrollArea(self)
        self._selection_area.setFixedWidth(106)
        self._selection_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._selection_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        circuit_area = CircuitArea(app_model, self)
        selection_panel = ComponentSelection(app_model, circuit_area, self)

        self._selection_area.setWidget(selection_panel)

        self.layout().addWidget(self._selection_area)
        self.layout().setStretchFactor(self._selection_area, 0)

        self.layout().addWidget(circuit_area)
        self.layout().setStretchFactor(circuit_area, 1)

    def _control_notify(self, started):
        self._selection_area.setEnabled(not started)


class CentralWidget(QWidget):
    """
    The central widget with the top widget and circuit editor widget.
    """

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model

        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        top_bar = TopBar(app_model, self)
        self.layout().addWidget(top_bar)
        self.layout().setStretchFactor(top_bar, 0)

        working_area = CircuitEditor(app_model, self)
        self.layout().addWidget(working_area)
        self.layout().setStretchFactor(working_area, 1)


class MainWindow(QMainWindow):
    """
    The main window for the applicaton.
    """

    def __init__(self, app_model):
        super().__init__()

        self._app_model = app_model
        self.resize(1280, 720)
        central_widget = CentralWidget(app_model, self)
        self.setWindowTitle("DigSim - Interactive Digital Logic Simulator")
        self.setCentralWidget(central_widget)
        self.setAcceptDrops(True)  # Needed to avoid "No drag target set."
        self._app_model.sig_error.connect(self.error_dialog)

    def error_dialog(self, error_message):
        """Error dialog for circuit area"""
        QMessageBox.critical(self.parent(), "Error!", error_message, QMessageBox.Ok)

    def closeEvent(self, event):
        """QT event callback function"""
        self._app_model.model_stop()
        self._app_model.wait()
        super().closeEvent(event)
