# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A button component with an image as symbol the GUI"""

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QPen

from digsim.app.settings import ShortcutDialog

from ._image_objects import ImageObject, ImageObjectWithActiveRect


class _ShortcutObject:
    """The class for a ShortcutObject component placed in the GUI"""

    @classmethod
    def add_context_menu_action(cls, menu, parent, app_model, component):
        """Add context menu action"""
        shortcutAction = QAction("Shortcut", menu)
        menu.addAction(shortcutAction)
        shortcutAction.triggered.connect(partial(cls._shortcut, parent, app_model, component))

    @classmethod
    def _shortcut(cls, parent, app_model, component):
        shortcutDialog = ShortcutDialog(parent, app_model)
        key = shortcutDialog.start()
        if key is not None:
            app_model.shortcuts.set_component(key, component)


class ButtonObject(ImageObject):
    """The class for a PushButton image component placed in the GUI"""

    IMAGE_FILENAME = "images/PB.png"
    BUTTON_RADIUS = 35

    _BUTTON_ACTIVE_PEN = QPen(Qt.green)

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos)
        self.show_name(False)
        self.paint_port_names(False)

    def paint_component(self, painter):
        super().paint_component(painter)
        if self.component.active:
            pen = self._BUTTON_ACTIVE_PEN
            pen.setWidth(4)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(
                self.object_pos.x() + self.width / 2 - self.BUTTON_RADIUS,
                self.object_pos.y() + self.height / 2 - self.BUTTON_RADIUS,
                self.BUTTON_RADIUS * 2,
                self.BUTTON_RADIUS * 2,
            )

    def add_context_menu_action(self, menu, parent):
        _ShortcutObject.add_context_menu_action(menu, parent, self._app_model, self._component)


class OnOffSwitchObject(ImageObjectWithActiveRect):
    """The class for a On/Off-Switch image component placed in the GUI"""

    IMAGE_FILENAME = "images/Switch_OFF.png"
    ACTIVE_IMAGE_FILENAME = "images/Switch_ON.png"

    def single_click_action(self):
        self._toggle()

    def add_context_menu_action(self, menu, parent):
        _ShortcutObject.add_context_menu_action(menu, parent, self._app_model, self._component)
        toggleAction = QAction("Toggle Switch", menu)
        menu.addAction(toggleAction)
        toggleAction.triggered.connect(self._toggle)

    def _toggle(self):
        self.component.toggle()
        self.repaint()
