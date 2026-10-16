# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Preview images of components, shown in the circuit area while a component is dragged
into it. The drag image itself is drawn by the window system, and is missing in some
Wayland sessions.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsScene

import digsim.app.gui_objects
import digsim.circuit.components
from digsim.app.gui_objects._gui_object_factory import CLASS_NAME_TO_COMPONENT_OBJECT
from digsim.circuit import Circuit
from digsim.circuit.components import IntegratedCircuit
from digsim.circuit.components.atoms import DigsimException, Parameter


if TYPE_CHECKING:
    from digsim.app.model import AppModel


# The size of the component icons in the component selector
_ICON_SIZE = QSize(80, 105)

# Preview pixmap and the position of the component center in it, per component name and
# settings (label wires show their label, which depends on the labels in the circuit)
_previews: dict[tuple[str, str], tuple[QPixmap, QPointF]] = {}


def _default_settings(parameters: dict[str, Parameter]) -> dict[str, Any] | None:
    """The settings dialog defaults, or None if a parameter has no default (a file path)"""
    settings: dict[str, Any] = {}
    for key, parameter in parameters.items():
        if "default" in parameter:
            settings[key] = parameter["default"]
            # As the settings dialog: change a text that is already in use
            while settings[key] in parameter.get("invalid_list", []):
                settings[key] += "x"
        elif "default_index" in parameter:
            settings[key] = parameter["range"][parameter["default_index"]]
        elif parameter["type"] == "component_name":
            settings[key] = next(iter(parameter["component_list"]))
        elif parameter["type"] == "ic_name":
            ic_files = sorted(Path(IntegratedCircuit.folder()).glob("*.json"))
            settings[key] = ic_files[0].stem
        elif parameter["type"] == "list" and len(parameter["items"]) > 0:
            settings[key] = parameter["items"][0]
        else:
            return None
    return settings


def _preview_settings(app_model: AppModel, name: str) -> dict[str, Any] | None:
    """The settings the component gets when it is dropped with the dialog defaults"""
    component_class = getattr(digsim.circuit.components, name)
    return _default_settings(component_class.get_circuit_parameters(app_model.objects.circuit))


def _component_preview(
    app_model: AppModel, name: str, settings: dict[str, Any]
) -> tuple[QPixmap, QPointF]:
    """Draw the component with default settings, as it looks when it has been dropped"""
    # Components like FlipFlop select the class to create with their "name" setting
    component_class = getattr(digsim.circuit.components, settings.get("name", name))
    # A circuit of its own, the preview must not be added to the circuit in the GUI
    component = component_class(Circuit(), **settings)
    object_class = digsim.app.gui_objects.class_factory(type(component).__name__)
    component_object = object_class(app_model, component, 0, 0)

    scene = QGraphicsScene()
    scene.addItem(component_object)
    source = component_object.mapRectToScene(
        component_object.boundingRect().united(component_object.childrenBoundingRect())
    ).adjusted(-1, -1, 1, 1)
    pixmap = QPixmap(source.size().toSize())
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    scene.render(painter, QRectF(pixmap.rect()), source)
    painter.end()
    center = component_object.mapRectToScene(component_object.rect()).center()
    return pixmap, center - source.topLeft()


def _icon_preview(name: str) -> tuple[QPixmap, QPointF]:
    """The component's icon from the component selector"""
    pixmap = QPixmap(_ICON_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    digsim.app.gui_objects.class_factory(name).paint_selectable_component(
        painter, _ICON_SIZE, name
    )
    painter.end()
    return pixmap, QPointF(pixmap.rect().center())


def drag_preview(app_model: AppModel, name: str) -> tuple[QPixmap, QPointF] | None:
    """
    A preview pixmap for a component (class name), and the position in the pixmap that
    should be under the mouse pointer: the center of the component.
    None if 'name' is not a component in the component selector.
    """
    if name not in CLASS_NAME_TO_COMPONENT_OBJECT:
        return None
    try:
        settings = _preview_settings(app_model, name)
    except (DigsimException, OSError, TypeError, ValueError):
        settings = None
    key = (name, repr(settings))
    if key not in _previews:
        preview = None
        if settings is not None:
            try:
                preview = _component_preview(app_model, name, settings)
            except (DigsimException, OSError, TypeError, ValueError):
                # The component could not be created with default settings
                preview = None
        # Without settings (like a file path) or a component, use the selector icon
        _previews[key] = preview if preview is not None else _icon_preview(name)
    return _previews[key]
