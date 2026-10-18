# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle component objects in the model"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPointF

import digsim.app.gui_objects
import digsim.circuit.components
from digsim.app.gui_objects import ComponentObject
from digsim.circuit import Circuit
from digsim.circuit.components import Buzzer
from digsim.circuit.components.atoms import (
    CallbackComponent,
    Component,
    DigsimException,
    Parameter,
)
from digsim.storage_model import GuiPositionDataClass, ModelDataClass


if TYPE_CHECKING:
    from ._model import AppModel


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
        self._app_model.objects.push_undo_state()
        component_class = self._get_component_class(name)
        try:
            with self._circuit.adding_components():
                component = component_class(self._circuit, **settings)
        except (DigsimException, OSError) as exc:
            # For example a Verilog file with errors, or a file that can't be read
            self._app_model.objects.drop_undo_state()
            self._app_model.sig_error.emit(f"Could not add {name}: {exc!s}")
            return None
        self._app_model.model_init()
        component_object = self._add_object(component, pos.x(), pos.y())
        self._app_model.model_changed()
        return component_object

    def get_object(self, component: Component) -> ComponentObject:
        """Get component object (from component)"""
        return self._component_objects[component]

    def get_object_list(self) -> list[ComponentObject]:
        """Get list of component objects"""
        return list(self._component_objects.values())

    def update_settings(self, component_object: ComponentObject, settings: dict[str, Any]) -> None:
        """Update settings for a component"""
        self._app_model.objects.push_undo_state()
        component_object.component.update_settings(settings)
        self._app_model.model_changed()
        # Settings can change the component size
        component_object.update_size()
        self._app_model.sig_repaint.emit()

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

    def add_gui_positions(self, gui_dc_dict: dict[str, GuiPositionDataClass]) -> None:
        """Create model components from circuit_dict"""
        for comp in self._circuit.get_toplevel_components():
            gui_dc = gui_dc_dict.get(comp.name(), GuiPositionDataClass())
            component_object = self._add_object(comp, gui_dc.x, gui_dc.y)
            component_object.zlevel = gui_dc.z

    def get_gui_dict(self) -> dict[str, GuiPositionDataClass]:
        """Return gui dict from component objects"""
        gui_dict = {}
        for comp, comp_object in self.get_dict().items():
            gui_dict[comp.name()] = comp_object.to_gui_dataclass()
        return gui_dict
