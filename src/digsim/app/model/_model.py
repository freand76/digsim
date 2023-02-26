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

import digsim.app.gui_objects
import digsim.circuit.components
from digsim.circuit import Circuit
from digsim.circuit.components.atoms import CallbackComponent, Component


class AppModel(QThread):
    """The application model class for a GUI simulated circuit"""

    sig_component_notify = Signal(Component)
    sig_control_notify = Signal(bool)
    sig_sim_time_notify = Signal(float)
    sig_update_gui_components = Signal()
    sig_error = Signal(str)

    def __init__(self):
        super().__init__()
        self._component_objects = {}
        self._wire_objects = {}
        self._circuit = Circuit(name="DigSimCircuit", vcd="gui.vcd")
        self._started = False
        self._changed = False
        self._sim_tick_ms = 50
        self._gui_event_queue = queue.Queue()
        self._component_callback_list = []
        self._new_wire = None
        self._new_wire_end_pos = None
        self._multi_select = False

    def clear(self):
        """Clear components and wires"""
        self._component_objects = {}
        self._wire_objects = {}

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
        for _, comp in self._component_objects.items():
            self.sig_component_notify.emit(comp.component)
        self.sig_sim_time_notify.emit(0)

    def get_component_object(self, component):
        """Get component object (from component)"""
        return self._component_objects[component]

    def get_component_parameters(self, name):
        """Get parameters for a component"""
        component_class = getattr(digsim.circuit.components, name)
        return component_class.get_parameters()

    def add_component_by_name(self, name, pos, settings):
        """Add component object from class name"""
        component_class = getattr(digsim.circuit.components, name)
        component = component_class(self._circuit, name=name, **settings)
        self._circuit_init()
        component_object = self._add_component(component, pos.x(), pos.y())
        component_object.center()  # Component is plced @ mouse pointer, make it center
        self._changed = True
        self.sig_control_notify.emit(self._started)
        return component_object

    def _add_component(self, component, xpos, ypos):
        """Add component object in position"""
        component_object_class = digsim.app.gui_objects.class_factory(type(component).__name__)
        self._component_objects[component] = component_object_class(component, xpos, ypos)
        if isinstance(component, CallbackComponent):
            component.set_callback(partial(AppModel.comp_cb, self))
        return self._component_objects[component]

    def add_wire(self, src_port, dst_port, connect=True):
        """Add wire object between source and destination port"""
        wire = digsim.app.gui_objects.WireObject(self, src_port, dst_port, connect)
        self._wire_objects[wire.key] = wire
        self.sig_component_notify.emit(dst_port.parent())

    def get_component_objects(self):
        """Get list of component objects"""
        component_objects = []
        for _, comp in self._component_objects.items():
            component_objects.append(comp)
        return component_objects

    def get_wire_objects(self):
        """Get list of wire objects"""
        wire_objects = []
        for _, wire in self._wire_objects.items():
            wire_objects.append(wire)
        return wire_objects

    def get_placed_objects(self):
        """Get list of all placed objects"""
        placed_objects = self.get_component_objects()
        placed_objects.extend(self.get_wire_objects())
        return placed_objects

    def multi_select(self, multi_select):
        """Enable/Disable multiple select of objects"""
        self._multi_select = multi_select

    def select(self, placed_object=None):
        """Select placed object"""
        if placed_object is not None and placed_object.selected:
            return
        for comp in self.get_placed_objects():
            if comp == placed_object:
                comp.select(True)
            elif not self._multi_select:
                comp.select(False)

    def select_by_position(self, pos):
        """Select object from position"""
        something_selected = False
        self.select(None)
        for wire in self.get_wire_objects():
            if wire.is_close(pos):
                wire.select(True)
                something_selected = True
            elif not self._multi_select:
                wire.select(False)
        return something_selected

    def get_selected_objects(self):
        """Get selected objects"""
        objects = []
        placed_objects = self.get_placed_objects()
        for obj in placed_objects:
            if obj.selected:
                objects.append(obj)
        return objects

    def select_by_rect(self, rect):
        """Select object be rectangle"""
        self.select(None)
        placed_objects = self.get_placed_objects()
        for obj in placed_objects:
            if obj.in_rect(rect):
                obj.select(True)

    def _delete_wire(self, wire_object):
        wire_object.disconnect()
        if wire_object.key in self._wire_objects:
            del self._wire_objects[wire_object.key]

    def _delete_component(self, component_object):
        for port in component_object.component.ports:
            for wire in self.get_wire_objects():
                if wire.has_port(port):
                    self._delete_wire(wire)
        del self._component_objects[component_object.component]
        self._circuit.delete_component(component_object.component)
        self._changed = True
        self.sig_control_notify.emit(self._started)

    def delete(self):
        """Delete selected object(s)"""
        selected_objects = self.get_selected_objects()
        for obj in selected_objects:
            if isinstance(obj, digsim.app.gui_objects.ComponentObject):
                self._delete_component(obj)
        for obj in selected_objects:
            if isinstance(obj, digsim.app.gui_objects.WireObject):
                self._delete_wire(obj)
        self.sig_update_gui_components.emit()

    def update_wires(self):
        """Update wire objects"""
        for _, wire in self._wire_objects.items():
            wire.update()
        self.sig_control_notify.emit(self._started)

    def move_selected_components(self, delta_pos):
        """Move selected objects"""
        selected_objects = self.get_selected_objects()
        for obj in selected_objects:
            if isinstance(obj, digsim.app.gui_objects.ComponentObject):
                obj.pos = obj.pos + delta_pos
                self.sig_component_notify.emit(obj.component)
                self.update_wires()
                self._changed = True

    def paint_wires(self, painter):
        """Paint wire objects"""
        wires = self.get_wire_objects()
        for wire in wires:
            wire.paint(painter)

        if self._new_wire is not None and self._new_wire_end_pos is not None:
            self._new_wire.paint_new(painter, self._new_wire_end_pos)

    def new_wire_start(self, component, portname):
        """Start new wire object"""
        if component.port(portname).can_add_wire():
            self._new_wire = digsim.app.gui_objects.WireObject(self, component.port(portname))

    def new_wire_end(self, component, portname):
        """End new wire object"""
        self._new_wire.set_end_port(component.port(portname))
        self._wire_objects[self._new_wire.key] = self._new_wire
        self._new_wire = None
        self._new_wire_end_pos = None

    def new_wire_abort(self):
        """Abort new wire object"""
        self._new_wire = None
        self._new_wire_end_pos = None

    def set_new_wire_end_pos(self, pos):
        """Update end point for unfinished new wire object"""
        self._new_wire_end_pos = pos

    def has_new_wire(self):
        """Return True if an unfinished new wire object is active"""
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
        for comp, comp_object in self._component_objects.items():
            circuit_dict["gui"][comp.name()] = comp_object.to_dict()
        json_object = json.dumps(circuit_dict, indent=4)
        with open(path, mode="w", encoding="utf-8") as json_file:
            json_file.write(json_object)
        self._changed = False
        self.sig_control_notify.emit(self._started)

    def load_circuit(self, path):
        """Load a circuit with GUI information"""
        self.clear()
        with open(path, mode="r", encoding="utf-8") as json_file:
            circuit_dict = json.load(json_file)

        circuit_folder = os.path.dirname(path)
        if len(circuit_folder) == 0:
            circuit_folder = "."
        self._circuit.from_dict(circuit_dict, circuit_folder)
        for comp in self._circuit.get_toplevel_components():
            x = circuit_dict["gui"][comp.name()]["x"]
            y = circuit_dict["gui"][comp.name()]["y"]
            self._add_component(comp, x, y)

        for comp in self._circuit.get_toplevel_components():
            for src_port in comp.outports():
                for dst_port in src_port.get_wires():
                    self.add_wire(src_port, dst_port, connect=False)
        self._circuit_init()
        self._changed = False
        self.sig_update_gui_components.emit()
        self.sig_control_notify.emit(self._started)

    def clear_circuit(self):
        """Clear the circuit"""
        self.clear()
        self._changed = False
        self.sig_update_gui_components.emit()
        self.sig_control_notify.emit(self._started)

    def has_objects(self):
        """Return True if there are objects in the model"""
        return len(self._component_objects) > 0

    def set_changed(self):
        """Set changed to True, for example when gui has moved component"""
        self._changed = True
        self.sig_control_notify.emit(self._started)
        self.sig_update_gui_components.emit()

    def has_changes(self):
        """Return True if there are changes in the model since last save"""
        return self._changed
