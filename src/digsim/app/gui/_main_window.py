# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" The main window and widgets of the digsim gui application """

# pylint: disable=too-few-public-methods

from PySide6.QtCore import QMimeData, QSize, Qt
from PySide6.QtGui import QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class ComponentWidget(QPushButton):
    """A component widget, a 'clickable' widget with a custom paintEvent"""

    def __init__(self, app_model, placed_component, parent):
        super().__init__(parent, objectName=placed_component.component.name())
        self._app_model = app_model
        self._app_model.sig_component_notify.connect(self._component_notify)
        self._placed_component = placed_component
        self._mouse_grab_pos = None
        self._active_port = None

        self.setMouseTracking(True)
        self.move(self._placed_component.pos)

    def sizeHint(self):
        """QT event callback function"""
        return self._placed_component.size

    @property
    def component(self):
        """Get component from widget"""
        return self._placed_component.component

    def _component_notify(self, component):
        if component == self.component:
            self.update()

    def paintEvent(self, _):
        """QT event callback function"""
        painter = QPainter(self)
        self._placed_component.paint_component(painter)
        self._placed_component.paint_ports(painter, self._active_port)
        painter.end()

    def enterEvent(self, _):
        """QT event callback function"""
        if self._app_model.is_running and self.component.has_action:
            self.setCursor(Qt.PointingHandCursor)

    def leaveEvent(self, _):
        """QT event callback function"""
        self.setCursor(Qt.ArrowCursor)
        self._active_port = None

    def mousePressEvent(self, event):
        """QT event callback function"""
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                self._app_model.add_gui_event(self.component.onpress)
            elif self._app_model.has_new_wire():
                if self._active_port is not None:
                    self._app_model.new_wire_end(self.component, self._active_port)
            else:
                self._app_model.select(self._placed_component)
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
                self._placed_component.create_context_menu(self, event)
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
                self._placed_component.pos = self.pos()
                self._app_model.update_wires()
                self.parent().update()

    def mouseMoveEvent(self, event):
        """QT event callback function"""
        if self._app_model.is_running:
            return

        active_port = self._placed_component.get_port_for_point(event.pos())
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
                end_pos = self._placed_component.get_port_pos(self._active_port)
            self._app_model.set_new_wire_end_pos(self.pos() + end_pos)
            self.parent().update()

        elif self._mouse_grab_pos is not None:
            self.move(self.pos() + event.pos() - self._mouse_grab_pos)
            self._placed_component.pos = self.pos()
            self._app_model.update_wires()
            self.parent().update()


class CircuitArea(QWidget):
    """The circuit area class, this is where the component widgets are placed"""

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model
        self._app_model.sig_update_gui_components.connect(self._update_gui_components)

        for placed_comp in self._app_model.get_placed_components():
            ComponentWidget(app_model, placed_comp, self)

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

    def keyPressEvent(self, event):
        """QT event callback function"""
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
        position = event.pos()
        placed_component = self._app_model.add_component_by_name(component_name, position)
        comp = ComponentWidget(self._app_model, placed_component, self)
        comp.show()
        self._app_model.select(placed_component)

    def _update_gui_components(self):
        children = self.findChildren(ComponentWidget)
        for child in children:
            child.deleteLater()

        placed_components = self._app_model.get_placed_components()
        for placed_component in placed_components:
            comp = ComponentWidget(self._app_model, placed_component, self)
            comp.show()
        self._app_model.update_wires()
        self.update()


class SelectableComponentWidget(QPushButton):
    """
    The selectable component class,
    this is the component widget than can be dragged into the circuit area.
    """

    def __init__(self, app_model, name, parent):
        super().__init__(parent)
        self._app_model = app_model
        self._name = name
        self.setText(name)

    def sizeHint(self):
        """QT event callback function"""
        return QSize(70, 70)

    def mousePressEvent(self, event):
        """QT event callback function"""
        if event.buttons() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self._name)
            drag.setMimeData(mime)
            drag.setHotSpot(event.pos() - self.rect().topLeft())
            pixmap = QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.exec_(Qt.CopyAction | Qt.MoveAction, Qt.CopyAction)


