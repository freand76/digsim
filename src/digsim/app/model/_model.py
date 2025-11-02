# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""An application model for a GUI simulated circuit"""

import queue
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from digsim.app.gui_objects import ComponentObject
from digsim.circuit.components.atoms import Component
from digsim.storage_model import AppFileDataClass

from ._model_objects import ModelObjects
from ._model_settings import ModelSettings
from ._model_shortcuts import ModelShortcuts


class AppModel(QThread):
    """The application model class for a GUI simulated circuit"""

    sig_audio_start = Signal(bool)
    sig_audio_notify = Signal(Component)
    sig_control_notify = Signal()
    sig_sim_time_notify = Signal(float)
    sig_synchronize_gui = Signal()
    sig_repaint = Signal()
    sig_update_wires = Signal()
    sig_delete_component = Signal(ComponentObject)
    sig_delete_wires = Signal()
    sig_error = Signal(str)
    sig_warning_log = Signal(str, str)
    sig_zoom_in_gui = Signal()
    sig_zoom_out_gui = Signal()

    def __init__(self):
        super().__init__()
        self._setup_model_components()
        self._started = False
        self._single_step = False
        self._changed = False
        self._gui_event_queue = queue.Queue()
        self._multi_select = False

    def _setup_model_components(self):
        self._model_objects = ModelObjects(self)
        self._model_shortcuts = ModelShortcuts(self)
        self._model_settings = ModelSettings(self)

    @property
    def objects(self):
        """return the model objects"""
        return self._model_objects

    @property
    def shortcuts(self):
        """return the model shortcuts"""
        return self._model_shortcuts

    @property
    def settings(self):
        """return the model settings"""
        return self._model_settings

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
        self.model_abort_wire()
        self._started = True
        self._single_step = False
        self.start()
        self.sig_control_notify.emit()

    def model_single_step(self):
        """Start model simulation thread"""
        self._started = True
        self._single_step = True
        self.start()
        self.sig_control_notify.emit()

    def model_stop(self):
        """Stop model simulation thread"""
        self._started = False
        self.wait()

    def model_reset(self):
        """Reset model simulation"""
        if not self._started:
            self.model_init()

    def model_changed(self):
        """Set changed to True, for example when gui has moved component"""
        self._changed = True
        self.sig_control_notify.emit()

    def model_add_event(self, func):
        """Add medel events (functions) from the GUI"""
        self._gui_event_queue.put(func)

    def model_abort_wire(self):
        if self._model_objects.new_wire.ongoing():
            self._model_objects.new_wire.abort()
            self.sig_repaint.emit()

    def run(self):
        """Simulation thread run function"""
        start_time = time.perf_counter()
        next_tick = start_time
        sim_tick_ms = 1000 / self._model_settings.get("update_frequency")
        real_time = self._model_settings.get("real_time")
        self.sig_audio_start.emit(True)
        while self._started:
            next_tick += sim_tick_ms / 1000

            # Execute one GUI event at a time
            if not self._gui_event_queue.empty():
                gui_event_func = self._gui_event_queue.get()
                gui_event_func()

            single_step_stop = self.objects.circuit.run(
                ms=sim_tick_ms, single_step=self._single_step
            )
            if single_step_stop:
                self._started = False

            self.objects.components.update_callback_objects()

            if not self._single_step and real_time:
                now = time.perf_counter()
                sleep_time = next_tick - now
                sleep_time = max(0.01, sleep_time)
            else:
                sleep_time = 0.01  # Sleep a little, to be able to handle event
            time.sleep(sleep_time)

            self.sig_sim_time_notify.emit(self.objects.circuit.time_ns / 1000000000)

        self._single_step = False
        self.sig_control_notify.emit()
        self.sig_audio_start.emit(False)

    def save_circuit(self, path):
        """Save the circuit with GUI information"""
        circuit_folder = str(Path(path).parent)
        model_dataclass = self.objects.circuit_to_model(circuit_folder)
        appfile_dataclass = AppFileDataClass(
            circuit=model_dataclass.circuit,
            gui=model_dataclass.gui,
            shortcuts=self.shortcuts.to_dict(),
            settings=self.settings.get_all(),
        )
        appfile_dataclass.save(path)
        self._changed = False
        self.sig_control_notify.emit()

    def load_circuit(self, path):
        """Load a circuit with GUI information"""
        self._model_clear()
        app_file_dc = AppFileDataClass.load(path)
        circuit_folder = str(Path(path).parent)
        if len(circuit_folder) == 0:
            circuit_folder = "."
        exception_str_list = self.objects.model_to_circuit(app_file_dc, circuit_folder)
        self.shortcuts.from_dict(app_file_dc.shortcuts)
        self.settings.from_dict(app_file_dc.settings)
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

    def zoom_in(self):
        """Send zoom in signal to GUI"""
        self.sig_zoom_in_gui.emit()

    def zoom_out(self):
        """Send zoom out signal to GUI"""
        self.sig_zoom_out_gui.emit()
