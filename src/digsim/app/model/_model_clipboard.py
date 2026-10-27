# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Copy and paste components in the model"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from digsim.app._clipboard_lines import lines_between, moved_lines
from digsim.app._wire_key import port_key
from digsim.circuit.components.atoms import DigsimException
from digsim.storage_model import ClipboardDataClass, ComponentDataClass, GuiPositionDataClass


if TYPE_CHECKING:
    from digsim.app.gui_objects import ComponentObject

    from ._model import AppModel


class ModelClipboard:
    """
    Copies of components, with the lines between them, and pasting them: the pasted
    components get new names where theirs are taken, and are connected like the copied
    ones were to each other.
    """

    def __init__(self, app_model: AppModel) -> None:
        self._app_model = app_model

    def copy(self, component_objects: list[ComponentObject]) -> ClipboardDataClass | None:
        """The components of some objects, None if there are none"""
        names = {component_object.component.name() for component_object in component_objects}
        if not names:
            return None
        objects = self._app_model.objects
        circuit = objects.circuit
        circuit_dc = circuit.to_dataclass(self._app_model.circuit_folder)
        components = []
        for component_dc in circuit_dc.components:
            if component_dc.name not in names:
                continue
            settings = dict(component_dc.settings)
            if settings.get("path"):
                # Absolute, the copy can be pasted in a circuit in another folder
                settings["path"] = os.path.abspath(circuit.load_path(settings["path"]))
            components.append(
                ComponentDataClass(
                    name=component_dc.name,
                    type=component_dc.type,
                    display_name=component_dc.display_name,
                    settings=settings,
                )
            )
        gui = {
            name: position
            for name, position in objects.components.get_gui_dict().items()
            if name in names
        }
        ports = {
            port_key(port)
            for component_object in component_objects
            for port in component_object.component.ports
        }
        # The places of the other ports, a line between copied ports can go through them
        places = {
            port_key(port): [round(value) for value in objects.wires.port_pos(port)]
            for port in objects.wires.ports()
        }
        lines = lines_between(objects.wires.to_lines(), ports, places)
        return ClipboardDataClass(components=components, gui=gui, lines=lines)

    def paste(self, data: ClipboardDataClass, dx: int, dy: int) -> list[ComponentObject]:
        """
        Add copied components, moved by (dx, dy), on top of the others, an undo step.
        Returns their objects, for the GUI to show. A component that can't be created
        (like one from a Verilog file that is gone) is left out, with a warning.
        """
        objects = self._app_model.objects
        circuit = objects.circuit
        undo_state = self._app_model.circuit_to_model()
        top = objects.components.get_top_zlevel() + 1
        names: dict[str, str] = {}
        created: list[ComponentObject] = []
        warnings: list[str] = []
        for component_dc in data.components:
            try:
                with circuit.adding_components():
                    component = component_dc.create(circuit)
            except (DigsimException, OSError) as exc:
                warnings.append(f"{component_dc.name} is not pasted: {exc!s}")
                continue
            names[component_dc.name] = component.name()
            position = data.gui.get(component_dc.name, GuiPositionDataClass())
            created.append(
                objects.components.add_placed_object(
                    component, position.x + dx, position.y + dy, top + position.z
                )
            )
        if created:
            # Only the ports of the components that were pasted
            pasted_ports = {
                port_key(port)
                for component_object in created
                for port in component_object.component.ports
            }
            lines = lines_between(moved_lines(data.lines, names, dx, dy), pasted_ports, {})
            for line in lines:
                line.connect(circuit, warnings)
            objects.wires.add_lines(lines)
            objects.add_undo_state(undo_state)
            self._app_model.model_init()
            self._app_model.model_changed()
        if warnings:
            self._app_model.sig_warning_log.emit("Paste Warning", "\n".join(warnings))
        return created
