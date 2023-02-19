# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" The main window and widgets of the digsim gui application """

# pylint: disable=too-few-public-methods
# pylint: disable=too-many-instance-attributes

from PySide6.QtCore import QMimeData, QPoint, QSize, Qt, QThread, Signal
from PySide6.QtGui import QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import digsim.app.gui_objects
from digsim.circuit.components.atoms import PortConnectionError


class ComponentSettingsBase(QFrame):
    """SettingsBase"""

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Panel)
        self._parent = parent
        self._parameter = parameter
        self._parameter_dict = parameter_dict
        self._settings = settings
        self._parent.sig_value_updated.connect(self._on_setting_change)

    def emit_signal(self):
        """Signal other settings components that a value has changed"""
        self._parent.sig_value_updated.emit(self._parameter)

    def _on_setting_change(self, parameter):
        if parameter != self._parameter:
            self.on_setting_change(parameter)

    def on_setting_change(self, parameter):
        """Called when other setting is changed"""


class ComponentSettingsSlider(ComponentSettingsBase):
    """SettingsSlider"""

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent, parameter, parameter_dict, settings)
        self.setLayout(QGridLayout(self))
        self._settings_slider = QSlider(Qt.Horizontal, self)
        self._settings_slider.setSingleStep(1)
        self._settings_slider.setPageStep(1)
        self._settings_slider.setTickPosition(QSlider.TicksBothSides)
        self._settings_slider.valueChanged.connect(self._update)
        self._value_label = QLabel("")
        self.layout().addWidget(QLabel(self._parameter_dict["description"]), 0, 0, 1, 6)
        self._setup()
        self.layout().addWidget(self._value_label, 1, 6, 1, 1)
        self.layout().addWidget(self._settings_slider, 1, 0, 1, 5)
        self._init_slider()

    def _init_slider(self):
        self._settings_slider.setValue(self._parameter_dict["default"])
        self._update(self._parameter_dict["default"])

    def _setup(self):
        self._settings_slider.setMaximum(self._parameter_dict["max"])
        self._settings_slider.setMinimum(self._parameter_dict["min"])
        self._settings_slider.setValue(self._parameter_dict["default"])
        self._settings_slider.setTickInterval(
            max(1, (self._parameter_dict["max"] - self._parameter_dict["min"]) / 10)
        )

    def _update(self, value):
        self._settings[self._parameter] = value
        self._value_label.setText(f"{value}")
        self.emit_signal()


class ComponentSettingsSliderWidthPow2(ComponentSettingsSlider):
    """SettingsSlider which is dependent on bitwidth"""

    def _setup(self):
        value_max = 2 ** self._settings.get("width", 1) - 1
        self._settings_slider.setMaximum(value_max)
        self._settings_slider.setMinimum(0)
        self._settings_slider.setTickInterval(max(1, (value_max - 0) / 10))

    def _update(self, value):
        self._settings[self._parameter] = value
        self._value_label.setText(f"{value}")
        self.emit_signal()

    def on_setting_change(self, parameter):
        if parameter == "width":
            self._setup()


class ComponentSettingsIntRangeSlider(ComponentSettingsSlider):
    """SettingsSlider (range)"""

    def _init_slider(self):
        default_index = self._parameter_dict["default_index"]
        self._settings_slider.setValue(default_index)
        self._update(default_index)

    def _setup(self):
        self._settings_slider.setMaximum(len(self._parameter_dict["range"]) - 1)
        self._settings_slider.setMinimum(0)
        self._settings_slider.setTickInterval(1)

    def _update(self, value):
        range_val = self._parameter_dict["range"][value]
        self._settings[self._parameter] = range_val
        self._value_label.setText(f"{range_val}")
        self.emit_signal()


