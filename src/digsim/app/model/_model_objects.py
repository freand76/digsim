# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Handle objects in the model"""

from __future__ import annotations

import re
from collections import deque
from typing import TYPE_CHECKING, Any

from digsim.app._auto_layout import auto_layout
from digsim.app._clipboard_lines import renamed_port, renamed_port_keys
from digsim.app._line_graph import without_ports
from digsim.app._netlist_layout import NodeShape
from digsim.app._settings_values import given_name, has_given_name, unique_name
from digsim.app._wire_route import rotated
from digsim.circuit import Circuit
from digsim.circuit.components import CircuitPort, YosysComponent
from digsim.circuit.components._yosys_component import YosysVariant
from digsim.circuit.components.atoms import Component, DigsimException, Port, PortInOut
from digsim.storage_model import LineDataClass, ModelDataClass
from digsim.utils import YosysNetlist

from ._model_clipboard import ModelClipboard
from ._model_components import ModelComponents
from ._model_new_wire import NewWire
from ._model_wires import ModelWires


if TYPE_CHECKING:
    from digsim.app.gui_objects import ComponentObject

    from ._model import AppModel


# The number of undo (and redo) steps that are kept, the oldest step is dropped when there
# are more. Each step is a copy of the circuit's top-level components, wires, positions and
# wire paths (a Yosys component only stores its file path), so 100 steps use little memory.
UNDO_STACK_DEPTH = 100


