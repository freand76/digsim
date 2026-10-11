# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle objects in the model"""

from __future__ import annotations

from typing import TYPE_CHECKING

from digsim.circuit import Circuit
from digsim.storage_model import ModelDataClass

from ._model_components import ModelComponents
from ._model_new_wire import NewWire


if TYPE_CHECKING:
    from digsim.app.gui_objects import ComponentObject

    from ._model import AppModel


class ModelObjects:
    """Class to handle objects in the model"""

    def __init__(self, app_model: AppModel) -> None:
        self._app_model = app_model
        self._circuit = Circuit(name="DigSimCircuit")
        self._model_components = ModelComponents(app_model, self._circuit)
        self._undo_stack: list[ModelDataClass] = []
        self._redo_stack: list[ModelDataClass] = []
        self._new_wire = NewWire(self._app_model)

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
        """return the model components"""
        return self._new_wire

    def init(self) -> None:
        """Initialize objects"""
        self._model_components.init()

    def clear(self) -> None:
        """Clear components and wires"""
        self._model_components.clear()
        self._circuit.clear()

    def get_list(self) -> list[ComponentObject]:
        """Get list of all model objects"""
        model_objects = self._model_components.get_object_list()
        return model_objects

    def get_selected(self) -> list[ComponentObject]:
        """Get selected objects"""
        return [obj for obj in self.get_list() if obj.selected]

    def _delete(self, selected_objects: list[ComponentObject]) -> None:
        for obj in selected_objects:
            if ModelComponents.is_component_object(obj):
                self._model_components.delete(obj)

    def delete_selected(self) -> None:
        """Delete selected object(s)"""
        self.push_undo_state()
        selected_objects = self._app_model.objects.get_selected()
        if len(selected_objects) > 0:
            self._delete(selected_objects)
            self._app_model.model_changed()
        self._app_model.sig_delete_wires.emit()

    def _restore_state(self, model_dc: ModelDataClass) -> None:
        self.clear()
        exception_str_list = self._app_model.model_to_circuit(model_dc)
        self._app_model.model_init()
        self._app_model.model_changed()
        if len(exception_str_list) > 0:
            self._app_model.sig_warning_log.emit(
                "Load Circuit Warning", "\n".join(exception_str_list)
            )

    def reset_undo_stack(self) -> None:
        """Clear undo/redo stacks"""
        self._undo_stack = []
        self._redo_stack = []
        self._app_model.sig_control_notify.emit()

    def push_undo_state(self, clear_redo_stack: bool = True) -> None:
        """Push undo state to stack"""
        self._undo_stack.append(self._app_model.circuit_to_model())
        if clear_redo_stack:
            self._redo_stack = []
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
        if len(self._undo_stack) > 0:
            self.push_redo_state()
            model_dc = self._undo_stack.pop()
            self._restore_state(model_dc)
            self._app_model.sig_control_notify.emit()
            self._app_model.sig_synchronize_gui.emit()

    def redo(self) -> None:
        """Undo to last saved state"""
        if len(self._redo_stack) > 0:
            self.push_undo_state(clear_redo_stack=False)
            model_dc = self._redo_stack.pop()
            self._restore_state(model_dc)
            self._app_model.sig_control_notify.emit()
            self._app_model.sig_synchronize_gui.emit()

    def can_undo(self) -> bool:
        """Return true if the undo stack is not empty"""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Return true if the undo stack is not empty"""
        return len(self._redo_stack) > 0
