# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A Logic Analyzer component placed in the GUI"""

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainterPath, QPen

from ._image_objects import ImageObject


class LogicAnalyzerObject(ImageObject):
    """The class for a LogicAnalyzer component placed in the GUI"""

    IMAGE_FILENAME = "images/Analyzer.png"

    SIGNAL_NAME_WIDTH = 40
    ANALYZER_DISPLAY_WIDTH = 200

    _ANALYZER_PEN = QPen(Qt.green)
    _SIGNAL_VERTICAL_SCALE = 10
    _SIGNAL_HORIZONTAL_SCALE = 2

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos)
        self.width = self.SIGNAL_NAME_WIDTH + self.ANALYZER_DISPLAY_WIDTH + 2 * self.RECT_TO_BORDER
        self.update_ports()

    def paint_component(self, painter):
        self.paint_component_base(painter)
        painter.setBrush(Qt.SolidPattern)
        painter.setBrush(Qt.black)
        painter.drawRoundedRect(
            QRect(
                self.object_pos.x() + self.SIGNAL_NAME_WIDTH,
                self.object_pos.y() + 2 * self.RECT_TO_BORDER,
                self.ANALYZER_DISPLAY_WIDTH,
                self.height - 4 * self.RECT_TO_BORDER,
            ),
            5,
            5,
        )

        pen = self._ANALYZER_PEN
        pen.setWidth(2)
        painter.setPen(pen)
        signal_data_dict = self.component.signal_data()
        for portname, signal_data in signal_data_dict.items():
            signal_data = signal_data_dict[portname]
            port_pos = self.get_port_pos(portname)
            path = QPainterPath(
                QPoint(
                    self.object_pos.x() + self.SIGNAL_NAME_WIDTH,
                    port_pos.y() - signal_data[0] * self._SIGNAL_VERTICAL_SCALE,
                )
            )
            last_level = signal_data[0]
            for idx, level in enumerate(signal_data[1:]):
                if level == last_level:
                    continue
                path.lineTo(
                    QPoint(
                        self.object_pos.x()
                        + self.SIGNAL_NAME_WIDTH
                        + (idx + 1) * self._SIGNAL_HORIZONTAL_SCALE,
                        port_pos.y() - last_level * self._SIGNAL_VERTICAL_SCALE,
                    )
                )
                path.lineTo(
                    QPoint(
                        self.object_pos.x()
                        + self.SIGNAL_NAME_WIDTH
                        + (idx + 1) * self._SIGNAL_HORIZONTAL_SCALE,
                        port_pos.y() - level * self._SIGNAL_VERTICAL_SCALE,
                    )
                )
                last_level = level
            path.lineTo(
                QPoint(
                    self.object_pos.x()
                    + self.SIGNAL_NAME_WIDTH
                    + len(signal_data) * self._SIGNAL_HORIZONTAL_SCALE,
                    port_pos.y() - last_level * self._SIGNAL_VERTICAL_SCALE,
                )
            )
            painter.drawPath(path)
