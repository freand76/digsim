# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A component with an image as symbol the GUI """

import os

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPen, QPixmap

from ._component_object import ComponentObject


class ImageObject(ComponentObject):
    """The class for a image component placed in the GUI"""

    IMAGE_FILENAME = None
    ACTIVE_IMAGE_FILENAME = None
    _pixmap = None
    _pixmap_active = None

    def __init__(self, component, xpos, ypos, show_name=True):
        super().__init__(component, xpos, ypos)
        self._show_name = show_name
        self.setup_size()
        self.update_ports()

    def setup_size(self):
        """Change size of component"""

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


class ImageObjectAND(ImageObject):
    """The class for a AND image component placed in the GUI"""

    IMAGE_FILENAME = "images/AND.png"


class ImageObjectOR(ImageObject):
    """The class for a OR image component placed in the GUI"""

    IMAGE_FILENAME = "images/OR.png"


class ImageObjectNAND(ImageObject):
    """The class for a NAND image component placed in the GUI"""

    IMAGE_FILENAME = "images/NAND.png"


class ImageObjectNOR(ImageObject):
    """The class for a NOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/NOR.png"


class ImageObjectNOT(ImageObject):
    """The class for a NOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/NOT.png"


class ImageObjectXOR(ImageObject):
    """The class for a XOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/XOR.png"


class ImageObjectDFF(ImageObject):
    """The class for a DFF image component placed in the GUI"""

    IMAGE_FILENAME = "images/DFF.png"
    PORT_TO_IMAGE_DIST = 20

    def setup_size(self):
        self._get_pixmaps()
        _, str_pixels_w, _ = self.get_port_display_name_metrics("D")
        self._width = 2 * (str_pixels_w + self.PORT_TO_IMAGE_DIST) + self._pixmap.width()


class ImageObjectMUX(ImageObject):
    """The class for a MUX image component placed in the GUI"""

    IMAGE_FILENAME = "images/MUX.png"
    PORT_TO_IMAGE_DIST = 20

    def setup_size(self):
        self._get_pixmaps()
        _, str_pixels_w, _ = self.get_port_display_name_metrics("A")
        self._width = 2 * (str_pixels_w + self.PORT_TO_IMAGE_DIST) + self._pixmap.width()


class ImageObjectStaticValue(ImageObject):
    """The class for a StaticValue image component placed in the GUI"""

    IMAGE_FILENAME = "images/ZERO.png"
    ACTIVE_IMAGE_FILENAME = "images/ONE.png"

    def __init__(self, component, xpos, ypos):
        super().__init__(component, xpos, ypos, show_name=False)

    def paint_component(self, painter):
        if self.component.O.width == 1:
            super().paint_component(painter)
        else:
            self.paint_component_base(painter)
            font = QFont("Arial", 16)
            fm = QFontMetrics(font)
            value_str = f"{self.component.O.value}"
            str_w = fm.horizontalAdvance(value_str)
            str_h = fm.height()
            painter.setFont(font)
            painter.drawText(
                self.get_rect().x() + self.get_rect().width() / 2 - str_w / 2,
                self.get_rect().y() + str_h,
                value_str,
            )


class ImageObjectLed(ImageObject):
    """The class for a Led image component placed in the GUI"""

    IMAGE_FILENAME = "images/LED_OFF.png"
    ACTIVE_IMAGE_FILENAME = "images/LED_ON.png"

    def __init__(self, component, xpos, ypos):
        super().__init__(component, xpos, ypos, show_name=False)


class ImageObjectYosys(ImageObject):
    """The class for a Yosys image component placed in the GUI"""

    IMAGE_FILENAME = "images/YOSYS.png"

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self.paint_component_name(painter)


class ImageObjectIC(ImageObject):
    """The class for a Yosys image component placed in the GUI"""

    IMAGE_FILENAME = "images/IC.png"

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self.paint_component_name(painter)


class ImageObjectPushButton(ImageObject):
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


class ImageObjectWithActiveRect(ImageObject):
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


class ImageObjectOnOffSwitch(ImageObjectWithActiveRect):
    """The class for a On/Off-Switch image component placed in the GUI"""

    IMAGE_FILENAME = "images/Switch_OFF.png"
    ACTIVE_IMAGE_FILENAME = "images/Switch_ON.png"

    def __init__(self, component, xpos, ypos):
        super().__init__(component, xpos, ypos, show_name=False)


class ImageObjectClock(ImageObjectWithActiveRect):
    """The class for a Clock image component placed in the GUI"""

    IMAGE_FILENAME = "images/Clock.png"

    def __init__(self, component, xpos, ypos):
        super().__init__(component, xpos, ypos, show_name=False)
