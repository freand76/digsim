# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Handle component objects in the model"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPointF

import digsim.app.gui_objects
import digsim.circuit.components
from digsim.app._line_graph import without_ports
from digsim.app._settings_values import (
    CLASS_PARAMETER,
    NAME_PARAMETER,
    is_flip_flop,
    name_problem,
)
from digsim.app._wire_key import Wire
from digsim.app._wire_lines import At
from digsim.app._yosys_interface import (
    InterfaceChanges,
    YosysUpdate,
    components_of_file,
    interface_changes,
    removed_wires,
    same_file,
    variant_with,
)
from digsim.app.gui_objects import ComponentObject
from digsim.circuit import Circuit
from digsim.circuit.components import (
    Buzzer,
    Probe,
    SubCircuit,
    YosysComponent,
    YosysVariant,
)
from digsim.circuit.components._subcircuit import files_used
from digsim.circuit.components.atoms import (
    CallbackComponent,
    Component,
    DigsimException,
    Parameter,
)
from digsim.storage_model import GuiPositionDataClass, ModelDataClass
from digsim.utils import YosysNetlist


if TYPE_CHECKING:
    from ._model import AppModel

# Where the input of a probe added on a wire is, from the point on the wire
PROBE_OFFSET = (20, -20)


@dataclass
class SubCircuitUpdate:
    """The subcircuits of a file to build again, how their ports change, the wires that go"""

    path: str
    changes: dict[SubCircuit, InterfaceChanges]
    removed: list[str]
    # The same ports, in another order in the file (from top to bottom)
    reordered: bool = False

    def ports_change(self) -> bool:
        return any(self.changes.values())

    def port_changes(self) -> InterfaceChanges:
        """The changes of the ports (the same for every subcircuit of the file)"""
        return next(iter(self.changes.values()))

    def names(self) -> str:
        return ", ".join(subcircuit.name() for subcircuit in self.changes)


