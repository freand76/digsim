# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from PySide6.QtCore import QPoint

from ._placed_seven_segment import PlacedSevenSegment


class PlacedHexDigit(PlacedSevenSegment):
    def __init__(self, component, xpos, ypos):
        super().__init__(component, xpos, ypos)
        _, str_pixels_w, _ = self.get_port_display_name_metrics("val")
        self.digit_left = self.inport_x_pos() + str_pixels_w + self.PORT_TO_RECT_MARGIN
        self.digits = self.component.get_digits()
        self._width = self.digit_left + self.digits * self.DIGIT_WIDTH + self.RECT_TO_DIGIT_MARGIN

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self.paint_digit_rect(painter)
        for digit_id in range(self.digits):
            active_segments = self.component.segments(digit_id)
            self.draw_digit(
                painter,
                QPoint(
                    self.digit_left + self.RECT_TO_DIGIT_MARGIN + self.DIGIT_WIDTH * digit_id, 20
                ),
                active_segments,
            )
