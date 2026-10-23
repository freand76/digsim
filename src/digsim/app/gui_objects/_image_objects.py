# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A component with an image as symbol the GUI"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPixmap

from digsim.circuit.components.atoms import Component

from . import _theme as theme
from ._component_object import ComponentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class ImageObject(ComponentObject):
    """The class for a image component placed in the GUI"""

    IMAGE_FILENAME: str | None = None
    ACTIVE_IMAGE_FILENAME: str | None = None
    # Draw the component's name on the image
    SHOW_NAME = True
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
        self.setup_size()
        self.update_ports()

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
        if self.SHOW_NAME:
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


class NamedBoxObject(ImageObject):
    """
    A base class for components drawn as a body with their name and port names, like an
    IC. The name is in a header above the ports. The image is not used.
    """

    BORDER_TO_PORT = 25

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        self.paint_component_name(painter)
        # The header
        painter.setPen(theme.ink_pen(1.0, theme.OFF))
        y = self.rect().top() + 16
        painter.drawLine(QPointF(self.rect().left() + 4, y), QPointF(self.rect().right() - 4, y))

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(size.width() / 2 - 22, 10, 44, 58)
        theme.paint_body(painter, rect)
        painter.setPen(theme.ink_pen(1.0, theme.OFF))
        painter.drawLine(
            QPointF(rect.left() + 4, rect.top() + 14), QPointF(rect.right() - 4, rect.top() + 14)
        )
        theme.paint_text(
            painter,
            QRectF(rect.left(), rect.top() + 1, rect.width(), 13),
            cls.ICON_TEXT,
            7,
            bold=True,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.INK)
        for row in range(3):
            y = rect.top() + 24 + 12 * row
            painter.drawEllipse(QPointF(rect.left() - 1, y), 2.5, 2.5)
            if row < 2:
                painter.drawEllipse(QPointF(rect.right(), y), 2.5, 2.5)
        painter.restore()
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)

    # The text in the header of the icon
    ICON_TEXT = ""


class ICObject(NamedBoxObject):
    """An IC placed in the GUI"""

    IMAGE_FILENAME = "images/IC.png"
    ICON_TEXT = "74xx"
