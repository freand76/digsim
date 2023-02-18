# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A hexdigit component placed in the GUI """

from ._seven_segment_object import SevenSegmentObject


class HexDigitObject(SevenSegmentObject):
    """The class for a hexdigit component placed in the GUI"""

    def setup_size(self):
        """Setup the size of the component"""
        _, str_pixels_w, _ = self.get_port_display_name_metrics("val")
        self.digit_left = self.inport_x_pos() + str_pixels_w + self.PORT_TO_RECT_MARGIN
        self.digit_top = self.RECT_TO_DIGIT_RECT_MARGIN
        self.digits = self.component.get_digits()
        self._width = (
            self.digit_left + self.digits * self.DIGIT_WIDTH + self.DIGIT_RECT_TO_DIGIT_MARGIN
        )

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self.paint_digit_rect(
            painter, self.digit_left, self.RECT_TO_DIGIT_RECT_MARGIN, self.digits
        )
        for digit_id in range(self.digits):
            active_segments = self.component.segments(digit_id)
            self.draw_digit(
                painter,
                self.digit_left + self.DIGIT_WIDTH * digit_id,
                self.digit_top,
                active_segments,
            )

    @classmethod
    def paint_selectable_component(cls, painter, size, name):
        cls.paint_selectable_digit(painter, size, name, "ABDEG")
