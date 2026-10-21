# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""An application model for a GUI simulated circuit"""

from __future__ import annotations

import queue
import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from digsim.app._wire_key import port_key
from digsim.app.gui_objects import ComponentObject
from digsim.circuit.components.atoms import Component, DigsimException
from digsim.storage_model import AppFileDataClass, ModelDataClass

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

    def __init__(self) -> None:
        super().__init__()
        self._setup_model_components()
        # Set to keep the simulation loop in run() going, cleared to stop it
        self._keep_running = False
        self._single_step = False
        self._changed = False
        self._gui_event_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._circuit_folder = ""
        self.finished.connect(self._thread_finished)

    def _setup_model_components(self) -> None:
        self._model_objects = ModelObjects(self)
        self._model_shortcuts = ModelShortcuts(self)
        self._model_settings = ModelSettings(self)

    @property
    def objects(self) -> ModelObjects:
        """return the model objects"""
        return self._model_objects

    @property
    def shortcuts(self) -> ModelShortcuts:
        """return the model shortcuts"""
        return self._model_shortcuts

    @property
    def settings(self) -> ModelSettings:
        """return the model settings"""
        return self._model_settings

    @property
    def is_running(self) -> bool:
        """
        Return True if the simulation thread is running. That is also after the loop has
        been told to stop, until the thread has finished, since it still uses the circuit.
        """
        return self._keep_running or self.isRunning()

    @property
    def is_changed(self) -> bool:
        """Return True if there are changes in the model since last save"""
        return self._changed

    def _model_clear(self) -> None:
        """Clear model"""
        self.objects.clear()
        self.shortcuts.clear()
        self._changed = False

    def model_init(self) -> None:
        """(Re)initialize the model/circuit"""
        # Events from before the reset are not for the new state
        while not self._gui_event_queue.empty():
            self._gui_event_queue.get_nowait()
        self.objects.circuit.init()
        self.objects.init()
        self.sig_sim_time_notify.emit(0)

    def model_start(self) -> None:
        """Start model simulation thread"""
        self.model_abort_wire()
        self._keep_running = True
        self._single_step = False
        self.start()
        self.sig_control_notify.emit()

    def model_single_step(self) -> None:
        """Start the simulation thread, to run until the next input event"""
        self._keep_running = True
        self._single_step = True
        self.start()
        self.sig_control_notify.emit()

    def model_stop(self) -> None:
        """Stop model simulation thread"""
        self._keep_running = False
        self.wait()

    def model_reset(self) -> None:
        """Reset model simulation"""
        if not self.is_running:
            self.model_init()

    def model_changed(self) -> None:
        """Set changed to True, for example when gui has moved component"""
        self._changed = True
        self.sig_control_notify.emit()

    def model_add_event(self, func: Callable[[], None]) -> None:
        """Add model events (functions) from the GUI, run by the simulation thread"""
        self._gui_event_queue.put(func)

    def model_abort_wire(self) -> None:
        """Abort a wire that is being drawn"""
        if self._model_objects.new_wire.ongoing():
            self._model_objects.new_wire.abort()
            self.sig_repaint.emit()

    def model_remove_wire_corner(self) -> None:
        """Remove the last corner of a wire that is being drawn"""
        if self._model_objects.new_wire.ongoing():
            self._model_objects.new_wire.remove_last_click()
            self.sig_repaint.emit()

    def run(self) -> None:
        """Simulation thread run function"""
        start_time = time.perf_counter()
        next_tick = start_time
        sim_tick_ms = 1000 / self._model_settings.get("update_frequency")
        real_time = self._model_settings.get("real_time")
        self.sig_audio_start.emit(True)
        while self._keep_running:
            next_tick += sim_tick_ms / 1000

            # Execute one GUI event at a time
            if not self._gui_event_queue.empty():
                gui_event_func = self._gui_event_queue.get()
                gui_event_func()

            single_step_stop = self.objects.circuit.run(
                ms=sim_tick_ms, single_step=self._single_step
            )
            if single_step_stop:
                self._keep_running = False

            self.objects.components.update_callback_objects()

            if not self._single_step and real_time:
                now = time.perf_counter()
                sleep_time = next_tick - now
                sleep_time = max(0.01, sleep_time)
            else:
                sleep_time = 0.01  # Sleep a little, to be able to handle event
            time.sleep(sleep_time)

            self.sig_sim_time_notify.emit(self.objects.circuit.time_ns / 1000000000)

        # Handle the GUI events that came before the stop (like the release of a button),
        # instead of at the next start
        self._run_gui_events()
        self.objects.components.update_callback_objects()

        self._single_step = False
        self.sig_audio_start.emit(False)
        # sig_control_notify is sent by _thread_finished(), when the thread has stopped

    def _thread_finished(self) -> None:
        """Called in the GUI thread when the simulation thread has finished"""
        # QThread.finished is sent right before the thread ends, wait until it has
        self.wait()
        self.sig_control_notify.emit()

    def _run_gui_events(self) -> None:
        """Execute all queued GUI events"""
        while True:
            try:
                gui_event_func = self._gui_event_queue.get_nowait()
            except queue.Empty:
                return
            gui_event_func()

    def model_to_circuit(self, model_dc: AppFileDataClass | ModelDataClass) -> list[str]:
        if isinstance(model_dc, AppFileDataClass):
            # Loaded model
            dc = ModelDataClass.from_app_file_dc(model_dc)
        else:
            dc = model_dc

        exception_str_list: list[str] = []
        try:
            # Create circuit
            exception_str_list = self.objects.circuit.from_dataclass(
                dc.circuit,
                self._circuit_folder,
                component_exceptions=False,
                connect_exceptions=False,
            )
            # Add component positions
            self.objects.components.add_gui_positions(dc.gui)
            # The wires, after the components are placed: lines, or the wires of files
            # from before lines (and of undo states)
            if dc.lines:
                for line in dc.lines:
                    line.connect(self.objects.circuit, exception_str_list)
                self.objects.wires.from_lines(dc.lines)
            else:
                self.objects.wires.from_dict(dc.wires)
                if isinstance(model_dc, AppFileDataClass):
                    # Every output of a line drives every input of it, as when it is saved
                    for src_port, dst_port in self.objects.wires.complete_lines():
                        exception_str_list.append(
                            f"Line completed: {port_key(src_port)} drives {port_key(dst_port)}"
                        )
        except DigsimException as exc:
            self.sig_error.emit(f"Circuit error: {exc!s}")
            return exception_str_list
        return exception_str_list

    def circuit_to_model(self) -> ModelDataClass:
        model_dc = ModelDataClass(
            circuit=self.objects.circuit.to_dataclass(self._circuit_folder),
            gui=self.objects.components.get_gui_dict(),
            shortcuts=self.shortcuts.to_dict(),
            wires=self.objects.wires.to_dict(),
        )
        return model_dc

    def save_circuit(self, path: str | Path) -> None:
        """Save the circuit with GUI information"""
        old_circuit_folder = self._circuit_folder
        # Paths in the circuit are stored relative to the circuit file
        self._circuit_folder = str(Path(path).parent)
        model_dataclass = self.circuit_to_model()
        # The lines have the connections
        model_dataclass.circuit.wires = []
        appfile_dataclass = AppFileDataClass(
            circuit=model_dataclass.circuit,
            gui=model_dataclass.gui,
            lines=self.objects.wires.to_lines(),
            shortcuts=model_dataclass.shortcuts,
            settings=self.settings.get_all(),
        )
        try:
            appfile_dataclass.save(path)
        except OSError as exc:
            self._circuit_folder = old_circuit_folder
            self.sig_error.emit(f"Could not save circuit: {exc!s}")
            return
        self._changed = False
        self.sig_control_notify.emit()

    def load_circuit(self, path: str | Path) -> None:
        """Load a circuit with GUI information"""
        try:
            app_file_dc = AppFileDataClass.load(path)
        except (ValueError, OSError) as exc:
            # Malformed (pydantic's ValidationError is a ValueError), missing or unreadable file
            self.sig_error.emit(f"Could not load circuit: {exc!s}")
            return
        self._model_clear()
        # Path("file.circuit").parent is "."
        self._circuit_folder = str(Path(path).parent)
        exception_str_list = self.model_to_circuit(app_file_dc)
        self.shortcuts.from_dict(app_file_dc.shortcuts)
        self.settings.from_dict(app_file_dc.settings)
        self.model_init()
        self._changed = False
        self.objects.reset_undo_stack()
        self.sig_synchronize_gui.emit()
        self.sig_control_notify.emit()
        if len(exception_str_list) > 0:
            self.sig_warning_log.emit("Load Circuit Warning", "\n".join(exception_str_list))

    def clear_circuit(self) -> None:
        """Clear the circuit"""
        self.objects.push_undo_state()
        self._model_clear()
        self.sig_synchronize_gui.emit()
        self.sig_control_notify.emit()

    def zoom_in(self) -> None:
        """Send zoom in signal to GUI"""
        self.sig_zoom_in_gui.emit()

    def zoom_out(self) -> None:
        """Send zoom out signal to GUI"""
        self.sig_zoom_out_gui.emit()
