# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" An application model for a GUI simulated circuit """

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods

import json
import os
import queue
import time
from functools import partial

from PySide6.QtCore import QThread, Signal

import digsim.circuit.components
from digsim.circuit import Circuit
from digsim.circuit.components.atoms import CallbackComponent, Component, PortConnectionError

from ._placed_component import PlacedComponent
from ._placed_component_factory import get_placed_component_by_name  # noqa: F401
from ._placed_wire import PlacedWire


class AppModel(QThread):
    """The application model class for a GUI simulated circuit"""

    sig_component_notify = Signal(Component)
    sig_control_notify = Signal(bool)
    sig_sim_time_notify = Signal(float)
    sig_update_gui_components = Signal()

    def __init__(self):
        super().__init__()
        self._placed_components = {}
        self._placed_wires = {}
        self._circuit = Circuit(name="DigSimCircuit", vcd="gui.vcd")
        self._started = False
        self._sim_tick_ms = 50
        self._gui_event_queue = queue.Queue()
        self._component_callback_list = []
        self._new_wire = None
        self._new_wire_end_pos = None

    def clear(self):
        """Clear components and wires"""
        self._placed_components = {}
        self._placed_wires = {}

    @property
    def callback_list(self):
        """
        Get callback list,
        the components that have change during the last simulation execution
        """
        return self._component_callback_list

    @staticmethod
    def comp_cb(model, comp):
        """Add component to callback list (if not available)"""
        if comp not in model.callback_list:
            model.callback_list.append(comp)

    def _circuit_init(self):
        self._circuit.init()
        for _, comp in self._placed_components.items():
            self.sig_component_notify.emit(comp.component)
        self.sig_sim_time_notify.emit(0)

    def get_placed_component(self, component):
        """Get placed component (from component)"""
        return self._placed_components[component]

    def add_component_by_name(self, name, pos):
        """Add placed component from class name"""
        component_class = getattr(digsim.circuit.components, name)
        component = component_class(self._circuit, name=name)
        self._circuit_init()
        return self.add_component(component, pos.x(), pos.y())

    def add_component(self, component, xpos, ypos):
        """Add placed component in position"""
        placed_component_class = get_placed_component_by_name(type(component).__name__)
        self._placed_components[component] = placed_component_class(component, xpos, ypos)
        if isinstance(component, CallbackComponent):
            component.set_callback(partial(AppModel.comp_cb, self))
        return self._placed_components[component]

    def add_wire(self, src_port, dst_port, connect=True):
        """Add placed wire between source and destination port"""
        wire = PlacedWire(self, src_port, dst_port, connect)
        self._placed_wires[wire.key] = wire
        self.sig_component_notify.emit(dst_port.parent())

    def get_placed_components(self):
        """Get list of placed components"""
        placed_components = []
        for _, comp in self._placed_components.items():
            placed_components.append(comp)
        return placed_components

    def get_placed_wires(self):
        """Get list of placed wires"""
        placed_wires = []
        for _, wire in self._placed_wires.items():
            placed_wires.append(wire)
        return placed_wires

    def get_placed_objects(self):
        """Get list of all placed objects"""
        placed_objects = self.get_placed_components()
        placed_objects.extend(self.get_placed_wires())
        return placed_objects

    def select(self, placed_object=None):
        """Select placed object"""
        for comp in self.get_placed_objects():
            if comp == placed_object:
                comp.select(True)
            else:
                comp.select(False)

    def select_pos(self, pos):
        """Select object from position"""
        self.select(None)
        for wire in self.get_placed_wires():
            if wire.is_close(pos):
                wire.select(True)
            else:
                wire.select(False)

    def get_selected_objects(self):
        """Get selected objects"""
        objects = []
        placed_objects = self.get_placed_objects()
        for obj in placed_objects:
            if obj.selected:
                objects.append(obj)
        return objects

    def _delete_wire(self, placed_wire):
        placed_wire.disconnect()
        del self._placed_wires[placed_wire.key]

    def _delete_component(self, placed_component):
        for port in placed_component.component.ports:
            for wire in self.get_placed_wires():
                if wire.has_port(port):
                    self._delete_wire(wire)
        del self._placed_components[placed_component.component]
        self._circuit.delete_component(placed_component.component)

    def delete(self):
        """Delete selected object(s)"""
        selected_objects = self.get_selected_objects()
        for obj in selected_objects:
            if isinstance(obj, PlacedWire):
                self._delete_wire(obj)
            elif isinstance(obj, PlacedComponent):
                self._delete_component(obj)
        self.sig_update_gui_components.emit()

    def update_wires(self):
        """Update placed wires"""
        for _, wire in self._placed_wires.items():
            wire.update()

    def paint_wires(self, painter):
        """Paint placed wires"""
        wires = self.get_placed_wires()
        for wire in wires:
            wire.paint(painter)

        if self._new_wire is not None and self._new_wire_end_pos is not None:
            self._new_wire.paint_new(painter, self._new_wire_end_pos)

    def new_wire_start(self, component, portname):
        """Start new placed wire"""
        if component.port(portname).can_add_wire():
            self._new_wire = PlacedWire(self, component.port(portname))

    def new_wire_end(self, component, portname):
        """End new placed wire"""
        try:
            self._new_wire.set_end_port(component.port(portname))
            self._placed_wires[self._new_wire.key] = self._new_wire
        except PortConnectionError as exc:
            print("ERROR:", str(exc))
        self._new_wire = None
        self._new_wire_end_pos = None

    def new_wire_abort(self):
        """Abort new placed wire"""
        self._new_wire = None
        self._new_wire_end_pos = None

    def set_new_wire_end_pos(self, pos):
        """Update end point for unfinished new placed wire"""
        self._new_wire_end_pos = pos

    def has_new_wire(self):
        """Return True if an unfinished new placed wire is active"""
        return self._new_wire is not None

    @property
    def circuit(self):
        """Return the circuit"""
        return self._circuit

    def model_start(self):
        """Start model simulation thread"""
        self._started = True
        self.start()
        self.sig_control_notify.emit(self._started)

    def model_stop(self):
        """Stop model simulation thread"""
        self._started = False

    def model_reset(self):
        """Resetp model simulation"""
        if not self._started:
            self._circuit_init()

    def add_gui_event(self, func):
        """Add medel events (functions) from the GUI"""
        self._gui_event_queue.put(func)

    def run(self):
        """Simulation thread run function"""
        start_time = time.perf_counter()
        next_tick = start_time
        while self._started:
            next_tick += self._sim_tick_ms / 1000

            self._component_callback_list = []

            # Execute one GUI event at a time
            if not self._gui_event_queue.empty():
                gui_event_func = self._gui_event_queue.get()
                gui_event_func()

            self._circuit.run(ms=self._sim_tick_ms)

            for comp in self._component_callback_list:
                self.sig_component_notify.emit(comp)

            now = time.perf_counter()
            sleep_time = next_tick - now
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.sig_sim_time_notify.emit(self._circuit.time_ns / 1000000000)

        self.sig_control_notify.emit(self._started)

    @property
    def is_running(self):
        """Return True if the simulation thread is running"""
        return self._started

    def save_circuit(self, path):
        """Save the circuit with GUI information"""
        circuit_folder = os.path.dirname(path)
        circuit_dict = self._circuit.to_dict(circuit_folder)
        circuit_dict["gui"] = {}
        for comp, placed_comp in self._placed_components.items():
            circuit_dict["gui"][comp.name()] = placed_comp.to_dict()
        json_object = json.dumps(circuit_dict, indent=4)
        with open(path, mode="w", encoding="utf-8") as json_file:
            json_file.write(json_object)

    def load_circuit(self, path):
        """Load a circuit with GUI information"""
        self.clear()
        with open(path, mode="r", encoding="utf-8") as json_file:
            circuit_dict = json.load(json_file)

        circuit_folder = os.path.dirname(path)
        self._circuit.from_dict(circuit_dict, circuit_folder)
        for comp in self._circuit.get_toplevel_components():
            x = circuit_dict["gui"][comp.name()]["x"]
            y = circuit_dict["gui"][comp.name()]["y"]
            self.add_component(comp, x, y)

        for comp in self._circuit.get_toplevel_components():
            for src_port in comp.outports():
                for dst_port in src_port.get_wires():
                    self.add_wire(src_port, dst_port, connect=False)
            self._circuit_init()
        self.sig_update_gui_components.emit()
