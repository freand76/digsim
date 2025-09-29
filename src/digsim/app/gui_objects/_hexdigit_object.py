# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A hexdigit component placed in the GUI"""

from ._component_object import ComponentObject
from ._seven_segment_object import SevenSegmentObject


class HexDigitObject(SevenSegmentObject):
    """The class for a hexdigit component placed in the GUI"""

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(
            app_model,
            component,
            xpos,
            ypos,
            port_distance=ComponentObject.DEFAULT_PORT_TO_PORT_DISTANCE,
        )

    def setup_size(self):
        """Setup the size of the component"""
        self.digits = self.component.get_digits()
        str_pixels_w, _ = self.get_string_metrics(f"val[{4 * self.digits - 1}:0]")
        self.digit_left = self.inport_x_pos() + str_pixels_w + self.PORT_TO_RECT_MARGIN
        self.digit_top = self.RECT_TO_DIGIT_RECT_MARGIN
        self.width = (
            self.digit_left + self.digits * self.DIGIT_WIDTH + self.RECT_TO_DIGIT_RECT_MARGIN
        )
        self.height = 2 * self.RECT_TO_DIGIT_RECT_MARGIN + self.DIGIT_HEIGHT
        self.update_ports()

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self.paint_digit_rect(
            painter,
            self.object_pos.x() + self.digit_left,
            self.object_pos.y() + self.RECT_TO_DIGIT_RECT_MARGIN,
            self.digits,
        )
        for digit_id in range(self.digits):
            active_segments = self.component.segments(digit_id)
            self.draw_digit(
                painter,
                self.object_pos.x() + self.digit_left + self.DIGIT_WIDTH * digit_id,
                self.object_pos.y() + self.digit_top,
                active_segments,
            )

    @classmethod
    def paint_selectable_component(cls, painter, size, name):
        cls.paint_selectable_digit(painter, size, name, "ABDEG")
