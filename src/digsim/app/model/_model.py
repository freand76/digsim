# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" An application model for a GUI simulated circuit """

import json
import os
import queue
import time

from PySide6.QtCore import QThread, Signal

from digsim.circuit import Circuit
from digsim.circuit.components.atoms import Component, DigsimException

from ._model_objects import ModelObjects


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
        self._model_objects = ModelObjects(self, self._circuit)
        self._started = False
        self._changed = False
        self._sim_tick_ms = 50
        self._gui_event_queue = queue.Queue()
        self._multi_select = False

    @property
    def objects(self):
        """return the model objects"""
        return self._model_objects

    @property
    def is_running(self):
        """Return True if the simulation thread is running"""
        return self._started

    @property
    def is_changed(self):
        """Return True if there are changes in the model since last save"""
        return self._changed

    def model_init(self):
        """(Re)initialize the model/circuit"""
        self._circuit.init()
        self.objects.init()
        self.sig_sim_time_notify.emit(0)

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
            self.model_init()

    def model_changed(self, update_control=True, update_components=True):
        """Set changed to True, for example when gui has moved component"""
        self._changed = True
        if update_control:
            self.sig_control_notify.emit()
        if update_components:
            self.sig_update_gui_components.emit()

    def model_add_event(self, func):
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

            self.objects.components.update_callback_objects()

            now = time.perf_counter()
            sleep_time = next_tick - now
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.sig_sim_time_notify.emit(self._circuit.time_ns / 1000000000)

        self.sig_control_notify.emit()

    def save_circuit(self, path):
        """Save the circuit with GUI information"""
        circuit_folder = os.path.dirname(path)
        circuit_dict = self._circuit.to_dict(circuit_folder)
        circuit_dict["gui"] = {}
        for comp, comp_object in self.objects.components.get_dict().items():
            circuit_dict["gui"][comp.name()] = comp_object.to_dict()
        json_object = json.dumps(circuit_dict, indent=4)
        with open(path, mode="w", encoding="utf-8") as json_file:
            json_file.write(json_object)
        self._changed = False
        self.sig_control_notify.emit()

    def load_circuit(self, path):
        """Load a circuit with GUI information"""
        self.objects.clear()
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
            self.objects.components.add_object(comp, x, y)

        for comp in self._circuit.get_toplevel_components():
            for src_port in comp.outports():
                for dst_port in src_port.get_wires():
                    self.objects.wires.add_object(src_port, dst_port, connect=False)
        self.model_init()
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