class ModelObjects:
    """Class to handle objects in the model"""

    def __init__(self, app_model: AppModel) -> None:
        self._app_model = app_model
        self._circuit = Circuit(name="DigSimCircuit")
        self._model_components = ModelComponents(app_model, self._circuit)
        self._undo_stack: deque[ModelDataClass] = deque(maxlen=UNDO_STACK_DEPTH)
        self._redo_stack: deque[ModelDataClass] = deque(maxlen=UNDO_STACK_DEPTH)
        self._new_wire = NewWire(self._app_model)
        self._wires = ModelWires(self._app_model)
        self._clipboard = ModelClipboard(self._app_model)

    @property
    def circuit(self) -> Circuit:
        """return the model circuit"""
        return self._circuit

    @property
    def components(self) -> ModelComponents:
        """return the model components"""
        return self._model_components

    @property
    def new_wire(self) -> NewWire:
        """return the wire that is being drawn"""
        return self._new_wire

    @property
    def wires(self) -> ModelWires:
        """return the shape of the wires"""
        return self._wires

    @property
    def clipboard(self) -> ModelClipboard:
        """return the copy and paste of components"""
        return self._clipboard

    def init(self) -> None:
        """Initialize objects"""
        self._model_components.init()

    def clear(self) -> None:
        """Clear components and wires"""
        self._model_components.clear()
        self._wires.clear()
        self._circuit.clear()

    def get_list(self) -> list[ComponentObject]:
        """Get list of all model objects"""
        return self._model_components.get_object_list()

    def get_selected(self) -> list[ComponentObject]:
        """Get selected objects"""
        return [obj for obj in self.get_list() if obj.selected]

    def _delete(self, selected_objects: list[ComponentObject]) -> None:
        for obj in selected_objects:
            self._model_components.delete(obj)

    def delete_selected(self) -> None:
        """Delete selected object(s)"""
        # The circuit can't change while the simulation thread runs it (the Del shortcut)
        if self._app_model.is_running:
            return
        undo_state = self._app_model.circuit_to_model()
        selected_objects = self._app_model.objects.get_selected()
        if len(selected_objects) > 0:
            self._delete(selected_objects)
            self._app_model.model_changed()
        # The circuit area deletes the selected wires
        self._app_model.sig_delete_wires.emit()
        # An undo step only if something was deleted
        if self._app_model.circuit_to_model() != undo_state:
            self.add_undo_state(undo_state)

    def auto_layout(self) -> None:
        """
        Edit > Auto Layout: place the components in columns from the inputs on the left to
        the outputs on the right, not rotated, and draw the wires again between them. One
        undo step, then zoomed to fit.
        """
        if self._app_model.is_running or self._model_components.is_empty():
            return
        undo_state = self._app_model.circuit_to_model()
        model_dc = self._app_model.circuit_to_model()
        shapes: dict[str, NodeShape] = {}
        directions: dict[str, dict[str, str]] = {}
        for component, component_object in self._model_components.get_dict().items():
            # Not rotated: the ports where they are in the rect of the component
            rect = component_object.rect()
            pins: dict[str, tuple[float, float]] = {}
            for port in component.ports:
                pos = component_object.mapFromScene(component_object.get_port_item(port).portPos())
                pins[port.name()] = (pos.x() - rect.x(), pos.y() - rect.y())
                # Not rotated: a port on the top or the bottom, like those of the LCD
                turn = (360 - component_object.rotation_angle) % 360
                direction = rotated(component_object.port_direction(port), turn)
                if direction in ("up", "down"):
                    directions.setdefault(component.name(), {})[port.name()] = direction
            shapes[component.name()] = NodeShape(rect.width(), rect.height(), pins)
        lines: list[tuple[list[str], set[str]]] = []
        # The lines of the drawn wires (a state has their paths, not lines)
        for line in self._wires.to_lines():
            outputs = set()
            for key in line.ports:
                line_port = self._port(key)
                # An inout port (like the data bus of the LCD) is not where a line comes
                # from, when it has an output
                inout = isinstance(line_port, PortInOut)
                if line_port is not None and line_port.is_output() and not inout:
                    outputs.add(key)
            lines.append((list(line.ports), outputs))
        origin = (
            min(position.x for position in model_dc.gui.values()),
            min(position.y for position in model_dc.gui.values()),
        )
        result = auto_layout(shapes, lines, origin, directions)
        for name, (x, y) in result.positions.items():
            position = model_dc.gui[name]
            position.x, position.y = x, y
            position.rotation, position.flipped = 0, False
        model_dc.circuit.wires = []
        model_dc.wires = {}
        model_dc.lines = result.lines
        self.add_undo_state(undo_state)
        self._restore_and_warn(model_dc)
        self._app_model.sig_control_notify.emit()
        self._app_model.sig_synchronize_gui.emit()
        # The whole circuit, in its new places
        self._app_model.zoom_fit()

    def _restore_state(self, model_dc: ModelDataClass) -> list[str]:
        """Build the circuit from a state, returns the warnings"""
        self.clear()
        exception_str_list = self._app_model.model_to_circuit(model_dc)
        self._app_model.shortcuts.from_dict(model_dc.shortcuts)
        self._app_model.model_init()
        self._app_model.model_changed()
        return exception_str_list

    def _restore_and_warn(self, model_dc: ModelDataClass) -> None:
        exception_str_list = self._restore_state(model_dc)
        if len(exception_str_list) > 0:
            self._app_model.sig_warning_log.emit(
                "Load Circuit Warning", "\n".join(exception_str_list)
            )

    def rebuild(self, lines: list[LineDataClass]) -> list[str]:
        """
        Build the circuit again, as when it is loaded: each component from its settings
        (a Yosys component from its file, or a netlist given with
        YosysComponent.given_netlists()), and the wires from lines. Used when the ports
        of a component change, the lines must not have the ports that are gone. The undo
        steps are dropped: they have wires to the ports from before. Returns the warnings.
        """
        before = {component.name() for component in self._circuit.get_toplevel_components()}
        model_dc = self._app_model.circuit_to_model()
        model_dc.circuit.wires = []
        model_dc.wires = {}
        model_dc.lines = lines
        exception_str_list = self._restore_state(model_dc)
        after = {component.name() for component in self._circuit.get_toplevel_components()}
        missing = sorted(before - after)
        if missing:
            # Like a Yosys component whose file has an error now: keep the undo steps,
            # they have the components
            exception_str_list.insert(
                0, f"Not built again: {', '.join(missing)}, undo brings them back"
            )
        else:
            self.reset_undo_stack()
        self._app_model.sig_synchronize_gui.emit()
        return exception_str_list

    def change_component(
        self,
        name: str,
        settings: dict[str, Any],
        class_name: str | None = None,
        new_name: str | None = None,
    ) -> tuple[str, list[str]]:
        """
        Build the circuit again with other settings for a component, another class (a
        flip-flop of another kind) or another name, an undo step. It keeps its place, and
        the wires to the ports that it still has. Returns its name, and the ports whose
        wires are gone. Raises DigsimException, and nothing changes, if it can't be built
        with them.

        A component with the name it got (like an IC named after its module) gets the
        name of what it is now, a name the user gave it is kept.
        """
        undo_state = self._app_model.circuit_to_model()
        model_dc = self._app_model.circuit_to_model()
        lines = self._app_model.objects.wires.to_lines()
        component_dc = next(dc for dc in model_dc.circuit.components if dc.name == name)
        old_component = self._toplevel(name)
        assert old_component is not None
        follows = new_name is None and has_given_name(old_component)
        component_dc.settings = {**component_dc.settings, **settings}
        if class_name is not None:
            module, _, _ = component_dc.type.rpartition(".")
            component_dc.type = f"{module}.{class_name}"
        if class_name is not None or follows:
            # The display name of the new class, or the new module
            component_dc.display_name = ""
        if isinstance(old_component, CircuitPort):
            # Its port is named after its label, the wires go to the port with the new one
            label = str(settings.get("label", old_component.label()))
            if label != old_component.label():
                lines = renamed_port_keys(
                    lines, {f"{name}.{old_component.label()}": f"{name}.{label}"}
                )
        if new_name is not None and new_name != name:
            # The name is shown where the component shows its name, not a kind like SR
            shown = old_component.display_name() in (name, given_name(old_component))
            lines = self._renamed(model_dc, lines, name, new_name, shown)
            name = new_name
        model_dc.circuit.wires = []
        model_dc.wires = {}
        model_dc.lines = lines
        # The other Yosys components are built from the netlists they have now, not from
        # their files: those may have changed since, or have errors now
        netlists = self._yosys_netlists()

        def restore(state: ModelDataClass) -> list[str]:
            with YosysComponent.given_netlists(netlists):
                return self._restore_state(state)

        self._check_build(model_dc, name, netlists)
        warnings = restore(model_dc)
        component = self._toplevel(name)
        if component is None:
            restore(undo_state)
            self._app_model.sig_synchronize_gui.emit()
            raise DigsimException(self._reasons(warnings, name) or f"{name} could not be built")
        if follows and given_name(component) != given_name(old_component):
            taken = {c.name() for c in self._circuit.get_toplevel_components()} - {name}
            lines = self._renamed(
                model_dc, lines, name, unique_name(given_name(component), taken), shown=False
            )
            name = component_dc.name
            restore(model_dc)
        # The ports that are gone, or that have another width than their line now
        gone: set[str] = set()
        for line in lines:
            ports = {key: self._port(key) for key in line.ports}
            width = LineDataClass.width([port for port in ports.values() if port is not None])
            gone |= {key for key, port in ports.items() if port is None or port.width != width}
        if gone:
            model_dc.lines = without_ports(lines, gone)
            restore(model_dc)
        self.add_undo_state(undo_state)
        self._app_model.sig_synchronize_gui.emit()
        return name, sorted(gone)

    def _yosys_netlists(self) -> list[tuple[str, YosysVariant, YosysNetlist]]:
        """The netlists of the Yosys components, to build them again without their files"""
        return [
            (component.source_file, component.variant, component.netlist())
            for component in self._circuit.get_toplevel_components()
            if isinstance(component, YosysComponent) and component.source_file is not None
        ]

    def _check_build(
        self,
        model_dc: ModelDataClass,
        name: str,
        netlists: list[tuple[str, YosysVariant, YosysNetlist]],
    ) -> None:
        """
        Raises DigsimException if a component of a state can't be built, before the
        circuit changes: the component 'name', or another one, like a subcircuit whose
        file has an error now, which would be gone from the circuit
        """
        scratch = Circuit()
        with YosysComponent.given_netlists(netlists):
            warnings = scratch.from_dataclass(
                model_dc.circuit, self._app_model.circuit_folder, component_exceptions=False
            )
        built = {component.name() for component in scratch.get_toplevel_components()}
        missing = [dc.name for dc in model_dc.circuit.components if dc.name not in built]
        scratch.clear()
        if name in missing:
            raise DigsimException(self._reasons(warnings, name) or f"{name} could not be built")
        if missing:
            raise DigsimException(
                f"{', '.join(missing)} can't be built again from "
                f"{'its file' if len(missing) == 1 else 'their files'} now, so nothing is "
                "changed:\n" + self._reasons(warnings, "")
            )

    @staticmethod
    def _reasons(warnings: list[str], name: str) -> str:
        """The warnings about a component (all if none is), without the class of the error"""
        reasons = [warning for warning in warnings if name in warning] or warnings
        # The reason, not the class of the exception that the warning starts with
        return "\n".join(re.sub(r"^\w+(Exception|Error):", "", reason) for reason in reasons)

    @staticmethod
    def _renamed(
        model_dc: ModelDataClass,
        lines: list[LineDataClass],
        name: str,
        new_name: str,
        shown: bool = True,
    ) -> list[LineDataClass]:
        """
        Give a component of a state another name, in the GUI positions and the shortcuts
        too, and returns the lines with its ports renamed. The name is 'shown' on the
        component, else it keeps what it shows.
        """
        names = {name: new_name}
        for component_dc in model_dc.circuit.components:
            if component_dc.name == name:
                component_dc.name = new_name
                if shown:
                    component_dc.display_name = new_name
        model_dc.gui = {names.get(key, key): value for key, value in model_dc.gui.items()}
        model_dc.shortcuts = {
            key: names.get(value, value) for key, value in model_dc.shortcuts.items()
        }
        renamed = [
            LineDataClass(
                ports=[renamed_port(port, names) for port in line.ports],
                points=line.points,
                segments=[
                    [renamed_port(end, names) if end in line.ports else end for end in segment]
                    for segment in line.segments
                ],
            )
            for line in lines
        ]
        model_dc.lines = renamed
        return renamed

    def _toplevel(self, name: str) -> Component | None:
        """A top-level component of the circuit by its name"""
        return next((c for c in self._circuit.get_toplevel_components() if c.name() == name), None)

    def _port(self, key: str) -> Port | None:
        """A port of a top-level component by its key, like "and1.A", None if it isn't there"""
        component_name, _, port_name = key.rpartition(".")
        component = self._toplevel(component_name)
        if component is None:
            return None
        return next((port for port in component.ports if port.name() == port_name), None)

    def reset_undo_stack(self) -> None:
        """Clear undo/redo stacks"""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._app_model.sig_control_notify.emit()

    def push_undo_state(self, clear_redo_stack: bool = True) -> None:
        """Push undo state to stack"""
        self.add_undo_state(self._app_model.circuit_to_model(), clear_redo_stack)

    def add_undo_state(self, undo_state: ModelDataClass, clear_redo_stack: bool = True) -> None:
        """Push a state from before a change, taken before the change was known to work"""
        self._undo_stack.append(undo_state)
        if clear_redo_stack:
            self._redo_stack.clear()
            self._app_model.sig_control_notify.emit()

    def drop_undo_state(self) -> None:
        """Drop last undo state"""
        if len(self._undo_stack) > 0:
            self._undo_stack.pop()
            self._app_model.sig_control_notify.emit()

    def push_redo_state(self) -> None:
        """Push redo state to stack"""
        self._redo_stack.append(self._app_model.circuit_to_model())

    def undo(self) -> None:
        """Undo to last saved state"""
        # The circuit can't be rebuilt while the simulation thread runs it (Ctrl+Z)
        if self._app_model.is_running:
            return
        if len(self._undo_stack) > 0:
            self.push_redo_state()
            model_dc = self._undo_stack.pop()
            self._restore_and_warn(model_dc)
            self._app_model.sig_control_notify.emit()
            self._app_model.sig_synchronize_gui.emit()

    def redo(self) -> None:
        """Redo the last undone change"""
        # The circuit can't be rebuilt while the simulation thread runs it (Ctrl+Y)
        if self._app_model.is_running:
            return
        if len(self._redo_stack) > 0:
            self.push_undo_state(clear_redo_stack=False)
            model_dc = self._redo_stack.pop()
            self._restore_and_warn(model_dc)
            self._app_model.sig_control_notify.emit()
            self._app_model.sig_synchronize_gui.emit()

    def can_undo(self) -> bool:
        """Return true if the undo stack is not empty"""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Return true if the undo stack is not empty"""
        return len(self._redo_stack) > 0
