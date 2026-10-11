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
from digsim.circuit.components.atoms import DigsimException


if TYPE_CHECKING:
    from digsim.app.model import AppModel


# Components that must not be created for a preview: label wires register their label
# in storage shared by all circuits
_NO_COMPONENT_PREVIEW = {"LabelWireIn", "LabelWireOut"}

# The size of the component icons in the component selector
_ICON_SIZE = QSize(80, 105)

# Preview pixmap and the position of the component center in it, per component name
_previews: dict[str, tuple[QPixmap, QPointF]] = {}


def _default_settings(parameters: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """The settings dialog defaults, or None if a parameter has no default (a file path)"""
    settings: dict[str, Any] = {}
    for key, parameter in parameters.items():
        if "default" in parameter:
            settings[key] = parameter["default"]
        elif "default_index" in parameter:
            settings[key] = parameter["range"][parameter["default_index"]]
        elif parameter["type"] == "component_name":
            settings[key] = next(iter(parameter["component_list"]))
        elif parameter["type"] == "ic_name":
            ic_files = sorted(Path(IntegratedCircuit.folder()).glob("*.json"))
            settings[key] = ic_files[0].stem
        else:
            return None
    return settings


def _component_preview(app_model: AppModel, name: str) -> tuple[QPixmap, QPointF] | None:
    """Draw the component with default settings, as it looks when it has been dropped"""
    if name in _NO_COMPONENT_PREVIEW:
        return None
    component_class = getattr(digsim.circuit.components, name)
    settings = _default_settings(component_class.get_parameters())
    if settings is None:
        return None
    # Components like FlipFlop select the class to create with their "name" setting
    component_class = getattr(digsim.circuit.components, settings.get("name", name))
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
    if name not in _previews:
        try:
            preview = _component_preview(app_model, name)
        except (DigsimException, OSError, TypeError, ValueError):
            # The component could not be created with default settings, use the icon
            preview = None
        _previews[name] = preview if preview is not None else _icon_preview(name)
    return _previews[name]
