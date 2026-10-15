# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A Logic Analyzer component placed in the GUI"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen

from digsim.circuit.components import LogicAnalyzer
from digsim.circuit.components.atoms import Component

from ._image_objects import ImageObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class LogicAnalyzerObject(ImageObject):
    """The class for a LogicAnalyzer component placed in the GUI"""

    IMAGE_FILENAME = "images/Analyzer.png"

    SIGNAL_NAME_WIDTH = 40
    ANALYZER_DISPLAY_WIDTH = 200

    _ANALYZER_PEN = QPen(Qt.GlobalColor.green)
    _SIGNAL_VERTICAL_SCALE = 10
    _SIGNAL_HORIZONTAL_SCALE = 2

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.width = self.SIGNAL_NAME_WIDTH + self.ANALYZER_DISPLAY_WIDTH + 2 * self.RECT_TO_BORDER
        self.update_ports()

    @property
    def component(self) -> LogicAnalyzer:
        component = self._component
        assert isinstance(component, LogicAnalyzer)
        return component

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        painter.setBrush(Qt.GlobalColor.black)
        painter.drawRoundedRect(
            QRect(
                int(self.object_pos.x() + self.SIGNAL_NAME_WIDTH),
                int(self.object_pos.y() + 2 * self.RECT_TO_BORDER),
                self.ANALYZER_DISPLAY_WIDTH,
                int(self.height - 4 * self.RECT_TO_BORDER),
            ),
            5,
            5,
        )

        # A copy: the class pen is shared by all instances
        pen = QPen(self._ANALYZER_PEN)
        pen.setWidth(2)
        painter.setPen(pen)
        signal_data_dict = self.component.signal_data()
        for portname, signal_data in signal_data_dict.items():
            signal_data = signal_data_dict[portname]
            port_pos = self.get_port_pos(portname)
            path = QPainterPath(
                QPoint(
                    int(self.object_pos.x() + self.SIGNAL_NAME_WIDTH),
                    int(port_pos.y() - signal_data[0] * self._SIGNAL_VERTICAL_SCALE),
                )
            )
            last_level = signal_data[0]
            for idx, level in enumerate(signal_data[1:]):
                if level == last_level:
                    continue
                path.lineTo(
                    QPoint(
                        int(
                            self.object_pos.x()
                            + self.SIGNAL_NAME_WIDTH
                            + (idx + 1) * self._SIGNAL_HORIZONTAL_SCALE
                        ),
                        int(port_pos.y() - last_level * self._SIGNAL_VERTICAL_SCALE),
                    )
                )
                path.lineTo(
                    QPoint(
                        int(
                            self.object_pos.x()
                            + self.SIGNAL_NAME_WIDTH
                            + (idx + 1) * self._SIGNAL_HORIZONTAL_SCALE
                        ),
                        int(port_pos.y() - level * self._SIGNAL_VERTICAL_SCALE),
                    )
                )
                last_level = level
            path.lineTo(
                QPoint(
                    int(
                        self.object_pos.x()
                        + self.SIGNAL_NAME_WIDTH
                        + len(signal_data) * self._SIGNAL_HORIZONTAL_SCALE
                    ),
                    int(port_pos.y() - last_level * self._SIGNAL_VERTICAL_SCALE),
                )
            )
            painter.drawPath(path)
