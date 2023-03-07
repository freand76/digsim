# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" An application model for a GUI simulated circuit """

import json
import os
import queue
import time

from PySide6.QtCore import QThread, Signal

from digsim.circuit.components.atoms import Component

from ._model_objects import ModelObjects
from ._model_shortcuts import ModelShortcuts


class AppModel(QThread):
    """The application model class for a GUI simulated circuit"""

    sig_component_notify = Signal(Component)
    sig_control_notify = Signal()
    sig_sim_time_notify = Signal(float)
    sig_synchronize_gui = Signal()
    sig_error = Signal(str)
    sig_warning_log = Signal(str, str)

    def __init__(self):
        super().__init__()
        self._model_objects = ModelObjects(self)
        self._model_shortcuts = ModelShortcuts(self)
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
    def shortcuts(self):
        """return the model shortcuts"""
        return self._model_shortcuts

    @property
    def is_running(self):
        """Return True if the simulation thread is running"""
        return self._started

    @property
    def is_changed(self):
        """Return True if there are changes in the model since last save"""
        return self._changed

    def _model_clear(self):
        """Clear model"""
        self.objects.clear()
        self.shortcuts.clear()
        self._changed = False

    def model_init(self):
        """(Re)initialize the model/circuit"""
        self.objects.circuit.init()
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
            self.sig_synchronize_gui.emit()

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

            self.objects.circuit.run(ms=self._sim_tick_ms)

            self.objects.components.update_callback_objects()

            now = time.perf_counter()
            sleep_time = next_tick - now
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.sig_sim_time_notify.emit(self.objects.circuit.time_ns / 1000000000)

        self.sig_control_notify.emit()

    def save_circuit(self, path):
        """Save the circuit with GUI information"""
        circuit_folder = os.path.dirname(path)
        circuit_dict = self.objects.circuit_to_dict(circuit_folder)
        shortcuts_dict = self.shortcuts.to_dict()
        circuit_dict.update(shortcuts_dict)
        json_object = json.dumps(circuit_dict, indent=4)
        with open(path, mode="w", encoding="utf-8") as json_file:
            json_file.write(json_object)
        self._changed = False
        self.sig_control_notify.emit()

    def load_circuit(self, path):
        """Load a circuit with GUI information"""
        self._model_clear()
        with open(path, mode="r", encoding="utf-8") as json_file:
            circuit_dict = json.load(json_file)
        circuit_folder = os.path.dirname(path)
        if len(circuit_folder) == 0:
            circuit_folder = "."
        exception_str_list = self.objects.dict_to_circuit(circuit_dict, circuit_folder)
        self.shortcuts.from_dict(circuit_dict)
        self.model_init()
        self._changed = False
        self.objects.reset_undo_stack()
        self.sig_synchronize_gui.emit()
        self.sig_control_notify.emit()
        if len(exception_str_list) > 0:
            self.sig_warning_log.emit("Load Circuit Warning", "\n".join(exception_str_list))

    def clear_circuit(self):
        """Clear the circuit"""
        self.objects.push_undo_state()
        self._model_clear()
        self.sig_synchronize_gui.emit()
        self.sig_control_notify.emit()
