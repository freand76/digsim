# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A component with an image as symbol the GUI"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont, QPen, QPixmap

from ._component_object import ComponentObject


class ImageObject(ComponentObject):
    """The class for a image component placed in the GUI"""

    IMAGE_FILENAME: str | None = None
    ACTIVE_IMAGE_FILENAME: str | None = None
    _pixmap = None
    _pixmap_active = None

    def __init__(
        self,
        app_model,
        component,
        xpos,
        ypos,
        port_distance=ComponentObject.DEFAULT_PORT_TO_PORT_DISTANCE,
    ):
        super().__init__(app_model, component, xpos, ypos, port_distance=port_distance)
        self._show_name = True
        self.setup_size()
        self.update_ports()

    def show_name(self, enable):
        """Enable/Disable name on image component"""
        self._show_name = enable

    def setup_size(self):
        """Change size of component"""

    @classmethod
    def _get_pixmaps(cls):
        """Load the pixmap at first use"""
        if cls.ACTIVE_IMAGE_FILENAME is not None and cls._pixmap_active is None:
            cls._pixmap_active = QPixmap(Path(__file__).parent / cls.ACTIVE_IMAGE_FILENAME)
        if cls.IMAGE_FILENAME is not None and cls._pixmap is None:
            cls._pixmap = QPixmap(Path(__file__).parent / cls.IMAGE_FILENAME)

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self._get_pixmaps()
        xpos = self.size.width() / 2 - self._pixmap.width() / 2
        ypos = self.size.height() / 2 - self._pixmap.height() / 2
        self.paint_pixmap(
            painter, self.object_pos.x() + xpos, self.object_pos.y() + ypos, self.component.active
        )
        if self._show_name:
            self.paint_selectable_component_name(
                painter, self.object_pos, self.size, self.component.display_name()
            )

    @classmethod
    def paint_selectable_component(cls, painter, size, name):
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)
        cls._get_pixmaps()
        xpos = size.width() / 2 - cls._pixmap.width() / 2
        ypos = size.width() / 2 - cls._pixmap.height() / 2
        cls.paint_pixmap(painter, xpos, ypos)

    @classmethod
    def paint_pixmap(cls, painter, xpos, ypos, active=False):
        """Paint the pixmap"""
        pixmap = cls._pixmap_active if active and cls._pixmap_active is not None else cls._pixmap
        painter.drawPixmap(QPoint(xpos, ypos), pixmap)


class GateImageObject(ImageObject):
    """The base class for gate components placed in the GUI"""

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos)
        self.paint_port_names(False)


class ImageObjectAND(GateImageObject):
    """The class for a AND image component placed in the GUI"""

    IMAGE_FILENAME = "images/AND.png"


class ImageObjectOR(GateImageObject):
    """The class for a OR image component placed in the GUI"""

    IMAGE_FILENAME = "images/OR.png"


class ImageObjectNAND(GateImageObject):
    """The class for a NAND image component placed in the GUI"""

    IMAGE_FILENAME = "images/NAND.png"


class ImageObjectNOR(GateImageObject):
    """The class for a NOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/NOR.png"


class ImageObjectNOT(GateImageObject):
    """The class for a NOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/NOT.png"


class ImageObjectXOR(GateImageObject):
    """The class for a XOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/XOR.png"


class ImageObjectDFF(ImageObject):
    """The class for a DFF image component placed in the GUI"""

    IMAGE_FILENAME = "images/DFF.png"
    PORT_TO_IMAGE_DIST = 20

    def setup_size(self):
        self._get_pixmaps()
        str_pixels_w, _ = self.get_string_metrics("D")
        self.width = 2 * (str_pixels_w + self.PORT_TO_IMAGE_DIST) + self._pixmap.width()


class ImageObjectFlipFlop(ImageObject):
    """The class for a FlipFLop image component placed in the GUI"""

    IMAGE_FILENAME = "images/FlipFlop.png"
    PORT_TO_IMAGE_DIST = 20

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self.paint_component_name(painter)


class ImageObjectMUX(ImageObject):
    """The class for a MUX image component placed in the GUI"""

    IMAGE_FILENAME = "images/MUX.png"
    PORT_TO_IMAGE_DIST = 20

    def setup_size(self):
        self._get_pixmaps()
        if self.component.port("A").width == 1:
            str_pixels_w, _ = self.get_string_metrics("A")
        else:
            str_pixels_w, _ = self.get_string_metrics("A[31:0]")
        self.width = 2 * (str_pixels_w + self.PORT_TO_IMAGE_DIST) + self._pixmap.width()


class ImageObjectStaticValue(ImageObject):
    """The class for a StaticValue image component placed in the GUI"""

    IMAGE_FILENAME = "images/ZERO.png"
    ACTIVE_IMAGE_FILENAME = "images/ONE.png"

    _STATIC_VALUE_FONT = QFont("Arial", 16)

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos)
        self.show_name(False)

    def paint_component(self, painter):
        if self.component.O.width == 1:
            super().paint_component(painter)
        else:
            self.paint_component_base(painter)
            value_str = f"{self.component.parameter_get('value')}"
            str_w, str_h = self.get_string_metrics(value_str, font=self._STATIC_VALUE_FONT)
            painter.setFont(self._STATIC_VALUE_FONT)
            painter.drawText(
                self.rect().x() + self.rect().width() / 2 - str_w / 2,
                self.rect().y() + str_h,
                value_str,
            )


class ImageObjectLed(ImageObject):
    """The class for a Led image component placed in the GUI"""

    IMAGE_FILENAME = "images/LED_OFF.png"
    ACTIVE_IMAGE_FILENAME = "images/LED_ON.png"

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos)
        self.show_name(False)
        self.paint_port_names(False)


class ImageObjectIC(ImageObject):
    """The class for a Yosys image component placed in the GUI"""

    IMAGE_FILENAME = "images/IC.png"

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self.paint_component_name(painter)


class ImageObjectWithActiveRect(ImageObject):
    """
    A base class for a image component placed in the GUI.
    When active the image will have a green border painted around it.
    """

    _ACTIVE_RECT_PEN = QPen(Qt.green)

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos)
        self.show_name(False)
        self.paint_port_names(False)

    def paint_component(self, painter):
        super().paint_component(painter)
        if self.component.active:
            xpos = self.object_pos.x() + self.size.width() / 2 - self._pixmap.width() / 2
            ypos = self.object_pos.y() + self.size.height() / 2 - self._pixmap.height() / 2
            pen = self._ACTIVE_RECT_PEN
            pen.setWidth(4)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(xpos, ypos, self._pixmap.width(), self._pixmap.height(), 5, 5)


class ImageObjectClock(ImageObjectWithActiveRect):
    """The class for a Clock image component placed in the GUI"""

    IMAGE_FILENAME = "images/Clock.png"
