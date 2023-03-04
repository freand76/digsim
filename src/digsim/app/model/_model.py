# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" An application model for a GUI simulated circuit """

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods

import json
import os
import queue
import time

from PySide6.QtCore import QThread, Signal

from digsim.circuit import Circuit
from digsim.circuit.components.atoms import Component, DigsimException

from ._model_components import ModelComponents
from ._model_wires import ModelWires


class AppModel(QThread):
    """The application model class for a GUI simulated circuit"""

    sig_component_notify = Signal(Component)
    sig_control_notify = Signal()
    sig_sim_time_notify = Signal(float)
    sig_update_gui_components = Signal()
    sig_error = Signal(str)
    sig_warning_log = Signal(str, str)

    def __init__(self):
        super().__init__()
        self._circuit = Circuit(name="DigSimCircuit", vcd="gui.vcd")
        self._model_components = ModelComponents(self, self._circuit)
        self._model_wires = ModelWires(self)
        self._started = False
        self._changed = False
        self._sim_tick_ms = 50
        self._gui_event_queue = queue.Queue()
        self._multi_select = False

    @property
    def component_objects(self):
        """return the model components"""
        return self._model_components

    @property
    def wire_objects(self):
        """return the model components"""
        return self._model_wires

    def clear(self):
        """Clear components and wires"""
        self._model_components.clear()
        self._model_wires.clear()

    def circuit_init(self):
        """(Re)initialize the circuit"""
        self._circuit.init()
        self._model_components.init()
        self.sig_sim_time_notify.emit(0)

    def _get_model_objects(self):
        """Get list of all model objects"""
        model_objects = self._model_components.get_object_list()
        model_objects.extend(self._model_wires.get_object_list())
        return model_objects

    def multi_select(self, multi_select):
        """Enable/Disable multiple select of objects"""
        self._multi_select = multi_select

    def select(self, model_object=None):
        """Select model object"""
        if model_object is not None and model_object.selected:
            return
        for comp in self._get_model_objects():
            if comp == model_object:
                comp.select(True)
            elif not self._multi_select:
                comp.select(False)

    def select_by_position(self, pos):
        """Select object from position"""
        self.select(None)
        return self._model_wires.select(pos, self._multi_select)

    def get_selected_objects(self):
        """Get selected objects"""
        objects = []
        for obj in self._get_model_objects():
            if obj.selected:
                objects.append(obj)
        return objects

    def select_by_rect(self, rect):
        """Select object be rectangle"""
        self.select(None)
        for obj in self._get_model_objects():
            if obj.in_rect(rect):
                obj.select(True)

    def delete(self):
        """Delete selected object(s)"""
        selected_objects = self.get_selected_objects()
        for obj in selected_objects:
            if ModelComponents.is_component_object(obj):
                self._model_components.delete(obj)
        for obj in selected_objects:
            if ModelWires.is_wire_object(obj):
                self._model_wires.delete(obj)
        self.model_changed()
        self.sig_update_gui_components.emit()

    def move_selected_components(self, delta_pos):
        """Move selected objects"""
        selected_objects = self.get_selected_objects()
        for obj in selected_objects:
            if ModelComponents.is_component_object(obj):
                obj.move_delta(delta_pos)
                obj.update()
                self._model_wires.update()
                self.model_changed(update_components=False)

    @property
    def circuit(self):
        """Return the circuit"""
        return self._circuit

    def model_start(self):
        """Start model simulation thread"""
        self._started = True
        self.start()
        self.sig_control_notify.emit()

    def model_stop(self):
        """Stop model simulation thread"""
        self._started = False

    def model_reset(self):
        """Reset model simulation"""
        if not self._started:
            self.circuit_init()

    def model_changed(self, update_control=True, update_components=True):
        """Set changed to True, for example when gui has moved component"""
        self._changed = True
        if update_control:
            self.sig_control_notify.emit()
        if update_components:
            self.sig_update_gui_components.emit()

    def add_gui_event(self, func):
        """Add medel events (functions) from the GUI"""
        self._gui_event_queue.put(func)

    def run(self):
        """Simulation thread run function"""
        start_time = time.perf_counter()
        next_tick = start_time
        while self._started:
            next_tick += self._sim_tick_ms / 1000

            # Execute one GUI event at a time
            if not self._gui_event_queue.empty():
                gui_event_func = self._gui_event_queue.get()
                gui_event_func()

            self._circuit.run(ms=self._sim_tick_ms)

            self._model_components.update_callback_objects()

            now = time.perf_counter()
            sleep_time = next_tick - now
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.sig_sim_time_notify.emit(self._circuit.time_ns / 1000000000)

        self.sig_control_notify.emit()

    @property
    def is_running(self):
        """Return True if the simulation thread is running"""
        return self._started

    def save_circuit(self, path):
        """Save the circuit with GUI information"""
        circuit_folder = os.path.dirname(path)
        circuit_dict = self._circuit.to_dict(circuit_folder)
        circuit_dict["gui"] = {}
        for comp, comp_object in self._component_objects.items():
            circuit_dict["gui"][comp.name()] = comp_object.to_dict()
        json_object = json.dumps(circuit_dict, indent=4)
        with open(path, mode="w", encoding="utf-8") as json_file:
            json_file.write(json_object)
        self._changed = False
        self.sig_control_notify.emit()

    def load_circuit(self, path):
        """Load a circuit with GUI information"""
        self.clear()
        with open(path, mode="r", encoding="utf-8") as json_file:
            circuit_dict = json.load(json_file)

        circuit_folder = os.path.dirname(path)
        if len(circuit_folder) == 0:
            circuit_folder = "."
        exception_str_list = []
        try:
            exception_str_list = self._circuit.from_dict(
                circuit_dict, circuit_folder, component_exceptions=False, connect_exceptions=False
            )
        except DigsimException as exc:
            self.sig_error.emit(f"Load Circuit error: {str(exc)}")
            return

        for comp in self._circuit.get_toplevel_components():
            x = circuit_dict["gui"][comp.name()]["x"]
            y = circuit_dict["gui"][comp.name()]["y"]
            self._model_components.add_object(comp, x, y)

        for comp in self._circuit.get_toplevel_components():
            for src_port in comp.outports():
                for dst_port in src_port.get_wires():
                    self._model_wires.add_object(src_port, dst_port, connect=False)
        self.circuit_init()
        self._changed = False
        self.sig_update_gui_components.emit()
        self.sig_control_notify.emit()
        if len(exception_str_list) > 0:
            self.sig_warning_log.emit("Load Circuit Warning", "\n".join(exception_str_list))

    def clear_circuit(self):
        """Clear the circuit"""
        self.clear()
        self._changed = False
        self.sig_update_gui_components.emit()
        self.sig_control_notify.emit()

    def has_changes(self):
        """Return True if there are changes in the model since last save"""
        return self._changed
