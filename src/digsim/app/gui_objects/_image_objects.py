# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A component with an image as symbol the GUI"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QFont, QPainter, QPen, QPixmap

from digsim.circuit.components.atoms import Component

from ._component_object import ComponentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class ImageObject(ComponentObject):
    """The class for a image component placed in the GUI"""

    IMAGE_FILENAME: str | None = None
    ACTIVE_IMAGE_FILENAME: str | None = None
    _pixmap: QPixmap | None = None
    _pixmap_active: QPixmap | None = None

    def __init__(
        self,
        app_model: AppModel,
        component: Component,
        xpos: float,
        ypos: float,
        port_distance: int = ComponentObject.DEFAULT_PORT_TO_PORT_DISTANCE,
    ) -> None:
        super().__init__(app_model, component, xpos, ypos, port_distance=port_distance)
        self._show_name = True
        self.setup_size()
        self.update_ports()

    def show_name(self, enable: bool) -> None:
        """Enable/Disable name on image component"""
        self._show_name = enable

    def setup_size(self) -> None:
        """Change size of component"""

    @classmethod
    def _get_pixmaps(cls) -> None:
        """
        Load the pixmaps at first use. Each class loads its own: a subclass with another
        image must not use the pixmap that its base class has already loaded.
        """
        if cls.ACTIVE_IMAGE_FILENAME is not None and "_pixmap_active" not in cls.__dict__:
            cls._pixmap_active = QPixmap(Path(__file__).parent / cls.ACTIVE_IMAGE_FILENAME)
        if cls.IMAGE_FILENAME is not None and "_pixmap" not in cls.__dict__:
            cls._pixmap = QPixmap(Path(__file__).parent / cls.IMAGE_FILENAME)

    @classmethod
    def _image(cls) -> QPixmap:
        """Get the (inactive) pixmap, loading it at first use"""
        cls._get_pixmaps()
        assert cls._pixmap is not None
        return cls._pixmap

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        xpos = self.size.width() / 2 - self._image().width() / 2
        ypos = self.size.height() / 2 - self._image().height() / 2
        self.paint_pixmap(
            painter, self.object_pos.x() + xpos, self.object_pos.y() + ypos, self.component.active
        )
        if self._show_name:
            self.paint_selectable_component_name(
                painter, self.object_pos, self.size, self.component.display_name()
            )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)
        cls._get_pixmaps()
        xpos = size.width() / 2 - cls._image().width() / 2
        ypos = size.width() / 2 - cls._image().height() / 2
        cls.paint_pixmap(painter, xpos, ypos)

    @classmethod
    def paint_pixmap(
        cls, painter: QPainter, xpos: float, ypos: float, active: bool = False
    ) -> None:
        """Paint the pixmap"""
        pixmap = cls._pixmap_active if active and cls._pixmap_active is not None else cls._image()
        painter.drawPixmap(QPoint(int(xpos), int(ypos)), pixmap)


class GateImageObject(ImageObject):
    """The base class for gate components placed in the GUI"""

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
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
    """The class for a NOT image component placed in the GUI"""

    IMAGE_FILENAME = "images/NOT.png"


class ImageObjectXNOR(GateImageObject):
    """The class for a XNOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/XNOR.png"


class ImageObjectXOR(GateImageObject):
    """The class for a XOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/XOR.png"


class ImageObjectDFF(ImageObject):
    """The class for a DFF image component placed in the GUI"""

    IMAGE_FILENAME = "images/DFF.png"
    PORT_TO_IMAGE_DIST = 20

    def setup_size(self) -> None:
        self._get_pixmaps()
        str_pixels_w, _ = self.get_string_metrics("D")
        self.width = 2 * (str_pixels_w + self.PORT_TO_IMAGE_DIST) + self._image().width()


class ImageObjectFlipFlop(ImageObject):
    """The class for a flip-flop image component placed in the GUI"""

    IMAGE_FILENAME = "images/FlipFlop.png"
    PORT_TO_IMAGE_DIST = 20

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        self.paint_component_name(painter)


class ImageObjectMUX(ImageObject):
    """The class for a MUX image component placed in the GUI"""

    IMAGE_FILENAME = "images/MUX.png"
    PORT_TO_IMAGE_DIST = 20

    def setup_size(self) -> None:
        self._get_pixmaps()
        if self.component.port("A").width == 1:
            str_pixels_w, _ = self.get_string_metrics("A")
        else:
            str_pixels_w, _ = self.get_string_metrics("A[31:0]")
        self.width = 2 * (str_pixels_w + self.PORT_TO_IMAGE_DIST) + self._image().width()


class ImageObjectStaticValue(ImageObject):
    """The class for a StaticValue image component placed in the GUI"""

    IMAGE_FILENAME = "images/ZERO.png"
    ACTIVE_IMAGE_FILENAME = "images/ONE.png"

    _STATIC_VALUE_FONT = QFont("Arial", 16)

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.show_name(False)

    def paint_component(self, painter: QPainter) -> None:
        if self.component.O.width == 1:
            super().paint_component(painter)
        else:
            self.paint_component_base(painter)
            value_str = f"{self.component.parameter_get('value')}"
            str_w, str_h = self.get_string_metrics(value_str, font=self._STATIC_VALUE_FONT)
            painter.setFont(self._STATIC_VALUE_FONT)
            painter.drawText(
                int(self.rect().x() + self.rect().width() / 2 - str_w / 2),
                int(self.rect().y() + str_h),
                value_str,
            )


class ImageObjectLed(ImageObject):
    """The class for a Led image component placed in the GUI"""

    IMAGE_FILENAME = "images/LED_OFF.png"
    ACTIVE_IMAGE_FILENAME = "images/LED_ON.png"

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.show_name(False)
        self.paint_port_names(False)


class ImageObjectIC(ImageObject):
    """The class for an IC image component placed in the GUI"""

    IMAGE_FILENAME = "images/IC.png"

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        self.paint_component_name(painter)


class ImageObjectWithActiveRect(ImageObject):
    """
    A base class for a image component placed in the GUI.
    When active the image will have a green border painted around it.
    """

    _ACTIVE_RECT_PEN = QPen(Qt.GlobalColor.green)

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.show_name(False)
        self.paint_port_names(False)

    def paint_component(self, painter: QPainter) -> None:
        super().paint_component(painter)
        if self.component.active:
            xpos = self.object_pos.x() + self.size.width() / 2 - self._image().width() / 2
            ypos = self.object_pos.y() + self.size.height() / 2 - self._image().height() / 2
            # A copy: the class pen is shared by all instances
            pen = QPen(self._ACTIVE_RECT_PEN)
            pen.setWidth(4)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                int(xpos), int(ypos), self._image().width(), self._image().height(), 5, 5
            )


class ImageObjectClock(ImageObjectWithActiveRect):
    """The class for a Clock image component placed in the GUI"""

    IMAGE_FILENAME = "images/Clock.png"
