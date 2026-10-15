# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A button component with an image as symbol the GUI"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QPainter, QPen
from PySide6.QtWidgets import QMenu, QWidget

from digsim.app.settings import ShortcutDialog
from digsim.circuit.components import OnOffSwitch
from digsim.circuit.components.atoms import Component

from ._image_objects import ImageObject, ImageObjectWithActiveRect


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class _ShortcutObject:
    """The class for a ShortcutObject component placed in the GUI"""

    @classmethod
    def add_context_menu_action(
        cls, menu: QMenu, parent: QWidget | None, app_model: AppModel, component: Component
    ) -> None:
        """Add context menu action"""
        shortcutAction = QAction("Shortcut", menu)
        menu.addAction(shortcutAction)
        shortcutAction.triggered.connect(partial(cls._shortcut, parent, app_model, component))

    @classmethod
    def _shortcut(cls, parent: QWidget | None, app_model: AppModel, component: Component) -> None:
        shortcutDialog = ShortcutDialog(parent, app_model)
        key = shortcutDialog.start()
        if key is not None:
            app_model.shortcuts.set_component(key, component)


class ButtonObject(ImageObject):
    """The class for a PushButton image component placed in the GUI"""

    IMAGE_FILENAME = "images/PB.png"
    BUTTON_RADIUS = 35

    SHOW_NAME = False
    SHOW_PORT_NAMES = False

    _BUTTON_ACTIVE_PEN = QPen(Qt.GlobalColor.green)

    def paint_component(self, painter: QPainter) -> None:
        super().paint_component(painter)
        if self.component.active:
            # A copy: the class pen is shared by all instances
            pen = QPen(self._BUTTON_ACTIVE_PEN)
            pen.setWidth(4)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(
                int(self.object_pos.x() + self.width / 2 - self.BUTTON_RADIUS),
                int(self.object_pos.y() + self.height / 2 - self.BUTTON_RADIUS),
                self.BUTTON_RADIUS * 2,
                self.BUTTON_RADIUS * 2,
            )

    def add_context_menu_action(self, menu: QMenu, parent: QWidget | None) -> None:
        _ShortcutObject.add_context_menu_action(menu, parent, self._app_model, self._component)


class OnOffSwitchObject(ImageObjectWithActiveRect):
    """The class for a On/Off-Switch image component placed in the GUI"""

    IMAGE_FILENAME = "images/Switch_OFF.png"
    ACTIVE_IMAGE_FILENAME = "images/Switch_ON.png"

    @property
    def component(self) -> OnOffSwitch:
        component = self._component
        assert isinstance(component, OnOffSwitch)
        return component

    def single_click_action(self) -> None:
        self._toggle()

    def add_context_menu_action(self, menu: QMenu, parent: QWidget | None) -> None:
        _ShortcutObject.add_context_menu_action(menu, parent, self._app_model, self._component)
        toggleAction = QAction("Toggle Switch", menu)
        menu.addAction(toggleAction)
        toggleAction.triggered.connect(self._toggle)

    def _toggle(self) -> None:
        self.component.toggle()
        self.repaint()
