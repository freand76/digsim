# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle the shape of the wires in the model"""

from __future__ import annotations

from typing import TYPE_CHECKING

from digsim.app._wire_key import Wire
from digsim.app._wire_lines import WireDrawing
from digsim.app._wire_path import Point, Rect
from digsim.circuit.components.atoms import Port


if TYPE_CHECKING:
    from ._model import AppModel


class ModelWires(WireDrawing):
    """
    The drawn wires of the circuit in the GUI and the lines they make, see
    digsim.app._wire_lines. Changes are undo steps of the model.
    """

    def __init__(self, app_model: AppModel) -> None:
        super().__init__()
        self._app_model = app_model

    def connections(self) -> list[Wire]:
        """The wires shown in the GUI, (output port, input port)"""
        components = self._app_model.objects.components
        return [
            (src_port, dst_port)
            for component_object in components.get_object_list()
            for src_port in component_object.component.outports()
            for dst_port in src_port.wired_ports
            if dst_port.parent() in components.get_dict()
        ]

    def ports(self) -> list[Port]:
        """All ports of the components in the GUI"""
        return [
            port
            for component_object in self._app_model.objects.components.get_object_list()
            for port in component_object.component.ports
        ]

    def port_pos(self, port: Port) -> Point:
        """The position of a port in the scene"""
        component_object = self._app_model.objects.components.get_object(port.parent())
        pos = component_object.get_port_item(port).portPos()
        return pos.x(), pos.y()

    def port_rect(self, port: Port) -> Rect:
        component_object = self._app_model.objects.components.get_object(port.parent())
        rect = component_object.get_port_item(port).portParentRect()
        return rect.x(), rect.y(), rect.width(), rect.height()

    def _push_undo(self) -> None:
        self._app_model.objects.push_undo_state()

    def _changed(self) -> None:
        self._app_model.model_changed()