class ComponentSelection(QWidget):
    """
    The component selection area,
    these are the components than can be dragged into the circuit area.
    """

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self.app_model = app_model
        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(5, 5, 5, 5)
        self.layout().setSpacing(5)
        self.layout().addWidget(SelectableComponentWidget(app_model, "OR", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "AND", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "NOT", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "XOR", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "NAND", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "NOR", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "DFF", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "VDD", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "GND", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "Clock", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "PushButton", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "OnOffSwitch", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "SevenSegment", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "HexDigit", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "Led", self))
        self.layout().addWidget(SelectableComponentWidget(app_model, "YosysComponent", self))


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

        selection_panel = ComponentSelection(app_model, self)
        self._selection_area = QScrollArea(self)
        self._selection_area.setFixedWidth(96)
        self._selection_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._selection_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._selection_area.setWidget(selection_panel)
        self.layout().addWidget(self._selection_area)
        self.layout().setStretchFactor(self._selection_area, 0)

        circuit_area = CircuitArea(app_model, self)
        self.layout().addWidget(circuit_area)
        self.layout().setStretchFactor(circuit_area, 1)

    def _control_notify(self, started):
        self._selection_area.setEnabled(not started)


class TopBar(QFrame):
    """
    The top widget with the control and status widgets
    """

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model
        self._app_model.sig_control_notify.connect(self._control_notify)
        self._app_model.sig_sim_time_notify.connect(self._sim_time_notify)
        self._time_s = 0

        self.setObjectName("TopBar")
        self.setStyleSheet("QFrame#TopBar {background: #ebebeb;}")

        self.setLayout(QHBoxLayout(self))
        self._start_button = QPushButton("Start Simulation", self)
        self._start_button.clicked.connect(self.start)
        self.layout().addWidget(self._start_button)
        self._reset_button = QPushButton("Reset Simulation", self)
        self._reset_button.clicked.connect(self.reset)
        self._reset_button.setEnabled(False)
        self.layout().addWidget(self._reset_button)
        self._sim_time = QLineEdit("0 s")
        self._sim_time.setReadOnly(True)
        self._sim_time.setAlignment(Qt.AlignRight)
        self._sim_time.setFrame(False)
        self._sim_time.selectionChanged.connect(lambda: self._sim_time.setSelection(0, 0))
        self.layout().addWidget(self._sim_time)
        self.layout().addStretch(1)
        self._load_button = QPushButton("Load Circuit", self)
        self._load_button.clicked.connect(self.load)
        self.layout().addWidget(self._load_button)
        self._save_button = QPushButton("Save Circuit", self)
        self._save_button.clicked.connect(self.save)
        self.layout().addWidget(self._save_button)

    def start(self):
        """Button action: Start"""
        self._start_button.setEnabled(False)
        self._load_button.setEnabled(False)
        self._save_button.setEnabled(False)
        self._app_model.model_start()

    def stop(self):
        """Button action: Stop"""
        self._start_button.setEnabled(False)
        self._app_model.model_stop()

    def load(self):
        """Button action: Load"""
        path = QFileDialog.getOpenFileName(
            self, "Load Circuit", "", "Circuit Files (*.circuit);;All Files (*.*)"
        )
        if len(path[0]) == 0:
            return
        self._app_model.load_circuit(path[0])

    def save(self):
        """Button action: Save"""
        path = QFileDialog.getSaveFileName(
            self, "Save Circuit", "", "Circuit Files (*.circuit);;All Files (*.*)"
        )
        if len(path[0]) == 0:
            return
        self._app_model.save_circuit(path[0])

    def reset(self):
        """Button action: Reset"""
        self._time_s = 0
        self._app_model.model_reset()
        self._reset_button.setEnabled(False)

    def _control_notify(self, started):
        if started:
            self._start_button.setText("Stop Similation")
            self._start_button.clicked.connect(self.stop)
            self._start_button.setEnabled(True)
        else:
            self._start_button.setText("Start Similation")
            self._start_button.clicked.connect(self.start)
            self._start_button.setEnabled(True)
            self._load_button.setEnabled(True)
            self._save_button.setEnabled(True)
            if self._time_s > 0:
                self._reset_button.setEnabled(True)

    def _sim_time_notify(self, time_s):
        self._sim_time.setText(f"{time_s:.2f} s")
        self._time_s = time_s
        if self._time_s and not self._app_model.is_running:
            self._reset_button.setEnabled(True)
        else:
            self._reset_button.setEnabled(False)


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

    def closeEvent(self, event):
        """QT event callback function"""
        self._app_model.model_stop()
        self._app_model.wait()
        super().closeEvent(event)