class ModelComponents:
    """Class to handle the component objects in the model"""

    def __init__(self, app_model: AppModel, circuit: Circuit) -> None:
        self._app_model = app_model
        self._circuit = circuit
        self._component_objects: dict[Component, ComponentObject] = {}
        self._component_callback_list: list[Component] = []
        self._move_undo_state: ModelDataClass | None = None

    def clear(self) -> None:
        """Clear components objects"""
        for component_object in self.get_object_list():
            component_object.disconnect()
        self._component_objects = {}

    def init(self) -> None:
        """Initialize components objects"""
        self._app_model.sig_repaint.emit()

    def get_dict(self) -> dict[Component, ComponentObject]:
        """Get component objects dict"""
        return self._component_objects

    def is_empty(self) -> bool:
        """Return True if there are component objects in the model"""
        return len(self._component_objects) == 0

    def get_top_zlevel(self) -> float:
        """Get the highest z level in the model"""
        return max((obj.zlevel for obj in self._component_objects.values()), default=0)

    def set_move_undo_state(self, undo_state: ModelDataClass | None) -> None:
        """
        The state from before a move (taken at the mouse press), for the undo step of the
        move: the components and the wires that move with them change while they move
        """
        self._move_undo_state = undo_state

    def component_moved(self) -> None:
        """Call when component has moved to update state"""
        if self._move_undo_state is not None:
            self._app_model.objects.add_undo_state(self._move_undo_state)
            self._move_undo_state = None
        else:
            self._app_model.objects.push_undo_state()
        self._app_model.model_changed()

    def rotate(self, component_objects: list[ComponentObject]) -> None:
        """
        Rotate components a quarter clockwise, each around its middle (those that can be
        rotated). The wires to them get the automatic path.
        """
        rotatable = [obj for obj in component_objects if obj.ROTATABLE]
        if not rotatable:
            return
        self._app_model.objects.push_undo_state()
        for component_object in rotatable:
            component_object.rotation_angle = component_object.rotation_angle + 90
        self._app_model.objects.wires.reroute({obj.component for obj in rotatable})
        self._app_model.model_changed()
        self._app_model.sig_update_wires.emit()
        self._app_model.sig_repaint.emit()

    def flip(self, component_objects: list[ComponentObject], horizontal: bool) -> None:
        """
        Mirror components on the screen, each around its middle: left to right
        ('horizontal'), or top to bottom (those that can be rotated). The wires to them get
        the automatic path.
        """
        rotatable = [obj for obj in component_objects if obj.ROTATABLE]
        if not rotatable:
            return
        self._app_model.objects.push_undo_state()
        for component_object in rotatable:
            component_object.flip(horizontal)
        self._app_model.objects.wires.reroute({obj.component for obj in rotatable})
        self._app_model.model_changed()
        self._app_model.sig_update_wires.emit()
        self._app_model.sig_repaint.emit()

    def bring_to_front(self, component_object: ComponentObject) -> None:
        """Make the component object the highest in the stack"""
        self._app_model.objects.push_undo_state()
        max_zlevel = self.get_top_zlevel()
        component_object.zlevel = max_zlevel + 1
        self._app_model.model_changed()

    def send_to_back(self, component_object: ComponentObject) -> None:
        """Make the component object the lowest in the stack"""
        self._app_model.objects.push_undo_state()
        min_zlevel = min((obj.zlevel for obj in self._component_objects.values()), default=None)
        if min_zlevel is None or min_zlevel == 0:
            for comp_object in self._component_objects.values():
                comp_object.zlevel = comp_object.zlevel + 1
            component_object.zlevel = 0
        else:
            component_object.zlevel = min_zlevel - 1
        self._app_model.model_changed()

    def update_callback_objects(self) -> None:
        """
        Update the GUI for the components that have changed since the last call
        """
        if len(self._component_callback_list) == 0:
            return
        for comp in self._component_callback_list:
            if isinstance(comp, Buzzer):
                self._app_model.sig_audio_notify.emit(comp)
        self._app_model.sig_repaint.emit()
        self._component_callback_list = []

    def _component_callback(self, component: Component) -> None:
        """Add component to callback list (if not available)"""
        if component not in self._component_callback_list:
            self._component_callback_list.append(component)

    def _get_component_class(self, name: str) -> type[Component]:
        return getattr(digsim.circuit.components, name)

    def get_object_parameters(self, name: str) -> dict[str, Parameter]:
        """Get parameters for a component"""
        return self._get_component_class(name).get_circuit_parameters(self._circuit)

    def _add_object(self, component: Component, xpos: float, ypos: float) -> ComponentObject:
        """Add component object in position"""
        component_object_class = digsim.app.gui_objects.class_factory(type(component).__name__)
        self._component_objects[component] = component_object_class(
            self._app_model, component, xpos, ypos
        )
        if isinstance(component, CallbackComponent):
            component.set_callback(self._component_callback)
        return self._component_objects[component]

    def add_object_by_name(
        self, name: str, pos: QPointF, settings: dict[str, Any]
    ) -> ComponentObject | None:
        """Add component object from class name, None if the component can't be created"""
        if name == "SubCircuit":
            try:
                self.check_subcircuit_file(str(settings.get("path", "")))
            except DigsimException as exc:
                self._app_model.sig_error.emit(f"Could not add the subcircuit: {exc!s}")
                return None
        self._app_model.objects.push_undo_state()
        component_object = self.add_object(
            self._get_component_class(name), pos.x(), pos.y(), settings
        )
        if component_object is None:
            self._app_model.objects.drop_undo_state()
            return None
        self._app_model.model_init()
        self._app_model.model_changed()
        return component_object

    def add_object(
        self, component_class: type[Component], xpos: float, ypos: float, settings: dict[str, Any]
    ) -> ComponentObject | None:
        """
        Add a component and its object, as part of a change (not an undo step), None if
        the component can't be created
        """
        try:
            with self._circuit.adding_components():
                component = component_class(self._circuit, **settings)
        except (DigsimException, OSError) as exc:
            # For example a Verilog file with errors, or a file that can't be read
            self._app_model.sig_error.emit(f"Could not add {component_class.__name__}: {exc!s}")
            return None
        return self._add_object(component, xpos, ypos)

    def add_probe(self, wire: Wire, at: At) -> ComponentObject | None:
        """
        Add a probe on a wire, at a corner or at a point of a segment (see At), with its
        input up and to the right of it. An undo step. Returns the probe's object, for the
        GUI to show, None if it can't be added.
        """
        wires = self._app_model.objects.wires
        undo_state = self._app_model.circuit_to_model()
        anchor = wires.anchor_point(wire, at)
        component_object = self.add_object(Probe, anchor[0], anchor[1], {"width": wire[0].width})
        if component_object is None:
            return None
        probe = component_object.component
        assert isinstance(probe, Probe)
        port = wires.port_pos(probe.I)
        component_object.moveBy(
            anchor[0] + PROBE_OFFSET[0] - port[0], anchor[1] + PROBE_OFFSET[1] - port[1]
        )
        # A new port of the wire's width, this can't fail
        wires.connect_branch(wire, at, probe.I)
        self._app_model.objects.add_undo_state(undo_state)
        self._app_model.model_init()
        self._app_model.model_changed()
        return component_object

    def get_object(self, component: Component) -> ComponentObject:
        """Get component object (from component)"""
        return self._component_objects[component]

    def get_object_list(self) -> list[ComponentObject]:
        """Get list of component objects"""
        return list(self._component_objects.values())

    def change_settings(
        self, component_object: ComponentObject, changed: dict[str, Any]
    ) -> ComponentObject | None:
        """
        Change settings of a component, or its name (NAME_PARAMETER), an undo step (see
        the settings pane). Settings that can be reconfigured change the component, others
        build it again, with the wires to the ports it still has (see
        ModelObjects.change_component). Returns the
        object of the component, a new one if it was built again. None, with an error,
        if it can't have the settings.
        """
        component = component_object.component
        changed = dict(changed)
        new_name = changed.pop(NAME_PARAMETER, None)
        if new_name == component.name():
            new_name = None
        if new_name is not None:
            problem = name_problem(str(new_name), component, self._circuit)
            if problem:
                self._app_model.sig_error.emit(f"Could not rename {component.name()}: {problem}")
                return None
        class_name = changed.pop(CLASS_PARAMETER, None) if is_flip_flop(component) else None
        if (
            class_name is None
            and new_name is None
            and set(changed) <= set(component.get_reconfigurable_parameters())
        ):
            return component_object if self.update_settings(component_object, changed) else None
        if self._app_model.is_running:
            self._app_model.model_stop()
        try:
            if isinstance(component, SubCircuit) and "path" in changed:
                self.check_subcircuit_file(str(changed["path"]))
            name, gone = self._app_model.objects.change_component(
                component.name(), changed, class_name, new_name
            )
        except (DigsimException, OSError) as exc:
            self._app_model.sig_error.emit(f"Could not change the settings: {exc!s}")
            return None
        if gone:
            self._app_model.sig_warning_log.emit(
                "Settings Warning",
                "The wires of these ports are removed, the ports are gone or have another "
                "width now:\n" + "\n".join(gone),
            )
        return next(obj for comp, obj in self._component_objects.items() if comp.name() == name)

    def update_settings(self, component_object: ComponentObject, settings: dict[str, Any]) -> bool:
        """Update settings for a component"""
        component = component_object.component
        self._app_model.objects.push_undo_state()
        try:
            component.update_settings(settings)
        except (DigsimException, OSError) as exc:
            # For example a signal for state names that the netlist doesn't have
            self._app_model.objects.drop_undo_state()
            self._app_model.sig_error.emit(f"Could not change the settings: {exc!s}")
            return False
        if isinstance(component, YosysComponent):
            # New gates, the simulation starts over
            self._app_model.model_init()
        self._app_model.model_changed()
        # Settings can change the component size
        component_object.update_size()
        self._app_model.sig_repaint.emit()
        return True

    def yosys_components(self, path: str) -> list[YosysComponent]:
        """The Yosys components made from a Verilog or netlist file"""
        return components_of_file(self._circuit, path)

    def prepare_yosys_update(
        self,
        path: str,
        netlists: dict[YosysVariant, dict[str, Any]],
        parameters: dict[str, str] | None = None,
    ) -> YosysUpdate:
        """
        Check new netlists for the components of a file (see load_netlists), and how their
        ports change. 'parameters' has new parameters for components, by name, which the
        netlists are synthesized with.

        Raises:
            DigsimException: If a component can't be built from its new netlist. Nothing
                has changed then.
        """
        netlist_objects = {variant: YosysNetlist(**data) for variant, data in netlists.items()}
        changes: dict[YosysComponent, InterfaceChanges] = {}
        variants: dict[YosysComponent, YosysVariant] = {}
        for component in self.yosys_components(path):
            variant = variant_with(component, (parameters or {}).get(component.name()))
            variants[component] = variant
            netlist = netlist_objects[variant]
            component.check_netlist(netlist)
            changes[component] = interface_changes(
                component.interface(), YosysComponent.netlist_interface(netlist)
            )
        lines = self._app_model.objects.wires.to_lines()
        removed = sorted(
            {
                port
                for component, component_changes in changes.items()
                for port in removed_wires(lines, [component.name()], component_changes)
            }
        )
        return YosysUpdate(path, netlists, changes, removed, variants)

    def apply_yosys_update(self, update: YosysUpdate) -> list[str]:
        """
        Build the components of a file from new netlists (see prepare_yosys_update). With
        the same ports, the components are rebuilt, an undo step. When the ports change,
        the circuit is built again without the wires of the ports that are gone, and the
        undo steps are dropped. The simulation is stopped. Returns the warnings.
        """
        if self._app_model.is_running:
            self._app_model.model_stop()
        if not update.changes:
            return []
        if not update.ports_change():
            self._app_model.objects.push_undo_state()
            for component in update.changes:
                variant = update.variant(component)
                component.set_parameters(variant.parameters)
                component.reload_from_netlist(YosysNetlist(**update.netlists[variant]))
            self._app_model.model_init()
            self._app_model.model_changed()
            self._app_model.sig_repaint.emit()
            self._app_model.sig_yosys_updated.emit(update.path)
            return []
        gone = {
            f"{component.name()}.{port}"
            for component, changes in update.changes.items()
            for port in changes.gone()
        }
        lines = without_ports(self._app_model.objects.wires.to_lines(), gone)
        # The circuit is built from the settings of the components, with the new parameters
        for component in update.changes:
            component.set_parameters(update.variant(component).parameters)
        # The other Yosys components are built again from the netlists they have now, not
        # from their files: those may have changed since, or have errors now
        netlists = [
            (
                component.source_file,
                update.variant(component),
                YosysNetlist(**update.netlists[update.variant(component)])
                if component in update.changes
                else component.netlist(),
            )
            for component in self._circuit.get_toplevel_components()
            if isinstance(component, YosysComponent) and component.source_file is not None
        ]
        with YosysComponent.given_netlists(netlists):
            warnings = self._app_model.objects.rebuild(lines)
        self._app_model.sig_yosys_updated.emit(update.path)
        return warnings

    def check_subcircuit_file(self, path: str) -> None:
        """
        Raises DigsimException if a subcircuit's file is the file of this circuit, or uses
        it: the circuit would use itself. Every way a subcircuit's file gets into the
        circuit checks it (adding, settings and paste).
        """
        circuit_path = self._app_model.circuit_path
        if not path or circuit_path is None:
            return
        own = Path(circuit_path).resolve()
        if Path(path).resolve() == own or own in files_used(path):
            raise DigsimException(f"{path} uses this circuit's file, the circuit would use itself")

    def subcircuits(self, path: str | Path) -> list[SubCircuit]:
        """The subcircuits of a circuit file"""
        return [
            component
            for component in self._circuit.get_toplevel_components()
            if isinstance(component, SubCircuit) and same_file(component.source_file(), path)
        ]

    def prepare_subcircuit_reload(self, path: str | Path) -> SubCircuitUpdate:
        """
        How the ports of the subcircuits of a file change when they are built again from it

        Raises:
            SubCircuitException: If the file can't be read.
        """
        new = SubCircuit.file_interface(path)
        changes = {
            subcircuit: interface_changes(subcircuit.interface(), new)
            for subcircuit in self.subcircuits(path)
        }
        lines = self._app_model.objects.wires.to_lines()
        removed = sorted(
            {
                port
                for subcircuit, subcircuit_changes in changes.items()
                for port in removed_wires(lines, [subcircuit.name()], subcircuit_changes)
            }
        )
        reordered = any(list(subcircuit.interface()) != list(new) for subcircuit in changes)
        return SubCircuitUpdate(str(path), changes, removed, reordered)

    def apply_subcircuit_reload(self, update: SubCircuitUpdate) -> list[str]:
        """
        Build the subcircuits of a file again (see prepare_subcircuit_reload). With the same
        ports they are rebuilt, an undo step. When the ports change, the circuit is built
        again without the wires of the ports that are gone, and the undo steps are dropped.
        The simulation is stopped. Returns the warnings.
        """
        if self._app_model.is_running:
            self._app_model.model_stop()
        if not update.changes:
            return []
        if not update.ports_change() and update.reordered:
            # Built again with the ports in their new order, the wires stay
            return self._app_model.objects.rebuild(self._app_model.objects.wires.to_lines())
        if not update.ports_change():
            self._app_model.objects.push_undo_state()
            try:
                for subcircuit in update.changes:
                    subcircuit.reload()
            except DigsimException as exc:
                self._app_model.objects.undo()
                return [str(exc)]
            self._app_model.model_init()
            self._app_model.model_changed()
            self._app_model.sig_repaint.emit()
            return []
        gone = {
            f"{subcircuit.name()}.{port}"
            for subcircuit, changes in update.changes.items()
            for port in changes.gone()
        }
        lines = without_ports(self._app_model.objects.wires.to_lines(), gone)
        return self._app_model.objects.rebuild(lines)

    def update_sizes(self) -> None:
        """Update all component sizes"""
        for comp_object in self.get_object_list():
            comp_object.update_size()

    def delete(self, component_object: ComponentObject) -> None:
        """Delete a component object in the model"""
        # The wires that start on the component's wires are kept
        self._app_model.objects.wires.remove_component(component_object.component)
        component_object.disconnect()
        # A new component with the same name must not get the shortcut
        self._app_model.shortcuts.remove_component(component_object.component)
        del self._component_objects[component_object.component]
        self._circuit.delete_component(component_object.component)
        self._app_model.sig_delete_component.emit(component_object)

    def add_placed_object(
        self,
        component: Component,
        xpos: float,
        ypos: float,
        zlevel: float,
        rotation: int = 0,
        flipped: bool = False,
    ) -> ComponentObject:
        """Add the object of a component that was added to the circuit, at a position"""
        component_object = self._add_object(component, xpos, ypos)
        component_object.zlevel = zlevel
        component_object.rotation_angle = rotation
        component_object.flipped = flipped
        return component_object

    def add_gui_positions(self, gui_dc_dict: dict[str, GuiPositionDataClass]) -> None:
        """Create model components from circuit_dict"""
        for comp in self._circuit.get_toplevel_components():
            gui_dc = gui_dc_dict.get(comp.name(), GuiPositionDataClass())
            component_object = self._add_object(comp, gui_dc.x, gui_dc.y)
            component_object.zlevel = gui_dc.z
            component_object.rotation_angle = gui_dc.rotation
            component_object.flipped = gui_dc.flipped

    def get_gui_dict(self) -> dict[str, GuiPositionDataClass]:
        """Return gui dict from component objects"""
        gui_dict = {}
        for comp, comp_object in self.get_dict().items():
            gui_dict[comp.name()] = comp_object.to_gui_dataclass()
        return gui_dict
