from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


class ComponentWidget(QPushButton):
    def __init__(self, app_model, placed_component, parent):
        super().__init__(parent, objectName=placed_component.component.name)
        self._app_model = app_model
        self._app_model.sig_component_notify.connect(self._component_notify)
        self._placed_component = placed_component
        self._mouse_grab_pos = None
        self._active_port = None

        self.setMouseTracking(True)
        self.resize(self._placed_component.size)
        self.move(self._placed_component.pos)

    @property
    def component(self):
        return self._placed_component.component

    def _component_notify(self, component):
        if component == self.component:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        self._placed_component.paint_component(painter)
        self._placed_component.paint_ports(painter, self._active_port)
        painter.end()

    def enterEvent(self, event):
        if self._app_model.is_running and self.component.has_action:
            self.setCursor(Qt.PointingHandCursor)

    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        self._active_port = None

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            if self._app_model.is_running:
                self._app_model.add_gui_event(self.component.onpress)
            elif self._app_model.has_new_wire():
                if self._active_port is not None:
                    self._app_model.new_wire_end(self.component, self._active_port)
            else:
                if self._active_port is None:
                    # Prepare to move
                    self.setCursor(Qt.ClosedHandCursor)
                    self._mouse_grab_pos = event.pos()
                else:
                    self._app_model.new_wire_start(self.component, self._active_port)

    def mouseReleaseEvent(self, event):
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
    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model

        for placed_comp in self._app_model.get_placed_components():
            ComponentWidget(app_model, placed_comp, self)

        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        self._app_model.paint_wires(painter)
        painter.end()

    def mouseMoveEvent(self, event):
        if self._app_model.is_running:
            return

        if self._app_model.has_new_wire():
            self._app_model.set_new_wire_end_pos(event.pos())
            self.update()


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
        self._sim_time.selectionChanged.connect(lambda: self._sim_time.setSelection(0, 0))
        self.layout().addWidget(self._sim_time)
        self.layout().setStretchFactor(self._start_button, 0)
        self.layout().addStretch(1)

    def start(self):
        self._start_button.setEnabled(False)
        self._app_model.model_start()

    def stop(self):
        self._start_button.setEnabled(False)
        self._app_model.model_stop()

    def reset(self):
        self._time_s = 0
        self._sim_time.setText("0 s")
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
            if self._time_s > 0:
                self._reset_button.setEnabled(True)

    def _sim_time_notify(self, time_s):
        self._sim_time.setText(f"{time_s:.2f} s")
        self._time_s = time_s


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

    def closeEvent(self, event):
        self._app_model.model_stop()
        self._app_model.wait()
        super().closeEvent(event)
