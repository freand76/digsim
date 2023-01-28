# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" HexDigit component module """

from .atoms import CallbackComponent, PortIn


class HexDigit(CallbackComponent):
    """HexDigit component class"""

    VAL_TO_SEGMENTS = {
        0: "ABCDEF",
        1: "BC",
        2: "ABDEG",
        3: "ABCDG",
        4: "BCFG",
        5: "ACDFG",
        6: "ACDEFG",
        7: "ABC",
        8: "ABCDEFG",
        9: "ABCDFG",
        10: "ABCEFG",
        11: "CDEFG",
        12: "ADEF",
        13: "BCDEG",
        14: "ADEFG",
        15: "AEFG",
    }

    def __init__(self, circuit, name="HexDigit", digits=1, dot=True):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "val", width=(4 * digits)))
        self._digits = digits
        self._dot = dot
        if self._dot:
            self.add_port(PortIn(self, "dot"))

    def set_digits(self, digits):
        self._digits = digits
        self.val.width = digits * 4
        self.dot.width = digits

    def get_digits(self):
        return self._digits

    def value(self):
        return self.val.value

    def dot_active(self, digit_id=1):
        if not self._dot:
            return False
        if self.dot.value == "X":
            return False
        dot_value = self.dot.value >> (self.dot.width - (digit_id + 1)) & 1
        return dot_value == 1

    def segments(self, digit_id=0):
        if self.value() == "X":
            segments = ""
        else:
            digit_value = (self.value() >> (self.val.width - (digit_id + 1) * 4)) & 0xF
            segments = self.VAL_TO_SEGMENTS.get(digit_value, "")
        if self.dot_active(digit_id):
            segments += "."
        return segments

    def setup(self, digits=1):
        if digits is not None:
            self.set_digits(digits)

    def settings_to_dict(self):
        return {"digits": self._digits}