class ComponentSettingsCheckBox(ComponentSettingsBase):
    """SettingsCheckbox"""

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent, parameter, parameter_dict, settings)
        self.setLayout(QHBoxLayout(self))
        self.setFrameStyle(QFrame.Panel)
        self._settings[parameter] = parameter_dict["default"]
        self._settings_checkbox = QCheckBox(parameter_dict["description"], self)
        self._settings_checkbox.setChecked(parameter_dict["default"])
        self.layout().addWidget(self._settings_checkbox)
        self._settings_checkbox.stateChanged.connect(self._update)
        self._settings_checkbox.setFocus()

    def _update(self, _):
        self._settings[self._parameter] = self._settings_checkbox.isChecked()


class ComponentSettingsCheckBoxWidthBool(ComponentSettingsBase):
    """SettingsCheckbox for width number of bits (max32)"""

    MAX_WIDTH = 32

    def __init__(self, parent, parameter, parameter_dict, settings):
        super().__init__(parent, parameter, parameter_dict, settings)
        self.setLayout(QGridLayout(self))
        self._bit_checkboxes = []
        for checkbox_id in range(self.MAX_WIDTH):
            checkbox = QCheckBox(f"bit{checkbox_id}")
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._update)
            self.layout().addWidget(checkbox, checkbox_id % 8, checkbox_id / 8, 1, 1)
            self._bit_checkboxes.append(checkbox)
        disable_all = QPushButton("Disable All")
        disable_all.clicked.connect(self._disable_all)
        enable_all = QPushButton("Enable All")
        enable_all.clicked.connect(self._enable_all)
        self.layout().addWidget(disable_all, 8, 0, 2, 1)
        self.layout().addWidget(enable_all, 8, 2, 2, 1)
        self._update()

    def _set_all(self, state):
        for checkbox_id in range(self.MAX_WIDTH):
            checkbox = self._bit_checkboxes[checkbox_id]
            checkbox.setChecked(state)

    def _enable_all(self):
        self._set_all(True)

    def _disable_all(self):
        self._set_all(False)

    def _update(self):
        self._settings[self._parameter] = []
        for checkbox_id in range(32):
            checkbox = self._bit_checkboxes[checkbox_id]
            checkbox.setEnabled(checkbox_id < self._settings["width"])
            if checkbox_id < self._settings["width"] and checkbox.isChecked():
                self._settings[self._parameter].append(checkbox_id)

    def on_setting_change(self, parameter):
        if parameter == "width":
            self._update()


class ComponentSettingsDialog(QDialog):
    """SettingsDialog"""

    sig_value_updated = Signal(str)

    @staticmethod
    def _is_file_path(parent, parameters):
        parameters_list = list(parameters.keys())
        first_key = parameters_list[0]
        settings = {}
        is_file_path = len(parameters_list) == 1 and parameters[first_key]["type"] == "path"
        if is_file_path:
            description = parameters[first_key]["description"]
            fileinfo = parameters[first_key]["fileinfo"]
            path = QFileDialog.getOpenFileName(
                parent, description, "", f"{fileinfo};;All Files (*.*)"
            )
            if len(path[0]) > 0:
                settings[first_key] = path[0]
        return is_file_path, settings

    @classmethod
    def start(cls, parent, name, parameters):
        """Start a settings dialog and return the settings"""
        if len(parameters) == 0:
            # No parameters, just place component without settings
            return True, {}

        is_file_path, settings = cls._is_file_path(parent, parameters)
        if is_file_path:
            return len(settings) > 0, settings

        dialog = ComponentSettingsDialog(parent, name, parameters)
        result = dialog.exec_()
        if result == QDialog.DialogCode.Rejected:
            return False, {}
        return True, dialog.get_settings()

    def __init__(self, parent, name, parameters):
        super().__init__(parent)
        self.setLayout(QVBoxLayout(self))
        self.setWindowTitle(f"Setup {name} component")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("QLabel{font-size: 18pt;}")

        self._settings = {}
        for parameter, parameter_dict in parameters.items():
            if parameter_dict["type"] == "width_pow2":
                widget = ComponentSettingsSliderWidthPow2(
                    self, parameter, parameter_dict, self._settings
                )
            elif parameter_dict["type"] == "width_bool":
                widget = ComponentSettingsCheckBoxWidthBool(
                    self, parameter, parameter_dict, self._settings
                )
            elif parameter_dict["type"] == int:
                widget = ComponentSettingsSlider(self, parameter, parameter_dict, self._settings)
            elif parameter_dict["type"] == bool:
                widget = ComponentSettingsCheckBox(self, parameter, parameter_dict, self._settings)
            elif parameter_dict["type"] == "intrange":
                widget = ComponentSettingsIntRangeSlider(
                    self, parameter, parameter_dict, self._settings
                )
            else:
                self._app_model.sig_error.emit(f"Unknown settings type '{parameter_dict['type']}'")
                continue

            self.layout().addWidget(widget)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout().addWidget(self.buttonBox)

    def get_settings(self):
        """Get settings from setting dialog"""
        return self._settings


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


