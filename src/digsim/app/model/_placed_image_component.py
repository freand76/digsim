# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A component with an image as symbol the GUI """

import os

from PySide6.QtCore import QPoint
from PySide6.QtGui import QPixmap

from ._placed_component import PlacedComponent


class PlacedImageComponent(PlacedComponent):
    """The class for a image component placed in the GUI"""

    IMAGE_FILENAME = None
    _pixmap = None

    @classmethod
    def get_pixmap(cls):
        """Load the pixmap at first use"""
        if cls._pixmap is None:
            cls._pixmap = QPixmap(f"{os.path.dirname(__file__)}/{cls.IMAGE_FILENAME}")
            print("LOAD", cls._pixmap)

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self.get_pixmap()
        xpos = self.size.width() / 2 - self._pixmap.width() / 2
        ypos = self.size.height() / 2 - self._pixmap.height() / 2
        self.paint_pixmap(painter, xpos, ypos)
        self.paint_selectable_component_name(painter, self.size, self.component.display_name())

    @classmethod
    def paint_selectable_component(cls, painter, size, name):
        cls.paint_selectable_component_name(painter, size, name)
        cls.get_pixmap()
        xpos = size.width() / 2 - cls._pixmap.width() / 2
        ypos = size.width() / 2 - cls._pixmap.height() / 2
        cls.paint_pixmap(painter, xpos, ypos)

    @classmethod
    def paint_pixmap(cls, painter, xpos, ypos):
        """Paint the pixmap"""
        painter.drawPixmap(QPoint(xpos, ypos), cls._pixmap)


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
