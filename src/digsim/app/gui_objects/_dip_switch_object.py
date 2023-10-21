# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A hexdigit component placed in the GUI """

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QPen

from ._component_object import ComponentObject
from ._image_objects import ImageObject


# pylint: disable=too-many-arguments


class DipSwitchObject(ImageObject):
    """The class for a bus/bit component placed in the GUI"""

    IMAGE_FILENAME = "images/DIP_SWITCH.png"
    DIP_SWITCH_WIDTH = 40
    DIP_SWITCH_HEIGHT = ComponentObject.MIN_PORT_TO_PORT_DISTANCE - 2

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos)
        self._height = self.component.bits() * self.DIP_SWITCH_HEIGHT + 2 * self.BORDER_TO_PORT
        self._rects = []
        self.update_ports()

    def update_ports(self):
        super().update_ports()
        self._rects = []
        for idx in range(0, self.component.bits()):
            self._rects.append(
                QRect(
                    self.pos.x() + self.get_rect().width() / 2 - 0.8 * self.DIP_SWITCH_WIDTH,
                    self.pos.y() + self.BORDER_TO_PORT + idx * self.DIP_SWITCH_HEIGHT,
                    self.DIP_SWITCH_WIDTH,
                    self.DIP_SWITCH_HEIGHT,
                )
            )
        
    def mouse_position(self, pos):
        """update component according to on mouse move"""
        select = None
        for idx, rect in enumerate(self._rects):
            if pos.x() > rect.x() and pos.x() < (rect.x() + rect.width()):
                if pos.y() > rect.y() and pos.y() < (rect.y() + rect.height()):
                    select = idx
                    break
        self.component.select(select)

    def single_click_action(self):
        self.component.toggle()
        self.repaint()

    def _paint_dip_switch(self, painter):
        pen = QPen()
        pen.setColor(Qt.black)
        pen.setWidth(1)
        painter.setPen(pen)
        for idx, rect in enumerate(self._rects):
            painter.setBrush(Qt.gray)
            painter.drawRect(rect)
            painter.setBrush(Qt.white)
            if self.component.is_set(idx):
                painter.drawRect(
                    rect.x() + rect.width() / 2 + 2,
                    rect.y() + 2,
                    rect.width() / 2 - 4,
                    rect.height() - 4,
                )
            else:
                painter.drawRect(
                    rect.x() + 2, rect.y() + 2, rect.width() / 2 - 4, rect.height() - 4
                )

    def _portlist(self):
        return self.component.outports()

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self._paint_dip_switch(painter)