class _DropActionThread(QThread):
    """This class is used to thredify the drop action"""

    sig_drop_action = Signal(str, QPoint)

    def __init__(self, circuit_area):
        super().__init__()
        self._circuit_area = circuit_area
        self._name = None
        self._position = None
        self.sig_drop_action.connect(self._setup)

    def _setup(self, name, position):
        self._name = name
        self._position = position
        self.start()

    def run(self):
        """Thread run function"""
        self._circuit_area.sig_add_component.emit(self._name, self._position)


class CircuitArea(QWidget):
    """The circuit area class, this is where the component widgets are placed"""

    sig_add_component = Signal(str, QPoint)

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self._app_model = app_model
        self._app_model.sig_update_gui_components.connect(self._update_gui_components)

        for component_object in self._app_model.get_component_objects():
            ComponentWidget(app_model, component_object, self)

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self.sig_add_component.connect(self._add_component)

        self._thread = _DropActionThread(self)

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
        self._thread.sig_drop_action.emit(component_name, event.pos())

    def _add_component(self, name, position):
        if position == QPoint(0, 0):
            position = self.rect().center()

        component_parameters = self._app_model.get_component_parameters(name)
        ok, settings = ComponentSettingsDialog.start(self, name, component_parameters)
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
        self._circuit_area.sig_add_component.emit(self._name, QPoint(0, 0))

    def paintEvent(self, event):
        """QT event callback function"""
        if self._paint_class is None:
            super().paintEvent(event)
        else:
            painter = QPainter(self)
            self._paint_class.paint_selectable_component(painter, self.size(), self._display_name)


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
        self.layout().addWidget(SelectableComponentWidget("OR", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("AND", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("NOT", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("XOR", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("NAND", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("NOR", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("DFF", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("MUX", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("Bus2Bits", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("Bits2Bus", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("PushButton", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("OnOffSwitch", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("Clock", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("StaticValue", self, circuit_area))
        self.layout().addWidget(
            SelectableComponentWidget("SevenSegment", self, circuit_area, display_name="7-Seg")
        )
        self.layout().addWidget(
            SelectableComponentWidget("HexDigit", self, circuit_area, display_name="Hex-digit")
        )
        self.layout().addWidget(SelectableComponentWidget("Led", self, circuit_area))
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
        self._started = False

        self.setObjectName("TopBar")
        self.setStyleSheet("QFrame#TopBar {background: #ebebeb;}")

        self.setLayout(QHBoxLayout(self))
        self._start_button = QPushButton("Start Simulation", self)
        self._start_button.clicked.connect(self.start_stop)
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

    def start_stop(self):
        """Button action: Start/Stop"""
        if not self._started:
            self._started = True
            self._start_button.setEnabled(False)
            self._load_button.setEnabled(False)
            self._save_button.setEnabled(False)
            self._app_model.model_start()
        else:
            self._started = False
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
            self._start_button.setEnabled(True)
        else:
            self._start_button.setText("Start Similation")
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
        self._app_model.sig_error.connect(self.error_dialog)

    def error_dialog(self, error_message):
        """Error dialog for circuit area"""
        QMessageBox.critical(self.parent(), "Error!", error_message, QMessageBox.Ok)

    def closeEvent(self, event):
        """QT event callback function"""
        self._app_model.model_stop()
        self._app_model.wait()
        super().closeEvent(event)
