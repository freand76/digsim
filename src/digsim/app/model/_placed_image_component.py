# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A component with an image as symbol the GUI """

import os

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPen, QPixmap

from ._placed_component import PlacedComponent


class PlacedImageComponent(PlacedComponent):
    """The class for a image component placed in the GUI"""

    IMAGE_FILENAME = None
    ACTIVE_IMAGE_FILENAME = None
    _pixmap = None
    _pixmap_active = None

    def __init__(self, component, xpos, ypos, show_name=True):
        super().__init__(component, xpos, ypos)
        self._show_name = show_name

    @classmethod
    def _get_pixmaps(cls):
        """Load the pixmap at first use"""
        if cls.ACTIVE_IMAGE_FILENAME is not None and cls._pixmap_active is None:
            cls._pixmap_active = QPixmap(
                f"{os.path.dirname(__file__)}/{cls.ACTIVE_IMAGE_FILENAME}"
            )
        if cls.IMAGE_FILENAME is not None and cls._pixmap is None:
            cls._pixmap = QPixmap(f"{os.path.dirname(__file__)}/{cls.IMAGE_FILENAME}")

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self._get_pixmaps()
        xpos = self.size.width() / 2 - self._pixmap.width() / 2
        ypos = self.size.height() / 2 - self._pixmap.height() / 2
        self.paint_pixmap(painter, xpos, ypos, self.component.active)
        if self._show_name:
            self.paint_selectable_component_name(painter, self.size, self.component.display_name())

    @classmethod
    def paint_selectable_component(cls, painter, size, name):
        cls.paint_selectable_component_name(painter, size, name)
        cls._get_pixmaps()
        xpos = size.width() / 2 - cls._pixmap.width() / 2
        ypos = size.width() / 2 - cls._pixmap.height() / 2
        cls.paint_pixmap(painter, xpos, ypos)

    @classmethod
    def paint_pixmap(cls, painter, xpos, ypos, active=False):
        """Paint the pixmap"""
        pixmap = cls._pixmap_active if active and cls._pixmap_active is not None else cls._pixmap
        painter.drawPixmap(QPoint(xpos, ypos), pixmap)


class PlacedImageComponentAND(PlacedImageComponent):
    """The class for a AND image component placed in the GUI"""

    IMAGE_FILENAME = "images/AND.png"


class PlacedImageComponentOR(PlacedImageComponent):
    """The class for a OR image component placed in the GUI"""

    IMAGE_FILENAME = "images/OR.png"


class PlacedImageComponentNAND(PlacedImageComponent):
    """The class for a NAND image component placed in the GUI"""

    IMAGE_FILENAME = "images/NAND.png"


class PlacedImageComponentNOR(PlacedImageComponent):
    """The class for a NOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/NOR.png"


class PlacedImageComponentNOT(PlacedImageComponent):
    """The class for a NOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/NOT.png"


class PlacedImageComponentXOR(PlacedImageComponent):
    """The class for a XOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/XOR.png"


class PlacedImageComponentDFF(PlacedImageComponent):
    """The class for a DFF image component placed in the GUI"""

    IMAGE_FILENAME = "images/DFF.png"


class PlacedImageComponentStaticLevel(PlacedImageComponent):
    """The class for a StaticLevel image component placed in the GUI"""

    IMAGE_FILENAME = "images/ZERO.png"
    ACTIVE_IMAGE_FILENAME = "images/ONE.png"

    def __init__(self, component, xpos, ypos):
        super().__init__(component, xpos, ypos, show_name=False)


class PlacedImageComponentLed(PlacedImageComponent):
    """The class for a Led image component placed in the GUI"""

    IMAGE_FILENAME = "images/LED_OFF.png"
    ACTIVE_IMAGE_FILENAME = "images/LED_ON.png"

    def __init__(self, component, xpos, ypos):
        super().__init__(component, xpos, ypos, show_name=False)


class PlacedImageComponentYosys(PlacedImageComponent):
    """The class for a Yosys image component placed in the GUI"""

    IMAGE_FILENAME = "images/YOSYS.png"

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self.paint_component_name(painter)


class PlacedImageComponentPushButton(PlacedImageComponent):
    """The class for a PushButton image component placed in the GUI"""

    IMAGE_FILENAME = "images/PB.png"
    BUTTON_RADIUS = 35

    def __init__(self, component, xpos, ypos):
        super().__init__(component, xpos, ypos, show_name=False)

    def paint_component(self, painter):
        super().paint_component(painter)
        if self.component.active:
            pen = QPen()
            pen.setWidth(4)
            pen.setColor(Qt.green)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(
                self._width / 2 - self.BUTTON_RADIUS,
                self._height / 2 - self.BUTTON_RADIUS,
                self.BUTTON_RADIUS * 2,
                self.BUTTON_RADIUS * 2,
            )


class PlacedImageComponentWithActiveRect(PlacedImageComponent):
    """
    A base class for a image component placed in the GUI.
    When active the image will have a green border painted around it.
    """

    def paint_component(self, painter):
        super().paint_component(painter)
        if self.component.active:
            xpos = self.size.width() / 2 - self._pixmap.width() / 2
            ypos = self.size.height() / 2 - self._pixmap.height() / 2
            pen = QPen()
            pen.setWidth(4)
            pen.setColor(Qt.green)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(xpos, ypos, self._pixmap.width(), self._pixmap.height(), 5, 5)


class PlacedImageComponentOnOffSwitch(PlacedImageComponentWithActiveRect):
    """The class for a On/Off-Switch image component placed in the GUI"""

    IMAGE_FILENAME = "images/Switch_OFF.png"
    ACTIVE_IMAGE_FILENAME = "images/Switch_ON.png"

    def __init__(self, component, xpos, ypos):
        super().__init__(component, xpos, ypos, show_name=False)


class PlacedImageComponentClock(PlacedImageComponentWithActiveRect):
    """The class for a DFF image component placed in the GUI"""

    IMAGE_FILENAME = "images/Clock.png"

    def __init__(self, component, xpos, ypos):
        super().__init__(component, xpos, ypos, show_name=False)
